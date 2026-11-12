from pathlib import Path

root=Path("app/src/main/java/com/alternative_studios/newswipe")
ime=root/"NewSwipeIME.java"
af=root/"InlineAutofill.java"

def swap(path, before, after, tag):
    t=path.read_text(encoding="utf-8")
    n=t.count(before)
    assert n==1,(tag,n)
    path.write_text(t.replace(before,after,1),encoding="utf-8")

swap(ime,
'''    private View autofillBar;
    private View toolSpacer;''',
'''    private View autofillBar;
    /** Visible only if an Android Autofill chip arrives or a new text
     * clipboard preview is offered. Never shown for ordinary suggestions.
     * Keeps the entire first toolbar row available for icons. */
    private FrameLayout eventPreviewRow;
    private TextView eventCopiedPreview;
    private View toolSpacer;''',
"event preview fields")

swap(ime,
'''        column.addView(topSlot, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, toolbarHeight));

        resultViews.clear();''',
'''        column.addView(topSlot, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, toolbarHeight));

        // A second full-width row is built once but takes NO screen height
        // until Samsung Pass / Android Autofill returns an inline suggestion,
        // or the user copies text. Text predictions never activate this row.
        eventPreviewRow = new FrameLayout(this);
        eventPreviewRow.setBackgroundColor(theme.background);
        eventPreviewRow.setPadding(Ui.dp(this, 6), Ui.dp(this, 3),
                Ui.dp(this, 6), Ui.dp(this, 3));
        eventPreviewRow.setVisibility(View.GONE);
        if (autofillBar != null) {
            toolbar.removeView(autofillBar);
            eventPreviewRow.addView(autofillBar,
                    new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,
                            ViewGroup.LayoutParams.MATCH_PARENT));
        }
        eventCopiedPreview = new TextView(this);
        eventCopiedPreview.setTextSize(TypedValue.COMPLEX_UNIT_SP, 16);
        eventCopiedPreview.setTextColor(theme.text);
        eventCopiedPreview.setGravity(Gravity.CENTER_VERTICAL);
        eventCopiedPreview.setPadding(Ui.dp(this, 14), 0, Ui.dp(this, 14), 0);
        eventCopiedPreview.setMaxLines(2);
        eventCopiedPreview.setEllipsize(TextUtils.TruncateAt.END);
        eventCopiedPreview.setBackground(Ui.round(theme.functionKey, Ui.dp(this, 14)));
        eventCopiedPreview.setContentDescription("복사한 내용 붙여넣기");
        eventCopiedPreview.setOnClickListener(v -> {
            feedback.onToolbar();
            pasteClipChip();
        });
        eventCopiedPreview.setVisibility(View.GONE);
        FrameLayout.LayoutParams previewParams = new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT);
        previewParams.setMargins(Ui.dp(this, 3), Ui.dp(this, 2),
                Ui.dp(this, 3), Ui.dp(this, 2));
        eventPreviewRow.addView(eventCopiedPreview, previewParams);
        column.addView(eventPreviewRow, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, Ui.dp(this, 56)));

        resultViews.clear();''',
"add conditional full-width row")

swap(ime,
'''        if (autofillBar != null) {
            toolbar.addView(autofillBar, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.MATCH_PARENT, 1f));
        }
        for (String id : order[1])''',
'''        // Autofill chips live in eventPreviewRow, never in this cramped
        // icons-only row. Reordering toolbar buttons must not move them back.
        for (String id : order[1])''',
"keep suggestions in dedicated row after reordering")

swap(ime,
'''        // 칩은 쪽으로 넘기며 보므로, 한 칩이 칩 줄(왼쪽 도구 버튼을 뺀 폭에서 쪽 넘김 버튼·고정 칩 자리를 뺀 폭)에
        // 들어갈 만큼만 키운다. 긴 글은 서비스가 줄여 보인다.
        int maxWidth = Math.max(Ui.dp(this, 96), Math.min(Ui.dp(this, 260), chipSlotWidth() - autofill.reservedWidth()));
        return autofill.request(t, height, maxWidth);''',
'''        // Dedicated full-width row, not the tiny slot left after toolbar
        // icons. Android/Samsung renders credential content, not this IME.
        int maxWidth = Math.max(Ui.dp(this, 96),
                Math.min(Ui.dp(this, 520),
                        getResources().getDisplayMetrics().widthPixels - Ui.dp(this, 44)));
        return autofill.request(t, Ui.dp(this, 52), maxWidth);''',
"larger Android inline chip presentation specs")

# Existing translation/customization patches sometimes add conditions to the
# suggesting expression, so modify only the autofill term while preserving all
# their other reasons to collapse toolbar buttons.
text_ime=ime.read_text(encoding="utf-8")
start=text_ime.index("        boolean suggesting = ")
finish=text_ime.index(";",start)+1
statement=text_ime[start:finish]
assert "autofillShowing()" in statement,statement
import re
updated,n=re.subn(r"\s*\|\|\s*autofillShowing\(\)", "", statement, count=1)
assert n==1,(statement,n)
text_ime=text_ime.replace(statement,updated,1)
start=text_ime.index("        boolean on = prefs.toolbar()")
finish=text_ime.index(";",start)+1
on_statement=text_ime[start:finish]
assert "autofillShowing()" not in on_statement
text_ime=text_ime.replace(on_statement,on_statement[:-1]+" || autofillShowing();",1)
ime.write_text(text_ime,encoding="utf-8")

# This part of the toolbar has changed across earlier clipboard/translation
# patches; replace only the final chip-display tail of the method, preserving
# the rest of the user's original toolbar behavior.
src=ime.read_text(encoding="utf-8")
method=src.index("    private void refreshToolbarVisibility()")
start=src.index("        boolean chip =",method)
end=src.index("\n    /** 방금 복사한 내용 칩",start)
assert end-start < 1600, ("unexpected refreshToolbarVisibility tail",end-start)
src=src[:start]+'''        toolSpacer.setVisibility(suggesting ? View.GONE : View.VISIBLE);
        if (clipChipSlot != null) clipChipSlot.setVisibility(View.GONE);
        updateEventPreviewRow(candidates);
    }

    /** Only Autofill inline suggestions or freshly copied text use this
     * second row. Protect sensitive/secret clipboard previews. */
    private void updateEventPreviewRow(boolean candidatesVisible) {
        if (eventPreviewRow == null || eventCopiedPreview == null) return;
        boolean inline = panel == PANEL_KEYBOARD && autofillShowing()
                && !candidatesVisible;
        boolean copied = panel == PANEL_KEYBOARD && !inline && clipChipShowing();
        if (autofillBar != null) autofillBar.setVisibility(inline ? View.VISIBLE : View.GONE);
        if (copied) {
            boolean secret = passwordField || clipChipPreview == null;
            eventCopiedPreview.setText(secret ? "복사한 내용 · 미리보기 숨김" : clipChipPreview);
            eventCopiedPreview.setContentDescription(
                    secret ? "복사한 내용 붙여넣기" : "복사한 내용 붙여넣기: " + clipChipPreview);
        }
        eventCopiedPreview.setVisibility(copied ? View.VISIBLE : View.GONE);
        int next = (inline || copied) ? View.VISIBLE : View.GONE;
        if (eventPreviewRow.getVisibility() != next) {
            eventPreviewRow.setVisibility(next);
            if (keyboard != null) updatePanelSizes();
        }
    }
''' + src[end:]
ime.write_text(src,encoding="utf-8")

# Avoid shrinking/fragmented inline account text: request 16sp in the
# AndroidX-compatible inline presentation style. Provider controls rendering.
swap(af,'''        v1.putBundle("title_style", textStyle(theme.text, 14));''',
'''        v1.putBundle("title_style", textStyle(theme.text, 16));''',
"increase requested account label font size")
swap(af,'''        v1.putBundle("subtitle_style", textStyle(theme.hint, 12));''',
'''        v1.putBundle("subtitle_style", textStyle(theme.hint, 13));''',
"increase secondary account text size")

# Invariants: when no event exists, extra row is GONE, and word suggestions
# alone cannot activate it. Apps never receive raw Samsung Pass credentials.
t=ime.read_text(encoding="utf-8")
assert "eventPreviewRow.setVisibility(View.GONE)" in t
assert "boolean copied = panel == PANEL_KEYBOARD && !inline && clipChipShowing();" in t
assert "|| autofillShowing();" in t
assert "return autofill.request(t, Ui.dp(this, 52), maxWidth);" in t
assert t.count("eventPreviewRow.addView(")==2
assert "updateEventPreviewRow(candidates);" in t
assert 'if (clipChipSlot != null) clipChipSlot.setVisibility(View.GONE);' in t
assert 'getPrimaryClip()' in t
print("NewSwipe v2.2.1: conditional 56dp second row for inline Autofill or recent copied text; toolbar icons retain width, sensitive previews masked.")
