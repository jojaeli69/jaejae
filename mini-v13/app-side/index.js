import {MessageBuilder} from '../shared/message'
const builder=new MessageBuilder()
function receiveAck(response){
  if(!response)return {ok:false,widgetCount:0,widgetPublished:false}
  let body=response.body
  if(typeof body==='string') {
    try{body=JSON.parse(body)}catch(e){return {ok:false}}
  }
  if(body instanceof ArrayBuffer) {
    try{
      const bytes=new Uint8Array(body);let json=''
      for(let i=0;i<bytes.length;i++)json+=String.fromCharCode(bytes[i])
      body=JSON.parse(json)
    }catch(e){return {ok:false}}
  }
  if(body&&body.data&&body.stored===undefined)body=body.data
  const status=Number(response.status||response.statusCode||response.code||200)
  const ok=status>=200&&status<300&&!!body&&body.stored===true&&body.receiver==='BatteryTrioMini'
  return {
    ok,
    widgetCount:body?Math.max(0,Number(body.widget_count)||0):0,
    widgetPublished:!!body&&body.widget_published===true
  }
}
function sendToPhone(level,trend) {
  // ONLY the integrated Battery Trio is allowed to ACK. Never fall back
  // to 18973 (the old BatteryLink port) or an older Mini Companion.
  const validTrend=trend==='UP'||trend==='DOWN'?trend:'UNKNOWN'
  const url='http://127.0.0.1:18974/?postData=GTS4MINIBAT%3A'+level+'%3BTREND%3A'+validTrend+'%3B'
  return fetch({url,method:'GET'}).then(response=>{
    const ack=receiveAck(response)
    if(ack.ok)return {ok:true,route:'trio-v67',widgetCount:ack.widgetCount,widgetPublished:ack.widgetPublished}
    console.log('BatteryTrio v67 did not ACK (wrong receiver or invalid response)')
    return {ok:false,route:'wrong-app'}
  }).catch(error=>{
    console.log('Battery Trio Mini receiver 18974 unavailable '+String(error))
    return {ok:false,route:'off'}
  })
}
AppSideService({
  onInit() {
    console.log('Mini side service v1.7 widget ACK')
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
        sendToPhone(n,req.trend).then(r=>reply({ok:r.ok,step:'PHONE',route:r.route})).catch(e=>{
          console.log('Mini phone relay failed '+String(e))
          reply({ok:false,step:'HTTP_ERROR',route:'none'})
        })
      } else reply({ok:false,step:'UNKNOWN_METHOD'})
    })
  },
  onRun(){},
  onDestroy(){}
})
