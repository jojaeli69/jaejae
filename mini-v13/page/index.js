// Zepp OS 1.0: battery percent CHANGE is available only while Device App runs.
// There is no documented charger-cable state and no background App Service.
// UP/DOWN are percent trends, not verified charging/discharging flags.
const POLL_MS=30000
const HEARTBEAT_TICKS=4
// Zepp OS 1.0 sensors fire only while the watch Device App stays alive.
Page({
  onInit(){
    this.battery=null
    this.active=false
    this.busy=false
    this.queued=false
    this.retryPending=false
    this.ticks=0
    this.poller=0
    this.observed=-1
    this.lastSent=-1
    this.trend='UNKNOWN'
    this.lastSensorCallback=null
    try{this.battery=hmSensor.createSensor(hmSensor.id.BATTERY)}
    catch(e){console.log('Battery init failed '+String(e))}
  },
  build(){
    this.active=true
    this.bridge=getApp()._options.globalData.messageBuilder
    const level=this.batteryLevel()
    this.observed=level
    hmUI.createWidget(hmUI.widget.TEXT,{x:14,y:29,w:308,h:54,text:'Mini BatteryLink v1.7',color:0xffffff,text_size:27,align_h:hmUI.align.CENTER_H})
    this.levelText=hmUI.createWidget(hmUI.widget.TEXT,{x:14,y:95,w:308,h:80,text:level<0?'--%':level+'%',color:0x70db9d,text_size:66,align_h:hmUI.align.CENTER_H})
    this.note=hmUI.createWidget(hmUI.widget.TEXT,{x:10,y:182,w:316,h:54,text:'AUTO CHANGE ACTIVE',color:0xd4e0e8,text_size:18,align_h:hmUI.align.CENTER_H})
    hmUI.createWidget(hmUI.widget.BUTTON,{x:22,y:244,w:292,h:52,text:'1 TEST ZEPP',normal_color:0x294d74,press_color:0x1b334d,color:0xffffff,text_size:23,radius:9,click_func:()=>this.ping()})
    hmUI.createWidget(hmUI.widget.BUTTON,{x:22,y:310,w:292,h:52,text:'2 SEND BATTERY',normal_color:0x287e4c,press_color:0x195c35,color:0xffffff,text_size:23,radius:9,click_func:()=>this.report('MANUAL')})
    if(!this.bridge){this.status('NO ZEPP BRIDGE');return}
    // The sensor callback is the fastest documented Zepp OS 1.0 path.
    this.lastSensorCallback=()=>this.checkChange('EVENT')
    try{this.battery.addEventListener(hmSensor.event.CHANGE,this.lastSensorCallback)}
    catch(e){console.log('BATTERY CHANGE callback unavailable '+String(e))}
    // Fallback poll when a firmware CHANGE event is missed (while page is open).
    try{this.poller=timer.createTimer(3000,POLL_MS,()=>{
      this.ticks++
      this.checkChange('POLL')
      // Retry a lost phone delivery on next poll without recursively hammering Zepp.
      if(this.retryPending && this.active && !this.busy) {
        this.retryPending=false
        this.report('RETRY')
      } else if(this.ticks%HEARTBEAT_TICKS===0 && this.active && !this.busy) this.report('HEARTBEAT')
    },{})}catch(e){this.status('POLL TIMER ERROR')}
    // Send the initial battery automatically; no manual tapping is required.
    this.report('OPEN')
  },
  batteryLevel(){
    try{const value=Number(this.battery.current);return Number.isInteger(value)&&value>=0&&value<=100?value:-1}
    catch(e){return -1}
  },
  status(value){
    if(this.note&&this.active)this.note.setProperty(hmUI.prop.MORE,{text:String(value).slice(0,42)})
  },
  checkChange(source){
    if(!this.active)return
    const n=this.batteryLevel()
    if(n<0)return
    if(this.levelText)this.levelText.setProperty(hmUI.prop.MORE,{text:n+'%'})
    if(this.observed<0){this.observed=n;this.report('INITIAL');return}
    if(n===this.observed)return
    const old=this.observed
    this.observed=n
    this.trend=n>old?'UP':'DOWN'
    this.status((this.trend==='UP'?'INCREASE ':'DECREASE ')+old+'->'+n+'%')
    // Every observed 1%-step gets sent. Queue latest if an earlier HTTP request
    // is still running, then flush on ACK or timeout; never parallelize requests.
    if(this.busy){this.queued=true;return}
    this.report('CHANGE')
  },
  request(payload,kind){
    if(!this.bridge){this.status('BRIDGE NOT READY');return}
    if(this.busy){if(kind==='BATTERY')this.queued=true;return}
    this.busy=true
    if(kind==='PING')this.status('TESTING ZEPP LINK')
    else this.status('SENDING '+String(payload.level)+'% '+String(payload.trend))
    const after=()=>{
      this.busy=false
      if(this.active&&this.queued) {
        this.queued=false
        this.report('QUEUED')
      }
    }
    try{
      this.bridge.request(payload,{timeout:12000}).then(raw=>{
        if(!this.active)return
        const res=raw&&raw.data&&raw.ok===undefined?raw.data:raw
        if(kind==='PING')
          this.status(res&&res.ok===true&&res.step==='ZEPP'?'ZEPP LINK SUCCESS':'ZEPP BAD RESPONSE')
        else if(res&&res.ok===true&&res.step==='PHONE') {
          this.lastSent=payload.level
          this.retryPending=false
          if(res.widgetPublished===true && Number(res.widgetCount)>0)
            this.status('WIDGET UPDATED '+payload.level+'%')
          else if(Number(res.widgetCount)===0)
            this.status('NO HOME WIDGET ('+payload.level+'%)')
          else
            this.status('TRIO SAVED; CHECK WIDGET')
        } else if(res&&res.step==='PHONE') {
          this.retryPending=true
          this.status(res.route==='wrong-app'?'MINI COMPANION CONFLICT':'PHONE RECEIVER OFF')
        }
        else this.status('ZEPP RESPONSE ERROR')
        after()
      }).catch(e=>{
        if(!this.active)return
        console.log('Mini '+kind+' request error '+String(e))
        if(kind==='BATTERY')this.retryPending=true
        this.status(String(e).toLowerCase().includes('time')?'NO ZEPP RESPONSE':'ZEPP BRIDGE ERROR')
        after()
      })
    }catch(e){
      console.log('Mini synchronous request '+String(e))
      if(kind==='BATTERY')this.retryPending=true
      this.status('REQUEST START ERROR')
      after()
    }
  },
  ping(){this.request({method:'PING'},'PING')},
  report(source){
    const level=this.batteryLevel()
    if(level<0){this.status('BATTERY SENSOR ERROR');return}
    if(this.observed>=0 && level!==this.observed) {
      this.trend=level>this.observed?'UP':'DOWN'
      this.observed=level
    }
    if(this.levelText)this.levelText.setProperty(hmUI.prop.MORE,{text:level+'%'})
    this.request({method:'BATTERY',level,trend:this.trend},'BATTERY')
  },
  onDestroy(){
    this.active=false
    this.queued=false
    this.retryPending=false
    if(this.poller)try{timer.stopTimer(this.poller)}catch(e){}
    if(this.lastSensorCallback&&this.battery){
      try{this.battery.removeEventListener(hmSensor.event.CHANGE,this.lastSensorCallback)}catch(e){}
    }
  }
})
