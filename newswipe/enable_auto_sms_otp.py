from pathlib import Path
base=Path("app/src/main")
pkg=base/"java/com/alternative_studios/newswipe"
pkg.mkdir(parents=True,exist_ok=True)
(pkg/"OtpAutoFillService.java").write_text(r'''package com.alternative_studios.newswipe;

import android.os.CancellationSignal;
import android.service.autofill.AutofillService;
import android.service.autofill.FillCallback;
import android.service.autofill.FillRequest;
import android.service.autofill.SaveCallback;
import android.service.autofill.SaveRequest;

/**
 * User-selected OTP-only AutofillService. Does not collect form values,
 * credentials, usernames, passwords or autofill history.
 */
public final class OtpAutoFillService extends AutofillService {
    @Override public void onFillRequest(FillRequest request,
            CancellationSignal cancellationSignal, FillCallback callback) {
        SmsCodeAutoBridge.get(getApplicationContext()).watch();
        callback.onSuccess(null);
    }
    @Override public void onSaveRequest(SaveRequest request, SaveCallback callback) {
        callback.onSuccess();
    }
}
''',encoding="utf-8")
(pkg/"SmsCodeAutoBridge.java").write_text(r'''package com.alternative_studios.newswipe;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.view.autofill.AutofillManager;
import com.google.android.gms.auth.api.phone.SmsCodeAutofillClient;
import com.google.android.gms.auth.api.phone.SmsCodeRetriever;
import com.google.android.gms.auth.api.phone.SmsRetriever;
import com.google.android.gms.common.api.CommonStatusCodes;
import com.google.android.gms.common.api.Status;

/**
 * SMS Code Autofill API for *user-designated* autofill services.
 * Requires one-time provider selection + one-time Google consent, not SMS permissions.
 * The receiver only processes official Google Play services code broadcasts.
 */
final class SmsCodeAutoBridge {
    private static SmsCodeAutoBridge singleton;
    static synchronized SmsCodeAutoBridge get(Context context) {
        if (singleton == null) singleton = new SmsCodeAutoBridge(context.getApplicationContext());
        return singleton;
    }

    private final Context app;
    private final Handler main = new Handler(Looper.getMainLooper());
    private boolean listening, starting;
    private long listenUntil;
    private final BroadcastReceiver receiver = new BroadcastReceiver() {
        @Override public void onReceive(Context context, Intent intent) {
            if (!SmsCodeRetriever.SMS_CODE_RETRIEVED_ACTION.equals(intent.getAction())) return;
            Bundle extra = intent.getExtras();
            if (extra == null) return;
            Status status = extra.getParcelable(SmsCodeRetriever.EXTRA_STATUS);
            if (status == null) { stop(); return; }
            if (status.getStatusCode() == CommonStatusCodes.SUCCESS) {
                String value = extra.getString(SmsCodeRetriever.EXTRA_SMS_CODE);
                if (value != null && value.matches("[0-9]{4,8}")) OtpCodeSession.publish(value);
            }
            stop();
        }
    };

    private SmsCodeAutoBridge(Context context) { app = context; }

    private boolean providerSelected() {
        AutofillManager mgr = (AutofillManager) app.getSystemService(AutofillManager.class);
        return mgr != null && mgr.hasEnabledAutofillServices();
    }

    void watch() {
        if (Looper.myLooper() != Looper.getMainLooper()) {
            main.post(this::watch);
            return;
        }
        if (!providerSelected()) return;
        long now = SystemClock.elapsedRealtime();
        if (listening && now < listenUntil) return;
        if (starting) return;
        starting = true;
        try {
            SmsCodeAutofillClient client = SmsCodeRetriever.getAutofillClient(app);
            client.checkPermissionState()
                    .addOnSuccessListener(state -> {
                        starting = false;
                        if (state == SmsCodeAutofillClient.PermissionState.GRANTED) start(client);
                    })
                    .addOnFailureListener(e -> { starting = false; });
        } catch (RuntimeException | LinkageError e) {
            starting = false;
        }
    }

    private void start(SmsCodeAutofillClient client) {
        if (listening && SystemClock.elapsedRealtime() < listenUntil) return;
        stop();
        IntentFilter f = new IntentFilter(SmsCodeRetriever.SMS_CODE_RETRIEVED_ACTION);
        try {
            if (Build.VERSION.SDK_INT >= 33) {
                app.registerReceiver(receiver, f, SmsRetriever.SEND_PERMISSION, main,
                        Context.RECEIVER_EXPORTED);
            } else {
                app.registerReceiver(receiver, f, SmsRetriever.SEND_PERMISSION, main);
            }
            listening = true;
            listenUntil = SystemClock.elapsedRealtime() + 5 * 60_000L;
            client.startSmsCodeRetriever().addOnFailureListener(e -> stop());
        } catch (RuntimeException | LinkageError e) {
            stop();
        }
    }

    private void stop() {
        if (listening) {
            try { app.unregisterReceiver(receiver); }
            catch (RuntimeException ignored) { }
        }
        listening = false;
        listenUntil = 0;
    }
}
''',encoding="utf-8")
(pkg/"OtpAutoSetupActivity.java").write_text(r'''package com.alternative_studios.newswipe;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.provider.Settings;
import android.view.Gravity;
import android.view.autofill.AutofillManager;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import com.google.android.gms.auth.api.phone.SmsCodeAutofillClient;
import com.google.android.gms.auth.api.phone.SmsCodeRetriever;
import com.google.android.gms.common.api.ResolvableApiException;

/**
 * Explicit one-time setup, never automatically opens over input fields.
 * Selecting this service can displace Samsung/Google/password manager autofill.
 */
public final class OtpAutoSetupActivity extends Activity {
    private static final int PERMISSION_REQUEST = 4551;
    private TextView status;

    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        LinearLayout col = new LinearLayout(this);
        col.setOrientation(LinearLayout.VERTICAL);
        int pad = (int)(24 * getResources().getDisplayMetrics().density);
        col.setPadding(pad,pad,pad,pad);
        status = new TextView(this);
        status.setTextSize(18);
        status.setText("권한 확인 중...");
        col.addView(status);

        Button select = new Button(this);
        select.setText("1. NewSwipe를 기본 자동완성 서비스로 지정");
        select.setOnClickListener(v -> {
            try {
                Intent intent = new Intent(Settings.ACTION_REQUEST_SET_AUTOFILL_SERVICE);
                intent.setData(Uri.parse("package:" + getPackageName()));
                startActivity(intent);
            } catch (RuntimeException e) {
                startActivity(new Intent(Settings.ACTION_SETTINGS));
            }
        });
        col.addView(select);

        Button grant = new Button(this);
        grant.setText("2. 문자 인증번호 접근 1회 허용");
        grant.setOnClickListener(v -> requestConsentOnce());
        col.addView(grant);

        TextView note = new TextView(this);
        note.setText("설정 후 인증번호는 문자마다 승인 없이 키보드 추천 영역에 표시됩니다. "
                +"NewSwipe를 자동완성 서비스로 지정하면 기존 삼성 패스·Google·비밀번호 관리자 자동완성이 교체될 수 있습니다. "
                +"지원되지 않는 앱이나 문자는 자동으로 뜨지 않을 수 있습니다.");
        col.addView(note);
        setContentView(col);
    }

    private boolean providerSelected() {
        AutofillManager mgr = (AutofillManager) getSystemService(AutofillManager.class);
        return mgr != null && mgr.hasEnabledAutofillServices();
    }

    @Override protected void onResume() {
        super.onResume();
        refresh();
    }
    private void refresh() {
        if (!providerSelected()) {
            status.setText("1번을 눌러 NewSwipe를 기본 자동완성 서비스로 선택해 주세요.");
            return;
        }
        try {
            SmsCodeRetriever.getAutofillClient(this).checkPermissionState()
                    .addOnSuccessListener(state -> {
                        if (state == SmsCodeAutofillClient.PermissionState.GRANTED) {
                            status.setText("설정 완료! 이제 문자마다 승인할 필요가 없습니다.");
                            SmsCodeAutoBridge.get(this).watch();
                        } else {
                            status.setText("2번을 눌러 인증번호 접근 권한을 한 번 허용해 주세요.");
                        }
                    })
                    .addOnFailureListener(e -> status.setText("Google Play 서비스 연결을 확인해 주세요."));
        } catch (RuntimeException | LinkageError e) {
            status.setText("Google Play 서비스 SMS 자동완성을 사용할 수 없습니다.");
        }
    }

    private void requestConsentOnce() {
        if (!providerSelected()) {
            status.setText("먼저 기본 자동완성 서비스를 NewSwipe로 지정해 주세요.");
            return;
        }
        try {
            SmsCodeRetriever.getAutofillClient(this).startSmsCodeRetriever()
                    .addOnSuccessListener(n -> refresh())
                    .addOnFailureListener(e -> {
                        if (e instanceof ResolvableApiException) {
                            try {
                                ((ResolvableApiException)e)
                                        .startResolutionForResult(this, PERMISSION_REQUEST);
                            } catch (Exception ex) {
                                status.setText("Google 권한 창을 열 수 없습니다. Google 설정에서 SMS 코드 자동완성을 확인해 주세요.");
                            }
                        } else {
                            status.setText("권한 요청 실패. Google Play 서비스 또는 문자 인증 설정을 확인해 주세요.");
                        }
                    });
        } catch (RuntimeException | LinkageError e) {
            status.setText("Google Play 서비스 API를 호출하지 못했습니다.");
        }
    }

    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode,resultCode,data);
        if (requestCode == PERMISSION_REQUEST) refresh();
    }
}
''',encoding="utf-8")

manifest=base/"AndroidManifest.xml"
s=manifest.read_text(encoding="utf-8")
needle='    <application\n'
assert s.count(needle)==1
# insert components directly inside application
needle_end='        <activity\n            android:name=".SettingsActivity"'
assert s.count(needle_end)==1
new_nodes='''        <service
            android:name=".OtpAutoFillService"
            android:exported="true"
            android:label="NewSwipe 인증번호 자동완성"
            android:permission="android.permission.BIND_AUTOFILL_SERVICE">
            <intent-filter>
                <action android:name="android.service.autofill.AutofillService" />
            </intent-filter>
            <meta-data
                android:name="android.autofill"
                android:resource="@xml/otp_autofill_service" />
        </service>

        <activity
            android:name=".OtpAutoSetupActivity"
            android:exported="false"
            android:label="인증번호 자동완성 설정" />

'''
s=s.replace(needle_end,new_nodes+needle_end,1)
manifest.write_text(s,encoding="utf-8")
xml=base/"res/xml/otp_autofill_service.xml"
xml.parent.mkdir(parents=True,exist_ok=True)
xml.write_text('''<?xml version="1.0" encoding="utf-8"?>
<autofill-service xmlns:android="http://schemas.android.com/apk/res/android"
    android:settingsActivity="com.alternative_studios.newswipe.OtpAutoSetupActivity" />
''',encoding="utf-8")

ime=pkg/"NewSwipeIME.java"
s=ime.read_text(encoding="utf-8")
def replace_once(a,b,label):
 global s
 n=s.count(a)
 assert n==1, (label,n)
 s=s.replace(a,b,1)
replace_once('smsOtp.watch(info);','SmsCodeAutoBridge.get(getApplicationContext()).watch();','replace consent watcher')
replace_once('''        refreshHwToolbar();
        main.removeCallbacks(releaseWhileHidden);''','''        refreshHwToolbar();
        if (prefs != null && prefs.smsOtpConsent()) SmsCodeAutoBridge.get(getApplicationContext()).watch();
        main.removeCallbacks(releaseWhileHidden);''','watch on IME shown')
replace_once('return otpCode != null || otpConsentIntent != null;','return otpCode != null;','no consent chip')
ime.write_text(s,encoding="utf-8")

settings=pkg/"SettingsActivity.java"
s=settings.read_text(encoding="utf-8")
needle='''            autofill.addView(note("기기 설정에서 고른 자동 완성 서비스(Autofill with Google, 삼성 패스 등)를 사용합니다. "));'''
assert s.count(needle)==1
s=s.replace(needle,'''            android.widget.Button autoOtpSetup = new android.widget.Button(this);
            autoOtpSetup.setText("인증번호 자동입력 (최초 1회 권한 설정)");
            autoOtpSetup.setOnClickListener(v -> startActivity(
                    new android.content.Intent(this, OtpAutoSetupActivity.class)));
            autofill.addView(autoOtpSetup);
            autofill.addView(note("인증번호 자동 제안에는 NewSwipe를 기본 자동완성 서비스로 설정하고, Google 문자 인증 권한을 최초 한 번 허용해야 합니다. 기존 자동완성 서비스가 바뀔 수 있습니다."));''',1)
s=s.replace('"문자 인증번호 제안 (승인 필요)",','"문자 인증번호 자동 제안",',1)
settings.write_text(s,encoding="utf-8")
print("Integrated user-designated SMS Code Autofill provider and setup UI into NewSwipe.")
