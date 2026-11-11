const PERIOD=15*60*1000
Page({
  onInit(){
    this.ready=false
    this.battery=null
    this.last=-1
    this.poller=0
    this.active=false
    this.busy=false
    try{this.battery=hmSensor.createSensor(hmSensor.id.BATTERY)}catch(e){}
  },
  build(){
    this.active=true
    this.bridge=getApp()._options.globalData.messageBuilder
    const level=this.batteryLevel()
    hmUI.createWidget(hmUI.widget.TEXT,{x:14,y:29,w:308,h:54,text:'Mini BatteryLink v1.4',color:0xffffff,text_size:27,align_h:hmUI.align.CENTER_H})
    this.levelText=hmUI.createWidget(hmUI.widget.TEXT,{x:14,y:95,w:308,h:80,text:level<0?'--%':level+'%',color:0x70db9d,text_size:66,align_h:hmUI.align.CENTER_H})
    this.note=hmUI.createWidget(hmUI.widget.TEXT,{x:10,y:183,w:316,h:50,text:'TEST ZEPP FIRST',color:0xd4e0e8,text_size:18,align_h:hmUI.align.CENTER_H})
    hmUI.createWidget(hmUI.widget.BUTTON,{x:22,y:244,w:292,h:52,text:'1 TEST ZEPP',normal_color:0x294d74,press_color:0x1b334d,color:0xffffff,text_size:23,radius:9,click_func:()=>this.ping()})
    hmUI.createWidget(hmUI.widget.BUTTON,{x:22,y:310,w:292,h:52,text:'2 SEND BATTERY',normal_color:0x287e4c,press_color:0x195c35,color:0xffffff,text_size:23,radius:9,click_func:()=>this.report()})
    if(!this.bridge){this.status('NO ZEPPOSE BRIDGE');return}
    try{this.poller=timer.createTimer(PERIOD,PERIOD,()=>this.report(),{})}catch(e){}
  },
  batteryLevel(){
    try{const value=Number(this.battery.current);return Number.isInteger(value)&&value>=0&&value<=100?value:-1}
    catch(e){return -1}
  },
  status(text){
    if(this.note&&this.active)this.note.setProperty(hmUI.prop.MORE,{text:String(text).slice(0,42)})
  },
  request(payload,kind){
    if(!this.bridge){this.status('BRIDGE NOT READY');return}
    if(this.busy){this.status('WAITING FOR LAST REQUEST');return}
    this.busy=true
    this.status(kind==='PING'?'TESTING ZEPPOSE LINK':'SENDING TO ZEPPOSE')
    try{
      this.bridge.request(payload,{timeout:12000}).then(raw=>{
        if(!this.active)return
        this.busy=false
        // Official samples may return the payload directly or wrap it.
        const res=raw&&raw.data&&raw.ok===undefined?raw.data:raw
        if(kind==='PING')
          this.status(res&&res.ok===true&&res.step==='ZEPP'?'ZEPP LINK SUCCESS':'ZEPPOSE BAD RESPONSE')
        else if(res&&res.ok===true&&res.step==='PHONE')
          this.status('PHONE SAVED: '+String(res.route||'mini'))
        else if(res&&res.step==='PHONE')
          this.status('PHONE RECEIVER OFF')
        else this.status('ZEPPOSE RESPONSE ERROR')
      }).catch(e=>{
        if(!this.active)return
        this.busy=false
        console.log('Mini '+kind+' request failed '+String(e))
        this.status(String(e).toLowerCase().includes('time')?'NO ZEPP RESPONSE':'ZEPPOSE BRIDGE ERROR')
      })
    }catch(e){this.busy=false;console.log('Mini bridge error '+String(e));this.status('REQUEST START ERROR')}
  },
  ping(){this.request({method:'PING'},'PING')},
  report(){
    const n=this.batteryLevel()
    if(n<0){this.status('BATTERY SENSOR ERROR');return}
    this.last=n
    if(this.levelText)this.levelText.setProperty(hmUI.prop.MORE,{text:n+'%'})
    this.request({method:'BATTERY',level:n},'BATTERY')
  },
  onDestroy(){
    this.active=false
    if(this.poller)try{timer.stopTimer(this.poller)}catch(e){}
  }
})
