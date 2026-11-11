'use strict';
// This is a read-only probe. Native start/stop caused a real GTS 4 mini freeze in v0.2.
const assert=require('assert');
const vm=require('vm');
const fs=require('fs');
const src=fs.readFileSync(require('path').join(__dirname,'../pages/index.js'),'utf8');
const calls={start:0,stop:0,open:0,add:0,remove:0};
function boot(factory){
 const trace=[],buttons={};let page,callback;
 const hmUI={widget:{FILL_RECT:1,TEXT:2,BUTTON:3},prop:{MORE:1},text_style:{WRAP:1},
   createWidget(kind,opts){
     if(kind===3)buttons[opts.text]=opts.click_func;
     return {setProperty(_p,v){if(v.text)trace.push(String(v.text));}};
   }
 };
 const hmSensor={id:{RECORDER:34},event:{},
   createSensor(id){calls.open++;return factory(id,cb=>{callback=cb;});}};
 const ctx={hmUI,hmSensor,Page(def){page=def;},console:{log(s){trace.push(String(s));}}};
 vm.createContext(ctx);
 vm.runInContext(src,ctx,{filename:'pages/index.js'});
 page.build();
 return {page,buttons,trace,click(b){assert.equal(typeof buttons[b],'function','Missing '+b);buttons[b]();},
   fire(payload){if(callback)callback(payload);},
   has(fragment){assert(trace.join('\n').includes(fragment),'Missing '+fragment+' in '+trace.join('\n'));}};
}
function makeSensor(register, cbSink){
 let listener;
 return {
   start(){calls.start++;throw Error('UNSAFE_NATIVE_START');},
   stop(){calls.stop++;throw Error('UNSAFE_NATIVE_STOP');},
   addEventListener(e,fn){calls.add++;if(register==='throw')throw new TypeError('native binding inaccessible');
     listener=fn;cbSink(fn);},
   removeEventListener(e,fn){calls.remove++;assert.strictEqual(fn,listener);}
 };
}
{
 const a=boot((_id,set)=>makeSensor('ok',set));
 a.has('READY');a.click('CHECK');a.has('id.RECORDER=34');
 a.click('STATE');a.has('MISSING');
 a.click('OPEN');a.has('OPEN_OBJECT');a.click('STATE');a.has('HELD');
 a.click('LINK');a.has('LINK_OPEN_OK');a.has('LINK_ADD_OK');
 a.fire(new Uint8Array(12));a.has('EVENT');
 a.click('CLOSE');a.has('STOP_OK');
 assert(!a.buttons.START);assert(!a.buttons.SAFE);assert(!a.buttons.ADD);
}
{
 const before=boot((_id,set)=>makeSensor('ok',set));
 before.click('OPEN');
 const after=boot((_id,set)=>makeSensor('ok',set)); // Simulated runtime page rebuild between taps
 after.click('STATE');after.has('MISSING');
 after.click('LINK');after.has('LINK_ADD_OK');
 after.click('CLOSE');after.page.onDestroy();
}
{
 const a=boot((_id,set)=>makeSensor('throw',set));
 a.click('LINK');a.has('LINK_OPEN_OK');a.has('ADD_ERR');a.has('LINK_ADD_FAIL');
 a.click('STATE');a.has('HELD');a.click('CLOSE');
}
{
 const a=boot(()=>null);
 a.click('LINK');a.has('LINK_OPEN_FAIL');a.click('STATE');a.has('MISSING');
}
{
 const a=boot(()=>({start(){calls.start++},stop(){calls.stop++}}));
 a.click('LINK');a.has('ADD_NO_API');a.has('LINK_ADD_FAIL');a.click('CLOSE');
}
{
 const a=boot((_id,set)=>makeSensor('ok',set));
 a.click('LINK');a.click('LINK');a.has('LINK_ADD_OK');a.page.onDestroy();
}
assert.strictEqual(calls.start,0,'Watch-freezing start invoked');
assert.strictEqual(calls.stop,0,'Native stop invoked');
assert(calls.open>=6 && calls.add>=3 && calls.remove>=1);
console.log('PASS 6 v0.4 GTS4 mini safe probe VM scenarios; native start=0 stop=0');
