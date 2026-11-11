// BatteryLink GTS 4 Mini: versioned, bounded binary JSON over Zepp OS 1.0 hmBle.
export function levelOK(n) { return Number.isInteger(n) && n >= 0 && n <= 100 }
export function msg(kind, id, extra={}) {
  if (!Number.isInteger(id) || id < 1 || id > 2147483647) throw new Error('invalid id')
  return Object.assign({bl:2,kind,device:'gts4mini',id},extra)
}
export function encode(x) {
  const t=JSON.stringify(x)
  if (t.length > 220) throw new Error('oversize payload')
  const b=new Uint8Array(t.length)
  for (let i=0;i<t.length;i++) {
    const ch=t.charCodeAt(i)
    if (ch>127) throw new Error('non-ASCII packet')
    b[i]=ch
  }
  return b.buffer
}
export function decode(raw,size) {
  let b
  if (raw instanceof ArrayBuffer) b=new Uint8Array(raw)
  else if (raw instanceof Uint8Array) b=raw
  else if (raw && raw.buffer instanceof ArrayBuffer) b=new Uint8Array(raw.buffer,raw.byteOffset||0,raw.byteLength||raw.buffer.byteLength)
  else throw new Error('invalid payload')
  if (Number.isInteger(size) && size>=0 && size <= b.length) b=b.subarray(0,size)
  if (b.length===0 || b.length>220) throw new Error('packet size')
  let t='';for(let i=0;i<b.length;i++) t+=String.fromCharCode(b[i])
  return JSON.parse(t)
}
export function valid(x) {
  return !!x && x.bl===2 && x.device==='gts4mini' && Number.isInteger(x.id) && x.id>0
}
export function endpoint(level,port) {
  if (!levelOK(level) || (port!==18974&&port!==18973)) throw new Error('bad address')
  return 'http://127.0.0.1:'+port+'/?postData=GTS4MINIBAT%3A'+level+'%3B'
}
export function storedBody(res) {
  if (!res) return false
  let b=res.body
  if(typeof b==='string'){try{b=JSON.parse(b)}catch(e){return false}}
  if(b instanceof ArrayBuffer) {try{
    let s='';const a=new Uint8Array(b);for(let i=0;i<a.length;i++)s+=String.fromCharCode(a[i]);b=JSON.parse(s)
  }catch(e){return false}}
  if(b && typeof b==='object' && b.data && b.stored===undefined) b=b.data
  const code=Number(res.status||res.statusCode||res.code||0)
  return !!b && b.stored===true && (code===0 || (code>=200&&code<300))
}
