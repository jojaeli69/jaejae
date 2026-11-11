import {encode,decode,valid,levelOK,msg,endpoint,storedBody} from '../shared/protocol.js'
function save(level) {
  // Existing BatteryLink v44 doesn't recognize the Mini tag.
  // Prefer standalone Mini receiver on :18974, then optional upgraded v45 on :18973.
  function attempt(port) {
    return fetch({url:endpoint(level,port),method:'GET'}).then(storedBody).catch(e => {
      console.log('Mini receiver port '+port+' unavailable: '+String(e))
      return false
    })
  }
  return attempt(18974).then(ok => ok ? {stored:true,route:'mini'} :
    attempt(18973).then(ok2 => ({stored:!!ok2,route:ok2?'v45':'none'})))
}
AppSideService({
  onInit() {
    this.active=true
    this.handler=(buffer)=>{
      let p;try{p=decode(buffer)}catch(e){return}
      if(!valid(p))return
      const ack=(stage,ok=false,route='none')=>{
        if(!this.active)return
        try{messaging.peerSocket.send(encode(msg('ack',p.id,{stage,ok,route})))}
        catch(e){console.log('Zepp Mini ack error',String(e))}
      }
      if(p.kind==='ping') {
        console.log('Mini test: Zepp BLE route working')
        ack('zepp',true,'zepp')
        return
      }
      if(p.kind!=='battery'||!levelOK(p.level)) {ack('invalid',false);return}
      // A phone acknowledgment MUST mean the battery was actually saved.
      // This is not merely a Bluetooth-received acknowledgment.
      save(p.level).then(r=>{
        console.log('Mini battery '+p.level+' saved='+r.stored+' route='+r.route)
        ack('stored',r.stored,r.route)
      }).catch(e=>{console.log('Mini unexpected relay error',String(e));ack('http-error',false)})
    }
    messaging.peerSocket.addListener('message',this.handler)
    console.log('Zepp Mini side service ready')
  },
  onRun(){},
  onDestroy(){
    this.active=false
    try{messaging.peerSocket.removeListener('message',this.handler)}catch(e){}
  }
})
