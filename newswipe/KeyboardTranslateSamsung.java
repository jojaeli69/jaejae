package com.alternative_studios.newswipe;

import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.text.TextUtils;
import android.view.Gravity;
import android.view.View;
import android.widget.LinearLayout;
import android.widget.PopupMenu;
import android.widget.TextView;
import android.widget.Toast;

import com.alternative_studios.newswipe.hangul.HangulComposer;
import com.google.mlkit.common.model.DownloadConditions;
import com.google.mlkit.nl.translate.TranslateLanguage;
import com.google.mlkit.nl.translate.Translation;
import com.google.mlkit.nl.translate.Translator;
import com.google.mlkit.nl.translate.TranslatorOptions;

/**
 * Compact Samsung-keyboard-style translation strip. Key presses are routed here by
 * the IME (rather than into the host editor) while the strip is open.
 * Translation is performed on-device with ML Kit; only language models are downloaded.
 */
public final class KeyboardTranslatePanel extends LinearLayout {
    public interface Actions {
        void onCloseTranslation();
        boolean onApplyTranslation(String translated, String original, boolean selected, boolean replace);
    }

    private static final int MAX_LENGTH = 350;
    private static final String[] LANGS = {
            TranslateLanguage.KOREAN, TranslateLanguage.ENGLISH,
            TranslateLanguage.JAPANESE, TranslateLanguage.CHINESE
    };
    private static final String[] NAMES = {"한국어", "영어", "일본어", "중국어"};

    private final Actions actions;
    private final TextView sourceButton, targetButton, inputText, resultText, sendButton, statusText;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final StringBuilder committed = new StringBuilder();
    private final HangulComposer hangul = new HangulComposer();
    private String originalSelection = "";
    private boolean selected;
    private String translated;
    private String sourceLang = TranslateLanguage.KOREAN;
    private String targetLang = TranslateLanguage.ENGLISH;
    private int seq;
    private Translator translator;
    private boolean sendWhenReady;
    private final int foreground, surface, muted, accent;

    public KeyboardTranslatePanel(Context context, int textColor, int background, Actions callbacks) {
        super(context);
        actions = callbacks;
        foreground = textColor;
        surface = background;
        double luminance = Color.red(background) * .2126 + Color.green(background) * .7152
                + Color.blue(background) * .0722;
        muted = luminance < 125 ? Color.rgb(161,166,173) : Color.rgb(101,106,113);
        accent = luminance < 125 ? Color.rgb(159,185,249) : Color.rgb(65,98,177);
        setOrientation(VERTICAL);
        setPadding(dp(10), dp(7), dp(10), dp(8));
        setBackgroundColor(background);

        // Row 1: compact language badge + long, rounded translation input + close.
        LinearLayout header = horizontal();
        sourceButton = chip("한국어 ▾", true);
        header.addView(sourceButton, new LayoutParams(dp(73), dp(42)));
        sourceButton.setOnClickListener(v -> showLanguageMenu(sourceButton, true));

        inputText = label("번역할 내용 입력", 15, muted);
        inputText.setSingleLine(true);
        inputText.setEllipsize(TextUtils.TruncateAt.START);
        inputText.setGravity(Gravity.CENTER_VERTICAL | Gravity.START);
        inputText.setPadding(dp(13), 0, dp(9), 0);
        inputText.setBackground(round(contrastColor(background), 24));
        LayoutParams textLp = new LayoutParams(0, dp(42), 1f);
        textLp.leftMargin = dp(6);
        header.addView(inputText, textLp);
        inputText.setContentDescription("번역할 텍스트. 아래 키보드로 입력하세요.");
        inputText.setOnClickListener(v -> Toast.makeText(getContext(),
                "아래 키보드로 번역할 문장을 입력하세요", Toast.LENGTH_SHORT).show());
        TextView close = label("×", 26, foreground);
        close.setGravity(Gravity.CENTER);
        close.setContentDescription("번역 닫기");
        close.setOnClickListener(v -> actions.onCloseTranslation());
        header.addView(close, new LayoutParams(dp(34), dp(42)));
        addView(header);

        // Row 2: target language, swap, live result and send. No full-page modal.
        LinearLayout resultRow = horizontal();
        TextView swap = chip("⇄", true);
        swap.setContentDescription("원본 언어와 번역 언어 바꾸기");
        resultRow.addView(swap, new LayoutParams(dp(38), dp(37)));
        swap.setOnClickListener(v -> {
            String tmp = sourceLang; sourceLang = targetLang; targetLang = tmp;
            updateLanguageNames();
            debounceTranslate();
        });
        targetButton = chip("영어 ▾", true);
        LayoutParams targetLp = new LayoutParams(dp(69), dp(37));
        targetLp.leftMargin = dp(3);
        resultRow.addView(targetButton, targetLp);
        targetButton.setOnClickListener(v -> showLanguageMenu(targetButton, false));

        resultText = label("번역 결과", 13, muted);
        resultText.setSingleLine(true);
        resultText.setEllipsize(TextUtils.TruncateAt.END);
        resultText.setGravity(Gravity.CENTER_VERTICAL);
        resultText.setPadding(dp(9), 0, dp(5), 0);
        resultRow.addView(resultText, new LayoutParams(0, dp(37), 1f));
        sendButton = chip("입력 ↗", true);
        sendButton.setTextColor(accent);
        sendButton.setContentDescription("번역 후 입력창에 삽입");
        resultRow.addView(sendButton, new LayoutParams(dp(59), dp(37)));
        sendButton.setOnClickListener(v -> insertTranslation());
        addView(resultRow);

        // Small third row: status + clipboard/clear, both available without leaving keys.
        LinearLayout bottom = horizontal();
        statusText = label("번역할 문장을 입력하세요", 11, muted);
        bottom.addView(statusText, new LayoutParams(0, dp(27), 1f));
        TextView paste = label("붙여넣기", 12, foreground);
        paste.setGravity(Gravity.CENTER);
        bottom.addView(paste, new LayoutParams(dp(69), dp(27)));
        paste.setOnClickListener(v -> loadClipboard());
        TextView clear = label("지우기", 12, foreground);
        clear.setGravity(Gravity.CENTER);
        bottom.addView(clear, new LayoutParams(dp(44), dp(27)));
        clear.setOnClickListener(v -> setInput("", false));
        addView(bottom);
        updateLanguageNames();
        updateText();
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private int contrastColor(int background) {
        return ((Color.red(background) + Color.green(background) + Color.blue(background)) / 3) < 125
                ? Color.rgb(56,57,63) : Color.rgb(238,239,243);
    }

    private GradientDrawable round(int color, int radius) {
        GradientDrawable bg = new GradientDrawable();
        bg.setColor(color);
        bg.setCornerRadius(dp(radius));
        return bg;
    }

    private LinearLayout horizontal() {
        LinearLayout row = new LinearLayout(getContext());
        row.setOrientation(HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);
        return row;
    }

    private TextView label(String value, int sp, int color) {
        TextView view = new TextView(getContext());
        view.setText(value);
        view.setTextSize(sp);
        view.setTextColor(color);
        return view;
    }

    private TextView chip(String value, boolean filled) {
        TextView view = label(value, 12, foreground);
        view.setGravity(Gravity.CENTER);
        if (filled) view.setBackground(round(contrastColor(surface), 17));
        view.setClickable(true);
        return view;
    }

    private static String nameFor(String code) {
        for (int i = 0; i < LANGS.length; i++) if (LANGS[i].equals(code)) return NAMES[i];
        return code;
    }

    private void updateLanguageNames() {
        sourceButton.setText(nameFor(sourceLang) + " ▾");
        targetButton.setText(nameFor(targetLang) + " ▾");
    }

    private void showLanguageMenu(View anchor, boolean source) {
        PopupMenu menu = new PopupMenu(getContext(), anchor);
        for (int i = 0; i < LANGS.length; i++) menu.getMenu().add(0, i, i, NAMES[i]);
        menu.setOnMenuItemClickListener(item -> {
            String picked = LANGS[item.getItemId()];
            if (source) sourceLang = picked; else targetLang = picked;
            if (sourceLang.equals(targetLang)) {
                if (source) targetLang = TranslateLanguage.ENGLISH.equals(sourceLang)
                        ? TranslateLanguage.KOREAN : TranslateLanguage.ENGLISH;
                else sourceLang = TranslateLanguage.KOREAN.equals(targetLang)
                        ? TranslateLanguage.ENGLISH : TranslateLanguage.KOREAN;
            }
            updateLanguageNames();
            debounceTranslate();
            return true;
        });
        menu.show();
    }

    public void showSource(String text, boolean selectedText) {
        originalSelection = selectedText && text != null ? text : "";
        selected = selectedText;
        setInput(text == null ? "" : text, true);
        if (text != null && text.matches("(?s).*[가-힣ㄱ-ㅎㅏ-ㅣ].*")) {
            sourceLang = TranslateLanguage.KOREAN;
            targetLang = TranslateLanguage.ENGLISH;
        } else if (text != null && text.matches("(?s).*[ぁ-ヿ].*")) {
            sourceLang = TranslateLanguage.JAPANESE;
            targetLang = TranslateLanguage.KOREAN;
        } else if (text != null && text.matches("(?s).*[a-zA-Z].*")) {
            sourceLang = TranslateLanguage.ENGLISH;
            targetLang = TranslateLanguage.KOREAN;
        }
        updateLanguageNames();
        debounceTranslate();
    }

    /** Typing is redirected here from the current NewSwipe keyboard, not the host editor. */
    public void onTypeText(String characters, boolean tap, boolean korean) {
        if (characters == null || characters.isEmpty() || currentText().length() >= MAX_LENGTH) return;
        if (characters.length() == 1 && korean && HangulComposer.isJamo(characters.charAt(0))) {
            hangul.input(characters.charAt(0), tap, SystemClock.uptimeMillis());
            committed.append(hangul.takeCommit());
        } else {
            flushHangul();
            committed.append(characters);
        }
        if (!selected) originalSelection = "";
        updateText();
        debounceTranslate();
    }

    public void onSpace() {
        flushHangul();
        if (committed.length() < MAX_LENGTH) committed.append(' ');
        updateText();
        debounceTranslate();
    }

    public void onBackspace() {
        if (!hangul.isEmpty()) {
            hangul.backspace();
            committed.append(hangul.takeCommit());
        } else if (committed.length() > 0) {
            int last = committed.offsetByCodePoints(committed.length(), -1);
            committed.delete(last, committed.length());
        }
        updateText();
        debounceTranslate();
    }

    public void onDeleteWord() {
        flushHangul();
        int i = committed.length();
        while (i > 0 && Character.isWhitespace(committed.charAt(i-1))) i--;
        while (i > 0 && !Character.isWhitespace(committed.charAt(i-1))) i--;
        committed.delete(i, committed.length());
        updateText();
        debounceTranslate();
    }

    private void flushHangul() {
        hangul.flush();
        committed.append(hangul.takeCommit());
    }

    private String currentText() {
        return committed.toString() + hangul.getComposing();
    }

    private void setInput(String value, boolean fromEditor) {
        hangul.reset();
        committed.setLength(0);
        if (value != null) committed.append(value.length() > MAX_LENGTH
                ? value.substring(0, MAX_LENGTH) : value);
        if (!fromEditor) {
            originalSelection = "";
            selected = false;
        }
        updateText();
        debounceTranslate();
    }

    private void updateText() {
        String text = currentText();
        inputText.setText(text.isEmpty() ? "번역할 내용 입력" : text + "│");
        inputText.setTextColor(text.isEmpty() ? muted : foreground);
    }

    private void loadClipboard() {
        ClipboardManager cb = (ClipboardManager) getContext().getSystemService(Context.CLIPBOARD_SERVICE);
        if (cb == null) return;
        try {
            ClipData data = cb.getPrimaryClip();
            if (data == null || data.getItemCount() == 0 || data.getItemAt(0).getText() == null) {
                statusText.setText("복사한 텍스트가 없습니다");
                return;
            }
            setInput(data.getItemAt(0).getText().toString(), false);
        } catch (RuntimeException ignored) {
            statusText.setText("클립보드를 읽지 못했습니다");
        }
    }

    private void debounceTranslate() {
        final int mySeq = ++seq;
        translated = null;
        resultText.setText("번역 결과");
        statusText.setText(currentText().trim().isEmpty() ? "번역할 문장을 입력하세요" : "입력을 마치면 자동 번역");
        handler.removeCallbacksAndMessages(null);
        if (currentText().trim().isEmpty()) return;
        handler.postDelayed(() -> {
            if (mySeq == seq) translate(mySeq);
        }, 450);
    }

    private void translate(int mySeq) {
        String phrase = currentText();
        if (phrase.trim().isEmpty() || sourceLang.equals(targetLang)) return;
        closeTranslator();
        resultText.setText("번역 중…");
        statusText.setText("언어 모델 준비 중");
        try {
            TranslatorOptions options = new TranslatorOptions.Builder()
                    .setSourceLanguage(sourceLang)
                    .setTargetLanguage(targetLang)
                    .build();
            Translator client = Translation.getClient(options);
            translator = client;
            client.downloadModelIfNeeded(new DownloadConditions.Builder().build())
                    .addOnSuccessListener(v -> {
                        if (mySeq != seq) return;
                        statusText.setText("번역 중…");
                        client.translate(phrase)
                                .addOnSuccessListener(result -> {
                                    if (mySeq != seq) return;
                                    translated = result;
                                    resultText.setText(result);
                                    statusText.setText("번역 완료 · '입력' 또는 ↵");
                                    if (translator == client) {
                                        translator = null;
                                        client.close();
                                    }
                                    if (sendWhenReady) {
                                        sendWhenReady = false;
                                        insertTranslation();
                                    }
                                })
                                .addOnFailureListener(e -> fail(mySeq, "번역할 수 없습니다"));
                    })
                    .addOnFailureListener(e -> fail(mySeq, "언어 모델 다운로드 실패"));
        } catch (RuntimeException | LinkageError e) {
            fail(mySeq, "번역 엔진 연결 실패");
        }
    }

    private void fail(int mySeq, String message) {
        if (mySeq != seq) return;
        sendWhenReady = false;
        translated = null;
        resultText.setText(message);
        statusText.setText("네트워크·저장 공간 확인 후 재시도");
        closeTranslator();
    }

    public void onEnter() {
        flushHangul();
        updateText();
        if (translated != null) {
            insertTranslation();
        } else if (!currentText().trim().isEmpty()) {
            sendWhenReady = true;
            final int mySeq = ++seq;
            handler.removeCallbacksAndMessages(null);
            translate(mySeq);
        }
    }

    private void insertTranslation() {
        if (translated == null) {
            onEnter();
            return;
        }
        boolean useSelection = selected && !originalSelection.isEmpty();
        boolean ok = actions.onApplyTranslation(translated, originalSelection,
                useSelection, useSelection);
        if (ok) actions.onCloseTranslation();
        else statusText.setText("입력 위치가 바뀌었습니다. 다시 시도해 주세요");
    }

    private void closeTranslator() {
        if (translator != null) {
            translator.close();
            translator = null;
        }
    }

    public void dismiss() {
        seq++;
        handler.removeCallbacksAndMessages(null);
        closeTranslator();
        translated = null;
        sendWhenReady = false;
        hangul.reset();
        committed.setLength(0);
    }
}
