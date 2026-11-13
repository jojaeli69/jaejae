#!/usr/bin/env python3
"""v81: decay inferred charging after five minutes without battery increase.
Never claims charger disconnection was directly observed."""
from pathlib import Path
ROOT=Path("batterytrio-v80-src")
JAVA=ROOT/"app/src/main/java/org/example/galaxybatterybridge"
def edit(path,before,after,count=1):
    s=path.read_text()
    found=s.count(before)
    if found!=count:raise AssertionError(f"{path.name} expected {count} matches got {found}: {before[:140]}")
    path.write_text(s.replace(before,after,count))
heuristic=JAVA/"MiniChargeHeuristic.java"
edit(heuristic,"""    public static boolean visible(int level,boolean stale,boolean estimatedCharging) {
        return !stale&&level>=0&&level<100&&estimatedCharging;
    }""","""    public static final long MAX_ESTIMATE_MS=5L*60L*1000L;
    public static long lastRiseAt(int previous,int current,long previousRiseAt,long now) {
        if(current<0||current>=100||previous>current)return 0L;
        return previous>=0&&previous<current?now:previousRiseAt;
    }
    public static boolean visible(int level,boolean stale,boolean estimatedCharging,long riseAt,long now) {
        return !stale&&level>=0&&level<100&&estimatedCharging&&riseAt>0
            &&now>=riseAt&&(now-riseAt)<MAX_ESTIMATE_MS;
    }""")
# Record time when a fresh battery increase is actually observed. Identical values
# must NOT reset this timer. A lower reading and 100% reset the timer immediately.
for name,old,new in [
 ("BridgeService.java",
  '.putBoolean("mini_inferred_charging",MiniChargeHeuristic.next(prefs.getBoolean("mini_inferred_charging",false),previous,level))',
  '.putBoolean("mini_inferred_charging",MiniChargeHeuristic.next(prefs.getBoolean("mini_inferred_charging",false),previous,level))\n                .putLong("mini_last_increase",MiniChargeHeuristic.lastRiseAt(previous,level,prefs.getLong("mini_last_increase",0),System.currentTimeMillis()))'),
 ("MiniGattMonitor.java",
  '.putBoolean("mini_inferred_charging",MiniChargeHeuristic.next(p.getBoolean("mini_inferred_charging",false),previous,level))',
  '.putBoolean("mini_inferred_charging",MiniChargeHeuristic.next(p.getBoolean("mini_inferred_charging",false),previous,level))\n            .putLong("mini_last_increase",MiniChargeHeuristic.lastRiseAt(previous,level,p.getLong("mini_last_increase",0),System.currentTimeMillis()))'),
 ("MiniHuamiAuthMonitor.java",
  '.putBoolean("mini_inferred_charging",MiniChargeHeuristic.next(p.getBoolean("mini_inferred_charging",false),oldLevel,f.percent))',
  '.putBoolean("mini_inferred_charging",MiniChargeHeuristic.next(p.getBoolean("mini_inferred_charging",false),oldLevel,f.percent))\n            .putLong("mini_last_increase",MiniChargeHeuristic.lastRiseAt(oldLevel,f.percent,p.getLong("mini_last_increase",0),System.currentTimeMillis()))'),
 ("MiniHuamiAuthMonitor.java",
  '.putBoolean("mini_inferred_charging",MiniChargeHeuristic.next(p.getBoolean("mini_inferred_charging",false),old,level))',
  '.putBoolean("mini_inferred_charging",MiniChargeHeuristic.next(p.getBoolean("mini_inferred_charging",false),old,level))\n            .putLong("mini_last_increase",MiniChargeHeuristic.lastRiseAt(old,level,p.getLong("mini_last_increase",0),System.currentTimeMillis()))'),
 ("MiniSystemBattery.java",
  '.putBoolean("mini_inferred_charging",charge)',
  '.putBoolean("mini_inferred_charging",charge)\n            .putLong("mini_last_increase",MiniChargeHeuristic.lastRiseAt(old,next,p.getLong("mini_last_increase",0),now))')
]:
    edit(JAVA/name,old,new)
widget=JAVA/"BatteryWidget.java"
edit(widget,
     'MiniChargeHeuristic.visible(watch,watchStale,p.getBoolean("mini_inferred_charging",false))',
     'MiniChargeHeuristic.visible(watch,watchStale,p.getBoolean("mini_inferred_charging",false),p.getLong("mini_last_increase",0),System.currentTimeMillis())')
edit(widget,
     'MiniChargeHeuristic.visible(mini,watchStale,p.getBoolean("mini_inferred_charging",false))',
     'MiniChargeHeuristic.visible(mini,watchStale,p.getBoolean("mini_inferred_charging",false),p.getLong("mini_last_increase",0),System.currentTimeMillis())')
edit(widget,
     'MiniChargeHeuristic.visible(watch,watchStale,watchPrefs.getBoolean("mini_inferred_charging",false))',
     'MiniChargeHeuristic.visible(watch,watchStale,watchPrefs.getBoolean("mini_inferred_charging",false),watchPrefs.getLong("mini_last_increase",0),System.currentTimeMillis())')
# schedule one alarm at the actual expiry while an estimate is visible; if the
# estimate is no longer visible, cancel any previously scheduled timeout.
edit(widget,
     '        int directCharge=-1;',
     '        MiniChargeTimeout.schedule(c,p.getLong("mini_last_increase",0),watchEstimated);\n        int directCharge=-1;',
     count=2)
activity=JAVA/"MainActivity.java"
edit(activity,
     'MiniChargeHeuristic.visible(miniPercent,stale,p.getBoolean("mini_inferred_charging",false))',
     'MiniChargeHeuristic.visible(miniPercent,stale,p.getBoolean("mini_inferred_charging",false),p.getLong("mini_last_increase",0),System.currentTimeMillis())')
(JAVA/"MiniChargeTimeout.java").write_text("""package org.example.galaxybatterybridge;

import android.app.AlarmManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/** Triggers a widget redraw after the battery-rise charging estimate expires. */
public final class MiniChargeTimeout extends BroadcastReceiver {
    private static final int REQUEST_CODE=81081;
    private static PendingIntent intent(Context c) {
        Intent i=new Intent(c,MiniChargeTimeout.class);
        return PendingIntent.getBroadcast(c,REQUEST_CODE,i,
            PendingIntent.FLAG_IMMUTABLE|PendingIntent.FLAG_UPDATE_CURRENT);
    }
    static void schedule(Context c,long lastRise,boolean visible) {
        AlarmManager alarms=(AlarmManager)c.getSystemService(Context.ALARM_SERVICE);
        if(alarms==null)return;
        PendingIntent p=intent(c);
        if(!visible||lastRise<=0L){alarms.cancel(p);return;}
        long cutoff=lastRise+MiniChargeHeuristic.MAX_ESTIMATE_MS+1000L;
        if(cutoff<=System.currentTimeMillis()){alarms.cancel(p);return;}
        alarms.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP,cutoff,p);
    }
    @Override public void onReceive(Context c,Intent i) {
        BatteryWidget.refreshWatch(c);
    }
}
""")
manifest=ROOT/"app/src/main/AndroidManifest.xml"
edit(manifest,'</application>','  <receiver android:name="org.example.galaxybatterybridge.MiniChargeTimeout" android:exported="false" />\n</application>')
edit(manifest,'android:versionCode="10080" android:versionName="0.80-level-rise-estimate"',
    'android:versionCode="10081" android:versionName="0.81-charge-expiry-5min"')
edit(manifest,'android:name="org.example.galaxybatterybridge.v80.permission.ZEPP_RELAY"',
    'android:name="org.example.galaxybatterybridge.v81.permission.ZEPP_RELAY"')
edit(manifest,'android:label="배터리 연동 v80 테스트"','android:label="배터리 연동 v81 테스트"')
# Update and extend v80 unit tests.
tests=ROOT/"MiniChargeHeuristicTest.java"
edit(tests,
 'eq(MiniChargeHeuristic.visible(73,false,true),true,"show estimate");',
 'eq(MiniChargeHeuristic.visible(73,false,true,100000,100001),true,"show estimate");')
edit(tests,
 'eq(MiniChargeHeuristic.visible(100,false,true),false,"never show full as charging");',
 'eq(MiniChargeHeuristic.visible(100,false,true,100000,100001),false,"never show full as charging");')
edit(tests,
 'eq(MiniChargeHeuristic.visible(73,true,true),false,"stale not live");',
 '''eq(MiniChargeHeuristic.visible(73,true,true,100000,100001),false,"stale not live");
        eq(MiniChargeHeuristic.visible(92,false,true,100000,400001),false,"five minutes later should stop");
        eq(MiniChargeHeuristic.visible(92,false,true,100000,399999),true,"before five minutes keep");
        eq(MiniChargeHeuristic.visible(92,false,true,0,399999),false,"old data with no rise timestamp not charging");
        eq(MiniChargeHeuristic.lastRiseAt(91,92,0,100000)==100000,true,"rising starts timer");
        eq(MiniChargeHeuristic.lastRiseAt(92,92,100000,150000)==100000,true,"same percentage does not extend");
        eq(MiniChargeHeuristic.lastRiseAt(92,91,100000,160000)==0,true,"falling clears timer");
        eq(MiniChargeHeuristic.lastRiseAt(99,100,100000,160000)==0,true,"full clears timer");''')
edit(tests,'BatteryTrio v80 heuristic tests passed','BatteryTrio v81 timeout tests passed')
print("v81: infer from 5-minute freshness of latest verified rise, alarm redraw included")
