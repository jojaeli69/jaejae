#!/usr/bin/env python3
"""v83: mirror *confirmed* Samsung widget charge glyph when unique phone row
matches Android percentage. Galaxy phone state continues to receive immediate
Android battery broadcasts; Buds/case state uses user-approved Samsung host.
No accessibility service or private Samsung DB access.
"""
from pathlib import Path
ROOT=Path("batterytrio-v80-src")
JAVA=ROOT/"app/src/main/java/org/example/galaxybatterybridge"
def edit(p,before,after,n=1):
    s=p.read_text()
    assert s.count(before)==n,(p.name,s.count(before),n,before[:110])
    p.write_text(s.replace(before,after,n))
(JAVA/"SamsungMirrorPolicy.java").write_text("""package org.example.galaxybatterybridge;
/** Only mirror a Samsung provider's explicit state when its device row
 * can be confidently linked to the same phone percentage. */
final class SamsungMirrorPolicy {
    private SamsungMirrorPolicy(){}
    static int matchedPhoneCharge(boolean approvedProvider,int systemLevel,int samsungLevel,int samsungCharging){
        if(!approvedProvider||systemLevel<0||systemLevel>100
             ||samsungLevel!=systemLevel||samsungCharging<0||samsungCharging>1) return -1;
        return samsungCharging;
    }
}
""")
bridge=JAVA/"SamsungWidgetBridge.java"
edit(bridge,
     '    SamsungStateReader.State sourceState(){return stateReader.state;}',
     '''    /** A user-approved host that actually received its provider's RemoteViews. */
    boolean hasConfirmedProviderFrame(){return widgetId>=0 && providerFrameReceived;}
    SamsungStateReader.State sourceState(){return stateReader.state;}''')
widget=JAVA/"BatteryWidget.java"
edit(widget,
     '''        SamsungStateReader.State source=nativeBridge.sourceState();
        int mask=source.budsMask!=0?source.budsMask:budsCharging.mask();''',
     '''        SamsungStateReader.State source=nativeBridge.sourceState();
        // Phone: Android's power event remains the fallback. If a user-approved
        // Samsung widget has received a native update with a uniquely recognized
        // phone row at the same percentage, its charge glyph takes priority.
        int samsungPhone=SamsungMirrorPolicy.matchedPhoneCharge(
            nativeBridge.hasConfirmedProviderFrame(),phone,source.levels[SamsungStateReader.PHONE],
            source.charges[SamsungStateReader.PHONE]);
        if(samsungPhone>=0)charging[0]=samsungPhone==1;
        int mask=source.budsMask!=0?source.budsMask:budsCharging.mask();''')
# Existing Buds and case path already consumes the approved Samsung widget's
# explicit charge state; preserve it intact. Also preserve Zepp watch values.
reader=JAVA/"SamsungStateReader.java"
old='''  next.report=report+"충전 점: "+next.chargingDots+"\\n버즈 좌우: "+(next.budsMask==1?"왼쪽":next.budsMask==2?"오른쪽":next.budsMask==3?"양쪽":"판독 안 됨");if(next.left>=0||next.right>=0)next.report+="\\n왼쪽 "+next.left+"% / 오른쪽 "+next.right+"%";next.report+="\\n케이스 충전: "+(next.charges[CASE]==1?"충전 중":next.charges[CASE]==0?"충전 표시 없음":"미확인");state=next;'''
new='''  next.report=report+"충전 점: "+next.chargingDots+"\\n버즈 좌우: "+(next.budsMask==1?"왼쪽":next.budsMask==2?"오른쪽":next.budsMask==3?"양쪽":"판독 안 됨");if(next.left>=0||next.right>=0)next.report+="\\n왼쪽 "+next.left+"% / 오른쪽 "+next.right+"%";
  for(int k=0;k<4;k++) next.report+="\\n"+new String[]{"휴대폰","워치(식별 전 미적용)","버즈","케이스"}[k]+": "+(next.levels[k]>=0?next.levels[k]+"%":"숫자 미인식")+" / "+(next.charges[k]==1?"삼성 충전 표시":next.charges[k]==0?"삼성 충전 표시 없음":"충전 상태 미확인");
  state=next;'''
edit(reader,old,new)
m=ROOT/"app/src/main/AndroidManifest.xml"
edit(m,
    'android:versionCode="10082" android:versionName="0.82-phone-full-no-bolt"',
    'android:versionCode="10083" android:versionName="0.83-samsung-native-bridge"')
edit(m,
    'android:name="org.example.galaxybatterybridge.v82.permission.ZEPP_RELAY"',
    'android:name="org.example.galaxybatterybridge.v83.permission.ZEPP_RELAY"')
edit(m,'android:label="배터리 연동 v82 테스트"',
       'android:label="배터리 연동 v83 테스트"')
(ROOT/"SamsungMirrorPolicyTest.java").write_text("""package org.example.galaxybatterybridge;
public final class SamsungMirrorPolicyTest {
    private static void eq(int found,int want,String name){
        if(found!=want)throw new AssertionError(name+" got "+found+" wanted "+want);
    }
    public static void main(String[] a){
        eq(SamsungMirrorPolicy.matchedPhoneCharge(true,100,100,0),0,"Samsung shows full without bolt");
        eq(SamsungMirrorPolicy.matchedPhoneCharge(true,80,80,1),1,"Samsung shows charging");
        eq(SamsungMirrorPolicy.matchedPhoneCharge(true,80,79,1),-1,"stale percentage, use Android");
        eq(SamsungMirrorPolicy.matchedPhoneCharge(false,80,80,1),-1,"no confirmed user bound widget");
        eq(SamsungMirrorPolicy.matchedPhoneCharge(true,80,-1,1),-1,"unknown native phone row");
        eq(SamsungMirrorPolicy.matchedPhoneCharge(true,80,80,-1),-1,"unknown native charge glyph");
        System.out.println("v83 Samsung confirmed phone row policy tests passed");
    }
}
""")
print("BatteryTrio v83: confirmed Samsung bound widget phone charging mirror, native charge report; no Huami changes")
