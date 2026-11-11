// Non-invasive GTS 4 mini mic access check. Uses unverified vendor internals.
var sensor = null;
var widget = null;
var eventCount = 0;
var lastError = '';
var eventListener = null;
function show(s) {
  var msg = String(s);
  console.log('[MiniMicProbe] ' + msg);
  if (widget) widget.setProperty(hmUI.prop.MORE, {text: msg.slice(0, 180)});
}
function clearSensor() {
  if (!sensor) return;
  try { if (eventListener && typeof sensor.removeEventListener === 'function') sensor.removeEventListener(0x2201, eventListener); } catch(e) {}
  try { if (typeof sensor.stop === 'function') sensor.stop(); } catch(e) {}
  sensor = null;
  eventListener = null;
}
function check() {
  try {
    var name = typeof hmSensor !== 'undefined' && hmSensor.id ? hmSensor.id.RECORDER : undefined;
    show('Sensor id.RECORDER=' + String(name) + ' candidate=34; event=8705');
  } catch(e) { show('CHECK_ERR ' + String(e)); }
}
function open() {
  clearSensor();
  try {
    if (typeof hmSensor === 'undefined' || typeof hmSensor.createSensor !== 'function') {
      show('NO_SENSOR_API'); return;
    }
    var id = hmSensor.id && typeof hmSensor.id.RECORDER === 'number' ? hmSensor.id.RECORDER : 34;
    sensor = hmSensor.createSensor(id);
    if (!sensor) { show('OPEN_RETURNED_EMPTY'); return; }
    show('OPEN_OK methods start=' + typeof sensor.start + ' getData=' + typeof sensor.getData);
  } catch(e) { sensor = null; lastError = String(e); show('OPEN_ERR ' + lastError); }
}
function listen() {
  if (!sensor) { show('OPEN_FIRST'); return; }
  eventCount = 0;
  try {
    eventListener = function(data) { eventCount++; show('EVENT ' + eventCount + ' type=' + typeof data); };
    if (typeof sensor.addEventListener !== 'function') { show('NO_EVENT_METHOD'); return; }
    sensor.addEventListener(0x2201, eventListener);
    if (typeof sensor.start !== 'function') { show('NO_START_METHOD'); return; }
    var result = sensor.start();
    show('START_RET=' + String(result) + '; eventCount=' + eventCount);
  } catch(e) { lastError = String(e); show('LISTEN_ERR ' + lastError); clearSensor(); }
}
Page({
  build: function() {
    hmUI.createWidget(hmUI.widget.FILL_RECT, {x:0,y:0,w:336,h:384,color:0x101820});
    hmUI.createWidget(hmUI.widget.TEXT, {x:10,y:15,w:318,h:42,text:'GTS 4 mini microphone probe',text_size:20,color:0xffffff});
    widget = hmUI.createWidget(hmUI.widget.TEXT, {x:10,y:72,w:316,h:146,text:'Not tested; tap CHECK',text_size:17,color:0xffdca3,text_style:hmUI.text_style.WRAP});
    function btn(x, label, fn) {
      hmUI.createWidget(hmUI.widget.BUTTON, {x:x,y:240,w:101,h:60,text:label,text_size:18,normal_color:0x285b75,press_color:0x14354a,color:0xffffff,click_func:fn});
    }
    btn(8, 'CHECK', check);
    btn(116, 'OPEN', open);
    btn(224, 'LISTEN', listen);
    hmUI.createWidget(hmUI.widget.BUTTON, {x:8,y:320,w:320,h:48,text:'STOP',text_size:17,normal_color:0x5c3842,press_color:0x3e242a,color:0xffffff,click_func:function(){clearSensor();show('STOPPED / events=' + eventCount);}});
    check();
  },
  onDestroy: function() { clearSensor(); widget = null; }
});
