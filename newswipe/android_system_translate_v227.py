from pathlib import Path
p=Path("app/src/main/java/com/alternative_studios/newswipe/KeyboardTranslatePanel.java")
s=p.read_text(encoding="utf-8")

def one(old, new, reason):
    global s
    n=s.count(old)
    assert n==1,(reason,n)
    s=s.replace(old,new,1)

# Preserve the exact existing translation panel and single Translate button.
# Prefer Android's PUBLIC on-device translator (if this Galaxy implements
# a service). The service could be Samsung, Google or another OEM; do not
# claim it is the proprietary Samsung Keyboard / Galaxy AI translator.
# The official OS call needs no user API key.
one('''    private String pendingCopyResult;''',
'''    private String pendingCopyResult;
    /** One-shot guard for fallback into current ML Kit translator. */
    private boolean retryLocalTranslation;''',
"one-shot fallback state")

one('''        if (DeepLTranslate.enabled(getContext())) {
            translateWithDeepL(input);
            return;
        }
        invalidateTranslation();''',
'''        if (DeepLTranslate.enabled(getContext())) {
            // Explicit online setting still overrides both offline engines.
            translateWithDeepL(input);
            return;
        }
        if (!retryLocalTranslation) {
            translateWithAndroidSystem(input);
            return;
        }
        retryLocalTranslation = false;
        invalidateTranslation();''',
"public OS service first, then existing ML Kit translation, no new buttons")

needle='''    private void translateWithDeepL(String input) {'''
assert s.count(needle)==1, ("online translation method",s.count(needle))
method='''    /** No navigation, account setup or API key: use the existing button.
     * Samsung/Google/OEM may provide Android's on-device translator. */
    private void translateWithAndroidSystem(String input) {
        invalidateTranslation();
        final int token = ++generation;
        translating = true;
        submitButton.setEnabled(false);
        status.setText("기기 번역 엔진 확인 중…");
        AndroidSystemTranslate.translate(getContext(), input, from, to, result -> {
            if (token != generation) return;
            boolean selection = originallySelected && !originalSelection.isEmpty();
            boolean inserted = actions.onApplyTranslation(result, originalSelection,
                    selection, selection);
            if (inserted) {
                resetText(false);
                actions.onTranslationCommitted();
                status.setText("번역 완료 · 본문 수정 중");
            } else {
                translating = false;
                pendingCopyResult = result;
                submitButton.setText("복사");
                submitButton.setEnabled(true);
                status.setText("번역 완료 · 입력창 삽입 실패 · 복사 가능");
            }
        }, reason -> {
            if (token != generation) return;
            // A device without an Android TranslationService still works
            // with the same on-device ML Kit translator as prior releases.
            translating = false;
            retryLocalTranslation = true;
            status.setText("기기 번역 미지원 · 기존 번역으로 전환");
            onEnter();
        });
    }

'''
s=s.replace(needle,method+needle,1)
p.write_text(s,encoding="utf-8")

# Add only a true description, with no new toolbar buttons/settings to
# burden the original 1-tap translation workflow.
settings=Path("app/src/main/java/com/alternative_studios/newswipe/SettingsActivity.java")
t=settings.read_text(encoding="utf-8")
old='''        betterTranslate.addView(note("기본 번역은 기기 내 ML Kit입니다. "'''
new='''        betterTranslate.addView(note("기본 번역은 Android 기기 번역 서비스를 먼저 확인하고, "
                + "지원하지 않으면 기기 내 ML Kit를 사용합니다. 삼성 전용 Galaxy AI 엔진과는 별도입니다. "'''
assert t.count(old)==1,("about default translator",t.count(old))
t=t.replace(old,new,1)
settings.write_text(t,encoding="utf-8")

s=p.read_text(encoding="utf-8")
assert "AndroidSystemTranslate.translate(getContext(), input, from, to, result -> {" in s
assert "retryLocalTranslation = true;" in s
assert "onEnter();" in s
assert "DeepLTranslate.enabled(getContext())" in s
assert "actions.onApplyTranslation(result, originalSelection" in s
assert "private void translateWithAndroidSystem(String input)" in s
assert 'private void translateWithDeepL(String input)' in s
assert "Translation.getClient" in s
print("v2.2.7: retain original NewSwipe 1-tap UI; try Android OS on-device translator first (OEM unknown), auto-fallback to existing ML Kit, no API key required.")
