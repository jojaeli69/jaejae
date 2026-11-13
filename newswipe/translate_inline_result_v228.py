from pathlib import Path
p=Path("app/src/main/java/com/alternative_studios/newswipe/KeyboardTranslatePanel.java")
s=p.read_text(encoding="utf-8")
def one(a,b,label):
 global s
 n=s.count(a)
 assert n==1,(label,n)
 s=s.replace(a,b,1)

one('''    private final StringBuilder resultDraft = new StringBuilder();''',
'''    private final StringBuilder resultDraft = new StringBuilder();
    private final HangulComposer resultHangul = new HangulComposer();''',"result Jamo editor")

# More legible original input, visible only when the Translate panel is open.
one('''        entry.setSingleLine(true);
        entry.setEllipsize(TextUtils.TruncateAt.START);''',
'''        entry.setSingleLine(false);
        entry.setMaxLines(2);
        entry.setEllipsize(TextUtils.TruncateAt.END);''',"visible input editing preview")
one('''        LayoutParams inputParams = new LayoutParams(0, dp(42), 1f);''',
'''        LayoutParams inputParams = new LayoutParams(0, dp(60), 1f);''',"source preview height")
one('''        entryRow.addView(submitButton, new LayoutParams(dp(57), dp(42)));
        addView(entryRow, new LayoutParams(LayoutParams.MATCH_PARENT, dp(52)));''',
'''        entryRow.addView(submitButton, new LayoutParams(dp(57), dp(60)));
        addView(entryRow, new LayoutParams(LayoutParams.MATCH_PARENT, dp(65)));

        // The original one-tap translation is still inserted immediately.
        // Afterward, a compact result row appears; touching it edits the
        // result with the SAME NewSwipe keyboard, without an extra editor app.
        resultRow = row();
        resultRow.setVisibility(View.GONE);
        resultText = chip("번역된 문장 수정", theme.text, theme.key, dp(130));
        resultText.setSingleLine(false);
        resultText.setMaxLines(2);
        resultText.setEllipsize(TextUtils.TruncateAt.END);
        resultText.setGravity(Gravity.START | Gravity.CENTER_VERTICAL);
        resultText.setPadding(dp(9), 0, dp(9), 0);
        resultText.setContentDescription("번역 결과를 누르면 즉시 수정");
        resultRow.addView(resultText, new LayoutParams(0, dp(50), 1f));
        applyResultButton = chip("반영", theme.onAccent, theme.accent, dp(50));
        applyResultButton.setOnClickListener(v -> applyEditedResult());
        LayoutParams applyParams = new LayoutParams(dp(54), dp(50));
        applyParams.leftMargin = dp(5);
        resultRow.addView(applyResultButton, applyParams);
        addView(resultRow, new LayoutParams(LayoutParams.MATCH_PARENT, dp(55)));
        resultText.setOnClickListener(v -> enterResultEditing());
        resultText.setOnTouchListener((v, event) -> {
            if (event.getAction() != android.view.MotionEvent.ACTION_UP) return true;
            int currentCaret = resultEditing
                    ? resultCaret + resultHangul.getComposing().length()
                    : Integer.MAX_VALUE;
            int clicked = textCaretAt(resultText, event, currentCaret);
            v.performClick();
            flushResultHangul();
            resultCaret = Math.max(0, Math.min(clicked, resultDraft.length()));
            showResultText();
            return true;
        });''',"conditional result editor and apply button")

# Input text and result text share keyboard handlers but not their edit buffers.
one('''    private void insertSource(String text) {
        if (text == null || text.isEmpty()) return;
        committed.insert(sourceCaret, text);
        sourceCaret += text.length();
    }''',
'''    private void insertSource(String text) {
        if (text == null || text.isEmpty()) return;
        committed.insert(sourceCaret, text);
        sourceCaret += text.length();
    }

    private void insertResult(String text) {
        if (text == null || text.isEmpty()) return;
        resultDraft.insert(resultCaret, text);
        resultCaret += text.length();
    }

    private void flushResultHangul() {
        resultHangul.flush();
        insertResult(resultHangul.takeCommit());
    }

    private String currentResult() {
        return resultDraft.substring(0, resultCaret) + resultHangul.getComposing()
                + resultDraft.substring(resultCaret);
    }

    private void showResultText() {
        if (lastAppliedTranslation == null || resultRow == null) return;
        String value = currentResult();
        if (resultEditing) {
            int caret = resultCaret + resultHangul.getComposing().length();
            caret = Math.min(caret, value.length());
            resultText.setText(value.substring(0, caret) + "│" + value.substring(caret));
            resultText.setContentDescription("번역 결과 수정 중 · 반영 버튼을 누르면 입력창에 적용");
        } else {
            resultText.setText(value);
            resultText.setContentDescription("번역된 문장 · 눌러서 수정");
        }
        applyResultButton.setText(resultEditing ? "반영" : "완료");
    }

    private void enterResultEditing() {
        if (lastAppliedTranslation == null) return;
        flushHangul();
        if (hostEditing) actions.onToggleHostEditing();
        resultEditing=true;
        submitButton.setText("반영");
        showResultText();
        status.setText("번역 결과 수정 · 반영을 누르면 기존 문장을 교체");
    }

    private void recordTranslation(String result) {
        // Release translator locks after success so both editors stay usable.
        invalidateTranslation();
        lastAppliedTranslation=result;
        resultHangul.reset();
        resultDraft.setLength(0);
        resultDraft.append(result);
        resultCaret=resultDraft.length();
        resultEditing=false;
        if (resultRow != null) resultRow.setVisibility(View.VISIBLE);
        submitButton.setText("번역");
        showResultText();
    }

    private boolean insertTranslationResult(String next, String original, boolean selected) {
        // On a retry, REPLACE the previous translated text, never duplicate
        // it. NewSwipeIME validates the editor and current text at the caret.
        if (lastAppliedTranslation != null) {
            return actions.onApplyTranslation(next,lastAppliedTranslation,false,true);
        }
        return actions.onApplyTranslation(next,original,selected,selected);
    }

    private void applyEditedResult() {
        if (lastAppliedTranslation == null) return;
        flushResultHangul();
        String revised=resultDraft.toString();
        if (revised.trim().isEmpty()) {
            status.setText("빈 번역 결과는 반영할 수 없어요"); return;
        }
        if (!revised.equals(lastAppliedTranslation)) {
            if (!actions.onApplyTranslation(revised,lastAppliedTranslation,false,true)) {
                status.setText("기존 번역문 끝으로 커서를 옮겨 다시 반영하세요");
                Toast.makeText(getContext(),
                    "기존 번역 결과가 변경돼 안전하게 덮어쓰지 못했어요",
                    Toast.LENGTH_LONG).show();
                return;
            }
            lastAppliedTranslation=revised;
        }
        resultEditing=false;
        actions.onTranslationCommitted();
        submitButton.setText("번역");
        showResultText();
        status.setText("수정한 번역 결과를 입력창에 반영했어요");
    }''',"safe editable output and result reapplication")

# Put the button label change inside a method, NOT in the constructor's
# early click listener, because submitButton is a final field initialized later.
one('''    private void showSourceText() {
        String value=source();''',
'''    private void showSourceText() {
        if (!resultEditing) submitButton.setText("번역");
        String value=source();''',"source-editor toolbar label")

one('''        if (resultEditing) {
            if (resultDraft.length()+value.length()>LIMIT) return;
            insertResult(value);
            showResultText();
            return;
        }''',
'''        if (resultEditing) {
            if (currentResult().length()+value.length()>LIMIT) return;
            if (korean && value.length()==1 && HangulComposer.isJamo(value.charAt(0))) {
                resultHangul.input(value.charAt(0),tap,android.os.SystemClock.uptimeMillis());
                insertResult(resultHangul.takeCommit());
            } else {
                flushResultHangul();
                insertResult(value);
            }
            showResultText();
            return;
        }''',"Korean composition inside editable result")

one('''        if (resultEditing) {
            if (resultDraft.length()<LIMIT) insertResult(" ");
            showResultText();''',
'''        if (resultEditing) {
            flushResultHangul();
            if (currentResult().length()<LIMIT) insertResult(" ");
            showResultText();''',"flush result Hangul on space")

one('''        if (resultEditing) {
            if (resultCaret>0) {
                int i=resultDraft.offsetByCodePoints(resultCaret,-1);
                resultDraft.delete(i,resultCaret);
                resultCaret=i;
            }
            showResultText();''',
'''        if (resultEditing) {
            if (!resultHangul.isEmpty()) {
                resultHangul.backspace();
                insertResult(resultHangul.takeCommit());
            } else if (resultCaret>0) {
                int i=resultDraft.offsetByCodePoints(resultCaret,-1);
                resultDraft.delete(i,resultCaret);
                resultCaret=i;
            }
            showResultText();''',"Hangul-aware result backspace")

one('''        if (resultEditing) {
            int end=resultCaret, i=end;''',
'''        if (resultEditing) {
            flushResultHangul();
            int end=resultCaret, i=end;''',"result delete word flush")

one('''        resultDraft.setLength(0);
        if (resultRow!=null) resultRow.setVisibility(View.GONE);''',
'''        resultHangul.reset();
        resultDraft.setLength(0);
        resultCaret=0;
        if (resultRow!=null) resultRow.setVisibility(View.GONE);''',"release result composition")

# Existing ML Kit, DeepL and Android system service all auto-insert once.
one('''                            boolean ok=actions.onApplyTranslation(result, originalSelection,selection,selection);''',
'''                            boolean ok=insertTranslationResult(result, originalSelection, selection);''',"ML Kit insert")
one('''                                resetText(false);
                                actions.onTranslationCommitted();
                                status.setText("원문 수정 중 · 번역 입력창을 누르면 다음 번역");''',
'''                                recordTranslation(result);
                                actions.onTranslationCommitted();
                                status.setText("번역 완료 · 결과를 눌러 바로 수정 가능");''',"editable ML Kit result")

old='''            boolean inserted = actions.onApplyTranslation(result, originalSelection,
                    selection, selection);'''
assert s.count(old)==2,("DeepL/System insert",s.count(old))
s=s.replace(old,'''            boolean inserted = insertTranslationResult(result, originalSelection, selection);''')
one('''                resetText(false);
                actions.onTranslationCommitted();
                status.setText("DeepL 번역 완료 · 본문 수정 중");''',
'''                recordTranslation(result);
                actions.onTranslationCommitted();
                status.setText("DeepL 번역 완료 · 결과를 눌러 수정 가능");''',"editable DeepL result")
one('''                resetText(false);
                actions.onTranslationCommitted();
                status.setText("번역 완료 · 본문 수정 중");''',
'''                recordTranslation(result);
                actions.onTranslationCommitted();
                status.setText("번역 완료 · 결과를 눌러 수정 가능");''',"editable device result")

p.write_text(s,encoding="utf-8")
assert s.count("recordTranslation(result);")==3
assert 'resultText.setOnTouchListener' in s
assert 'insertTranslationResult' in s
assert 'resultHangul.input' in s
assert 'String revised=resultDraft.toString();' in s
print("v228 part2: same one-tap translation, editable result in keyboard, in-place replace with exact-string verification.")
