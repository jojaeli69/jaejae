import test from 'node:test'
import assert from 'node:assert/strict'
import {msg,valid,encode,decode,endpoint,storedBody,levelOK} from '../shared/protocol.js'
test('zepp BLE packets',()=>{
 for(const n of [0,1,55,99,100]){
   const p=msg('battery',n+1,{level:n})
   assert.deepEqual(decode(encode(p)),p)
   assert.equal(valid(decode(encode(p))),true)
 }
 assert.deepEqual(decode(encode(msg('ack',3,{stage:'zepp',ok:true,route:'zepp'}))),msg('ack',3,{stage:'zepp',ok:true,route:'zepp'}))
})
test('strict level and ports',()=>{
 for(const n of [-1,101,NaN,0.1,'10'])assert.equal(levelOK(n),false)
 assert.equal(endpoint(55,18974),'http://127.0.0.1:18974/?postData=GTS4MINIBAT%3A55%3B')
 assert.throws(()=>endpoint(50,12345))
})
test('local phone stored ACK required',()=>{
 for(const val of [{body:{stored:true},status:200},{body:'{"stored":true}',status:200}]){
  assert.equal(storedBody(val),true)
 }
 assert.equal(storedBody({body:{stored:false},status:200}),false)
 assert.equal(storedBody({body:{stored:true},status:500}),false)
 assert.equal(storedBody({status:200}),false)
})
