from pathlib import Path

pkg=Path("app/src/main/java/com/alternative_studios/newswipe")
panel=pkg/"KeyboardTranslatePanel.java"
s=panel.read_text(encoding="utf-8")
def swap(old,new,label):
    global s
    count=s.count(old)
    assert count==1,(label,count)
    s=s.replace(old,new,1)

swap('''import android.content.Context;''','''import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.text.SpannableString;
import android.text.Spanned;
import android.text.style.ReplacementSpan;''','caret imports')

swap('''        boolean onApplyTranslation(String translated, String original, boolean selected, boolean replace);''',
'''        boolean onApplyTranslation(String translated, String original, boolean selected, boolean replace);
        void onTranslationCommitted();
        void onToggleHostEditing();''','edit state callbacks')

swap('''    private final TextView fromButton, toButton, entry, submitButton, status;''',
'''    private final TextView fromButton, toButton, entry, submitButton, status, editModeButton;
    private boolean hostEditing;''','panel edit control')

swap('''        entry.setContentDescription("번역할 문장을 아래 자판에서 입력");
        LayoutParams inputParams''',
'''        entry.setContentDescription("번역할 문장을 아래 자판에서 입력");
        // Tapping this field returns to translation typing after editing the app's text.
        entry.setOnClickListener(v -> {
            if (hostEditing) actions.onToggleHostEditing();
        });
        LayoutParams inputParams''','translate field touch')

swap('''        footer.addView(status, new LayoutParams(0, dp(27), 1f));

        TextView paste''',
'''        footer.addView(status, new LayoutParams(0, dp(27), 1f));

        editModeButton = chip("본문 수정", theme.text, theme.functionKey, dp(72));
        editModeButton.setTextSize(11);
        editModeButton.setContentDescription("번역 모드와 원래 글 수정 모드 전환");
        editModeButton.setOnClickListener(v -> actions.onToggleHostEditing());
        footer.addView(editModeButton, new LayoutParams(dp(74), dp(27)));

        TextView paste''','native edit toggle')

swap('''        entry.setText(empty ? "번역할 텍스트를 입력하세요" : value+"│");
        entry.setTextColor(empty ? theme.hint : theme.text);''',
'''        // The unicode box-drawing bar "│" has wide font side bearings on One UI.
        // Render a measured 2dp caret span with NO intervening whitespace instead.
        if (empty) {
            entry.setText("번역할 텍스트를 입력하세요");
        } else {
            SpannableString content = new SpannableString(value + "\\uFFFC");
            content.setSpan(new ReplacementSpan() {
                @Override public int getSize(Paint paint, CharSequence text, int start, int end,
                        Paint.FontMetricsInt fm) {
                    return dp(2);
                }
                @Override public void draw(Canvas canvas, CharSequence text,
                        int start, int end, float x, int top, int y, int bottom, Paint paint) {
                    int oldColor = paint.getColor();
                    Paint.Style oldStyle = paint.getStyle();
                    paint.setColor(theme.text);
                    paint.setStyle(Paint.Style.FILL);
                    canvas.drawRect(x, y - paint.getTextSize() * .83f,
                            x + dp(1), y + dp(2), paint);
                    paint.setColor(oldColor);
                    paint.setStyle(oldStyle);
                }
            }, value.length(), content.length(), Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
            entry.setText(content);
        }
        entry.setTextColor(empty ? theme.hint : theme.text);''','zero-gap caret')

swap('''    public void showSource(String value, boolean selected) {
        originallySelected = selected;''',
'''    public void showSource(String value, boolean selected) {
        setHostEditing(false);
        originallySelected = selected;''','reset mode when opening')

swap('''    private String source() {
        return committed.toString() + hangul.getComposing();
    }''',
'''    /** Keep translation controls visible while normal keyboard keys edit the host app. */
    public void setHostEditing(boolean value) {
        hostEditing = value;
        if (editModeButton != null) {
            editModeButton.setText(value ? "번역 입력" : "본문 수정");
            editModeButton.setContentDescription(value
                    ? "번역 입력창으로 돌아가기" : "원래 앱 입력창의 글 수정");
        }
        if (value) {
            // Selection in the editor may now be unrelated to the original translation.
            originallySelected = false;
            originalSelection = "";
            if (status != null) status.setText("본문 수정 중 · 번역창 터치 시 복귀");
        } else if (status != null) {
            status.setText("번역 입력 중");
        }
    }

    private String source() {
        return committed.toString() + hangul.getComposing();
    }''','host edit status')

swap('''                            if(ok) {
                                // Keep mode open so the next message can be translated immediately.
                                resetText(false);
                                status.setText("번역 입력 완료 · 다음 문장을 입력할 수 있어요");''',
'''                            if(ok) {
                                // After inserting translated text, route typing to the original
                                // app: a tap on the English and Backspace now edits it immediately.
                                resetText(false);
                                actions.onTranslationCommitted();
                                status.setText("원문 수정 중 · 번역 입력창을 누르면 다음 번역");''','direct edit after translation')

panel.write_text(s,encoding="utf-8")

ime=pkg/"NewSwipeIME.java"
s=ime.read_text(encoding="utf-8")
def patch(old,new,label):
    global s
    count=s.count(old)
    assert count==1,(label,count)
    s=s.replace(old,new,1)

patch('''    private int translationOpenedGeneration;''',
'''    private int translationOpenedGeneration;
    private boolean translationEditingHost;
    private long translationOpenedAt;''','edit mode IME fields')

patch('''                    @Override public boolean onApplyTranslation(
                            String translated, String original, boolean selected, boolean replace) {
                        return applyTranslatedText(translated, original, selected, replace);
                    }
                });''',
'''                    @Override public boolean onApplyTranslation(
                            String translated, String original, boolean selected, boolean replace) {
                        return applyTranslatedText(translated, original, selected, replace);
                    }
                    @Override public void onTranslationCommitted() {
                        translationEditingHost = true;
                        if (translationPanel != null) translationPanel.setHostEditing(true);
                    }
                    @Override public void onToggleHostEditing() {
                        translationEditingHost = !translationEditingHost;
                        if (!translationEditingHost) {
                            translationOpenedAt = android.os.SystemClock.uptimeMillis();
                        }
                        if (translationPanel != null)
                            translationPanel.setHostEditing(translationEditingHost);
                    }
                });''','hook actions')

patch('''    private boolean translateMode() {
        return translationPanel != null && translationPanel.getVisibility() == View.VISIBLE;
    }''',
'''    private boolean translateMode() {
        return translationPanel != null && translationPanel.getVisibility() == View.VISIBLE;
    }

    /** Only intercept ordinary keystrokes when the user is typing a translation. */
    private boolean translationInputMode() {
        return translateMode() && !translationEditingHost;
    }''','separate visibility vs input capture')

# In six typing handlers ONLY; don't change panel/window lifecycle checks.
count=s.count('''        if (translateMode()) {''')
assert count==6,('six IME typing handlers',count)
s=s.replace('''        if (translateMode()) {''','''        if (translationInputMode()) {''')

patch('''        translationPanel.showSource(selected ? text : "", selected);
        translationPanel.setVisibility(View.VISIBLE);''',
'''        translationEditingHost = false;
        translationOpenedAt = android.os.SystemClock.uptimeMillis();
        translationPanel.showSource(selected ? text : "", selected);
        translationPanel.setHostEditing(false);
        translationPanel.setVisibility(View.VISIBLE);''','translation open state')

patch('''        translationPanel.dismiss();
        translationPanel.setVisibility(View.GONE);
        if (topSlot != null) applyTopSlotVisibility();''',
'''        translationPanel.dismiss();
        translationPanel.setVisibility(View.GONE);
        translationEditingHost = false;
        if (topSlot != null) applyTopSlotVisibility();''','translation close state')

patch('''        super.onUpdateSelection(oldSelStart, oldSelEnd, newSelStart, newSelEnd, candidatesStart, candidatesEnd);
        String mirrored = mirror.text();''',
'''        super.onUpdateSelection(oldSelStart, oldSelEnd, newSelStart, newSelEnd, candidatesStart, candidatesEnd);
        // Touching or selecting previously translated English in the host editor
        // automatically releases the keys back to normal editing, without closing
        // the translation controls. Ignore startup/composition transient updates.
        if (translationInputMode() && newSelStart >= 0 && newSelEnd >= 0
                && (newSelStart != oldSelStart || newSelEnd != oldSelEnd)
                && android.os.SystemClock.uptimeMillis() - translationOpenedAt > 400
                && candidatesStart < 0 && candidatesEnd < 0) {
            translationEditingHost = true;
            translationPanel.setHostEditing(true);
        }
        String mirrored = mirror.text();''','tap host to edit')

ime.write_text(s,encoding="utf-8")
print("Fixed caret glyph width, host app direct editing while translating, and explicit edit mode fallback.")
