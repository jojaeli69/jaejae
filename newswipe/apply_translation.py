from pathlib import Path

base=Path("app/src/main")
pkg=base/"java/com/alternative_studios/newswipe"
(source:=pkg/"KeyboardTranslatePanel.java").write_bytes(Path("../newswipe/KeyboardTranslatePanel.java").read_bytes())
# Internet is used only to download on-device language models (no text upload).
manifest=base/"AndroidManifest.xml"
m=manifest.read_text()
assert '<uses-permission android:name="android.permission.INTERNET" />' not in m
m=m.replace('<uses-permission android:name="android.permission.VIBRATE" />','<uses-permission android:name="android.permission.VIBRATE" />\n    <uses-permission android:name="android.permission.INTERNET" />',1)
manifest.write_text(m)

# ML Kit on-device translation, no server or API key, models loaded on demand.
gradle=Path("app/build.gradle.kts")
g=gradle.read_text()
assert '\ndependencies {\n' in g
g=g.replace('\ndependencies {\n','\ndependencies {\n    implementation("com.google.mlkit:translate:17.0.3")\n',1)
gradle.write_text(g)

p=pkg/"NewSwipeIME.java"
s=p.read_text()
def sub(a,b,label):
    global s
    n=s.count(a)
    assert n==1,(label,n)
    s=s.replace(a,b,1)

sub('    private ClipboardHistory clipHistory;',
'''    private ClipboardHistory clipHistory;
    private TextView translateQuickButton;
    private KeyboardTranslatePanel translationPanel;
    private int translationInputGeneration;
    private int translationOpenedGeneration;
    private String translationOriginalPackage;
    private int translationOriginalFieldId;
''','translation member fields')

sub('''        toolSpacer = new View(this);
        bar.addView(toolSpacer, new LinearLayout.LayoutParams(0, 1, 1f));''',
'''        translateQuickButton = new TextView(this);
        translateQuickButton.setText("번역");
        translateQuickButton.setTextSize(13);
        translateQuickButton.setTextColor(theme.text);
        translateQuickButton.setGravity(Gravity.CENTER);
        translateQuickButton.setContentDescription("선택한 글이나 입력 문장 번역");
        translateQuickButton.setClickable(true);
        translateQuickButton.setBackgroundColor(theme.key);
        translateQuickButton.setOnClickListener(v -> { feedback.onToolbar(); openTranslationPanel(); });
        bar.addView(translateQuickButton, new LinearLayout.LayoutParams(Ui.dp(this, 47), toolbarHeight));
        toolSpacer = new View(this);
        bar.addView(toolSpacer, new LinearLayout.LayoutParams(0, 1, 1f));''','build translation quick button')

sub('''        for (String id : ToolbarButtons.ALL) toolbar.removeView(toolButtonOf(id));
        toolbar.removeView(toolSpacer);''',
'''        for (String id : ToolbarButtons.ALL) toolbar.removeView(toolButtonOf(id));
        toolbar.removeView(translateQuickButton);
        toolbar.removeView(toolSpacer);''','tool order remove')

sub('''        for (String id : order[0]) toolbar.addView(toolButtonOf(id));
        toolbar.addView(toolSpacer, new LinearLayout.LayoutParams(0, 1, 1f));''',
'''        for (String id : order[0]) toolbar.addView(toolButtonOf(id));
        toolbar.addView(translateQuickButton,
                new LinearLayout.LayoutParams(Ui.dp(this, 47), toolbarHeight));
        toolbar.addView(toolSpacer, new LinearLayout.LayoutParams(0, 1, 1f));''','tool order add')

sub('''        boolean on = prefs.toolbar() || toolbarOnlyNow();''',
'''        boolean on = prefs.toolbar() || toolbarOnlyNow();
        if (translateQuickButton != null) {
            translateQuickButton.setVisibility(on && !passwordField && !candidates
                    && panel == PANEL_KEYBOARD ? View.VISIBLE : View.GONE);
        }''','toolbar button visibility')

sub('''        applyNavigationBarStyle();
        return root;
    }''',
'''        applyNavigationBarStyle();
        translationPanel = new KeyboardTranslatePanel(this, theme.text, theme.background,
                new KeyboardTranslatePanel.Actions() {
                    @Override public void onCloseTranslation() { closeTranslationPanel(); }
                    @Override public boolean onApplyTranslation(
                            String translated, String original, boolean selected, boolean replace) {
                        return applyTranslatedText(translated, original, selected, replace);
                    }
                });
        translationPanel.setVisibility(View.GONE);
        root.addView(translationPanel, 1, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        return root;
    }''','input view translation panel')

sub('''    public View onCreateInputView() {
        dismissForgetDialog();''',
'''    public View onCreateInputView() {
        if (translationPanel != null) translationPanel.dismiss();
        dismissForgetDialog();''','input view lifecycle')

sub('''    public void onStartInputView(EditorInfo info, boolean restarting) {
        super.onStartInputView(info, restarting);''',
'''    public void onStartInputView(EditorInfo info, boolean restarting) {
        closeTranslationPanel();
        translationInputGeneration++;
        super.onStartInputView(info, restarting);''','track editing field')

sub('''    public void onFinishInput() {''',
'''    public void onFinishInput() {
        closeTranslationPanel();
        translationInputGeneration++;''','input end')

sub('''    public void onDestroy() {
        if (clipboard != null) clipboard.removePrimaryClipChangedListener(this);''',
'''    public void onDestroy() {
        if (translationPanel != null) translationPanel.dismiss();
        if (clipboard != null) clipboard.removePrimaryClipChangedListener(this);''','destroy')

needle='''    /** 텍스트를 커서 자리에 붙여 넣는다 (키를 누르는 소리·진동은 부르는 쪽이 정한다). */'''
assert s.count(needle)==1
s=s.replace(needle,'''    /** Only user-initiated translation of the visible editor's selected/preceding text. */
    private void openTranslationPanel() {
        if (translationPanel == null || body == null || passwordField) return;
        InputConnection ic = getCurrentInputConnection();
        EditorInfo info = getCurrentInputEditorInfo();
        if (ic == null || info == null) return;
        commitComposing();
        CharSequence selectedText = ic.getSelectedText(0);
        boolean selected = selectedText != null && selectedText.length() > 0;
        CharSequence source = selected ? selectedText : ic.getTextBeforeCursor(350, 0);
        String text = source == null ? "" : source.toString();
        if (text.length() > 350) text = text.substring(text.length() - 350);
        if (!selected) {
            int newLine = text.lastIndexOf('\\n');
            if (newLine >= 0) text = text.substring(newLine + 1);
        }
        translationOriginalPackage = info.packageName;
        translationOriginalFieldId = info.fieldId;
        translationOpenedGeneration = translationInputGeneration;
        translationPanel.showSource(text, selected);
        body.setVisibility(View.GONE);
        translationPanel.setVisibility(View.VISIBLE);
        refreshBottomInset(null);
    }

    private void closeTranslationPanel() {
        if (translationPanel == null || translationPanel.getVisibility() != View.VISIBLE) return;
        translationPanel.dismiss();
        translationPanel.setVisibility(View.GONE);
        if (body != null) body.setVisibility(View.VISIBLE);
        refreshBottomInset(null);
    }

    private boolean applyTranslatedText(String translated, String original,
                                        boolean selected, boolean replace) {
        if (translationInputGeneration != translationOpenedGeneration || passwordField) return false;
        EditorInfo now = getCurrentInputEditorInfo();
        InputConnection ic = getCurrentInputConnection();
        if (ic == null || now == null
                || now.fieldId != translationOriginalFieldId
                || !TextUtils.equals(now.packageName, translationOriginalPackage)) return false;
        if (replace) {
            CharSequence actual = selected ? ic.getSelectedText(0)
                    : ic.getTextBeforeCursor(original.length(), 0);
            if (!TextUtils.equals(actual, original)) return false;
        }
        commitComposing();
        ic.beginBatchEdit();
        if (replace && !selected) ic.deleteSurroundingText(original.length(), 0);
        boolean success = ic.commitText(translated, 1);
        ic.endBatchEdit();
        if (success) {
            mirror.forget();
            scheduleSuggest();
        }
        return success;
    }

'''+needle,1)

p.write_text(s)
print("Translation button, inline sheet and editor-safe replacement integrated.")
