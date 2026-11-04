// NeonaMemo Worker: per-device approval and Kakao reverse geocoding.
// Set secrets KAKAO_REST_API_KEY and OWNER_ADMIN_KEY.
// Bind a KV namespace named DEVICES. No secret should be committed.
const KAKAO_URL = "https://dapi.kakao.com/v2/local/geo/coord2address.json";
const H = {"content-type":"application/json; charset=utf-8","cache-control":"no-store","x-content-type-options":"nosniff"};
function respond(data,status=200){return new Response(JSON.stringify(data),{status,headers:H});}
function error(status,message){return respond({ok:false,error:message},status);}
function hex(s){return typeof s==="string"&&s.length===64&&[...s.toLowerCase()].every(c=>"0123456789abcdef".includes(c));}
async function digest(s){const a=new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(s)));return [...a].map(v=>v.toString(16).padStart(2,"0")).join("");}
async function body(req){const raw=await req.text();if(raw.length>1600)throw Error("body too long");return JSON.parse(raw);}
function admin(req,env){const actual=req.headers.get("x-admin-key")||"",want=env.OWNER_ADMIN_KEY;if(!want||want.length<24)return false;const a=new TextEncoder().encode(actual),b=new TextEncoder().encode(want);let diff=a.length^b.length;for(let i=0;i<Math.max(a.length,b.length);i++)diff|=(a[i]||0)^(b[i]||0);return diff===0;}
async function device(req,env){const a=req.headers.get("authorization")||"";if(!a.startsWith("Bearer "))return null;const token=a.slice(7).toLowerCase();if(!hex(token))return null;return env.DEVICES.get("device:"+await digest(token),"json");}
function cors(req){const origin=req.headers.get("origin");if(!origin)return {};const u=new URL(req.url);const valid=[u.origin,"https://appassets.androidplatform.net","https://neonamemo.local"];if(!valid.includes(origin))return null;return {"access-control-allow-origin":origin,"vary":"Origin","access-control-allow-headers":"authorization,content-type,x-admin-key,x-nnm-workspace-key","access-control-allow-methods":"GET,POST,PUT,OPTIONS"};}
const ADMIN_HTML=[
"<!doctype html><html lang='ko'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
"<title>너나메모 승인</title><style>body{font-family:system-ui;max-width:540px;margin:2rem auto;padding:1rem;background:#f5f7fa;color:#142238}button,input{font:inherit;padding:.75rem;border:1px solid #bbb;border-radius:.6rem;margin:.25rem}button{background:#173d85;color:white}li{padding:.5rem 0}</style>",
"<h2>너나메모 기기 승인</h2><p>새 기기는 별도 승인 없이 자동 등록됩니다. 기기별 차단은 아래에서 관리하세요.</p><input id='pass' type='password' placeholder='관리자 암호'><button id='refresh'>기기 조회</button><ul id='list'></ul><p id='status' role='status'></p>",
"<script>const q=x=>document.querySelector(x);async function api(url,data){let r=await fetch(url,{method:data?'POST':'GET',headers:{'x-admin-key':q('#pass').value,'content-type':'application/json'},body:data?JSON.stringify(data):undefined});let j=await r.json();if(!r.ok)throw Error(j.error);return j}async function refresh(){try{let d=await api('/v1/admin/devices');q('#list').textContent='';for(let x of d.devices){let li=document.createElement('li');li.textContent=x.label+' · '+(x.approved?'승인':'차단')+' ';let b=document.createElement('button');b.textContent=x.approved?'승인 해제':'승인';b.onclick=async()=>{try{await api('/v1/admin/'+(x.approved?'revoke':'approve'),{id:x.id});refresh()}catch(e){q('#status').textContent=e.message}};li.append(b);q('#list').append(li)}q('#status').textContent=d.devices.length+'대 등록됨'}catch(e){q('#status').textContent=e.message}}q('#refresh').onclick=refresh;</script></html>"
].join("");

// Check legacy revoked devices before granting access; old manual revokes had updatedAt.
// Pending legacy devices have no updatedAt, so they become approved automatically.
function blocked(d){return !!(d?.revokedAt||(d&&!d.approved&&d.updatedAt&&d.enrollment!=="auto-all"));}
async function autoApprove(d,env){
  if(!d||d.approved||blocked(d))return d;
  d.approved=true;d.enrollment="auto-all";d.approvedAt=new Date().toISOString();
  await env.DEVICES.put("device:"+d.id,JSON.stringify(d));
  return d;
}
async function register(req,env){
  let b;try{b=await body(req);}catch{return error(400,"입력값 오류");}
  const token=String(b.installToken||"").toLowerCase();
  if(!hex(token))return error(422,"기기 인증값 형식 오류");
  const id=await digest(token),key="device:"+id;
  let d=await env.DEVICES.get(key,"json");
  if(!d){
    const now=new Date().toISOString();
    d={id,label:String(b.deviceLabel||"새 기기").slice(0,40),
      approved:true,enrollment:"auto-all",createdAt:now,approvedAt:now};
    await env.DEVICES.put(key,JSON.stringify(d));
  }else{
    await autoApprove(d,env);
  }
  return respond({ok:true,status:d.approved?"approved":"pending"});
}

async function list(env){
  const devices=[];let cursor;
  do {
    const page=await env.DEVICES.list({prefix:"device:",limit:100,...(cursor?{cursor}:{})});
    for(const k of page.keys){
      const d=await env.DEVICES.get(k.name,"json");if(d)devices.push(d);
    }
    cursor=page.list_complete?null:page.cursor;
  }while(cursor);
  devices.sort((a,b)=>String(b.createdAt).localeCompare(String(a.createdAt)));
  return respond({ok:true,devices});
}

async function approval(req,env,approve){
  let b;try{b=await body(req);}catch{return error(400,"입력값 오류");}
  if(!hex(b.id))return error(400,"기기 ID 오류");
  const key="device:"+b.id,d=await env.DEVICES.get(key,"json");
  if(!d)return error(404,"기기 없음");
  d.approved=Boolean(approve);d.updatedAt=new Date().toISOString();
  if(approve){delete d.revokedAt;d.approvedAt=d.updatedAt;}
  else d.revokedAt=d.updatedAt;
  await env.DEVICES.put(key,JSON.stringify(d));
  return respond({ok:true,approved:d.approved});
}
async function lookup(req,env){const d=await device(req,env);if(!d)return error(401,"기기 인증 필요");await autoApprove(d,env);if(!d.approved)return error(403,"관리자에 의해 차단된 기기");if(!env.KAKAO_REST_API_KEY)return error(503,"카카오 키 미설정");let b;try{b=await body(req);}catch{return error(400,"입력값 오류");}const lat=Number(b.latitude),lon=Number(b.longitude),acc=Number(b.accuracyMeters);if(!Number.isFinite(lat)||!Number.isFinite(lon)||lat<33||lat>39.6||lon<124||lon>132)return error(422,"한국 GPS 좌표 필요");if(!Number.isFinite(acc)||acc<0||acc>100)return error(422,"GPS 정확도 확인 필요");const u=new URL(KAKAO_URL);u.searchParams.set("x",String(lon));u.searchParams.set("y",String(lat));u.searchParams.set("input_coord","WGS84");let r;try{r=await fetch(u,{headers:{authorization:"KakaoAK "+env.KAKAO_REST_API_KEY,accept:"application/json"},signal:AbortSignal.timeout(8000)});}catch{return error(502,"주소 서버 연결 실패");}if(!r.ok)return error(502,r.status===401||r.status===403?"카카오 키 또는 활성화 확인 필요":"주소조회 오류");let data;try{data=await r.json();}catch{return error(502,"응답 오류");}const doc=data?.documents?.[0]||{},a=doc.address;if(!a?.address_name)return error(404,"지번주소 없음");const main=a.main_address_no||"",sub=a.sub_address_no||"";return respond({ok:true,source:"kakao",address:a.address_name,roadAddress:doc.road_address?.address_name||"",province:a.region_1depth_name||"",cityCounty:a.region_2depth_name||"",village:a.region_3depth_name||"",lot:[main,sub].filter(Boolean).join("-"),mainLot:main,subLot:sub,accuracyMeters:acc,needsConfirmation:true});}

const NNM_SHARED_KINDS=new Set(['record','task']);
function nnmValidId(id){return typeof id==='string' && /^[a-zA-Z0-9_-]{1,100}$/.test(id)}
async function nnmWorkspace(req){
 const token=req.headers.get('x-nnm-workspace-key')||'';
 if(!/^[0-9a-f]{64}$/.test(token))return null;
 return 'nnm36:'+await digest(token)+':';
}
async function nnmReadBody(req,limit){
 let n=Number(req.headers.get('content-length'));
 if(n>limit)throw Error('payload too large');
 let raw=await req.text();if(raw.length>limit)throw Error('payload too large');
 return JSON.parse(raw);
}
function nnmCipher(s){return typeof s==='string'&&s.length<380000&&/^[A-Za-z0-9+/=]+\.[A-Za-z0-9+/=]+$/.test(s)}

/* v4.2 optional R2 storage: private binding, encrypted binary content.
 * If FILES_R2 is not bound, all existing KV operations are unchanged.
 * Existing KV attachments remain readable; successful reads copy to R2.
 * Destructive archive cleanup is intentionally NOT implemented here.
 */
function nnmB64Binary(s){return Uint8Array.from(atob(s),c=>c.charCodeAt(0));}
function nnmBinaryB64(arr){
 let str='';for(let i=0;i<arr.length;i+=8192)str+=String.fromCharCode(...arr.subarray(i,i+8192));
 return btoa(str);
}
function nnmR2Pack(s){
 const parts=s.split('.');
 if(parts.length!==2)throw Error('잘못된 파일 암호문');
 const iv=nnmB64Binary(parts[0]),cipher=nnmB64Binary(parts[1]);
 if(iv.length!==12||cipher.length<16)throw Error('암호문 크기 오류');
 const out=new Uint8Array(iv.length+cipher.length);out.set(iv);out.set(cipher,12);return out;
}
function nnmR2Unpack(bytes){
 if(bytes.length<28)throw Error('원본 데이터 손상');
 return nnmBinaryB64(bytes.subarray(0,12))+'.'+nnmBinaryB64(bytes.subarray(12));
}
function nnmR2Enabled(env){return !!env.FILES_R2;}
async function nnmR2Usage(req,env,ns,u){
 if(!nnmR2Enabled(env))return respond({ok:true,enabled:false,reason:'FILES_R2 binding not configured'});
 const cursor=u.searchParams.get('cursor')||undefined;
 let page;try{
  page=await env.FILES_R2.list({prefix:ns+'file:',limit:1000,...(cursor?{cursor}:{})});
 }catch{return error(502,'R2 용량 조회 실패')}
 let bytes=0;
 for(const obj of page.objects)bytes+=Number(obj.size)||0;
 return respond({ok:true,enabled:true,scannedBytes:bytes,scannedObjects:page.objects.length,
   cursor:page.truncated?page.cursor||'':'',hasMore:!!page.truncated,
   targetBytes:10000000000,alertBytes:9000000000,needsArchiveCheck:false});
}

async function nnmShareRoutes(req,env,u){
 const ns=await nnmWorkspace(req);if(!ns)return error(401,'공유 앱 인증정보가 없음');
 if(!env.DEVICES)return error(503,'공유 저장소 미연결');
 const path=u.pathname;
 if(path==='/v1/share/items'){
  if(req.method==='GET'){
   const kind=u.searchParams.get('kind'),cursor=u.searchParams.get('cursor');
   if(!NNM_SHARED_KINDS.has(kind))return error(422,'잘못된 기록 종류');
   let page;try{page=await env.DEVICES.list({prefix:ns+kind+':',limit:50,...(cursor?{cursor}:{})})}catch{return error(400,'목록 커서 오류')}
   let items=[];for(const k of page.keys){let item=await env.DEVICES.get(k.name,'json');if(item?.id)items.push(item)}
   return respond({ok:true,items,cursor:page.list_complete?'':page.cursor||''});
  }
  if(req.method==='POST'){
   let b;try{b=await nnmReadBody(req,450000)}catch{return error(413,'기록 데이터가 너무 큼')}
   if(!NNM_SHARED_KINDS.has(b.kind)||!nnmValidId(b.id)||typeof b.mtime!=='string'||b.mtime.length>40||!/^\d{4}-\d\d-\d\dT/.test(b.mtime)||!nnmCipher(b.data))return error(422,'기록 형식 오류');
   const key=ns+b.kind+':'+b.id;
   const old=await env.DEVICES.get(key,'json');
   if(old?.mtime&&old.mtime>b.mtime)return error(409,'stale: 저장소의 내용이 더 최신');
   await env.DEVICES.put(key,JSON.stringify({id:b.id,mtime:b.mtime,data:b.data,deleted:!!b.deleted}));
   return respond({ok:true,saved:true,id:b.id});
  }
  return error(405,'지원하지 않는 요청');
 }
 if(path==='/v1/share/r2/usage'&&req.method==='GET')
  return nnmR2Usage(req,env,ns,u);
 const m=/^\/v1\/share\/files\/([a-zA-Z0-9_-]{1,100})\/(\d{1,4})$/.exec(path);
 if(m){
  const part=Number(m[2]);if(part>=300)return error(422,'파일 조각 최대 300개');
  const key=ns+'file:'+m[1]+':'+part;
  if(req.method==='GET'){
    if(nnmR2Enabled(env)){
      const object=await env.FILES_R2.get(key);
      if(object){
        try{return respond({ok:true,data:nnmR2Unpack(new Uint8Array(await object.arrayBuffer()))});}
        catch{return error(502,'R2 파일 손상 또는 읽기 실패')}
      }
    }
    const data=await env.DEVICES.get(key);
    if(!data)return error(404,'원본 파일 조각 없음');
    // Lazy copy: never delete the legacy KV chunk during migration.
    if(nnmR2Enabled(env)&&nnmCipher(data)){
      try{await env.FILES_R2.put(key,nnmR2Pack(data),
        {httpMetadata:{contentType:'application/octet-stream'}});}catch(e){
        console.warn('Legacy file R2 copy skipped',String(e).slice(0,120));
      }
    }
    return respond({ok:true,data});
  }
  if(req.method==='PUT'){
    let b;try{b=await nnmReadBody(req,410000)}catch{return error(413,'파일 조각 크기 초과')}
    if(!nnmCipher(b.data))return error(422,'암호화 파일 조각 형식 오류');
    if(nnmR2Enabled(env)){
      try{await env.FILES_R2.put(key,nnmR2Pack(b.data),
        {httpMetadata:{contentType:'application/octet-stream'}});}
      catch(e){console.error('R2 upload failed',String(e).slice(0,120));return error(503,'R2 원본 저장 실패')}
    }else await env.DEVICES.put(key,b.data);
    return respond({ok:true,saved:true,storage:nnmR2Enabled(env)?'r2':'kv'});
  }
  return error(405,'지원하지 않는 요청');
 }
 return error(404,'없는 공유 API');
}

export default {async fetch(req,env){const u=new URL(req.url),c=cors(req);if(c===null)return error(403,"허용되지 않은 출처");if(req.method==="OPTIONS")return new Response(null,{status:204,headers:c});let r;if((u.pathname==="/"||u.pathname==="/health")&&req.method==="GET")r=respond({ok:true,service:"너나메모 주소조회",enrollment:"automatic",checks:{devices:Boolean(env.DEVICES),kakao:Boolean(env.KAKAO_REST_API_KEY),admin:Boolean(env.OWNER_ADMIN_KEY&&env.OWNER_ADMIN_KEY.length>=24)},configured:Boolean(env.DEVICES&&env.KAKAO_REST_API_KEY&&env.OWNER_ADMIN_KEY&&env.OWNER_ADMIN_KEY.length>=24)});else if(u.pathname==="/admin"&&req.method==="GET")r=new Response(ADMIN_HTML,{headers:{"content-type":"text/html; charset=utf-8","cache-control":"no-store","content-security-policy":"default-src 'none';script-src 'unsafe-inline';style-src 'unsafe-inline';connect-src 'self';base-uri 'none';frame-ancestors 'none'"}});else if(!env.DEVICES)r=error(503,"DEVICES KV 연결 필요");else if(u.pathname==="/v1/device/register"&&req.method==="POST")r=await register(req,env);else if(u.pathname==="/v1/device/status"&&req.method==="GET"){const d=await device(req,env);if(d)await autoApprove(d,env);r=d?respond({ok:true,status:d.approved?"approved":"pending"}):error(401,"등록 안 된 기기");}else if(u.pathname==="/v1/address/reverse"&&req.method==="POST")r=await lookup(req,env);else if(u.pathname.startsWith("/v1/share/"))r=await nnmShareRoutes(req,env,u);else if(u.pathname.startsWith("/v1/admin/")){if(!admin(req,env))r=error(401,"관리자 인증 실패");else if(u.pathname==="/v1/admin/devices"&&req.method==="GET")r=await list(env);else if(u.pathname==="/v1/admin/approve"&&req.method==="POST")r=await approval(req,env,true);else if(u.pathname==="/v1/admin/revoke"&&req.method==="POST")r=await approval(req,env,false);else r=error(404,"없는 경로");}else r=error(404,"없는 경로");for(const [k,v] of Object.entries(c))r.headers.set(k,v);return r;}};