from pathlib import Path

root=Path("app/src/main/java/com/alternative_studios/newswipe")
panel=root/"KeyboardTranslatePanel.java"
ime=root/"NewSwipeIME.java"

def once(path, old, new, tag):
    s=path.read_text(encoding="utf-8")
    count=s.count(old)
    assert count==1,(tag,count)
    path.write_text(s.replace(old,new,1),encoding="utf-8")

# Previously a selected/copied passage was silently cut at 350 characters.
# Keep whole multi-sentence source with a clear upper bound instead.
once(panel,
'''    private static final int LIMIT = 350;''',
'''    /** Maximum source text accepted WITHOUT silent truncation. */
    public static final int MAX_SOURCE_CHARS = 3000;
    private static final int LIMIT = MAX_SOURCE_CHARS;
    /** Short sentence/paragraph groups to keep on-device translation focused. */
    private static final int TRANSLATE_PART_CHARS = 700;''',
"raise source limit")

once(panel,
'''            committed.append(value.length() > LIMIT ? value.substring(0,LIMIT) : value);''',
'''            // Never silently translate a partial selection. The host IME
            // validates selection length before opening this panel.
            if (value.length() <= LIMIT) committed.append(value);''',
"prevent silent selected-text shortening")

once(panel,
'''            status.setText("번역 입력은 350자까지 지원해요");''',
'''            status.setText("번역 입력은 최대 " + LIMIT + "자까지 지원해요");''',
"accurate typing limit prompt")

once(panel,
'''            committed.append(text.length()>LIMIT?text.subSequence(0,LIMIT):text);
            showSourceText();''',
'''            if (text.length() > LIMIT) {
                status.setText("복사한 글이 " + LIMIT + "자를 넘어요 · 필요한 구간을 선택해 주세요");
                Toast.makeText(getContext(), "복사한 글이 너무 길어 전체 번역하지 않았습니다. 일부를 선택해 주세요.",
                        Toast.LENGTH_LONG).show();
                return;
            }
            committed.append(text);
            showSourceText();''',
"never silently truncate pasted paragraphs")

# Previously 1 line was always shown in a small 42dp chip, making a
# complete source LOOK truncated even when it remained in memory.
once(panel,
'''        entry.setSingleLine(true);
        entry.setEllipsize(TextUtils.TruncateAt.START);''',
'''        entry.setSingleLine(false);
        entry.setMaxLines(2);
        entry.setEllipsize(TextUtils.TruncateAt.END);
        entry.setTextSize(13);''',
"two-line input preview")
once(panel,
'''        LayoutParams inputParams = new LayoutParams(0, dp(42), 1f);''',
'''        LayoutParams inputParams = new LayoutParams(0, dp(64), 1f);''',
"preview height")
once(panel,
'''        entryRow.addView(submitButton, new LayoutParams(dp(57), dp(42)));
        addView(entryRow, new LayoutParams(LayoutParams.MATCH_PARENT, dp(46)));''',
'''        entryRow.addView(submitButton, new LayoutParams(dp(57), dp(64)));
        addView(entryRow, new LayoutParams(LayoutParams.MATCH_PARENT, dp(68)));''',
"larger entry row")

# Translation should receive the entire selected text, or the previous
# paragraph(s) rather than the last arbitrary 350 characters.
# Never slice a sentence at an arbitrary character boundary.
s=ime.read_text(encoding="utf-8")
start=s.index('        CharSequence source = selected ? selectedText : ic.getTextBeforeCursor(350, 0);')
end=s.index('        translationOriginalPackage = info.packageName;',start)
old=s[start:end]
new='''        int max = KeyboardTranslatePanel.MAX_SOURCE_CHARS;
        CharSequence source = selected ? selectedText : ic.getTextBeforeCursor(max + 1, 0);
        String text = source == null ? "" : source.toString();
        if (!selected) {
            // Retain multi-line sentences in the current paragraph, not
            // just the text after the very last line break.
            int paragraph = text.lastIndexOf("\\\\n\\\\n");
            if (paragraph >= 0) text = text.substring(paragraph + 2);
        }
        if (text.length() > max) {
            Toast.makeText(this,
                    "긴 문장이에요. 번역할 부분을 선택해 주세요 (최대 " + max + "자)",
                    Toast.LENGTH_LONG).show();
            return;
        }
'''
assert 'substring(text.length() - 350)' in old and "lastIndexOf('\\\\n')" in old,old
s=s[:start]+new+s[end:]
ime.write_text(s,encoding="utf-8")

# Avoid producing a short partial translation for input with several long
# sentences. Sequentially translate complete sentence-aligned pieces, then
# combine all returned results. A failed piece aborts the entire translation.
s=panel.read_text(encoding="utf-8")
old='''                        active.translate(input).addOnSuccessListener(result -> {'''
assert s.count(old)==1,("ML Kit pipeline",s.count(old))
s=s.replace(old,'''                        translateEveryPart(active, input, token, result -> {''',1)
old='''                        }).addOnFailureListener(e -> failure(token,
                                "번역 처리 실패", e));'''
assert s.count(old)==1,("ML Kit failure pipeline",s.count(old))
s=s.replace(old,'''                        }, e -> failure(token, "번역 처리 실패", e));''',1)

needle='''    private void failure(int token, String message, Throwable cause) {'''
assert s.count(needle)==1
helpers='''    /** Preserve the entire meaning-bearing passage by sending full sentence-
     * aligned parts (not the arbitrary tail of the source) to on-device ML Kit.
     * No cloud service receives keyboard text. */
    private java.util.List<String> translationParts(String input) {
        java.util.ArrayList<String> parts = new java.util.ArrayList<>();
        int start = 0;
        while (start < input.length()) {
            int end = Math.min(input.length(), start + TRANSLATE_PART_CHARS);
            if (end < input.length()) {
                int sentence = -1, space = -1;
                // Prefer a complete sentence or line, then a word boundary.
                for (int i = start + TRANSLATE_PART_CHARS / 2; i < end; i++) {
                    char c = input.charAt(i);
                    if (c == '.' || c == '!' || c == '?' || c == '。'
                            || c == '！' || c == '？' || c == '\\\\n') sentence = i + 1;
                    else if (Character.isWhitespace(c)) space = i + 1;
                }
                if (sentence > start) end = sentence;
                else if (space > start) end = space;
            }
            // Keep input in original order; do not drop a single character.
            parts.add(input.substring(start, end));
            start = end;
        }
        return parts;
    }

    private void translateEveryPart(Translator active, String input, int token,
            java.util.function.Consumer<String> success,
            java.util.function.Consumer<Exception> fail) {
        java.util.List<String> parts = translationParts(input);
        translatePartAt(active, parts, 0, new StringBuilder(), token, success, fail);
    }

    private void translatePartAt(Translator active, java.util.List<String> parts, int index,
            StringBuilder combined, int token,
            java.util.function.Consumer<String> success,
            java.util.function.Consumer<Exception> fail) {
        if (token != generation) return;
        if (index == parts.size()) {
            success.accept(combined.toString());
            return;
        }
        final String originalPart = parts.get(index);
        status.setText(parts.size() == 1 ? "번역 중…" :
                "번역 중 " + (index + 1) + "/" + parts.size());
        active.translate(originalPart).addOnSuccessListener(result -> {
            if (token != generation) return;
            if (result == null || result.trim().isEmpty()) {
                fail.accept(new IllegalStateException("번역 결과가 비어 있어 전체 번역을 중단했습니다"));
                return;
            }
            // ML Kit may trim the whitespace at segment edges.
            if (combined.length() != 0 && !Character.isWhitespace(combined.charAt(combined.length()-1))
                    && !Character.isWhitespace(result.charAt(0))) combined.append(' ');
            combined.append(result);
            if (originalPart.endsWith("\\\\n") && !result.endsWith("\\\\n")) combined.append('\\\\n');
            translatePartAt(active, parts, index + 1, combined, token, success, fail);
        }).addOnFailureListener(fail::accept);
    }

'''
s=s.replace(needle,helpers+needle,1)
panel.write_text(s,encoding="utf-8")

p=panel.read_text(encoding="utf-8")
i=ime.read_text(encoding="utf-8")
checks=[
 'MAX_SOURCE_CHARS = 3000', 'TRANSLATE_PART_CHARS = 700',
 'committed.append(text);', 'translateEveryPart(active, input, token, result -> {',
 'translatePartAt(active, parts, index + 1, combined, token, success, fail);',
 'if (text.length() > max)', 'ic.getTextBeforeCursor(max + 1, 0)',
 'entry.setMaxLines(2)', 'entry.setSingleLine(false)'
]
for check in checks: assert check in p or check in i,check
assert 'value.substring(0,LIMIT)' not in p
assert 'text.subSequence(0,LIMIT)' not in p
assert 'ic.getTextBeforeCursor(350, 0)' not in i
assert 'substring(text.length() - 350)' not in i
print("NewSwipe 2.2.5: no 350-char truncation; 3000-char complete source; complete multi-line paragraphs; sentence-aligned translation for long passages.")
