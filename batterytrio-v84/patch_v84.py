#!/usr/bin/env python3
"""v84: use user-approved Samsung battery widget as GTS 4 Mini battery source.
Never initiate GATT or Huami auth in this mode. Only accept a real RemoteViews
update and an unambiguous watch icon OR the explicitly selected second-row case.
"""
from pathlib import Path
R=Path("batterytrio-v80-src")
J=R/"app/src/main/java/org/example/galaxybatterybridge"
def edit(path,before,after,n=1):
    s=path.read_text()
    assert s.count(before)==n,f"{path.name}: wanted {n} got {s.count(before)}: {before[:85]}"
    path.write_text(s.replace(before,after,n))
(J/"SamsungMiniSelector.java").write_text("""package org.example.galaxybatterybridge;

/** Refuse to guess if the Samsung provider's device order is ambiguous. */
final class SamsungMiniSelector {
    private SamsungMiniSelector(){}
    static int select(boolean userOptedIn,boolean newProviderFrame,
       int phoneLevel,int identifiedWatchLevel,int exactTextRowCount,
       int firstRowLevel,int secondRowLevel) {
        if(!userOptedIn||!newProviderFrame)return -1;
        if(identifiedWatchLevel>=0&&identifiedWatchLevel<=100)return identifiedWatchLevel;
        if(exactTextRowCount!=2||phoneLevel<0||phoneLevel>100||
            firstRowLevel!=phoneLevel||secondRowLevel<0||secondRowLevel>100)return -1;
        return secondRowLevel;
    }
}
""")
# Parse only distinct numeric TEXT views in view order. Accessibility descriptions
# can duplicate the same number and are deliberately excluded from this fallback.
bridge=J/"SamsungWidgetBridge.java"
edit(bridge,
     "    /** A user-approved host that actually received its provider's RemoteViews. */",
     '''    /** Explicitly confirmed by owner: the second displayed device is GTS 4 Mini.
     * A fallback is permitted only for EXACTLY two numeric TextViews and a
     * first row that matches the Android phone battery reading.
     * Samsung may reorder rows; in that case the route stops.
     */
    int secondDeviceLevelWhenPhoneMatches(int phoneLevel) {
        if(!hasConfirmedProviderFrame()||view==null||phoneLevel<0)return -1;
        List<Integer> nums=new ArrayList<>();
        numericTextViews(view,nums,0);
        if(nums.size()!=2||nums.get(0)!=phoneLevel)return -1;
        return nums.get(1);
    }
    long confirmedProviderUpdatedAt(){return latestProviderUpdateAt;}
    /** A user-approved host that actually received its provider's RemoteViews. */''')
edit(bridge,
     '        b.append("원본 갱신 횟수: ").append(providerUpdateCount).append("\\n");',
     '''        b.append("원본 갱신 횟수: ").append(providerUpdateCount).append("\\n");
        android.content.SharedPreferences bp=context.getSharedPreferences("bridge",0);
        b.append("GTS 4 Mini 삼성 연동: ").append(bp.getBoolean("samsungMiniMapEnabled",false)?"활성":"꺼짐").append("\\n");
        b.append("Mini 경로: ").append(bp.getString("samsungMiniRouteStatus","원본 위젯 판독 대기")).append("\\n");''')
(J/"SamsungMiniRelay.java").write_text("""package org.example.galaxybatterybridge;

import android.content.Context;
import android.content.SharedPreferences;

/** Do NOT pair or connect. Copies only an explicitly user-approved Samsung
 * widget's on-device numeric watch row AFTER a real RemoteViews provider update.
 */
final class SamsungMiniRelay {
    private SamsungMiniRelay(){}
    static void importLatest(Context context,SamsungWidgetBridge source,int phoneLevel) {
        SharedPreferences p=context.getSharedPreferences("bridge",Context.MODE_PRIVATE);
        if(!p.getBoolean("samsungMiniMapEnabled",false))return;
        if(p.getBoolean("mini_auth_auto",false)||p.getBoolean("mini_ble_auto",false)){
            p.edit().putString("samsungMiniRouteStatus","직접 BLE가 켜져 있어 삼성 Mini 연동은 대기").apply();
            return;
        }
        if(!source.hasConfirmedProviderFrame())return;
        long providerAt=source.confirmedProviderUpdatedAt();
        if(providerAt<=0L||providerAt<=p.getLong("samsungMiniLastSourceAt",0L))return;
        // Read only real per-device source values, not arbitrary second ring pixels.
        SamsungStateReader.State state=source.sourceState();
        int identified=state.levels[SamsungStateReader.WATCH];
        int second=source.secondDeviceLevelWhenPhoneMatches(phoneLevel);
        int level=SamsungMiniSelector.select(true,true,phoneLevel,identified,
            second>=0?2:0,phoneLevel,second);
        if(level<0){
            p.edit().putString("samsungMiniRouteStatus",
              "새 삼성 원본은 수신했지만 워치 아이콘/두 번째 숫자 식별 불가 · 기존 값 유지").apply();
            return;
        }
        long now=System.currentTimeMillis();
        // Honor the actual event time, not the time the local widget view was scanned.
        if(providerAt>now||now-providerAt>10L*60L*1000L)return;
        int prev=p.getInt("gts4mini",-1);
        boolean risen=MiniChargeHeuristic.next(p.getBoolean("mini_inferred_charging",false),prev,level);
        long riseAt=MiniChargeHeuristic.lastRiseAt(prev,level,p.getLong("mini_last_increase",0L),providerAt);
        int nativeCharge=(identified==level)?state.charges[SamsungStateReader.WATCH]:-1;
        // At 100%, user explicitly wants no lightning icon regardless of cable state.
        if(level==100)nativeCharge=0;
        String mode=(identified==level?"삼성 워치 아이콘 식별":"삼성 2기기 순서 확인");
        String trend=prev>=0&&level>prev?"UP":prev>=0&&level<prev?"DOWN":"UNKNOWN";
        SharedPreferences.Editor e=p.edit()
            .putInt("gts4mini",level)
            .putLong("mini_seen",providerAt)
            .putString("mini_source","Samsung widget GTS 4 Mini")
            .putBoolean("mini_inferred_charging",risen)
            .putLong("mini_last_increase",riseAt)
            .putString("mini_trend",trend)
            .putLong("mini_trend_at",trend.equals("UNKNOWN")?0L:providerAt)
            .putLong("mini_last_change",prev!=level?providerAt:p.getLong("mini_last_change",0))
            .putLong("samsungMiniLastSourceAt",providerAt)
            .putInt("samsungMiniNativeCharge",nativeCharge)
            .putString("samsungMiniRouteStatus",mode+" · "+level+"% · 원본갱신 "+(now-providerAt)/1000+"초 전");
        e.apply();
        if(prev!=level)ReceiveHistory.record(context,level,providerAt);
    }
    static int sourceCharge(Context c) {
        SharedPreferences p=c.getSharedPreferences("bridge",Context.MODE_PRIVATE);
        if(!p.getBoolean("samsungMiniMapEnabled",false)||
           p.getBoolean("mini_auth_auto",false)||p.getBoolean("mini_ble_auto",false))return -1;
        long at=p.getLong("samsungMiniLastSourceAt",0L),now=System.currentTimeMillis();
        if(at<=0L||now<at||now-at>10L*60L*1000L)return -1;
        int status=p.getInt("samsungMiniNativeCharge",-1);
        return status>=0&&status<=1?status:-1;
    }
}
""")
# Native provider frame is received in SamsungWidgetBridge.onProviderUpdate().
# It already calls BatteryWidget.refresh(c) after source parsing; align both
# the regular widget path and watch-only fast refresh.
widget=J/"BatteryWidget.java"
edit(widget,
    '        int phone = phoneBattery(c);',
    '''        int phone = phoneBattery(c);
        SamsungMiniRelay.importLatest(c,nativeBridge,phone);''')
edit(widget,
     '''        if(directCharge>=0)watchEstimated=false;
        boolean watchCharge=watch>=100?false:directCharge>=0?directCharge==1:watchEstimated;''',
     '''        if(directCharge>=0)watchEstimated=false;
        int nativeSamsungCharge=SamsungMiniRelay.sourceCharge(c);
        boolean watchCharge=watch>=100?false:directCharge>=0?directCharge==1:
            nativeSamsungCharge>=0?nativeSamsungCharge==1:watchEstimated;''')
edit(widget,
     '''        if(directCharge>=0)watchEstimated=false;
        boolean watchCharge=mini>=100?false:directCharge>=0?directCharge==1:watchEstimated;''',
     '''        if(directCharge>=0)watchEstimated=false;
        int nativeSamsungCharge=SamsungMiniRelay.sourceCharge(c);
        boolean watchCharge=mini>=100?false:directCharge>=0?directCharge==1:
            nativeSamsungCharge>=0?nativeSamsungCharge==1:watchEstimated;''')
# Add a visible opt-in switch; toggling to Samsung mode shuts off both direct
# BLE modes without deleting credentials. Stop old GATT service on restart.
activity=J/"MainActivity.java"
edit(activity,
     '''        advanced.addView(checkSamsung);''',
     '''        advanced.addView(checkSamsung);
        Switch samsungMiniMap=new Switch(this);
        samsungMiniMap.setText("삼성 배터리 위젯의 GTS 4 Mini 사용 · 직접 BLE 끄기");
        samsungMiniMap.setTextColor(-1);
        samsungMiniMap.setTextSize(14);
        samsungMiniMap.setPadding(0,dp(18),0,dp(18));
        samsungMiniMap.setChecked(getSharedPreferences("bridge",MODE_PRIVATE)
            .getBoolean("samsungMiniMapEnabled",false));
        advanced.addView(samsungMiniMap);
        samsungMiniMap.setOnCheckedChangeListener((button,enabled)->{
            android.content.SharedPreferences.Editor ed=getSharedPreferences("bridge",MODE_PRIVATE)
                .edit().putBoolean("samsungMiniMapEnabled",enabled);
            if(enabled)ed.putBoolean("mini_ble_auto",false)
                .putBoolean("mini_auth_auto",false);
            ed.apply();
            startBridge(); // updateBleMonitor() stops any active direct GATT monitor.
            if(widgetBridge!=null)widgetBridge.scanAndSave();
            BatteryWidget.refresh(this);
            update();
        });''')

# In Samsung-first mode, never establish any independent BLE session even
# if an old preference is accidentally re-enabled later.
edit(J/"BridgeService.java",
     '''        boolean auth=p.getBoolean("mini_auth_auto",false);
        boolean basic=p.getBoolean("mini_ble_auto",false);''',
     '''        boolean samsungMiniMode=p.getBoolean("samsungMiniMapEnabled",false);
        boolean auth=!samsungMiniMode&&p.getBoolean("mini_auth_auto",false);
        boolean basic=!samsungMiniMode&&p.getBoolean("mini_ble_auto",false);''')

manifest=R/"app/src/main/AndroidManifest.xml"
edit(manifest,'android:versionCode="10083" android:versionName="0.83-samsung-native-bridge"',
    'android:versionCode="10084" android:versionName="0.84-samsung-gts-mini-no-gatt"')
edit(manifest,'android:name="org.example.galaxybatterybridge.v83.permission.ZEPP_RELAY"',
    'android:name="org.example.galaxybatterybridge.v84.permission.ZEPP_RELAY"')
edit(manifest,'android:label="배터리 연동 v83 테스트"','android:label="배터리 연동 v84 테스트"')
(R/"SamsungMiniSelectorTest.java").write_text("""package org.example.galaxybatterybridge;
public final class SamsungMiniSelectorTest {
  static void eq(int got,int want,String which){if(got!=want)throw new AssertionError(which+": "+got+" expected "+want);}
  public static void main(String[] a){
    eq(SamsungMiniSelector.select(true,true,70,80,0,70,-1),80,"Watch icon recognized");
    eq(SamsungMiniSelector.select(true,true,70,-1,2,70,80),80,"Confirmed second device");
    eq(SamsungMiniSelector.select(false,true,70,80,2,70,80),-1,"Not opted in");
    eq(SamsungMiniSelector.select(true,false,70,-1,2,70,80),-1,"No provider frame");
    eq(SamsungMiniSelector.select(true,true,70,-1,3,70,80),-1,"Extra device row");
    eq(SamsungMiniSelector.select(true,true,70,-1,2,69,80),-1,"Wrong first row");
    eq(SamsungMiniSelector.select(true,true,70,-1,2,70,-1),-1,"No second row");
    eq(SamsungMiniSelector.select(true,true,100,-1,2,100,100),100,"Both full");
    System.out.println("v84 Samsung Mini selector tests passed");
  }
}
""")
print("v84 Samsung Mini source relay enabled, original Zepp BLE kept untouched")
