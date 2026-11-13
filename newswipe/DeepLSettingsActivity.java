package com.alternative_studios.newswipe;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.text.InputType;
import android.view.View;
import android.view.ViewGroup;
import android.view.inputmethod.EditorInfo;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

/** Optional DeepL account and translation-mode setup. */
public final class DeepLSettingsActivity extends Activity {
    private TextView state;
    private CheckBox onlineMode;

    @Override protected void attachBaseContext(Context base) {
        super.attachBaseContext(AppTheme.wrap(base));
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private TextView text(String content, float sp) {
        TextView v = new TextView(this);
        v.setText(content);
        v.setTextSize(sp);
        v.setPadding(0, dp(9), 0, dp(9));
        return v;
    }

    private Button button(String content, Runnable action) {
        Button b = new Button(this);
        b.setText(content);
        b.setAllCaps(false);
        b.setOnClickListener(v -> action.run());
        return b;
    }

    private void refresh() {
        if (state == null) return;
        state.setText(DeepLTranslate.hasKey(this)
                ? "API 키: 기기 내 암호화 저장됨"
                : "API 키: 미등록 · 현재 번역은 기존 기기 내 ML Kit 사용");
        if (onlineMode != null) onlineMode.setChecked(DeepLTranslate.enabled(this));
    }

    @Override protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setTitle("NewSwipe 고품질 번역 설정");
        ScrollView scroll = new ScrollView(this);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(20), dp(18), dp(20), dp(26));
        scroll.addView(root, new ScrollView.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        root.addView(text("DeepL 온라인 번역", 21));
        root.addView(text("원하는 문장을 번역 버튼으로 보낼 때에만 해당 문장이 DeepL 서버로 전송됩니다. "
                + "일반 타이핑·클립보드 기록·문자·비밀번호는 전송하지 않습니다.\n\n"
                + "인터넷과 본인의 DeepL API 키가 필요합니다. 계정의 무료 한도 또는 유료 요금에 따라 "
                + "사용량이 차감될 수 있습니다. 회사 내부자료나 개인정보는 외부 전송이 허용된 경우에만 번역해 주세요.", 14));

        state = text("", 14);
        root.addView(state);
        root.addView(text("API 키 등록 / 변경", 16));
        EditText edit = new EditText(this);
        edit.setHint("DeepL API 인증키 (새 키 입력)");
        edit.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        edit.setImeOptions(EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING);
        edit.setImportantForAutofill(View.IMPORTANT_FOR_AUTOFILL_NO);
        edit.setSingleLine(true);
        edit.setSelectAllOnFocus(false);
        root.addView(edit, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(56)));

        CheckBox legacyFree = new CheckBox(this);
        legacyFree.setText("기존 DeepL API Free 키 사용 (구형 계정만)");
        legacyFree.setChecked(DeepLTranslate.legacyFree(this));
        root.addView(legacyFree);

        root.addView(button("API 키 저장 · 온라인 번역 켜기", () -> {
            String key = edit.getText().toString().trim();
            try {
                DeepLTranslate.saveKey(this, key, legacyFree.isChecked());
                edit.setText("");
                refresh();
                Toast.makeText(this, "DeepL 설정 저장됨 · 이제 번역 버튼은 온라인 엔진 사용", Toast.LENGTH_LONG).show();
            } catch (Exception error) {
                // Do not reveal key or original text in a log/error message.
                Toast.makeText(this,
                        error instanceof IllegalArgumentException
                                ? error.getMessage()
                                : "키 암호화 저장 실패 · 다시 시도해 주세요",
                        Toast.LENGTH_LONG).show();
            }
        }));

        onlineMode = new CheckBox(this);
        onlineMode.setText("DeepL 온라인 번역 사용 (끄면 기존 ML Kit)");
        onlineMode.setChecked(DeepLTranslate.enabled(this));
        onlineMode.setOnCheckedChangeListener((view, checked) -> {
            if (checked && !DeepLTranslate.hasKey(this)) {
                Toast.makeText(this, "먼저 DeepL API 키를 저장해 주세요", Toast.LENGTH_SHORT).show();
                onlineMode.setChecked(false);
                return;
            }
            DeepLTranslate.setEnabled(this, checked);
        });
        root.addView(onlineMode);

        root.addView(button("DeepL API 키 발급 페이지 열기", () -> {
            try {
                startActivity(new Intent(Intent.ACTION_VIEW,
                        Uri.parse("https://www.deepl.com/en/developers")));
            } catch (RuntimeException e) {
                Toast.makeText(this, "브라우저를 열 수 없습니다", Toast.LENGTH_SHORT).show();
            }
        }));
        root.addView(button("저장한 API 키 삭제", () -> new AlertDialog.Builder(this)
                .setTitle("DeepL API 키 삭제")
                .setMessage("기기에 암호화 저장된 API 키를 지웁니다. 기존 ML Kit 번역으로 돌아갑니다.")
                .setPositiveButton("삭제", (d, w) -> {
                    DeepLTranslate.clearKey(this);
                    refresh();
                })
                .setNegativeButton("취소", null)
                .show()));
        root.addView(text("DeepL 사용 시 원문이 외부 서비스에 전달됩니다. "
                + "API 키는 공개 저장소나 다른 사람에게 공유하지 말고 이 화면에서만 등록해 주세요. "
                + "API 키를 등록하지 않으면 온라인 번역은 실행되지 않습니다.", 13));
        root.addView(button("닫기", this::finish));

        setContentView(scroll);
        refresh();
    }
}
