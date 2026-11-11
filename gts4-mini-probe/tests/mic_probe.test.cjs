'use strict';
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const src = fs.readFileSync(require('path').join(__dirname,'../pages/index.js'),'utf8');

function boot(sensorFactory, opts) {
  opts = opts || {};
  const log = [];
  const buttons = {};
  let page = null;
  let callback = null;
  const hmUI = {
    widget:{ FILL_RECT:1,TEXT:2,BUTTON:3 },
    prop:{MORE:1},
    text_style:{WRAP:1},
    createWidget(t,config) {
      if(t===3) buttons[config.text] = config.click_func;
      return { setProperty(_p,value) { if(value.text) log.push('UI '+value.text); }};
    }
  };
  const hmSensor = {id:{},event:{},
    createSensor(id) { return sensorFactory(id, cb=>{callback=cb;}); }};
  if(opts.id) hmSensor.id.RECORDER = opts.id;
  if(opts.event) hmSensor.event.RECDATA = opts.event;
  const context={hmUI,hmSensor,Page(def){page=def;},console:{log(s){log.push(String(s));}}};
  vm.createContext(context);
  vm.runInContext(src,context,{filename:'pages/index.js'});
  page.build();
  return {log,buttons,page,click(label){assert(buttons[label],'missing button '+label);buttons[label]();},
    text(){return log.join('\n');},fire(data){if(callback)callback(data);} };
}
function has(b,needle){assert(b.text().includes(needle),'missing '+needle+' in '+b.text());}
function sensorObject(h) {
  let fn=null;
  const instance={
    start(){return 'ok';},
    stop(){return true;},
    addEventListener(id,cb){h.eventId=id;fn=cb;h.onCallback(cb);},
    removeEventListener(id,cb){h.removeId=id;h.removed=(fn===cb);},
  };
  return instance;
}
{
 const data={};
 const app=boot((_id,onCallback)=>sensorObject({...data,onCallback, set eventId(v){data.eventId=v}, set removeId(v){data.removeId=v},set removed(v){data.removed=v}}));
 app.click('CHECK');app.click('OPEN');app.click('ADD');app.click('START');app.fire(new Uint8Array(32));app.click('STOP');
 has(app,'CHECK:');has(app,'OPEN_OBJECT:');has(app,'NOT_AUDIO:');
 has(app,'ADD_OK:');has(app,'START_RET:');has(app,'EVENT: count=1');has(app,'STOP_OK:');
 assert.equal(data.eventId,8705);
 assert.equal(data.removed,true);
 assert.equal(data.removeId,8705);
}
{
 const app=boot((_id,onCallback)=>({
  start(){return 1;},
  addEventListener(){throw new TypeError("cannot read property 'id' of undefined");},
  stop(){return 0;}
 }));
 app.click('OPEN');app.click('ADD');app.click('START');
 has(app,"ADD_ERR: TypeError: cannot read property 'id' of undefined");
 has(app,'START_NOTE:');has(app,'START_RET: 1');
 assert(!app.text().includes('LISTEN_ERR'));
}
{
 const app=boot(()=>({
   addEventListener(){},start(){throw new Error('native error');},stop(){return 0;}
 }));
 app.click('OPEN');app.click('ADD');app.click('START');
 has(app,'ADD_OK:');has(app,'START_ERR: Error: native error');
}
{
 const app=boot(()=>({
   addEventListener(){},start(){return 0;},stop(){return true;}
 }),{id:34,event:0x2201});
 app.click('OPEN');app.click('ADD');app.click('START');
 has(app,'ADD_TRY: event=8705 via hmSensor.event');
}
{
 const app=boot(()=>({start(){return 0;},stop(){return 0;}}));
 app.click('ADD');has(app,'ADD_NO_OPEN');
 app.click('OPEN');app.click('ADD');has(app,'ADD_NO_API');
 app.click('START');has(app,'START_NOTE:');
}
{
 let stopped=0;
 const app=boot(()=>({stop(){stopped++;},addEventListener(){},start(){return 0;}}));
 app.click('OPEN');app.click('ADD');app.click('START');app.page.onDestroy();
 assert.equal(stopped,1,'onDestroy cleans sensor');
}
{
 const app=boot(()=>({start(){return 0;},stop(){return 0;},addEventListener(){}}));
 app.click('OPEN');app.click('OPEN');app.click('ADD');app.click('START');app.click('STOP');
 has(app,'STOP_OK');
}
console.log('PASS: 7 staged Mini Mic Probe v0.2 VM tests');
