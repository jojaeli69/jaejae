from pathlib import Path
root=Path("app/src/main/java/com/alternative_studios/newswipe")
p=root/"KeyboardTranslatePanel.java"
s=p.read_text(encoding="utf-8")
def one(a,b,label):
 global s
 n=s.count(a)
 assert n==1,(label,n)
 s=s.replace(a,b,1)

one('''    private boolean hostEditing;''',
'''    private boolean hostEditing;
    private int sourceCaret;
    private boolean resultEditing;
    private String lastAppliedTranslation;
    private final StringBuilder resultDraft = new StringBuilder();
    private int resultCaret;
    private LinearLayout resultRow;
    private TextView resultText, applyResultButton;''',"editor state")

one('''        entry.setOnClickListener(v -> {
            if (hostEditing) actions.onToggleHostEditing();
        });''',
'''        entry.setOnClickListener(v -> {
            if (hostEditing) actions.onToggleHostEditing();
            resultEditing = false;
            showSourceText();
            showResultText();
        });
        entry.setOnTouchListener((v, event) -> {
            if (event.getAction() != android.view.MotionEvent.ACTION_UP) return true;
            int pos = textCaretAt(entry, event, sourceCaret + hangul.getComposing().length());
            flushHangul();
            sourceCaret = Math.max(0, Math.min(pos, committed.length()));
            v.performClick();
            return true;
        });''',"touch source to reposition caret")

one('''    private String source() {
        return committed.toString() + hangul.getComposing();
    }''',
'''    private String source() {
        sourceCaret = Math.max(0, Math.min(sourceCaret, committed.length()));
        return committed.substring(0, sourceCaret) + hangul.getComposing()
                + committed.substring(sourceCaret);
    }

    private int textCaretAt(TextView view, android.view.MotionEvent event, int visibleCaret) {
        android.text.Layout layout = view.getLayout();
        if (layout == null) return visibleCaret;
        int y = Math.max(0, (int) event.getY() - view.getTotalPaddingTop() + view.getScrollY());
        int line = layout.getLineForVertical(y);
        float x = event.getX() - view.getTotalPaddingLeft() + view.getScrollX();
        int offset = layout.getOffsetForHorizontal(line, x);
        return Math.max(0, offset > visibleCaret ? offset - 1 : offset);
    }

    private void insertSource(String text) {
        if (text == null || text.isEmpty()) return;
        committed.insert(sourceCaret, text);
        sourceCaret += text.length();
    }''',"source edit caret and insert")

one('''            SpannableString content = new SpannableString(value + "\\uFFFC");''',
'''            int caret = Math.max(0, Math.min(value.length(),
                    sourceCaret + hangul.getComposing().length()));
            SpannableString content = new SpannableString(
                    value.substring(0, caret) + "\\uFFFC" + value.substring(caret));''',"render movable caret")
one('''            }, value.length(), content.length(), Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);''',
'''            }, caret, caret + 1, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);''',"caret span")

one('''            committed.append(hangul.takeCommit());
        } else {
            flushHangul();
            committed.append(value);
        }
        invalidateTranslation();''',
'''            insertSource(hangul.takeCommit());
        } else {
            flushHangul();
            insertSource(value);
        }
        invalidateTranslation();''',"typing at caret")
one('''    private void flushHangul() {
        hangul.flush();
        committed.append(hangul.takeCommit());
    }''',
'''    private void flushHangul() {
        hangul.flush();
        insertSource(hangul.takeCommit());
    }''',"flush composing at caret")
one('''    public void onSpace() {
        flushHangul();
        if (source().length()<LIMIT) committed.append(' ');
        invalidateTranslation();
        showSourceText();
    }''',
'''    public void onSpace() {
        if (resultEditing) {
            if (resultDraft.length()<LIMIT) insertResult(" ");
            showResultText();
            return;
        }
        flushHangul();
        if (source().length()<LIMIT) insertSource(" ");
        invalidateTranslation();
        showSourceText();
    }''',"space in active edit")

one('''    public void onBackspace() {
        if (!hangul.isEmpty()) {
            hangul.backspace();
            committed.append(hangul.takeCommit());
        } else if (committed.length()>0) {
            int p=committed.offsetByCodePoints(committed.length(),-1);
            committed.delete(p, committed.length());
        }
        invalidateTranslation();
        showSourceText();
    }''',
'''    public void onBackspace() {
        if (resultEditing) {
            if (resultCaret>0) {
                int i=resultDraft.offsetByCodePoints(resultCaret,-1);
                resultDraft.delete(i,resultCaret);
                resultCaret=i;
            }
            showResultText();
            return;
        }
        if (!hangul.isEmpty()) {
            hangul.backspace();
            insertSource(hangul.takeCommit());
        } else if (sourceCaret>0) {
            int p=committed.offsetByCodePoints(sourceCaret,-1);
            committed.delete(p,sourceCaret);
            sourceCaret=p;
        }
        invalidateTranslation();
        showSourceText();
    }''',"delete before cursor")
one('''    public void onDeleteWord() {
        flushHangul();
        int i=committed.length();
        while(i>0 && Character.isWhitespace(committed.charAt(i-1)))i--;
        while(i>0 && !Character.isWhitespace(committed.charAt(i-1)))i--;
        committed.delete(i,committed.length());
        invalidateTranslation();
        showSourceText();
    }''',
'''    public void onDeleteWord() {
        if (resultEditing) {
            int end=resultCaret, i=end;
            while(i>0 && Character.isWhitespace(resultDraft.charAt(i-1)))i--;
            while(i>0 && !Character.isWhitespace(resultDraft.charAt(i-1)))i--;
            resultDraft.delete(i,end);
            resultCaret=i;
            showResultText();
            return;
        }
        flushHangul();
        int end=sourceCaret, i=end;
        while(i>0 && Character.isWhitespace(committed.charAt(i-1)))i--;
        while(i>0 && !Character.isWhitespace(committed.charAt(i-1)))i--;
        committed.delete(i,end);
        sourceCaret=i;
        invalidateTranslation();
        showSourceText();
    }''',"delete word at cursor")

one('''        committed.setLength(0);
        if (!preserveSelection) {''',
'''        committed.setLength(0);
        sourceCaret=0;
        if (!preserveSelection) {''',"reset cursor")

start=s.index("    public void showSource(String value, boolean selected) {")
end=s.index("    private String source()",start)
chunk=s[start:end]
assert chunk.count("        updateLanguageLabels();\n        showSourceText();")==1
chunk=chunk.replace("        updateLanguageLabels();\n        showSourceText();",
'''        sourceCaret=committed.length();
        updateLanguageLabels();
        showSourceText();''')
s=s[:start]+chunk+s[end:]

one('''    public void onTypeText(String value, boolean tap, boolean korean) {
        if (value==null || value.isEmpty()) return;
        if (source().length() + value.length() > LIMIT) {
            status.setText("번역 입력은 350자까지 지원해요");
            return;
        }''',
'''    public void onTypeText(String value, boolean tap, boolean korean) {
        if (value==null || value.isEmpty()) return;
        if (resultEditing) {
            if (resultDraft.length()+value.length()>LIMIT) return;
            insertResult(value);
            showResultText();
            return;
        }
        if (source().length() + value.length() > LIMIT) {
            status.setText("번역 입력은 350자까지 지원해요");
            return;
        }''',"typing result if active")
one('''            resetText(false);
            CharSequence text=data.getItemAt(0).getText();
            committed.append(text.length()>LIMIT?text.subSequence(0,LIMIT):text);
            showSourceText();''',
'''            CharSequence text=data.getItemAt(0).getText();
            String clip=text.length()>LIMIT?text.subSequence(0,LIMIT).toString():text.toString();
            if (resultEditing) {
                if (clip.length()+resultDraft.length()>LIMIT) {
                    status.setText("번역 결과가 너무 길어 붙여넣을 수 없어요");
                    return;
                }
                insertResult(clip);
                showResultText();
            } else {
                resetText(false);
                committed.append(clip);
                sourceCaret=committed.length();
                showSourceText();
            }''',"paste into source/result")
one('''    public void onEnter() {
        if (pendingCopyResult != null) {''',
'''    public void onEnter() {
        if (resultEditing) {
            applyEditedResult();
            return;
        }
        if (pendingCopyResult != null) {''',"enter applies edited translation")

one('''    public void dismiss() {
        invalidateTranslation();
        hangul.reset();
        committed.setLength(0);''',
'''    public void dismiss() {
        invalidateTranslation();
        lastAppliedTranslation=null;
        resultEditing=false;
        resultDraft.setLength(0);
        if (resultRow!=null) resultRow.setVisibility(View.GONE);
        hangul.reset();
        committed.setLength(0);
        sourceCaret=0;''',"dismiss result draft")

p.write_text(s,encoding="utf-8")
assert 'insertSource(value)' in s
assert 'entry.setOnTouchListener' in s
assert 'private void insertSource' in s
assert 'onEnter()' in s
print("v228 part 1: tap-to-edit original text at arbitrary cursor position; IME keys insert/delete at cursor.")
