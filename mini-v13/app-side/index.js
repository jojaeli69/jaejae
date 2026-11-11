import {MessageBuilder} from '../shared/message'
const builder=new MessageBuilder()
function savedResponse(response){
  if(!response)return false
  let body=response.body
  if(typeof body==='string'){try{body=JSON.parse(body)}catch(e){return false}}
  if(body instanceof ArrayBuffer){try{
    const b=new Uint8Array(body);let s='';for(let i=0;i<b.length;i++)s+=String.fromCharCode(b[i]);body=JSON.parse(s)
  }catch(e){return false}}
  if(body&&body.data&&body.stored===undefined)body=body.data
  const code=Number(response.status||response.statusCode||response.code||200)
  return code>=200&&code<300&&!!body&&body.stored===true
}
function sendToPhone(level) {
  // Keep the existing BatteryLink app unchanged: use the separate Mini companion.
  const ports=[18974,18973]
  function next(i){
    if(i>=ports.length)return Promise.resolve({ok:false,route:'none'})
    const url='http://127.0.0.1:'+ports[i]+'/?postData=GTS4MINIBAT%3A'+level+'%3B'
    return fetch({url,method:'GET'}).then(res=>{
      if(savedResponse(res))return {ok:true,route:ports[i]===18974?'mini':'v45'}
      return next(i+1)
    }).catch(e=>{
      console.log('Mini phone receiver '+ports[i]+' unavailable: '+String(e))
      return next(i+1)
    })
  }
  return next(0)
}
AppSideService({
  onInit() {
    console.log('Mini side service v1.4 boot')
    builder.listen(()=>{})
    builder.on('request',(ctx)=>{
      let req
      try {req=builder.buf2Json(ctx.request.payload)}
      catch(e){console.log('Mini invalid request '+String(e));return}
      const reply=(data)=>{
        try {ctx.response({data})}
        catch(e){console.log('Mini reply error: '+String(e))}
      }
      if(!req||typeof req!=='object')return reply({ok:false,step:'INVALID'})
      if(req.method==='PING') {
        // This must be returned even when Android mini companion is not running.
        reply({ok:true,step:'ZEPP',protocol:'MessageBuilder'})
      } else if(req.method==='BATTERY') {
        const n=Number(req.level)
        if(!Number.isInteger(n)||n<0||n>100)return reply({ok:false,step:'INVALID_LEVEL'})
        sendToPhone(n).then(r=>reply({ok:r.ok,step:'PHONE',route:r.route})).catch(e=>{
          console.log('Mini phone relay failed '+String(e))
          reply({ok:false,step:'HTTP_ERROR',route:'none'})
        })
      } else reply({ok:false,step:'UNKNOWN_METHOD'})
    })
  },
  onRun(){},
  onDestroy(){}
})
