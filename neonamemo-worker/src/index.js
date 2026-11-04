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
function cors(req){const origin=req.headers.get("origin");if(!origin)return {};const u=new URL(req.url);const valid=[u.origin,"https://appassets.androidplatform.net","https://neonamemo.local"];if(!valid.includes(origin))return null;return {"access-control-allow-origin":origin,"vary":"Origin","access-control-allow-headers":"authorization,content-type,x-admin-key","access-control-allow-methods":"GET,POST,OPTIONS"};}
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
export default {async fetch(req,env){const u=new URL(req.url),c=cors(req);if(c===null)return error(403,"허용되지 않은 출처");if(req.method==="OPTIONS")return new Response(null,{status:204,headers:c});let r;if((u.pathname==="/"||u.pathname==="/health")&&req.method==="GET")r=respond({ok:true,service:"너나메모 주소조회",enrollment:"automatic",checks:{devices:Boolean(env.DEVICES),kakao:Boolean(env.KAKAO_REST_API_KEY),admin:Boolean(env.OWNER_ADMIN_KEY&&env.OWNER_ADMIN_KEY.length>=24)},configured:Boolean(env.DEVICES&&env.KAKAO_REST_API_KEY&&env.OWNER_ADMIN_KEY&&env.OWNER_ADMIN_KEY.length>=24)});else if(u.pathname==="/admin"&&req.method==="GET")r=new Response(ADMIN_HTML,{headers:{"content-type":"text/html; charset=utf-8","cache-control":"no-store","content-security-policy":"default-src 'none';script-src 'unsafe-inline';style-src 'unsafe-inline';connect-src 'self';base-uri 'none';frame-ancestors 'none'"}});else if(!env.DEVICES)r=error(503,"DEVICES KV 연결 필요");else if(u.pathname==="/v1/device/register"&&req.method==="POST")r=await register(req,env);else if(u.pathname==="/v1/device/status"&&req.method==="GET"){const d=await device(req,env);if(d)await autoApprove(d,env);r=d?respond({ok:true,status:d.approved?"approved":"pending"}):error(401,"등록 안 된 기기");}else if(u.pathname==="/v1/address/reverse"&&req.method==="POST")r=await lookup(req,env);else if(u.pathname.startsWith("/v1/admin/")){if(!admin(req,env))r=error(401,"관리자 인증 실패");else if(u.pathname==="/v1/admin/devices"&&req.method==="GET")r=await list(env);else if(u.pathname==="/v1/admin/approve"&&req.method==="POST")r=await approval(req,env,true);else if(u.pathname==="/v1/admin/revoke"&&req.method==="POST")r=await approval(req,env,false);else r=error(404,"없는 경로");}else r=error(404,"없는 경로");for(const [k,v] of Object.entries(c))r.headers.set(k,v);return r;}};