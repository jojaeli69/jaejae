// GTS 4 mini experimental microphone access diagnostics v0.2.0.
// Tests an undocumented sensor candidate (34 / 0x2201). Object creation is NOT audio proof.
// Do not record, store, or transmit callback payloads.
var sensor = null;
var statusWidget = null;
var eventListener = null;
var eventId = 8705;
var eventCount = 0;
var added = false;
var started = false;
var statusLines = [];

function safeRead(obj, key) {
  try { return obj ? obj[key] : undefined; }
  catch (err) { return 'THREW:' + String(err); }
}
function briefError(err) { return String(err).replace(/\s+/g, ' ').slice(0, 96); }
function report(label, detail) {
  var line = label + (detail ? ': ' + detail : '');
  console.log('[MiniMicProbe v0.2] ' + line);
  statusLines.push(line);
  if (statusLines.length > 5) statusLines.shift();
  if (statusWidget) {
    try { statusWidget.setProperty(hmUI.prop.MORE, { text: statusLines.join('\n').slice(0, 300) }); }
    catch (ignored) { console.log('[MiniMicProbe] UI_ERR ' + briefError(ignored)); }
  }
}
function methods(obj) {
  return 'start=' + typeof safeRead(obj, 'start')
    + ' add=' + typeof safeRead(obj, 'addEventListener')
    + ' getData=' + typeof safeRead(obj, 'getData');
}
function resolveEvent() {
  var objEvent = safeRead(sensor, 'event');
  var sensorValue = safeRead(objEvent, 'RECDATA');
  if (typeof sensorValue === 'number') return { value: sensorValue, source: 'sensor.event' };
  var globalEvent = safeRead(typeof hmSensor === 'undefined' ? undefined : hmSensor, 'event');
  var globalValue = safeRead(globalEvent, 'RECDATA');
  if (typeof globalValue === 'number') return { value: globalValue, source: 'hmSensor.event' };
  return { value: 8705, source: 'fw-candidate' };
}
function cleanup(quiet) {
  if (!sensor) return;
  var failure = [];
  if (added && eventListener) {
    try {
      var removeFn = safeRead(sensor, 'removeEventListener');
      if (typeof removeFn === 'function') removeFn.call(sensor, eventId, eventListener);
    } catch (err) { failure.push('remove ' + briefError(err)); }
  }
  try {
    var stopFn = safeRead(sensor, 'stop');
    if (typeof stopFn === 'function') stopFn.call(sensor);
  } catch (err) { failure.push('stop ' + briefError(err)); }
  added = false;
  started = false;
  eventListener = null;
  sensor = null;
  if (!quiet) report(failure.length ? 'STOP_ERR' : 'STOP_OK', failure.length ? failure.join(' / ') : 'events=' + eventCount);
}
function check() {
  try {
    var idObject = safeRead(typeof hmSensor === 'undefined' ? undefined : hmSensor, 'id');
    var recorder = safeRead(idObject, 'RECORDER');
    var globalEvent = safeRead(typeof hmSensor === 'undefined' ? undefined : hmSensor, 'event');
    report('CHECK', 'id.RECORDER=' + String(recorder) + '; event.RECDATA=' + String(safeRead(globalEvent, 'RECDATA')));
    report('CANDIDATE', 'id=34 event=8705; NOT confirmed');
  } catch (err) { report('CHECK_ERR', briefError(err)); }
}
function open() {
  cleanup(true);
  eventCount = 0;
  var factory = safeRead(typeof hmSensor === 'undefined' ? undefined : hmSensor, 'createSensor');
  if (typeof factory !== 'function') { report('OPEN_NO_API', 'createSensor missing'); return; }
  var ids = safeRead(hmSensor, 'id');
  var named = safeRead(ids, 'RECORDER');
  var id = typeof named === 'number' ? named : 34;
  try {
    sensor = factory.call(hmSensor, id);
    if (!sensor) { report('OPEN_EMPTY', 'returned ' + String(sensor)); return; }
    report('OPEN_OBJECT', 'id=' + id + ' ' + methods(sensor));
    report('NOT_AUDIO', 'object exists; mic not proven');
  } catch (err) {
    sensor = null;
    report('OPEN_ERR', briefError(err));
  }
}
function add() {
  if (!sensor) { report('ADD_NO_OPEN', 'press OPEN first'); return; }
  if (added) { report('ADD_ALREADY', 'listener active'); return; }
  var method = safeRead(sensor, 'addEventListener');
  if (typeof method !== 'function') { report('ADD_NO_API', 'addEventListener=' + typeof method); return; }
  var e = resolveEvent();
  eventId = e.value;
  report('ADD_TRY', 'event=' + eventId + ' via ' + e.source);
  eventListener = function (data) {
    eventCount++;
    var kind = typeof data;
    var length = safeRead(data, 'byteLength');
    if (typeof length !== 'number') length = safeRead(data, 'length');
    if (eventCount <= 2 || eventCount === 5 || eventCount % 50 === 0) {
      report('EVENT', 'count=' + eventCount + ' type=' + kind + ' size=' + String(length));
    }
  };
  try {
    method.call(sensor, eventId, eventListener);
    added = true;
    report('ADD_OK', 'registered; NOT PCM proof');
  } catch (err) {
    eventListener = null;
    added = false;
    report('ADD_ERR', briefError(err));
  }
}
function start() {
  if (!sensor) { report('START_NO_OPEN', 'press OPEN first'); return; }
  if (started) { report('START_ALREADY', 'press STOP before retry'); return; }
  var fn = safeRead(sensor, 'start');
  if (typeof fn !== 'function') { report('START_NO_API', 'start=' + typeof fn); return; }
  if (!added) report('START_NOTE', 'listener missing; event count unavailable');
  try {
    var result = fn.call(sensor);
    started = true;
    report('START_RET', String(result) + ' (not recording proof)');
  } catch (err) {
    report('START_ERR', briefError(err));
  }
}
Page({
  build: function () {
    hmUI.createWidget(hmUI.widget.FILL_RECT, {x:0,y:0,w:336,h:384,color:0x101820});
    hmUI.createWidget(hmUI.widget.TEXT, {x:10,y:10,w:315,h:39,text:'Mini Mic Probe 0.2',text_size:20,color:0xffffff});
    hmUI.createWidget(hmUI.widget.TEXT, {x:10,y:50,w:315,h:23,text:'Mini only / experimental / no PCM',text_size:13,color:0xb7cad4});
    statusWidget = hmUI.createWidget(hmUI.widget.TEXT, {x:10,y:76,w:315,h:164,text:'CHECK > OPEN > ADD > START',text_size:15,color:0xffdca3,text_style:hmUI.text_style.WRAP});
    function button(x,y,w,label,fn) {
      hmUI.createWidget(hmUI.widget.BUTTON, {x:x,y:y,w:w,h:53,text:label,text_size:17,normal_color:0x285b75,press_color:0x14354a,color:0xffffff,click_func:fn});
    }
    button(6,244,103,'CHECK',check);
    button(116,244,103,'OPEN',open);
    button(226,244,103,'ADD',add);
    button(6,307,156,'START',start);
    hmUI.createWidget(hmUI.widget.BUTTON, {x:170,y:307,w:159,h:53,text:'STOP',text_size:17,normal_color:0x5c3842,press_color:0x3e242a,color:0xffffff,click_func:function(){cleanup(false);}});
    report('READY', 'mini sensor candidate 34; 8705');
  },
  onDestroy: function () { cleanup(true); statusWidget = null; statusLines = []; }
});
