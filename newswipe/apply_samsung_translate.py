from pathlib import Path

pkg=Path("app/src/main/java/com/alternative_studios/newswipe")
target=pkg/"KeyboardTranslatePanel.java"
target.write_bytes(Path("../newswipe/KeyboardTranslateSamsung.java").read_bytes())

p=pkg/"NewSwipeIME.java"
s=p.read_text()
def replace(a,b,label):
 global s
 n=s.count(a)
 assert n==1,(label,n)
 s=s.replace(a,b,1)

# Put the translation strip ABOVE the normal keyboard rather than below it.
replace('''        root.addView(translationPanel, 1, new LinearLayout.LayoutParams(''',
'''        root.addView(translationPanel, 0, new LinearLayout.LayoutParams(''','translation overlay index')

# Preserve the keyboard when the translation strip is shown.
replace('''        translationPanel.showSource(text, selected);
        body.setVisibility(View.GONE);
        translationPanel.setVisibility(View.VISIBLE);
        refreshBottomInset(null);''',
'''        // Samsung keyboard-style: a new translation entry stays inside the IME,
        // with original host text untouched until the translated result is sent.
        translationPanel.showSource(selected ? text : "", selected);
        translationPanel.setVisibility(View.VISIBLE);
        if (topSlot != null) topSlot.setVisibility(View.GONE);
        if (keyboard != null) keyboard.cancelAll();
        refreshBottomInset(null);''','preserve keyboard')

replace('''        translationPanel.dismiss();
        translationPanel.setVisibility(View.GONE);
        if (body != null) body.setVisibility(View.VISIBLE);
        refreshBottomInset(null);''',
'''        translationPanel.dismiss();
        translationPanel.setVisibility(View.GONE);
        if (topSlot != null) applyTopSlotVisibility();
        refreshBottomInset(null);''','restore toolbar')

# Route typed text to the translation pill, not to the active application.
replace('''    private void typeText(String s, boolean tap) {
        if (s == null || s.isEmpty()) return;''',
'''    private void typeText(String s, boolean tap) {
        if (s == null || s.isEmpty()) return;
        if (translateMode()) {
            translationPanel.onTypeText(s, tap, korean && lettersLayout());
            if (shiftState == 1 && lettersLayout() && !keyboard.isShiftHeld()) setShift(0);
            return;
        }''','text routing')

replace('''    private void handleSpace() {''',
'''    private void handleSpace() {
        if (translateMode()) {
            translationPanel.onSpace();
            return;
        }''','space routing')

replace('''    private void handleDelete(boolean skipSelectionCheck) {''',
'''    private void handleDelete(boolean skipSelectionCheck) {
        if (translateMode()) {
            translationPanel.onBackspace();
            return;
        }''','backspace routing')

replace('''    private void handleEnter() {''',
'''    private void handleEnter() {
        if (translateMode()) {
            translationPanel.onEnter();
            return;
        }''','enter routing')

replace('''    public void onDeleteRepeat(boolean word) {
        // 더 지울 것이 없어 커서가 멈췄으면 진동하지 않는다 (지우기 자체는 예전처럼 보낸다).''',
'''    public void onDeleteRepeat(boolean word) {
        if (translateMode()) {
            if (word) translationPanel.onDeleteWord();
            else translationPanel.onBackspace();
            return;
        }
        // 더 지울 것이 없어 커서가 멈췄으면 진동하지 않는다 (지우기 자체는 예전처럼 보낸다).''','repeat-delete routing')

replace('''    private void onDeleteWord() {''',
'''    private void onDeleteWord() {
        if (translateMode()) {
            translationPanel.onDeleteWord();
            return;
        }''','word delete routing')

replace('''    private void showPanel(int p) {
        dismissForgetDialog();''',
'''    private void showPanel(int p) {
        if (p != PANEL_KEYBOARD && translateMode()) closeTranslationPanel();
        dismissForgetDialog();''','panel transitions')

replace('''    public void onWindowHidden() {
        super.onWindowHidden();''',
'''    public void onWindowHidden() {
        if (translateMode()) closeTranslationPanel();
        super.onWindowHidden();''','window hide')

replace('''    private void openTranslationPanel() {''',
'''    private boolean translateMode() {
        return translationPanel != null && translationPanel.getVisibility() == View.VISIBLE;
    }

    private void openTranslationPanel() {''','translation mode helper')

# Avoid resurrecting toolbar on translation mode when suggestions refresh.
replace('''    private void applyTopSlotVisibility() {
        if (panel == PANEL_KEYBOARD && topSlot != null) topSlot.setVisibility(toolbarGone() ? View.GONE : View.VISIBLE);''',
'''    private void applyTopSlotVisibility() {
        if (panel == PANEL_KEYBOARD && topSlot != null)
            topSlot.setVisibility(translateMode() || toolbarGone() ? View.GONE : View.VISIBLE);''','top slot while translate')

# Protection: do not replace a user-selected range with a translation if it
# no longer matches the original selection captured before asynchronous work.
# Existing applyTranslatedText performs this check.
p.write_text(s)
print("Samsung-like compact input strip with routed Hangul/English typing integrated.")
