#!/usr/bin/env python3
"""BatteryTrio v80: infer charging from level increases; avoid acquiring Huami GATT."""
from pathlib import Path
ROOT=Path("batterytrio-v80-src")
JAVA=ROOT/"app/src/main/java/org/example/galaxybatterybridge"
def edit(path,original,replacement,count=1):
    text=path.read_text()
    actual=text.count(original)
    if actual!=count:
        raise AssertionError(f"{path.name}: wanted {count} occurrences, got {actual}: {original[:90]}")
    path.write_text(text.replace(original,replacement,count))
(JAVA/"MiniChargeHeuristic.java").write_text("""package org.example.galaxybatterybridge;

/** A LEVEL-BASED ESTIMATE. Not a statement that the cable is connected. */
public final class MiniChargeHeuristic {
    private MiniChargeHeuristic(){}
    public static boolean next(boolean wasCharging,int previous,int current) {
        if(current<0||current>=100)return false;
        if(previous<0||previous>100)return false;
        if(current>previous)return true;
        if(current<previous)return false;
        return wasCharging;
    }
    public static boolean visible(int level,boolean stale,boolean estimatedCharging) {
        return !stale&&level>=0&&level<100&&estimatedCharging;
    }
}
""")
(JAVA/"MiniSystemBattery.java").write_text("""package org.example.galaxybatterybridge;

import android.Manifest;
import android.bluetooth.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.SystemClock;
import java.util.Locale;

/**
 * Receives
 * Android battery broadcasts. NO scanning, GATT connections, service discovery,
 * pairing, writes, or proprietary Huami authentication.
 *
 * Android may not expose Zepp's private battery value; UNKNOWN is handled
 * honestly rather than creating artificial readings.
 */
public final class MiniSystemBattery {
    private static long lastPollElapsed=-120001;
    private MiniSystemBattery(){}
    private static boolean allowed(Context c) {
        return Build.VERSION.SDK_INT<31||
            c.checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT)==PackageManager.PERMISSION_GRANTED;
    }
    private static boolean matches(BluetoothDevice d) {
        if(d==null)return false;
        try {
            String name=d.getName();
            return name!=null&&name.toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9]","").contains("gts4mini");
        }catch(SecurityException e){return false;}
    }
    private static void receive(Context c,int next,String source,boolean event) {
        if(next<0||next>100)return;
        android.content.SharedPreferences p=c.getSharedPreferences("bridge",Context.MODE_PRIVATE);
        if(p.getBoolean("mini_auth_auto",false)||p.getBoolean("mini_ble_auto",false))return;
        int old=p.getInt("gts4mini",-1);
        if(!event&&old==next&&p.getLong("mini_seen",0)>0){
            p.edit().putString("mini_system_status","Android 캐시 "+next+"% · 변동 없음 (새 전송 확인 불가)").apply();
            return;
        }
        long now=System.currentTimeMillis();
        boolean charge=MiniChargeHeuristic.next(p.getBoolean("mini_inferred_charging",false),old,next);
        String trend=next>old&&old>=0?"UP":next<old&&old>=0?"DOWN":"UNKNOWN";
        p.edit().putInt("gts4mini",next)
            .putLong("mini_seen",now).putString("mini_source",source)
            .putBoolean("mini_inferred_charging",charge)
            .putString("mini_system_status","Android 수신: "+next+"% ("+source+")")
            .putString("mini_trend",trend)
            .putLong("mini_trend_at",!trend.equals("UNKNOWN")?now:0L)
            .putLong("mini_last_change",old!=next?now:p.getLong("mini_last_change",0))
            .apply();
        if(old!=next||old<0)ReceiveHistory.record(c,next,now);
        BatteryWidget.refreshWatch(c);
    }
    public static boolean onBatteryBroadcast(Context c,Intent intent) {
        if(intent==null||!"android.bluetooth.device.action.BATTERY_LEVEL_CHANGED".equals(intent.getAction())||!allowed(c))return false;
        BluetoothDevice d;
        try {d=intent.getParcelableExtra(BluetoothDevice.EXTRA_DEVICE);}
        catch(Exception e){return false;}
        if(!matches(d))return false;
        int level=intent.getIntExtra("android.bluetooth.device.extra.BATTERY_LEVEL",-1);
        receive(c,level,"Android Bluetooth 배터리 이벤트",true);
        return true;
    }
    public static void poll(Context c) {
        long elapsed=SystemClock.elapsedRealtime();
        if(elapsed-lastPollElapsed<120000L&&elapsed>=lastPollElapsed)return;
        lastPollElapsed=elapsed;
        if(!allowed(c))return;
        android.content.SharedPreferences p=c.getSharedPreferences("bridge",Context.MODE_PRIVATE);
        if(p.getBoolean("mini_auth_auto",false)||p.getBoolean("mini_ble_auto",false))return;
        // Android's BluetoothDevice.getBatteryLevel() is a restricted non-SDK API.
        // Listen to system battery broadcasts without a new GATT connection.
        if(!p.getString("mini_source","").startsWith("Android")) {
            p.edit().putString("mini_system_status",
                "Android 배터리 이벤트 대기 중 · 추가 BLE 연결 없음").apply();
        }
    }
}
""")
# Record inference on EVERY actual level-update path.
for name,old in [
 ("BridgeService.java",'boolean latestSaved=prefs.edit()\n                .putInt("gts4mini",level)'),
 ("MiniGattMonitor.java",'p.edit().putInt("gts4mini",level).putLong("mini_seen",now)'),
 ("MiniHuamiAuthMonitor.java",'p.edit().putInt("gts4mini",f.percent).putLong("mini_seen",lastResponse)'),
 ("MiniHuamiAuthMonitor.java",'p.edit().putInt("gts4mini",level).putLong("mini_seen",now)')
]:
    if name=="BridgeService.java":
        new='boolean latestSaved=prefs.edit()\n                .putBoolean("mini_inferred_charging",MiniChargeHeuristic.next(prefs.getBoolean("mini_inferred_charging",false),previous,level))\n                .putInt("gts4mini",level)'
    elif name=="MiniHuamiAuthMonitor.java" and "f.percent" in old:
        new='p.edit().putBoolean("mini_inferred_charging",MiniChargeHeuristic.next(p.getBoolean("mini_inferred_charging",false),oldLevel,f.percent)).putInt("gts4mini",f.percent).putLong("mini_seen",lastResponse)'
    elif name=="MiniHuamiAuthMonitor.java":
        new='p.edit().putBoolean("mini_inferred_charging",MiniChargeHeuristic.next(p.getBoolean("mini_inferred_charging",false),old,level)).putInt("gts4mini",level).putLong("mini_seen",now)'
    else:
        new='p.edit().putBoolean("mini_inferred_charging",MiniChargeHeuristic.next(p.getBoolean("mini_inferred_charging",false),previous,level)).putInt("gts4mini",level).putLong("mini_seen",now)'
    edit(JAVA/name,old,new)
# Gate stale direct charge data behind the explicitly enabled GATT mode.
widget=JAVA/"BatteryWidget.java"
original='''        boolean watchEstimated=MiniBatteryTrend.estimatedRising(watch,p.getString("mini_trend",MiniBatteryTrend.UNKNOWN),
                p.getLong("mini_trend_at",0),System.currentTimeMillis(),watchStale);
        int directCharge=MiniHuamiAuthMonitor.verifiedCharge(c,System.currentTimeMillis());
        if(directCharge<0)directCharge=MiniGattMonitor.verifiedCharge(c,System.currentTimeMillis());
        if(directCharge<0)directCharge=WatchChargingProbe.chargeState(c,System.currentTimeMillis());
        if(directCharge>=0)watchEstimated=false;
        boolean[] charging={phoneCharging(c), directCharge>=0?directCharge==1:watchEstimated,budsCharging.earbuds==1,budsCharging.caseState==1};'''
replacement='''        boolean watchEstimated=MiniChargeHeuristic.visible(watch,watchStale,p.getBoolean("mini_inferred_charging",false));
        int directCharge=-1;
        if(p.getBoolean("mini_auth_auto",false))directCharge=MiniHuamiAuthMonitor.verifiedCharge(c,System.currentTimeMillis());
        if(directCharge<0&&p.getBoolean("mini_ble_auto",false))directCharge=MiniGattMonitor.verifiedCharge(c,System.currentTimeMillis());
        if(directCharge>=0)watchEstimated=false;
        boolean watchCharge=watch>=100?false:directCharge>=0?directCharge==1:watchEstimated;
        boolean[] charging={phoneCharging(c),watchCharge,budsCharging.earbuds==1,budsCharging.caseState==1};'''
edit(widget,original,replacement)
original='''        boolean watchEstimated=MiniBatteryTrend.estimatedRising(mini,p.getString("mini_trend",MiniBatteryTrend.UNKNOWN),
                p.getLong("mini_trend_at",0),System.currentTimeMillis(),watchStale);
        int directCharge=MiniHuamiAuthMonitor.verifiedCharge(c,System.currentTimeMillis());
        if(directCharge<0)directCharge=MiniGattMonitor.verifiedCharge(c,System.currentTimeMillis());
        if(directCharge<0)directCharge=WatchChargingProbe.chargeState(c,System.currentTimeMillis());
        if(directCharge>=0)watchEstimated=false;
        boolean[] charging={phoneCharging(c),directCharge>=0?directCharge==1:watchEstimated,p.getBoolean("widget_buds_charge",false),p.getBoolean("widget_case_charge",false)};'''
replacement='''        boolean watchEstimated=MiniChargeHeuristic.visible(mini,watchStale,p.getBoolean("mini_inferred_charging",false));
        int directCharge=-1;
        if(p.getBoolean("mini_auth_auto",false))directCharge=MiniHuamiAuthMonitor.verifiedCharge(c,System.currentTimeMillis());
        if(directCharge<0&&p.getBoolean("mini_ble_auto",false))directCharge=MiniGattMonitor.verifiedCharge(c,System.currentTimeMillis());
        if(directCharge>=0)watchEstimated=false;
        boolean watchCharge=mini>=100?false:directCharge>=0?directCharge==1:watchEstimated;
        boolean[] charging={phoneCharging(c),watchCharge,p.getBoolean("widget_buds_charge",false),p.getBoolean("widget_case_charge",false)};'''
edit(widget,original,replacement)
original='''        boolean watchEstimated=charging[1] && MiniHuamiAuthMonitor.verifiedCharge(c,System.currentTimeMillis())<0
            && MiniGattMonitor.verifiedCharge(c,System.currentTimeMillis())<0
            && WatchChargingProbe.chargeState(c,System.currentTimeMillis())<0;'''
replacement='''        android.content.SharedPreferences watchPrefs=c.getSharedPreferences("bridge",Context.MODE_PRIVATE);
        boolean watchEstimated=charging[1] && MiniChargeHeuristic.visible(watch,watchStale,watchPrefs.getBoolean("mini_inferred_charging",false))
            && !watchPrefs.getBoolean("mini_auth_auto",false) && !watchPrefs.getBoolean("mini_ble_auto",false);'''
edit(widget,original,replacement)
# Inspect Android OS battery broadcasts BEFORE audio-specific handling.
receiver=JAVA/"BudsBatteryReceiver.java"
edit(receiver,'        String action=intent.getAction();','        String action=intent.getAction();\n        if(MiniSystemBattery.onBatteryBroadcast(context,intent))return;')
# Existing foreground service calls the no-GATT cache inspector every 2 minutes.
bridge=JAVA/"BridgeService.java"
edit(bridge,'            long now=System.currentTimeMillis();','            MiniSystemBattery.poll(getApplicationContext());\n            long now=System.currentTimeMillis();')
# Display estimate and 100% behavior; do not state a proven charger signal.
activity=JAVA/"MainActivity.java"
original='''        String syncMode=huamiAuto?"Huami 인증 충전+잔량":standardAuto?"표준 BLE 잔량(60초)":"자동 수신 꺼짐";'''
replacement='''        String syncMode=huamiAuto?"Huami 인증 충전+잔량 (Zepp 충돌 가능)":standardAuto?"표준 BLE 잔량(60초 · 충돌 가능)":"Zepp 수신/Android 배터리 이벤트 (직접 BLE 없음)";'''
edit(activity,original,replacement)
original='''        String miniState=verifiedMiniCharge==1?" · 충전 중 (직접 확인)":verifiedMiniCharge==0?" · 충전 중 아님 (직접 확인)":
            MiniBatteryTrend.UP.equals(miniTrend)?" · 잔량 상승(충전 추정)":MiniBatteryTrend.DOWN.equals(miniTrend)?" · 잔량 하락":"";
        int miniPercent=p.getInt("gts4mini",-1);
        if(seen>0&&miniPercent==100){
            int ext=p.getInt("mini_ble_external_power",-1);
            if(verifiedMiniCharge==0&&ext==1)miniState=" · 완충 추정(전원 연결 · 충전 중 아님)";
            else miniState=" · 잔량 100%(충전 종료 미확인)"+(verifiedMiniCharge==1?" · 충전 중":"");
        }'''
replacement='''        int miniPercent=p.getInt("gts4mini",-1);
        boolean inferred=MiniChargeHeuristic.visible(miniPercent,stale,p.getBoolean("mini_inferred_charging",false));
        boolean actualMode=huamiAuto||standardAuto;
        String miniState=miniPercent==100?" · 100% 완충 간주 · 충전 표시 해제":
            actualMode && verifiedMiniCharge==1?" · 충전 중 (직접 확인)":
            inferred?" · 충전 중 (잔량 증가로 추정)":
            MiniBatteryTrend.DOWN.equals(miniTrend)?" · 잔량 감소":"";
        if(stale&&miniPercent<100)miniState=" · 오래된 값 (충전 추정 일시 숨김)";'''
edit(activity,original,replacement)
edit(activity,'        String source=p.getString("mini_source","기존 수신");',
  '        String source=p.getString("mini_source","기존 수신");\n        String systemStatus=p.getString("mini_system_status","Android 배터리 캐시 검사 대기");')
edit(activity,'            "\\n최근 확인  "+when+" · "+source+(stale&&seen>0?" · 오래된 값":"")+"\\n자동 수신  "+syncMode+(!standardAuto&&!huamiAuto?" · 설정에서 복구 필요":"")+',
  '            "\\n최근 확인  "+when+" · "+source+(stale&&seen>0?" · 오래된 값":"")+"\\n자동 수신  "+syncMode+"\\nAndroid 상태  "+systemStatus+')
# Version and label: separate package for safe coexistence; no ability to reuse lost v79 test signing key.
manifest=ROOT/"app/src/main/AndroidManifest.xml"
edit(manifest,'android:versionCode="10079" android:versionName="0.79-huami-plain-query-fix"',
    'android:versionCode="10080" android:versionName="0.80-level-rise-estimate"')
edit(manifest,'android:name="org.example.galaxybatterybridge.permission.ZEPP_RELAY"',
    'android:name="org.example.galaxybatterybridge.v80.permission.ZEPP_RELAY"')
edit(manifest,'android:label="배터리 연동"',
    'android:label="배터리 연동 v80 테스트"')
# Pure JVM deterministic test (no Android libraries needed).
test=ROOT/"MiniChargeHeuristicTest.java"
test.write_text("""package org.example.galaxybatterybridge;
public final class MiniChargeHeuristicTest {
    private static void eq(boolean got,boolean want,String name){
        if(got!=want)throw new AssertionError(name+" expected "+want+" got "+got);
    }
    public static void main(String[] a){
        eq(MiniChargeHeuristic.next(false,-1,72),false,"first reading is baseline");
        eq(MiniChargeHeuristic.next(false,72,73),true,"rising starts");
        eq(MiniChargeHeuristic.next(true,73,73),true,"same percentage maintains");
        eq(MiniChargeHeuristic.next(true,99,100),false,"100 percent ends");
        eq(MiniChargeHeuristic.next(false,100,100),false,"full remains off");
        eq(MiniChargeHeuristic.next(true,74,73),false,"falling ends");
        eq(MiniChargeHeuristic.visible(73,false,true),true,"show estimate");
        eq(MiniChargeHeuristic.visible(100,false,true),false,"never show full as charging");
        eq(MiniChargeHeuristic.visible(73,true,true),false,"stale not live");
        System.out.println("BatteryTrio v80 heuristic tests passed");
    }
}
""")
print("v80 sources patched with no-GATT OS cache observer, rising estimate and 100% cutoff")
