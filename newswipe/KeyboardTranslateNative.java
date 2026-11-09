package com.alternative_studios.newswipe;

import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.text.TextUtils;
import android.view.Gravity;
import android.view.View;
import android.widget.LinearLayout;
import android.widget.PopupMenu;
import android.widget.TextView;
import android.widget.Toast;

import com.alternative_studios.newswipe.hangul.HangulComposer;
import com.alternative_studios.newswipe.keyboard.KeyboardTheme;
import com.alternative_studios.newswipe.ui.Ui;
import com.google.mlkit.common.model.DownloadConditions;
import com.google.mlkit.nl.translate.TranslateLanguage;
import com.google.mlkit.nl.translate.Translation;
import com.google.mlkit.nl.translate.Translator;
import com.google.mlkit.nl.translate.TranslatorOptions;

/**
 * NewSwipe-native appearance with Samsung Keyboard's translation workflow:
 * select languages -> type on the regular keyboard -> tap Translate/Enter ->
 * commit the translated text directly to the original editor.
 * Never switches the current autofill provider (Samsung Pass stays enabled).
 */
public final class KeyboardTranslatePanel extends LinearLayout {
    public interface Actions {
        void onCloseTranslation();
        boolean onApplyTranslation(String translated, String original, boolean selected, boolean replace);
    }

    private static final int LIMIT = 350;
    private static final String[] LANGUAGES = {
            TranslateLanguage.KOREAN, TranslateLanguage.ENGLISH,
            TranslateLanguage.JAPANESE, TranslateLanguage.CHINESE
    };
    private static final String[] LABELS = {"한국어", "영어", "일본어", "중국어"};

    private final Actions actions;
    private final KeyboardTheme theme;
    private final TextView fromButton, toButton, entry, submitButton, status;
    private final StringBuilder committed = new StringBuilder();
    private final HangulComposer hangul = new HangulComposer();

    private String from = TranslateLanguage.KOREAN;
    private String to = TranslateLanguage.ENGLISH;
    private String originalSelection = "";
    private boolean originallySelected;
    private Translator translator;
    private int generation;
    private boolean translating;

    public KeyboardTranslatePanel(Context c, int textColor, int backgroundColor, Actions callbacks) {
        super(c);
        actions = callbacks;
        theme = KeyboardTheme.of(c);
        setOrientation(VERTICAL);
        setBackgroundColor(theme.background);
        setPadding(dp(8), dp(5), dp(8), dp(5));

        // Native NewSwipe chip row: language -> language, swap, back.
        LinearLayout languages = row();
        TextView back = chip("‹", theme.text, theme.functionKey, dp(38));
        back.setContentDescription("번역 종료");
        back.setOnClickListener(v -> actions.onCloseTranslation());
        languages.addView(back, new LayoutParams(dp(38), dp(37)));

        fromButton = chip("한국어 ▾", theme.text, theme.functionKey, dp(87));
        languages.addView(fromButton, new LayoutParams(0, dp(37), 1f));
        fromButton.setOnClickListener(v -> languagePicker(fromButton, true));

        TextView swap = chip("⇄", theme.text, theme.functionKey, dp(40));
        swap.setContentDescription("번역 언어 바꾸기");
        languages.addView(swap, new LayoutParams(dp(40), dp(37)));
        swap.setOnClickListener(v -> {
            String temp = from;
            from = to;
            to = temp;
            updateLanguageLabels();
            invalidateTranslation();
        });

        toButton = chip("영어 ▾", theme.text, theme.functionKey, dp(87));
        languages.addView(toButton, new LayoutParams(0, dp(37), 1f));
        toButton.setOnClickListener(v -> languagePicker(toButton, false));
        addView(languages, new LayoutParams(LayoutParams.MATCH_PARENT, dp(39)));

        // Source is entered HERE, using the unmodified underlying NewSwipe keys.
        LinearLayout entryRow = row();
        entry = chip("번역할 텍스트를 입력하세요", theme.hint, theme.key, dp(210));
        entry.setGravity(Gravity.CENTER_VERTICAL | Gravity.START);
        entry.setPadding(dp(12), 0, dp(8), 0);
        entry.setSingleLine(true);
        entry.setEllipsize(TextUtils.TruncateAt.START);
        entry.setContentDescription("번역할 문장을 아래 자판에서 입력");
        LayoutParams inputParams = new LayoutParams(0, dp(42), 1f);
        inputParams.rightMargin = dp(5);
        entryRow.addView(entry, inputParams);

        submitButton = chip("번역", theme.onAccent, theme.accent, dp(57));
        submitButton.setContentDescription("번역한 문장을 원래 입력창에 넣기");
        submitButton.setOnClickListener(v -> onEnter());
        entryRow.addView(submitButton, new LayoutParams(dp(57), dp(42)));
        addView(entryRow, new LayoutParams(LayoutParams.MATCH_PARENT, dp(46)));

        // Short help row, no result pane or Samsung-style window.
        LinearLayout footer = row();
        status = text("글자를 입력한 뒤 '번역'을 누르세요", 11, theme.hint);
        footer.addView(status, new LayoutParams(0, dp(27), 1f));

        TextView paste = chip("붙여넣기", theme.text, theme.functionKey, dp(64));
        paste.setTextSize(11);
        footer.addView(paste, new LayoutParams(dp(65), dp(27)));
        paste.setOnClickListener(v -> pasteCopiedText());

        TextView clear = chip("지우기", theme.text, theme.functionKey, dp(49));
        clear.setTextSize(11);
        footer.addView(clear, new LayoutParams(dp(49), dp(27)));
        clear.setOnClickListener(v -> resetText(false));
        addView(footer, new LayoutParams(LayoutParams.MATCH_PARENT, dp(29)));
    }

    private int dp(int v) { return Ui.dp(getContext(), v); }

    private LinearLayout row() {
        LinearLayout result = new LinearLayout(getContext());
        result.setOrientation(HORIZONTAL);
        result.setGravity(Gravity.CENTER_VERTICAL);
        return result;
    }

    private TextView text(String string, int size, int color) {
        TextView t = new TextView(getContext());
        t.setText(string);
        t.setTextSize(size);
        t.setTextColor(color);
        t.setGravity(Gravity.CENTER_VERTICAL);
        t.setSingleLine(true);
        t.setEllipsize(TextUtils.TruncateAt.END);
        return t;
    }

    private TextView chip(String label, int color, int fill, int minWidth) {
        TextView t = text(label, 13, color);
        t.setGravity(Gravity.CENTER);
        t.setPadding(dp(5), 0, dp(5), 0);
        t.setMinWidth(minWidth);
        float radius = Ui.chipRadius(getContext());
        t.setBackground(Ui.ripple(Ui.tint(color), Ui.round(fill, radius), radius));
        t.setClickable(true);
        return t;
    }

    private static String name(String lang) {
        for (int i=0;i<LANGUAGES.length;i++) if (LANGUAGES[i].equals(lang)) return LABELS[i];
        return lang;
    }

    private void updateLanguageLabels() {
        fromButton.setText(name(from) + " ▾");
        toButton.setText(name(to) + " ▾");
    }

    private void languagePicker(View anchor, boolean source) {
        PopupMenu choices = new PopupMenu(getContext(), anchor);
        for (int i=0;i<LANGUAGES.length;i++) choices.getMenu().add(0, i, i, LABELS[i]);
        choices.setOnMenuItemClickListener(item -> {
            String chosen = LANGUAGES[item.getItemId()];
            if (source) from=chosen; else to=chosen;
            if (from.equals(to)) {
                if (source) to = TranslateLanguage.KOREAN.equals(from)
                        ? TranslateLanguage.ENGLISH : TranslateLanguage.KOREAN;
                else from = TranslateLanguage.KOREAN.equals(to)
                        ? TranslateLanguage.ENGLISH : TranslateLanguage.KOREAN;
            }
            updateLanguageLabels();
            invalidateTranslation();
            return true;
        });
        choices.show();
    }

    public void showSource(String value, boolean selected) {
        originallySelected = selected;
        originalSelection = selected && value != null ? value : "";
        resetText(true);
        if (selected && value != null) {
            committed.append(value.length() > LIMIT ? value.substring(0,LIMIT) : value);
            if (value.matches("(?s).*[a-zA-Z].*") && !value.matches("(?s).*[가-힣].*")) {
                from = TranslateLanguage.ENGLISH;
                to = TranslateLanguage.KOREAN;
            } else {
                from = TranslateLanguage.KOREAN;
                to = TranslateLanguage.ENGLISH;
            }
        }
        updateLanguageLabels();
        showSourceText();
    }

    private String source() {
        return committed.toString() + hangul.getComposing();
    }

    private void showSourceText() {
        String value=source();
        boolean empty=value.isEmpty();
        entry.setText(empty ? "번역할 텍스트를 입력하세요" : value+"│");
        entry.setTextColor(empty ? theme.hint : theme.text);
        if (!translating) status.setText(empty
                ? "글자를 입력한 뒤 '번역'을 누르세요" : "번역 버튼 또는 키보드 ↵로 입력");
    }

    public void onTypeText(String value, boolean tap, boolean korean) {
        if (value==null || value.isEmpty() || source().length()>=LIMIT) return;
        if (korean && value.length()==1 && HangulComposer.isJamo(value.charAt(0))) {
            hangul.input(value.charAt(0),tap,android.os.SystemClock.uptimeMillis());
            committed.append(hangul.takeCommit());
        } else {
            flushHangul();
            committed.append(value);
        }
        invalidateTranslation();
        showSourceText();
    }

    private void flushHangul() {
        hangul.flush();
        committed.append(hangul.takeCommit());
    }

    public void onSpace() {
        flushHangul();
        if (source().length()<LIMIT) committed.append(' ');
        invalidateTranslation();
        showSourceText();
    }

    public void onBackspace() {
        if (!hangul.isEmpty()) {
            hangul.backspace();
            committed.append(hangul.takeCommit());
        } else if (committed.length()>0) {
            int p=committed.offsetByCodePoints(committed.length(),-1);
            committed.delete(p, committed.length());
        }
        invalidateTranslation();
        showSourceText();
    }

    public void onDeleteWord() {
        flushHangul();
        int i=committed.length();
        while(i>0 && Character.isWhitespace(committed.charAt(i-1)))i--;
        while(i>0 && !Character.isWhitespace(committed.charAt(i-1)))i--;
        committed.delete(i,committed.length());
        invalidateTranslation();
        showSourceText();
    }

    private void resetText(boolean preserveSelection) {
        invalidateTranslation();
        hangul.reset();
        committed.setLength(0);
        if (!preserveSelection) {originallySelected=false;originalSelection="";}
        showSourceText();
    }

    private void pasteCopiedText() {
        ClipboardManager manager=(ClipboardManager)getContext()
                .getSystemService(Context.CLIPBOARD_SERVICE);
        if(manager==null)return;
        try {
            ClipData data=manager.getPrimaryClip();
            if(data==null || data.getItemCount()==0 || data.getItemAt(0).getText()==null) {
                status.setText("복사한 텍스트가 없습니다");
                return;
            }
            resetText(false);
            CharSequence text=data.getItemAt(0).getText();
            committed.append(text.length()>LIMIT?text.subSequence(0,LIMIT):text);
            showSourceText();
        } catch(RuntimeException ignored) {
            status.setText("클립보드를 읽을 수 없습니다");
        }
    }

    private void invalidateTranslation() {
        generation++;
        translating=false;
        submitButton.setEnabled(true);
        if(translator!=null) {
            translator.close();
            translator=null;
        }
    }

    /** Samsung-style action: translate and commit, without a separate result picker. */
    public void onEnter() {
        flushHangul();
        String input=source();
        if (input.trim().isEmpty() || translating) return;
        if(from.equals(to))return;
        invalidateTranslation();
        final int token=++generation;
        translating=true;
        submitButton.setEnabled(false);
        status.setText("번역 준비 중 · 최초 사용 시 언어 모델 다운로드");
        try {
            TranslatorOptions config=new TranslatorOptions.Builder()
                    .setSourceLanguage(from).setTargetLanguage(to).build();
            final Translator active=Translation.getClient(config);
            translator=active;
            active.downloadModelIfNeeded(new DownloadConditions.Builder().build())
                    .addOnSuccessListener(none -> {
                        if(token!=generation)return;
                        status.setText("번역 중…");
                        active.translate(input).addOnSuccessListener(result -> {
                            if(token!=generation)return;
                            boolean selection = originallySelected && !originalSelection.isEmpty();
                            boolean ok=actions.onApplyTranslation(result, originalSelection,selection,selection);
                            if(ok) {
                                // Keep mode open so the next message can be translated immediately.
                                resetText(false);
                                status.setText("번역 입력 완료 · 다음 문장을 입력할 수 있어요");
                            } else {
                                translating=false;
                                submitButton.setEnabled(true);
                                status.setText("원래 입력칸이 바뀌었습니다. 다시 선택해 주세요");
                            }
                        }).addOnFailureListener(e -> failure(token,"번역 오류 · 다시 시도해 주세요"));
                    })
                    .addOnFailureListener(e -> failure(token,"언어 모델 다운로드 실패 · 인터넷을 확인해 주세요"));
        } catch(RuntimeException | LinkageError e) {
            failure(token,"번역 기능을 실행할 수 없습니다");
        }
    }

    private void failure(int token, String message) {
        if(token!=generation)return;
        translating=false;
        status.setText(message);
        submitButton.setEnabled(true);
        if(translator!=null) {translator.close();translator=null;}
    }

    public void dismiss() {
        invalidateTranslation();
        hangul.reset();
        committed.setLength(0);
        originallySelected=false;
        originalSelection="";
    }
}
