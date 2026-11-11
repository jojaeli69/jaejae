import {encode,decode,valid,levelOK,msg} from '../shared/protocol.js'
const PERIOD=15*60*1000
Page({
  onInit() {
    this.live=true;this.seq=0;this.pending=0;this.awaiting='';this.note='INIT'
    this.lastSent=-1;this.battery=null;this.tick=0;this.started=0;this.timeout=0
    try{this.battery=hmSensor.createSensor(hmSensor.id.BATTERY)}
    catch(e){this.note='BATTERY INIT ERROR'}
    try{
      hmBle.createConnect((index,data,length)=>this.onMessage(data,length))
      hmBle.addListener(connected=>{
        if(!this.live)return
        if(connected){this.show('ZEPP LINK READY');this.ping()}
        else this.show('ZEPP BLE DISCONNECTED')
      })
    }catch(e){this.note='BLE INIT ERROR';console.log('BLE init',String(e))}
  },
  build() {
    const level=this.level()
    hmUI.createWidget(hmUI.widget.TEXT,{x:10,y:40,w:316,h:50,text:'GTS 4 Mini',color:0xffffff,text_size:29,align_h:hmUI.align.CENTER_H})
    this.levelText=hmUI.createWidget(hmUI.widget.TEXT,{x:10,y:95,w:316,h:78,text:level<0?'--%':level+'%',color:0x43d18a,text_size:65,align_h:hmUI.align.CENTER_H})
    this.statusText=hmUI.createWidget(hmUI.widget.TEXT,{x:8,y:182,w:320,h:48,text:this.note,color:0xffffff,text_size:18,align_h:hmUI.align.CENTER_H})
    hmUI.createWidget(hmUI.widget.BUTTON,{x:26,y:238,w:284,h:56,text:'1  TEST ZEPP',normal_color:0x284e78,press_color:0x1a334f,color:0xffffff,text_size:23,radius:11,click_func:()=>this.ping()})
    hmUI.createWidget(hmUI.widget.BUTTON,{x:26,y:306,w:284,h:56,text:'2  SEND BATTERY',normal_color:0x238049,press_color:0x165232,color:0xffffff,text_size:23,radius:11,click_func:()=>this.sendBattery()})
    try{this.battery.addEventListener(hmSensor.event.CHANGE,()=>this.onChange())}catch(e){}
    try{this.tick=timer.createTimer(PERIOD,PERIOD,()=>this.sendBattery(),{})}catch(e){this.show('TIMER NOT SUPPORTED')}
    try{this.started=timer.createTimer(2000,3600000,()=>{
      try{timer.stopTimer(this.started)}catch(e){}this.started=0;this.ping()
    },{})}catch(e){this.show('TIMER ERROR')}
  },
  show(s){this.note=String(s).slice(0,40);if(this.live&&this.statusText)this.statusText.setProperty(hmUI.prop.MORE,{text:this.note})},
  level(){try{const n=Number(this.battery.current);return levelOK(n)?n:-1}catch(e){return -1}},
  onChange(){
    const n=this.level();if(this.live&&this.levelText)this.levelText.setProperty(hmUI.prop.MORE,{text:n<0?'--%':n+'%'})
    if(n>=0&&n!==this.lastSent&&this.pending===0)this.sendBattery()
  },
  sendPacket(data,kind){
    if(!this.live)return
    if(this.pending){this.show('WAIT '+this.awaiting);return}
    try{if(!hmBle.connectStatus()){this.show('BLE NOT CONNECTED');return}}catch(e){this.show('BLE STATUS ERROR');return}
    const id=++this.seq;this.pending=id;this.awaiting=kind
    try{
      const b=encode(msg(kind,id,data))
      hmBle.send(b,b.byteLength)
      this.show(kind==='ping'?'TESTING ZEPP...':'SENDING TO ZEPP...')
      this.timeout=timer.createTimer(9000,3600000,()=>{
        if(this.pending!==id||!this.live)return
        this.pending=0;this.show(kind==='ping'?'NO ZEPP ACK':'NO PHONE ACK')
        try{timer.stopTimer(this.timeout)}catch(e){}this.timeout=0
      },{})
    }catch(e){this.pending=0;this.show('BLE SEND ERROR');console.log('Mini BLE send '+String(e))}
  },
  ping(){this.sendPacket({},'ping')},
  sendBattery(){
    const level=this.level()
    if(level<0){this.show('BATTERY SENSOR ERROR');return}
    this.lastSent=level;this.sendPacket({level},'battery')
  },
  onMessage(raw,length){
    if(!this.live)return
    let ack;try{ack=decode(raw,length)}catch(e){return}
    if(!valid(ack)||ack.kind!=='ack'||ack.id!==this.pending)return
    const was=this.awaiting;this.pending=0
    if(this.timeout){try{timer.stopTimer(this.timeout)}catch(e){}this.timeout=0}
    if(was==='ping')this.show(ack.stage==='zepp'&&ack.ok===true?'ZEPP LINK SUCCESS':'ZEPP ACK ERROR')
    else if(ack.stage==='stored'&&ack.ok===true)this.show('PHONE SAVED: '+ack.route)
    else if(ack.stage==='stored')this.show('PHONE SERVER OFF')
    else this.show('SIDE ERROR: '+String(ack.stage))
  },
  onDestroy(){
    this.live=false
    for(const k of ['tick','started','timeout'])if(this[k]){try{timer.stopTimer(this[k])}catch(e){}}
    try{hmBle.removeListener()}catch(e){}
    try{hmBle.disConnect()}catch(e){}
  }
})
