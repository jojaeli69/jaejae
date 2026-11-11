'use strict';
// Real-watch report: invoking undocumented sensor.start() freezes watch.
// Guarantee that the safe probe NEVER invokes start or stop.
const fs=require('fs'), vm=require('vm'), assert=require('assert');
const src=fs.readFileSync(require('path').join(__dirname,'../pages/index.js'),'utf8');
const forensic = {startCalls:0,stopCalls:0,removed:0,adds:0};
function boot(sensorFactory, id){
  let page,cb;
  const trace=[],buttons={};
  const hmUI={
    widget:{FILL_RECT:1,TEXT:2,BUTTON:3},
    prop:{MORE:1},
    text_style:{WRAP:1},
    createWidget(kind, config) {
      if(kind===3) buttons[config.text]=config.click_func;
      return {setProperty(_p, v){trace.push(v.text||'');}};
    }
  };
  const hmSensor={
    id: id ? {RECORDER:id}: {},event:{},
    createSensor(n){return sensorFactory(n,x=>{cb=x;});}
  };
  const sandbox={hmUI,hmSensor,Page(o){page=o;},console:{log(s){trace.push(String(s));}}};
  vm.createContext(sandbox);vm.runInContext(src,sandbox);
  page.build();
  return {buttons,page,trace,
    tap(b){assert.equal(typeof buttons[b],'function','missing '+b);buttons[b]();},
    fire(data){if(cb)cb(data);},
    has(s){assert(trace.join('\n').includes(s),s+' missing in '+trace.join('\n'));}};
}
function native(onCallback, failAdd){
  let listener=null;
  return {
    start(){forensic.startCalls++;throw new Error('UNSAFE_WATCH_FREEZE');},
    stop(){forensic.stopCalls++;throw new Error('UNSAFE_WATCH_FREEZE');},
    getData:undefined,
    addEventListener(_id,fn){forensic.adds++;if(failAdd)throw new TypeError("cannot read property 'id' of undefined");listener=fn;onCallback(fn);},
    removeEventListener(_id,fn){assert.equal(listener,fn);forensic.removed++;}
  };
}
{
 const a=boot((_id,onCallback)=>native(onCallback));
 a.has('READY');a.tap('CHECK');a.tap('OPEN');a.has('OPEN_OBJECT');
 a.tap('ADD');a.has('ADD_OK');a.fire(new Uint8Array(64));a.has('EVENT');
 a.tap('SAFE');a.has('START_DISABLED');a.tap('CLOSE');a.has('STOP_OK');
 assert(!a.buttons.START, 'Do not expose unsafe start button');
 assert(!a.buttons.STOP, 'Do not expose unsafe native stop button');
}
{
 const a=boot((_id,onCallback)=>native(onCallback,true));
 a.tap('OPEN');a.tap('ADD');a.has('ADD_ERR');a.tap('SAFE');a.has('START_DISABLED');
 a.tap('CLOSE');a.has('STOP_OK');
}
{
 const a=boot(()=>null);a.tap('OPEN');a.has('OPEN_EMPTY');a.tap('SAFE');a.has('START_DISABLED');
}
{
 const a=boot((_id,onCallback)=>native(onCallback),34);
 a.tap('OPEN');a.tap('OPEN');a.tap('ADD');a.tap('CLOSE');
 a.page.onDestroy();a.has('STOP_OK');
}
{
 const a=boot(()=>({start(){forensic.startCalls++},stop(){forensic.stopCalls++}}));
 a.tap('OPEN');a.tap('ADD');a.has('ADD_NO_API');a.tap('SAFE');a.has('START_DISABLED');a.tap('CLOSE');
}
assert.equal(forensic.startCalls,0,'Critical: native start was invoked');
assert.equal(forensic.stopCalls,0,'Critical: native stop was invoked');
assert(forensic.adds>=2);
assert(forensic.removed>=1);
console.log('PASS 5 v0.3 safe-probe VM scenarios, 0 native start/stop calls');
