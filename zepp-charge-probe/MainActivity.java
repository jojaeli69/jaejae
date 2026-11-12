package org.example.zeppchargeprobe;

import android.app.Activity;
import android.app.Notification;
import android.content.Intent;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.content.pm.ProviderInfo;
import android.content.pm.ServiceInfo;
import android.content.pm.ActivityInfo;
import android.os.Bundle;
import android.provider.Settings;
import android.service.notification.StatusBarNotification;
import android.graphics.Color;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import java.util.Locale;

public class MainActivity extends Activity {
  private static final String ZEPP = "com.huami.watch.hmwatchmanager";
  private TextView report;
  private StringBuilder lines = new StringBuilder();
  private void write(String s) { lines.append(s).append("\n"); if(report != null) report.setText(lines.toString()); }
  private void clear(String title) { lines = new StringBuilder(); write(title); write(""); }
  private Button button(String label, final View.OnClickListener action) {
    Button b = new Button(this);
    b.setText(label);
    b.setAllCaps(false);
    b.setTextSize(15);
    b.setOnClickListener(action);
    return b;
  }
  @Override public void onCreate(Bundle state) {
    super.onCreate(state);
    LinearLayout panel = new LinearLayout(this);
    panel.setOrientation(LinearLayout.VERTICAL);
    panel.setPadding(20, 22, 20, 18);
    panel.setBackgroundColor(Color.WHITE);
    TextView title = new TextView(this);
    title.setText("Zepp 충전 상태 경로 검사");
    title.setTextSize(21);
    title.setTextColor(Color.BLACK);
    title.setPadding(0, 0, 0, 10);
    panel.addView(title);
    TextView intro = new TextView(this);
    intro.setText("Huami 직접 BLE 연결을 전혀 사용하지 않습니다. Zepp 앱의 공개 구성요소 및 사용자가 허용한 Zepp 알림만 기기 안에서 확인합니다. 인터넷 전송·개인정보 업로드 없음.");
    intro.setTextSize(13);
    intro.setTextColor(Color.DKGRAY);
    panel.addView(intro);
    panel.addView(button("1. Zepp 외부 공개 경로 검사", v -> scanZepp()));
    panel.addView(button("2. 알림 접근 설정 열기 (선택)", v -> {
      try { startActivity(new Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS)); }
      catch(Exception e) { write("설정 화면 열기 실패: "+e.getClass().getSimpleName()); }
    }));
    panel.addView(button("3. Zepp 알림의 충전 문구 검사", v -> scanZeppNotifications()));
    panel.addView(button("4. 전체 재검사", v -> { scanZepp(); scanZeppNotifications(); }));
    ScrollView scroll = new ScrollView(this);
    report = new TextView(this);
    report.setTextSize(13);
    report.setTextColor(Color.BLACK);
    report.setTextIsSelectable(true);
    report.setPadding(12, 12, 12, 12);
    scroll.addView(report);
    panel.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1f));
    setContentView(panel);
    clear("현재 상태: 검사 전");
    write("워치는 Zepp와 평소대로 연결하세요.");
    write("v79의 Huami 직접 연동은 꺼둔 상태에서 테스트하세요.");
    write("충전 전/충전 중 두 번씩 3번 버튼을 눌러 비교합니다.");
  }
  private static boolean relevant(String s) {
    if(s == null) return false;
    String v=s.toLowerCase(Locale.ROOT);
    return v.contains("battery") || v.contains("charg") || v.contains("power") || v.contains("배터리") || v.contains("충전") || v.contains("电池") || v.contains("充电") || v.contains("電池") || v.contains("充電");
  }
  private void scanZepp() {
    clear("1. Zepp 공개 구성요소 검사");
    PackageManager pm=getPackageManager();
    try {
      PackageInfo p=pm.getPackageInfo(ZEPP, PackageManager.GET_PROVIDERS | PackageManager.GET_SERVICES | PackageManager.GET_RECEIVERS);
      write("Zepp 설치 확인 / version: "+p.versionName);
      int exported=0, relevantCount=0;
      if(p.providers!=null) for(ProviderInfo c:p.providers) if(c.exported) {
        exported++; String s="PROVIDER "+c.name+"  authority="+c.authority+"  read="+c.readPermission;
        if(relevant(s)){write(s);relevantCount++;}
      }
      if(p.services!=null) for(ServiceInfo c:p.services) if(c.exported) {
        exported++;String s="SERVICE "+c.name+"  permission="+c.permission;
        if(relevant(s)){write(s);relevantCount++;}
      }
      if(p.receivers!=null) for(ActivityInfo c:p.receivers) if(c.exported) {
        exported++;String s="RECEIVER "+c.name+"  permission="+c.permission;
        if(relevant(s)){write(s);relevantCount++;}
      }
      write("내보낸 구성요소 수: "+exported);
      write("이름에 배터리·충전 관련 단어가 포함된 공개 구성요소: "+relevantCount);
      write("0개여도 다른 경로가 절대 없다는 뜻은 아닙니다.");
      write("구성요소의 존재만으로 충전 데이터를 읽을 권한이 생기지 않습니다.");
    } catch(PackageManager.NameNotFoundException e) {
      write("Zepp 패키지가 안 보입니다. 설치 여부 및 기기 프로필을 확인하세요.");
    } catch(Exception e) {write("검사 오류: "+e.getClass().getSimpleName()+": "+e.getMessage());}
  }
  private void scanZeppNotifications() {
    clear("3. Zepp 알림 검사");
    ZeppNotificationListener listener=ZeppNotificationListener.instance;
    if(listener==null) {
      write("알림 접근이 활성화되지 않았거나 서비스가 아직 연결되지 않았습니다.");
      write("2번 버튼 → Zepp Charge Probe 접근 허용 → 앱으로 돌아와 다시 검사하세요.");
      write("삼성 '제한된 설정' 안내가 표시되면 설정 > 애플리케이션 > Zepp Charge Probe > 우측 상단 메뉴 > 제한된 설정 허용에서 허용 후 다시 시도할 수 있습니다.");
      return;
    }
    StatusBarNotification[] notifications;
    try {notifications=listener.getActiveNotifications();}
    catch(Exception e){write("알림 확인 실패: "+e.getClass().getSimpleName());return;}
    if(notifications==null){write("현재 시스템 알림 목록을 불러오지 못했습니다.");return;}
    int zeppCount=0,chargeCount=0;
    for(StatusBarNotification sbn:notifications) {
      if(!ZEPP.equals(sbn.getPackageName()))continue;
      zeppCount++;
      Bundle b=sbn.getNotification().extras;
      if(b==null)continue;
      CharSequence t=b.getCharSequence(Notification.EXTRA_TITLE);
      CharSequence c=b.getCharSequence(Notification.EXTRA_TEXT);
      String title=t==null?"":t.toString();
      String body=c==null?"":c.toString();
      if(relevant(title)||relevant(body)){
        chargeCount++;
        write("충전·배터리 키워드 알림 발견:");
        write("제목: "+title.substring(0,Math.min(140,title.length())));
        write("본문: "+body.substring(0,Math.min(220,body.length())));
      }
    }
    write("현재 Zepp 알림 수: "+zeppCount);
    write("배터리·충전 관련 알림 수: "+chargeCount);
    if(chargeCount==0)write("현재 활성 알림에는 충전 정보가 없습니다. 충전 시작/종료 직후 다시 검사하세요.");
    write("알림이 없어도 Zepp 내부에 해당 정보가 없다는 뜻은 아닙니다.");
    write("진단 결과는 이 화면에만 표시됩니다. 서버/파일로 전송하지 않습니다.");
  }
}
