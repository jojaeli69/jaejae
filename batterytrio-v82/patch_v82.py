#!/usr/bin/env python3
"""Fix Galaxy phone full-battery icon in BatteryTrioMini v82.
Preserves v81 Mini charging timeout logic and widget artwork.
"""
from pathlib import Path
root=Path("batterytrio-v80-src")
java=root/"app/src/main/java/org/example/galaxybatterybridge"
p=java/"BatteryWidget.java"
s=p.read_text()
old='''    private static boolean phoneCharging(Context c) {
        Intent i=c.registerReceiver(null,new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
        if(i==null) return false;
        int status=i.getIntExtra(BatteryManager.EXTRA_STATUS,-1);
        return i.getIntExtra(BatteryManager.EXTRA_PLUGGED,0)>0 &&
            (status==BatteryManager.BATTERY_STATUS_CHARGING || status==BatteryManager.BATTERY_STATUS_FULL);
    }'''
new='''    private static boolean phoneCharging(Context c) {
        Intent i=c.registerReceiver(null,new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
        if(i==null)return false;
        int level=i.getIntExtra(BatteryManager.EXTRA_LEVEL,-1);
        int scale=i.getIntExtra(BatteryManager.EXTRA_SCALE,100);
        int percentage=level<0||scale<=0?-1:(int)Math.round(level*100.0/scale);
        int status=i.getIntExtra(BatteryManager.EXTRA_STATUS,-1);
        boolean isPlugged=i.getIntExtra(BatteryManager.EXTRA_PLUGGED,0)>0;
        return PhoneChargeRule.showBolt(isPlugged,
            status==BatteryManager.BATTERY_STATUS_CHARGING,percentage);
    }'''
assert s.count(old)==1,f"expected phoneCharging original once, got {s.count(old)}"
p.write_text(s.replace(old,new))
(java/"PhoneChargeRule.java").write_text("""package org.example.galaxybatterybridge;

/** Distinguish powered/fully charged from actively charging on the phone ring. */
final class PhoneChargeRule {
    private PhoneChargeRule(){}
    static boolean showBolt(boolean plugged,boolean activelyCharging,int percentage) {
        return plugged&&activelyCharging&&percentage>=0&&percentage<100;
    }
}
""")
tests=root/"PhoneChargeRuleTest.java"
tests.write_text("""package org.example.galaxybatterybridge;
public final class PhoneChargeRuleTest {
    static void check(boolean got,boolean want,String caseName) {
        if(got!=want)throw new AssertionError(caseName);
    }
    public static void main(String[] args){
        check(PhoneChargeRule.showBolt(true,true,25),true,"25% charging");
        check(PhoneChargeRule.showBolt(true,true,99),true,"99% charging");
        check(PhoneChargeRule.showBolt(true,true,100),false,"100% even when status charging");
        check(PhoneChargeRule.showBolt(true,false,100),false,"100% full");
        check(PhoneChargeRule.showBolt(true,false,80),false,"battery protect full at 80%");
        check(PhoneChargeRule.showBolt(false,true,85),false,"unplugged");
        check(PhoneChargeRule.showBolt(true,true,-1),false,"unknown level");
        System.out.println("Phone full-battery icon tests passed");
    }
}
""")
m=root/"app/src/main/AndroidManifest.xml"
ms=m.read_text()
old='android:versionCode="10081" android:versionName="0.81-charge-expiry-5min"'
new='android:versionCode="10082" android:versionName="0.82-phone-full-no-bolt"'
assert ms.count(old)==1
ms=ms.replace(old,new)
old='android:name="org.example.galaxybatterybridge.v81.permission.ZEPP_RELAY"'
new='android:name="org.example.galaxybatterybridge.v82.permission.ZEPP_RELAY"'
assert ms.count(old)==1
ms=ms.replace(old,new)
old='android:label="배터리 연동 v81 테스트"'
new='android:label="배터리 연동 v82 테스트"'
assert ms.count(old)==1
ms=ms.replace(old,new)
m.write_text(ms)
print("BatteryTrioMini v82 phone charge icon: only show lightning for plugged, actively charging and below 100%")
