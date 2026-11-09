from pathlib import Path
p=Path("app/src/main/java/com/alternative_studios/newswipe/KeyboardTranslatePanel.java")
s=p.read_text(encoding="utf-8")
def change(old,new,label):
    global s
    count=s.count(old)
    assert count==1,(label,count)
    s=s.replace(old,new,1)

change('import android.content.Context;',
'''import android.content.Context;
import android.content.SharedPreferences;''','prefs import')

change('''    private final Actions actions;
    private final KeyboardTheme theme;''',
'''    private final Actions actions;
    private final KeyboardTheme theme;
    private final SharedPreferences translationPrefs;
    private boolean hasSavedLanguages;''','state fields')

change('''        actions = callbacks;
        theme = KeyboardTheme.of(c);''',
'''        actions = callbacks;
        theme = KeyboardTheme.of(c);
        translationPrefs = c.getSharedPreferences("newswipe_translation", Context.MODE_PRIVATE);
        String storedFrom = translationPrefs.getString("from_language", TranslateLanguage.KOREAN);
        String storedTo = translationPrefs.getString("to_language", TranslateLanguage.ENGLISH);
        if (validLanguage(storedFrom) && validLanguage(storedTo) && !storedFrom.equals(storedTo)) {
            from = storedFrom;
            to = storedTo;
        }
        hasSavedLanguages = translationPrefs.contains("from_language")
                && translationPrefs.contains("to_language");''','load language preferences')

change('''        swap.setOnClickListener(v -> {
            String temp = from;
            from = to;
            to = temp;
            updateLanguageLabels();
            invalidateTranslation();
        });''',
'''        swap.setOnClickListener(v -> {
            String temp = from;
            from = to;
            to = temp;
            rememberLanguages();
            updateLanguageLabels();
            invalidateTranslation();
            showSourceText();
        });''','swap persistence')

change('''        addView(footer, new LayoutParams(LayoutParams.MATCH_PARENT, dp(29)));
    }''',
'''        addView(footer, new LayoutParams(LayoutParams.MATCH_PARENT, dp(29)));
        updateLanguageLabels();
        showSourceText();
    }''','initialize UI')

change('''    private static String name(String lang) {''',
'''    private static boolean validLanguage(String value) {
        for (String lang : LANGUAGES) if (lang.equals(value)) return true;
        return false;
    }

    private void rememberLanguages() {
        hasSavedLanguages = true;
        translationPrefs.edit().putString("from_language",from)
                .putString("to_language",to).apply();
    }

    private static String name(String lang) {''','prefs helpers')

change('''            updateLanguageLabels();
            invalidateTranslation();
            return true;
        });
        choices.show();''',
'''            rememberLanguages();
            updateLanguageLabels();
            invalidateTranslation();
            showSourceText();
            return true;
        });
        choices.show();''','language menu persistence')

change('''        if (selected && value != null) {
            committed.append(value.length() > LIMIT ? value.substring(0,LIMIT) : value);
            if (value.matches("(?s).*[a-zA-Z].*") && !value.matches("(?s).*[가-힣].*")) {
                from = TranslateLanguage.ENGLISH;
                to = TranslateLanguage.KOREAN;
            } else {
                from = TranslateLanguage.KOREAN;
                to = TranslateLanguage.ENGLISH;
            }
        }''',
'''        if (selected && value != null) {
            committed.append(value.length() > LIMIT ? value.substring(0,LIMIT) : value);
            // Respect the user's explicitly chosen translation pair.
            if (!hasSavedLanguages) {
                if (value.matches("(?s).*[a-zA-Z].*") && !value.matches("(?s).*[가-힣].*")) {
                    from = TranslateLanguage.ENGLISH;
                    to = TranslateLanguage.KOREAN;
                } else if (value.matches("(?s).*[ぁ-ヿ].*")) {
                    from = TranslateLanguage.JAPANESE;
                    to = TranslateLanguage.KOREAN;
                } else if (value.matches("(?s).*[一-龥].*")) {
                    from = TranslateLanguage.CHINESE;
                    to = TranslateLanguage.KOREAN;
                } else {
                    from = TranslateLanguage.KOREAN;
                    to = TranslateLanguage.ENGLISH;
                }
            }
        }''','respect language choice')

change('''        entry.setTextColor(empty ? theme.hint : theme.text);
        if (!translating) status.setText(empty''',
'''        entry.setTextColor(empty ? theme.hint : theme.text);
        submitButton.setEnabled(!empty && !translating);
        if (!translating) status.setText(empty''','disable useless button')

# Make the incomplete/too-long source text bound visible to users instead
# of accepting a silently truncated selection and then failing at commit.
change('''        if (value==null || value.isEmpty() || source().length()>=LIMIT) return;''',
'''        if (value==null || value.isEmpty()) return;
        if (source().length() + value.length() > LIMIT) {
            status.setText("번역 입력은 350자까지 지원해요");
            return;
        }''','length feedback')

# The previous implementation muted failure feedback by reusing showSourceText.
# Keep clear error messages visible after failed translation.
change('''        translating=false;
        status.setText(message);
        submitButton.setEnabled(true);''',
'''        translating=false;
        status.setText(message);
        submitButton.setEnabled(!source().trim().isEmpty());''','failure retry')

p.write_text(s,encoding="utf-8")

ime=Path("app/src/main/java/com/alternative_studios/newswipe/NewSwipeIME.java")
s=ime.read_text(encoding="utf-8")
def patch(old,new,label):
    global s
    count=s.count(old)
    assert count==1,(label,count)
    s=s.replace(old,new,1)

patch('''        translateQuickButton.setBackgroundColor(theme.key);
        translateQuickButton.setOnClickListener''',
'''        float translateRadius = Ui.chipRadius(this);
        translateQuickButton.setBackground(Ui.ripple(
                Ui.tint(theme.text),
                Ui.round(theme.functionKey, translateRadius),
                translateRadius));
        translateQuickButton.setOnClickListener''','native toolbar button background')

patch('''        if (text.length() > 350) text = text.substring(text.length() - 350);
        if (!selected) {''',
'''        if (selected && text.length() > 350) {
            Toast.makeText(this, "번역할 문장은 350자 이내로 선택해 주세요",
                    Toast.LENGTH_SHORT).show();
            return;
        }
        if (text.length() > 350) text = text.substring(text.length() - 350);
        if (!selected) {''','too-long selection guard')

ime.write_text(s,encoding="utf-8")

# Fast checks for intended workflow and compatibility with original toolbar.
assert 'translationPanel.onEnter();' in s
assert 'getCurrentInputConnection()' in s
assert 'translationPanel.setVisibility(View.VISIBLE)' in s
assert 'theme.functionKey, translateRadius' in s
assert 'com.google.mlkit.nl.translate.Translation' in p.read_text(encoding="utf-8")
print("v1.9.9: remembered language pair; original NewSwipe chip styling; bounded selection; improved editor feedback.")
