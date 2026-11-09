from pathlib import Path
from textwrap import dedent
base=Path("app/src/main")
pkg=base/"java/com/alternative_studios/newswipe"
(pkg/"SmsDirectReceiver.java").write_text(dedent(r'''\
package com.alternative_studios.newswipe;

import android.Manifest;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.provider.Telephony;
import android.telephony.SmsMessage;

/**
 * Opt-in, RECEIVE_SMS-only OTP extraction. Never queries SMS history, never
 * transmits messages, never changes the default SMS app or autofill provider.
 * Android/installer may restrict SMS or sensitive OTP broadcasts.
 */
public final class SmsDirectReceiver extends BroadcastReceiver {
    public static boolean hasPermission(Context context) {
        return context.checkSelfPermission(Manifest.permission.RECEIVE_SMS)
                == PackageManager.PERMISSION_GRANTED;
    }

    @Override public void onReceive(Context context, Intent intent) {
        if (intent == null
                || !Telephony.Sms.Intents.SMS_RECEIVED_ACTION.equals(intent.getAction())
                || !hasPermission(context)) return;
        try {
            SmsMessage[] parts = Telephony.Sms.Intents.getMessagesFromIntent(intent);
            if (parts == null || parts.length == 0 || parts.length > 15) return;
            StringBuilder all = new StringBuilder();
            for (SmsMessage part : parts) {
                if (part == null || part.getMessageBody() == null) continue;
                all.append(part.getMessageBody());
                if (all.length() > 4096) return;
            }
            String code = OtpCodeParser.extract(all.toString());
            if (code != null) OtpCodeSession.publish(code);
        } catch (RuntimeException ignored) {
            // Don't fail SMS delivery, leak sensitive content or write logs.
        }
    }
}
''').lstrip('\\\n'), encoding="utf-8")

(pkg/"SmsDirectSetupActivity.java").write_text(dedent(r'''\
package com.alternative_studios.newswipe;

import android.Manifest;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.view.Gravity;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

/** Single initial action: grant incoming-SMS permission; Samsung Pass untouched. */
public final class SmsDirectSetupActivity extends Activity {
    private static final int REQUEST_CODE = 332;
    private TextView status;

    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        setTitle("NewSwipe 문자 인증번호");
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        int p = Math.round(22f * getResources().getDisplayMetrics().density);
        root.setPadding(p, p, p, p);
        TextView intro = new TextView(this);
        intro.setTextSize(18);
        intro.setText("삼성패스는 그대로 유지하고, 문자 인증번호만 NewSwipe에서 추천합니다.\n\n"
                + "이 앱이 수신하는 문자에서 인증번호로 추정되는 숫자만 기기 메모리에 잠시 보관합니다. "
                + "문자함을 조회하거나 메시지를 외부 서버로 보내지 않습니다.\n\n"
                + "일부 Android 버전은 권한을 허용해도 인증번호 문자를 차단할 수 있습니다.");
        root.addView(intro);
        status = new TextView(this);
        status.setTextSize(15);
        LinearLayout.LayoutParams s = new LinearLayout.LayoutParams(-1, -2);
        s.topMargin = p;
        root.addView(status,s);
        Button grant = new Button(this);
        grant.setText("문자 인증번호 자동추천 켜기");
        grant.setOnClickListener(v -> {
            if (SmsDirectReceiver.hasPermission(this)) {
                status.setText("켜져 있습니다. 삼성패스 설정은 변경되지 않았습니다.");
            } else {
                requestPermissions(new String[]{Manifest.permission.RECEIVE_SMS}, REQUEST_CODE);
            }
        });
        root.addView(grant);
        Button done = new Button(this);
        done.setText("설정 완료 · 닫기");
        done.setOnClickListener(v -> finish());
        root.addView(done);
        setContentView(root);
        refresh();
    }

    @Override protected void onResume() { super.onResume(); refresh(); }

    private void refresh() {
        if (status == null) return;
        status.setText(SmsDirectReceiver.hasPermission(this)
                ? "문자 수신 권한: 허용됨. 인증 문자를 새로 보내 테스트해 주세요."
                : "문자 수신 권한: 허용되지 않음. 아래 버튼을 눌러 한 번만 허용해 주세요.");
    }

    @Override public void onRequestPermissionsResult(int code, String[] permissions,
            int[] results) {
        super.onRequestPermissionsResult(code, permissions, results);
        if (code != REQUEST_CODE) return;
        refresh();
        if (!SmsDirectReceiver.hasPermission(this)) {
            status.setText("권한을 사용할 수 없습니다. 설치 프로그램 또는 Android 보안 제한이 "
                    + "원인일 수 있습니다. 삼성패스는 계속 사용할 수 있습니다.");
        }
    }
}
''').lstrip('\\\n'),encoding="utf-8")

manifest=base/"AndroidManifest.xml"
s=manifest.read_text(encoding="utf-8")
needle='    <uses-permission android:name="android.permission.VIBRATE" />'
assert s.count(needle)==1
s=s.replace(needle,needle+'\n    <uses-permission android:name="android.permission.RECEIVE_SMS" />',1)
needle='        <activity\n            android:name=".SettingsActivity"'
assert s.count(needle)==1
s=s.replace(needle,dedent('''\
        <!-- SMS_RECEIVED is an OS broadcast, not a default SMS handler. -->
        <receiver
            android:name=".SmsDirectReceiver"
            android:enabled="true"
            android:exported="true"
            android:permission="android.permission.BROADCAST_SMS">
            <intent-filter>
                <action android:name="android.provider.Telephony.SMS_RECEIVED" />
            </intent-filter>
        </receiver>
        <activity
            android:name=".SmsDirectSetupActivity"
            android:exported="false"
            android:label="NewSwipe 문자 인증 설정" />

''')+needle,1)
manifest.write_text(s,encoding="utf-8")

prefs=pkg/"Prefs.java"
s=prefs.read_text(encoding="utf-8")
old='public boolean smsOtpConsent() { return sp.getBoolean(SMS_OTP_CONSENT, false); }'
assert s.count(old)==1
s=s.replace(old,'public boolean smsOtpConsent() { return sp.getBoolean(SMS_OTP_CONSENT, true); }',1)
prefs.write_text(s,encoding="utf-8")

ime=pkg/"NewSwipeIME.java"
s=ime.read_text(encoding="utf-8")
# Current OTP consent watcher remains only a fallback when RECEIVE_SMS is unavailable.
needle='smsOtp.watch('
assert s.count(needle)>=1,(needle,s.count(needle))
# Suppress per-message approval for devices that grant direct SMS access.
import re
s,n=re.subn(r'(?m)^(\s*)smsOtp\.watch\(([^;]*)\);',
  r'\1if (!SmsDirectReceiver.hasPermission(this)) smsOtp.watch(\2);\n\1else smsOtp.stop();',s)
assert n>=1,('watchers',n)
ime.write_text(s,encoding="utf-8")

settings=pkg/"SettingsActivity.java"
s=settings.read_text(encoding="utf-8")
needle='''            autofill.addView(note("기기 설정에서 고른 자동 완성 서비스(Autofill with Google, 삼성 패스 등)를 사용합니다. "));'''
assert s.count(needle)==1, "Missing auto fill notes"
s=s.replace(needle, '''            autofill.addView(button("문자 인증번호 자동추천 · 최초 1회 권한 설정",
                    v -> startActivity(new Intent(this, SmsDirectSetupActivity.class))));
            autofill.addView(note("삼성패스는 그대로 사용합니다. 문자 수신 권한을 허용하면 인증번호를 자동 추천합니다. "
                    + "Android 버전에 따라 보호된 인증번호 문자는 접근할 수 없을 수 있습니다."));''',1)
# Avoid misleading consent-only messaging in the settings toggle.
s=s.replace('문자 인증번호 제안 (승인 필요)','문자 인증번호 자동 추천')
s=s.replace("인증번호 입력칸을 열고 문자가 도착하면 키보드에 '문자 승인' 버튼이 뜹니다.",
            '문자 수신 권한을 허용하면 인증번호를 자동 추천합니다. 권한이 없으면 Google 문자 읽기 승인이 필요할 수 있습니다.')
# Open the permission setup exactly once after onboarding; never change the autofill service.
needle='''        updateStatus();
        refreshLayoutPreview();'''
assert s.count(needle)==1
s=s.replace(needle,'''        updateStatus();
        if (getIntent().getStringExtra(EXTRA_SECTION) == null && prefs.onboardingDone()
                && !getPreferences(MODE_PRIVATE).getBoolean("sms_setup_seen", false)) {
            getPreferences(MODE_PRIVATE).edit().putBoolean("sms_setup_seen", true).apply();
            if (!SmsDirectReceiver.hasPermission(this)) {
                new android.os.Handler(android.os.Looper.getMainLooper()).post(
                        () -> { if (!isFinishing()) startActivity(
                                new Intent(this, SmsDirectSetupActivity.class)); });
            }
        }
        refreshLayoutPreview();''',1)
settings.write_text(s,encoding="utf-8")
print("Applied SMS receive integration, first-run grant flow and Samsung Pass preservation.")
