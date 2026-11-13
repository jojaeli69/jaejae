#!/usr/bin/env python3
import base64,zipfile,json,shutil
from io import BytesIO
from pathlib import Path

R=Path('gts4mini-os1');D=R/'build'
parts=sorted(R.glob('memo_src.b64.part*'))
assert len(parts)==5,parts
b64=''.join(''.join(p.read_text().split()) for p in parts)
src=base64.b64decode(b64,validate=True)
assert src[:4]==b'PK\x03\x04' and len(src)==1313822
if D.exists():shutil.rmtree(D)
memo=D/'memo';memo.mkdir(parents=True)
with zipfile.ZipFile(BytesIO(src)) as z:
  for entry in z.infolist():
    resolved=(memo/entry.filename).resolve()
    assert resolved.is_relative_to(memo.resolve())
    z.extract(entry,memo)
app_path=memo/'app.json'
app=json.loads(app_path.read_text(encoding='utf8'))
assert app['app']['appId']==90002201
assert app['runtime']['apiVersion']['minVersion']=='1.0.0'
assert 'gts4mini' in app['targets']
app['app']['version']={'code':41,'name':'1.0.0-mini-90min'}
app['app']['description']='Zepp OS 1.0 Memo UI + 90min screen hold. Microphone not verified'
app_path.write_text(json.dumps(app,ensure_ascii=False,indent=2),encoding='utf8')
(memo/'app.js').write_text("""App({
  onCreate(param) {
    this.quickStartMode = typeof param === 'string' && param.indexOf('quick-start') !== -1;
    console.log('Mini Memo OS 1.0: native mic not verified');
  },
  onDestroy(){}
});
""",encoding='utf8')
page_path=memo/'page/index.js'
page=page_path.read_text(encoding='utf8')
needle='  if(storage)ctr.restoreFiles(storage.list());else ctr.home();'
assert page.count(needle)==1
page=page.replace(needle,needle+"""
  let quickRequested=false;
  try{quickRequested=!!(typeof getApp==='function' && getApp().quickStartMode)}catch(_){}
  if(quickRequested){
    try{ctr.start()}catch(e){console.log('QuickMemo start failed: '+String(e))}
  }
""")
assert "createMemoScreenHold" in page and "onRecordingStart" in page
page_path.write_text(page,encoding='utf8')
quick=D/'quick';(quick/'page').mkdir(parents=True)
shutil.copy2(memo/'icon.png',quick/'icon.png')
q=json.loads(json.dumps(app))
q['app']['appId']=90002241
q['app']['appName']='퀵메모'
q['app']['version']={'code':1,'name':'1.0.0-mini'}
q['app']['description']='Zepp OS 1.0 launcher for Memo quick-start; audio recording not verified'
q['i18n']={'ko-KR':{'appName':'퀵메모'},'en-US':{'appName':'Quick Memo'}}
q['defaultLanguage']='ko-KR'
q['targets']['gts4mini']['module']={'page':{'pages':['page/index']}}
(quick/'app.json').write_text(json.dumps(q,ensure_ascii=False,indent=2),encoding='utf8')
(quick/'app.js').write_text('App({onCreate(){},onDestroy(){}});\n',encoding='utf8')
(quick/'page/index.js').write_text("""// GTS4 Mini ZeppOS 1.0 quick-start launcher
Page({
 build(){
   const openMemo=()=>{
     try{hmApp.startApp({appid:90002201,url:'page/index',param:'quick-start'})}
     catch(e){console.log('QuickMemo launch error: '+String(e))}
   };
   hmUI.createWidget(hmUI.widget.TEXT,{
     x:15,y:80,w:306,h:80,text:'퀵메모',text_size:30,color:0xffffff,
     align_h:hmUI.align.CENTER_H,align_v:hmUI.align.CENTER_V
   });
   hmUI.createWidget(hmUI.widget.BUTTON,{
     x:34,y:220,w:268,h:74,text:'메모 열기',text_size:23,color:0xffffff,
     normal_color:0x242424,press_color:0x454545,click_func:openMemo
   });
   openMemo();
 }
});
""",encoding='utf8')
(D/'audit.json').write_text(json.dumps({
 'device':'GTS4 mini','zeppOS':'1.0',
 'memoAppId':90002201,'quickAppId':90002241,
 'screenHoldSeconds':5400,'recorderVerified':False,
 'note':'No working microphone backend: do not imply recording works'
},indent=2),encoding='utf8')
print('SOURCE_OK',len(src),D)
