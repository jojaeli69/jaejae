from pathlib import Path

source=Path("app/src/main/java/com/alternative_studios/newswipe")
panel=source/"KeyboardTranslatePanel.java"
ime=source/"NewSwipeIME.java"
settings=source/"SettingsActivity.java"
manifest=Path("app/src/main/AndroidManifest.xml")

def once(path, old, new, tag):
    contents=path.read_text(encoding="utf-8")
    count=contents.count(old)
    assert count==1, (tag,count)
    path.write_text(contents.replace(old,new,1),encoding="utf-8")

once(panel,
'''        if (input.trim().isEmpty() || translating) return;
        if(from.equals(to))return;
        invalidateTranslation();''',
'''        if (input.trim().isEmpty() || translating) return;
        if(from.equals(to))return;
        // Only the explicit Translate action can send the typed source to
        // the user's DeepL API account. No background typing/clipboard uploads.
        if (DeepLTranslate.enabled(getContext())) {
            translateWithDeepL(input);
            return;
        }
        invalidateTranslation();''',
"opt-in online translation in existing translate action")

needle='''    private void failure(int token, String message, Throwable cause) {'''
s=panel.read_text(encoding="utf-8")
assert s.count(needle)==1,("error handler insertion",s.count(needle))
method='''    /**
     * Online translation never silently falls back to an unrelated engine.
     * This keeps failures clear and never inserts a partial result.
     * Translation text is sent only after the user taps Translate.
     */
    private void translateWithDeepL(String input) {
        invalidateTranslation();
        final int token = ++generation;
        translating = true;
        submitButton.setEnabled(false);
        status.setText("DeepL 고품질 번역 중…");
        DeepLTranslate.translate(getContext(), input, from, to, result -> {
            if (token != generation) return;
            boolean selection = originallySelected && !originalSelection.isEmpty();
            boolean inserted = actions.onApplyTranslation(result, originalSelection,
                    selection, selection);
            if (inserted) {
                // Mirror the existing ML Kit success behavior: return to
                // host editing while keeping translation controls available.
                resetText(false);
                actions.onTranslationCommitted();
                status.setText("DeepL 번역 완료 · 본문 수정 중");
            } else {
                translating = false;
                pendingCopyResult = result;
                submitButton.setText("복사");
                submitButton.setEnabled(true);
                status.setText("번역 완료 · 삽입 실패 · 복사 가능");
                Toast.makeText(getContext(),
                        "번역 완료 · 입력창에 삽입할 수 없어 복사를 선택할 수 있습니다",
                        Toast.LENGTH_LONG).show();
            }
        }, error -> {
            if (token != generation) return;
            translating = false;
            submitButton.setText("재시도");
            submitButton.setEnabled(!source().trim().isEmpty());
            status.setText(error);
            Toast.makeText(getContext(), error, Toast.LENGTH_LONG).show();
        });
    }

'''
panel.write_text(s.replace(needle,method+needle,1),encoding="utf-8")

# Allow users to reach key settings directly from the existing Translate chip
# without adding a permanent toolbar button or reducing typing area.
once(panel,
'''        submitButton.setOnClickListener(v -> onEnter());''',
'''        submitButton.setOnClickListener(v -> onEnter());
        submitButton.setOnLongClickListener(v -> {
            android.content.Intent intent = new android.content.Intent(getContext(),
                    DeepLSettingsActivity.class);
            intent.addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK);
            try {
                getContext().startActivity(intent);
            } catch (RuntimeException ignored) {
                Toast.makeText(getContext(),
                        "NewSwipe 설정에서 DeepL 번역을 설정해 주세요",
                        Toast.LENGTH_LONG).show();
            }
            return true;
        });''',
"long-press translate to configure engine")

# Register a separate settings screen. Key input must remain in an Activity,
# not within the IME where keystrokes would be visible to the keyboard itself.
once(manifest,
'''        <activity
            android:name=".SettingsActivity"''',
'''        <activity
            android:name=".DeepLSettingsActivity"
            android:exported="false"
            android:label="NewSwipe 온라인 번역"
            android:screenOrientation="portrait"
            android:windowSoftInputMode="adjustResize" />

        <activity
            android:name=".SettingsActivity"''',
"register local DeepL settings activity")

once(settings,
'''        buildDictionaryPack();''',
'''        LinearLayout betterTranslate = section("고품질 번역 · DeepL");
        betterTranslate.addView(button("DeepL API 키 · 온라인 번역 설정",
                v -> startActivity(new Intent(this, DeepLSettingsActivity.class))));
        betterTranslate.addView(note("기본 번역은 기기 내 ML Kit입니다. "
                + "DeepL API 키를 등록하고 온라인 번역을 켜면 "
                + "번역 버튼을 눌렀을 때의 원문만 DeepL로 전송됩니다. "
                + "일반 타이핑과 비밀번호는 전송하지 않습니다. "
                + "DeepL에 별도 가입 및 API 인증키가 필요합니다."));

        buildDictionaryPack();''',
"add visible DeepL engine settings")

# Existing privacy description must remain truthful with optional online mode.
once(settings,
'''        about.addView(note("모든 처리는 기기 안에서만 하며 인터넷을 쓰지 않습니다. 비밀번호·이메일 입력란에서는 학습을 하지 않습니다."));''',
'''        about.addView(note("기본 키보드 입력과 ML Kit 번역은 기기 내에서 처리합니다. "
                + "DeepL 온라인 번역을 명시적으로 켜고 번역 버튼을 누르면 해당 원문만 DeepL 서버로 전송됩니다. "
                + "비밀번호·이메일 입력란에서는 학습하지 않습니다."));''',
"update privacy copy for online translation")

for path,code in [
 (source/"DeepLTranslate.java", "public static void translate(Context context"),
 (source/"DeepLSettingsActivity.java", "DeepLTranslate.saveKey(this, key, legacyFree.isChecked())"),
 (panel, "private void translateWithDeepL(String input)"),
 (panel, "DeepLTranslate.enabled(getContext())"),
 (settings, "DeepL API 키 · 온라인 번역 설정"),
 (manifest, "android:name=\".DeepLSettingsActivity\"")]:
    assert code in path.read_text(encoding="utf-8"),(str(path),code)
assert 'android.permission.INTERNET' in manifest.read_text(encoding="utf-8")
assert 'key_ciphertext' in (source/"DeepLTranslate.java").read_text(encoding="utf-8")
assert 'AndroidKeyStore' in (source/"DeepLTranslate.java").read_text(encoding="utf-8")
assert 'https://api.deepl.com/v2/translate' in (source/"DeepLTranslate.java").read_text(encoding="utf-8")
print("NewSwipe v2.2.6: opt-in DeepL online natural translation with encrypted user API key, safe ML Kit fallback and explicit privacy notes.")
