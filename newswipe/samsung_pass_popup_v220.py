from pathlib import Path
root=Path("app/src/main/java/com/alternative_studios/newswipe")

def one(path,old,new,tag):
    s=path.read_text(encoding="utf-8")
    count=s.count(old)
    assert count==1, (tag,count)
    path.write_text(s.replace(old,new,1),encoding="utf-8")

prefs=root/"Prefs.java"
one(prefs,
'''    public static final String AUTOFILL_INLINE = "autofill_inline";''',
'''    /** Use framework's legacy popup Autofill instead of keyboard inline chips.
     * Defaults on Samsung phones for Samsung Pass compatibility, and can be
     * disabled to opt back into Android 11+ inline chips. */
    public static final String AUTOFILL_POPUP_MODE = "autofill_popup_mode";
    public static final String AUTOFILL_INLINE = "autofill_inline";''',
"preference key")
one(prefs,
'''    public boolean autofillInline() { return sp.getBoolean(AUTOFILL_INLINE, true); }''',
'''    public boolean autofillInline() { return sp.getBoolean(AUTOFILL_INLINE, true); }
    /** Samsung Pass may prefer the pre-Android-11 overlay on non-Samsung IMEs.
     * This preference never reads login fields or credentials. */
    public boolean autofillPopupMode() {
        return sp.getBoolean(AUTOFILL_POPUP_MODE,
                "samsung".equalsIgnoreCase(android.os.Build.MANUFACTURER));
    }''',
"popup mode getter")
ime=root/"NewSwipeIME.java"
one(ime,
'''        if (autofill == null || !prefs.autofillInline()) return null;''',
'''        // A third-party keyboard cannot force Samsung Pass to publish inline
        // password suggestions. On Samsung devices the default compatibility
        // mode allows Android/Samsung Pass to show its normal popup overlay,
        // instead of requesting an inline chip which might never arrive.
        // Users can switch back to inline chips from keyboard settings.
        if (autofill == null || !prefs.autofillInline() || prefs.autofillPopupMode()) return null;''',
"IME standard popup fallback")
settings=root/"SettingsActivity.java"
one(settings,
'''            autofill.addView(note("기기 설정에서 고른 자동 완성 서비스(Autofill with Google, 삼성 패스 등)를 사용합니다. "));''',
'''            autofill.addView(toggle("삼성패스 호환 모드 (앱 위 팝업)",
                    "삼성 기기에서는 기본 켜짐. 키보드 안쪽 칩 대신 Android의 기본 자동입력 팝업을 사용합니다. "
                    + "이 방식에서도 앱이 자동완성을 지원해야 제안이 나타납니다. "
                    + "끄면 키보드 위 자동완성 칩을 사용합니다.",
                    Prefs.AUTOFILL_POPUP_MODE, prefs.autofillPopupMode()));
            String providerText = "자동입력 서비스: 확인할 수 없음";
            try {
                android.view.autofill.AutofillManager mgr =
                        (android.view.autofill.AutofillManager)
                        getSystemService(android.content.Context.AUTOFILL_SERVICE);
                android.content.ComponentName chosen = mgr != null
                        ? mgr.getAutofillServiceComponentName() : null;
                if (chosen == null) providerText = "자동입력 서비스: 선택되지 않음 또는 사용할 수 없음";
                else if (chosen.getPackageName().toLowerCase(java.util.Locale.ROOT).contains("samsung")
                        && chosen.getPackageName().toLowerCase(java.util.Locale.ROOT).contains("pass"))
                    providerText = "자동입력 서비스: Samsung Pass";
                else providerText = "자동입력 서비스: " + chosen.getPackageName();
            } catch (RuntimeException ignored) { }
            autofill.addView(note(providerText));
            autofill.addView(note("휴대폰 설정 → 보안 및 개인정보 보호 → 기타 보안 설정 → "
                    + "비밀번호, 패스키, 자동 입력에서 Samsung Pass를 기본 서비스로 선택해 주세요. "
                    + "앱이나 로그인 웹페이지가 자동완성을 제공하지 않으면 키보드만으로 표시할 수 없습니다."));''',
"autofill control + provider diagnostic")

assert 'return sp.getBoolean(AUTOFILL_POPUP_MODE,' in prefs.read_text(encoding="utf-8")
assert '|| prefs.autofillPopupMode()' in ime.read_text(encoding="utf-8")
assert '자동입력 서비스: Samsung Pass' in settings.read_text(encoding="utf-8")
print("NewSwipe v2.2.0: Samsung Pass popup compatibility mode enabled by default on Samsung, user-switchable inline mode, provider diagnostics; never reads credentials.")
