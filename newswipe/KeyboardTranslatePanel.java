package com.alternative_studios.newswipe;

import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.graphics.Color;
import android.text.TextUtils;
import android.view.Gravity;
import android.view.View;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

import com.google.mlkit.common.model.DownloadConditions;
import com.google.mlkit.nl.translate.TranslateLanguage;
import com.google.mlkit.nl.translate.Translation;
import com.google.mlkit.nl.translate.Translator;
import com.google.mlkit.nl.translate.TranslatorOptions;

/**
 * Keyboard-local translation sheet, no text sent to an application server.
 * User initiates translation; first use may download ~30MB/language model.
 * Source text is collected only from explicit selection, current editor or
 * user-initiated clipboard action. No background keylogging.
 */
public final class KeyboardTranslatePanel extends LinearLayout {
    public interface Actions {
        void onCloseTranslation();
        boolean onApplyTranslation(String translated, String original, boolean selected, boolean replace);
    }

    private final Actions actions;
    private final Spinner directionSpinner;
    private final TextView sourcePreview, resultPreview, status;
    private final Button translateButton, replaceButton, insertButton;
    private String original = "";
    private boolean originallySelected;
    private boolean fromClipboard;
    private String result = null;
    private int requestId;
    private Translator translator;

    private static final String[] LABELS = {
        "한국어 → 영어", "영어 → 한국어",
        "한국어 → 일본어", "일본어 → 한국어",
        "한국어 → 중국어", "중국어 → 한국어"
    };
    private static final String[] SOURCES = {
        TranslateLanguage.KOREAN, TranslateLanguage.ENGLISH,
        TranslateLanguage.KOREAN, TranslateLanguage.JAPANESE,
        TranslateLanguage.KOREAN, TranslateLanguage.CHINESE
    };
    private static final String[] TARGETS = {
        TranslateLanguage.ENGLISH, TranslateLanguage.KOREAN,
        TranslateLanguage.JAPANESE, TranslateLanguage.KOREAN,
        TranslateLanguage.CHINESE, TranslateLanguage.KOREAN
    };

    public KeyboardTranslatePanel(Context c, int textColor, int backgroundColor, Actions actions) {
        super(c);
        this.actions = actions;
        setOrientation(VERTICAL);
        setBackgroundColor(backgroundColor);
        int pad = dp(12);
        setPadding(pad, dp(6), pad, dp(8));

        LinearLayout title = horizontal();
        TextView heading = new TextView(c);
        heading.setText("번역 · 기기 내 처리");
        heading.setTextColor(textColor);
        heading.setTextSize(17);
        heading.setGravity(Gravity.CENTER_VERTICAL);
        title.addView(heading, new LinearLayout.LayoutParams(0, dp(36), 1f));
        Button close = actionButton("닫기", v -> actions.onCloseTranslation());
        title.addView(close, new LinearLayout.LayoutParams(dp(56), dp(36)));
        addView(title);

        LinearLayout languageRow = horizontal();
        directionSpinner = new Spinner(c);
        ArrayAdapter<String> choices = new ArrayAdapter<>(c, android.R.layout.simple_spinner_item, LABELS);
        choices.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        directionSpinner.setAdapter(choices);
        languageRow.addView(directionSpinner, new LinearLayout.LayoutParams(0, dp(42), 1f));
        translateButton = actionButton("번역하기", v -> translate());
        languageRow.addView(translateButton, new LinearLayout.LayoutParams(dp(95), dp(42)));
        addView(languageRow);

        sourcePreview = bodyText(textColor);
        sourcePreview.setMaxLines(2);
        sourcePreview.setEllipsize(TextUtils.TruncateAt.END);
        sourcePreview.setTextIsSelectable(false);
        addView(sourcePreview);

        resultPreview = bodyText(textColor);
        resultPreview.setTextSize(15);
        resultPreview.setMaxLines(4);
        resultPreview.setText("번역 결과가 여기에 표시됩니다.");
        ScrollView scroll = new ScrollView(c);
        scroll.setFillViewport(false);
        scroll.addView(resultPreview);
        addView(scroll, new LinearLayout.LayoutParams(-1, dp(94)));

        status = new TextView(c);
        status.setTextSize(12);
        status.setTextColor(textColor);
        status.setMaxLines(2);
        addView(status);

        LinearLayout actionsRow = horizontal();
        replaceButton = actionButton("원문 교체", v -> insert(true));
        insertButton = actionButton("커서에 삽입", v -> insert(false));
        Button copy = actionButton("복사", v -> {
            if (result == null) return;
            ClipboardManager cb = (ClipboardManager)c.getSystemService(Context.CLIPBOARD_SERVICE);
            if (cb != null) cb.setPrimaryClip(ClipData.newPlainText("번역 결과", result));
            Toast.makeText(c, "번역 결과를 복사했습니다", Toast.LENGTH_SHORT).show();
        });
        actionsRow.addView(replaceButton, new LinearLayout.LayoutParams(0, dp(44), 1f));
        actionsRow.addView(insertButton, new LinearLayout.LayoutParams(0, dp(44), 1f));
        actionsRow.addView(copy, new LinearLayout.LayoutParams(0, dp(44), 1f));
        addView(actionsRow);

        LinearLayout extraRow = horizontal();
        Button clipboardButton = actionButton("복사한 글 번역", v -> readClipboard());
        extraRow.addView(clipboardButton, new LinearLayout.LayoutParams(0, dp(35), 1f));
        TextView privacy = new TextView(c);
        privacy.setText("최초 번역 시 모델 다운로드");
        privacy.setTextSize(11);
        privacy.setTextColor(textColor);
        privacy.setGravity(Gravity.CENTER_VERTICAL);
        extraRow.addView(privacy, new LinearLayout.LayoutParams(0, dp(35), 1f));
        addView(extraRow);
        resultActionsEnabled(false);
    }

    private int dp(int d) { return (int) (getResources().getDisplayMetrics().density*d + .5f); }

    private LinearLayout horizontal() {
        LinearLayout row = new LinearLayout(getContext());
        row.setOrientation(HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);
        return row;
    }

    private TextView bodyText(int color) {
        TextView view = new TextView(getContext());
        view.setTextSize(14);
        view.setTextColor(color);
        view.setPadding(0, dp(4), 0, dp(5));
        return view;
    }

    private Button actionButton(String label, OnClickListener listener) {
        Button b = new Button(getContext());
        b.setText(label);
        b.setTextSize(12);
        b.setAllCaps(false);
        b.setOnClickListener(listener);
        b.setPadding(0, 0, 0, 0);
        return b;
    }

    /** Called with text already entered in the host app. */
    public void showSource(String text, boolean selected) {
        original = text == null ? "" : text;
        originallySelected = selected;
        fromClipboard = false;
        result = null;
        requestId++;
        closeTranslator();
        sourcePreview.setText(original.isEmpty() ? "입력창에서 문장을 작성하거나 선택한 뒤 번역해 주세요." : "원문: " + original);
        resultPreview.setText("번역 결과가 여기에 표시됩니다.");
        status.setText(original.isEmpty() ? "또는 '복사한 글 번역'을 눌러 주세요." : "");
        resultActionsEnabled(false);
        directionSpinner.setSelection(suggestDirection(original));
        if (!original.trim().isEmpty()) translate();
    }

    private int suggestDirection(String input) {
        if (input.matches("(?s).*[가-힣ㄱ-ㅎㅏ-ㅣ].*")) return 0;
        if (input.matches("(?s).*[ぁ-ゟ゠-ヿ].*")) return 3;
        if (input.matches("(?s).*[一-龥].*")) return 5;
        return 1;
    }

    private void readClipboard() {
        ClipboardManager cb = (ClipboardManager) getContext().getSystemService(Context.CLIPBOARD_SERVICE);
        if (cb == null) { status.setText("클립보드를 읽을 수 없습니다."); return; }
        try {
            ClipData clip = cb.getPrimaryClip();
            if (clip == null || clip.getItemCount() == 0 || clip.getItemAt(0).getText() == null) {
                status.setText("클립보드에 복사된 텍스트가 없습니다.");
                return;
            }
            CharSequence text = clip.getItemAt(0).getText();
            showSource(text.length() > 350 ? text.subSequence(0, 350).toString() : text.toString(), false);
            fromClipboard = true;
            status.setText("클립보드의 글을 번역했습니다. 원문 교체는 사용할 수 없습니다.");
            replaceButton.setEnabled(false);
        } catch (RuntimeException ex) {
            status.setText("클립보드 접근이 제한됐습니다.");
        }
    }

    private void resultActionsEnabled(boolean enabled) {
        replaceButton.setEnabled(enabled && !original.trim().isEmpty() && !fromClipboard);
        insertButton.setEnabled(enabled);
    }

    private void translate() {
        if (original.trim().isEmpty()) {
            status.setText("먼저 입력창에 문장을 쓰거나 텍스트를 선택해 주세요.");
            return;
        }
        requestId++;
        int req = requestId;
        closeTranslator();
        result = null;
        resultActionsEnabled(false);
        resultPreview.setText("번역하는 중…");
        status.setText("언어 모델 확인 중 (첫 사용 시 다운로드)");
        translateButton.setEnabled(false);
        try {
            int direction = directionSpinner.getSelectedItemPosition();
            if (direction < 0 || direction >= SOURCES.length) direction = 0;
            TranslatorOptions options = new TranslatorOptions.Builder()
                    .setSourceLanguage(SOURCES[direction])
                    .setTargetLanguage(TARGETS[direction])
                    .build();
            Translator client = Translation.getClient(options);
            translator = client;
            DownloadConditions conditions = new DownloadConditions.Builder().build();
            client.downloadModelIfNeeded(conditions)
                    .addOnSuccessListener(v -> {
                        if (req != requestId) return;
                        status.setText("번역 중…");
                        client.translate(original)
                                .addOnSuccessListener(value -> {
                                    if (req != requestId) return;
                                    result = value;
                                    resultPreview.setText(value);
                                    status.setText("번역 완료 · 사용할 방법을 선택하세요.");
                                    resultActionsEnabled(true);
                                    translateButton.setEnabled(true);
                                    if (translator == client) { translator = null; client.close(); }
                                })
                                .addOnFailureListener(e -> failed(req, "번역할 수 없습니다. 언어 모델을 확인해 주세요."));
                    })
                    .addOnFailureListener(e -> failed(req, "모델 다운로드 실패 · 인터넷 연결/저장 공간을 확인해 주세요."));
        } catch (Exception e) {
            failed(req, "번역 엔진을 시작할 수 없습니다.");
        }
    }

    private void failed(int req, String message) {
        if (req != requestId) return;
        result = null;
        resultPreview.setText(message);
        status.setText("재시도할 수 있습니다.");
        translateButton.setEnabled(true);
        resultActionsEnabled(false);
        closeTranslator();
    }

    private void insert(boolean replace) {
        if (result == null || original.isEmpty()) return;
        boolean ok = actions.onApplyTranslation(result, original, originallySelected, replace);
        if (ok) actions.onCloseTranslation();
        else status.setText("입력 위치가 바뀌었습니다. 입력창에서 다시 선택한 뒤 시도해 주세요.");
    }

    private void closeTranslator() {
        if (translator != null) {
            translator.close();
            translator = null;
        }
    }

    public void dismiss() {
        requestId++;
        closeTranslator();
        result = null;
        translateButton.setEnabled(true);
    }
}
