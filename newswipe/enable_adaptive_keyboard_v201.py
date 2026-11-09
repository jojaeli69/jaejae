from pathlib import Path
import re
base=Path("app/src/main/java/com/alternative_studios/newswipe")
k=base/"keyboard/KeyboardView.java"
s=k.read_text(encoding="utf-8")
def sub(old,new,label):
    global s
    count=s.count(old)
    assert count==1,(label,count)
    s=s.replace(old,new,1)

sub('''        boolean cursorStarted;''',
'''        boolean cursorStarted;
        boolean heldSpaceCursor;''','pointer held space')

sub('''    private KeyboardTheme theme;''',
'''    private KeyboardTheme theme;
    private final AdaptiveTouch adaptive;''','adaptive member')

sub('''    public KeyboardView(Context context) {
        super(context);''',
'''    public KeyboardView(Context context) {
        super(context);
        adaptive = new AdaptiveTouch(context);''','adaptive init')

sub('''    public void setHitShrink(float deleteFraction, float spaceFraction) {''',
'''    public void setAdaptiveActive(boolean learnAllowed) {
        adaptive.setActive(learnAllowed);
    }

    public void resetAdaptivePending() {
        adaptive.clearRecent();
    }

    public void setHitShrink(float deleteFraction, float spaceFraction) {''','adaptive control')

sub('''        if (shrink <= 0f) return k;''',
'''        if (shrink <= 0f) return adaptive.choose(k,layout.rows[ri],x,layout.kind);''','adaptive hit mapping')

sub('''        if (del || lang || chars || select) {''',
'''        if (k.type == Key.SPACE || del || lang || chars || select) {''','always longpress for space')

sub('''            long delay = del || lang || select ? fnPressMs : longPressMs;''',
'''            long delay = k.type == Key.SPACE || del || lang || select ? fnPressMs : longPressMs;''','space function delay')

sub('''                boolean curH = p.gap ? gapSwipes != null && gapSwipes.cursorH() : p.freeCursor ? p.freeH''',
'''                boolean curH = p.heldSpaceCursor || (p.gap ? gapSwipes != null && gapSwipes.cursorH() : p.freeCursor ? p.freeH''','held space cursor horizontal')

# The horizontal change adds a parenthesis, close it on the following line.
sub(''': fnSwipes != null && fnSwipes.cursorH(p.cursorSlot);
                boolean curV = p.gap''',
''': fnSwipes != null && fnSwipes.cursorH(p.cursorSlot));
                boolean curV = p.heldSpaceCursor || (p.gap''','held space cursor group')

sub(''': fnSwipes != null && fnSwipes.cursorV(p.cursorSlot);
                // 커서 이동 속도''',
''': fnSwipes != null && fnSwipes.cursorV(p.cursorSlot));
                // 커서 이동 속도''','held space cursor vertical')

sub('''                } else if (p.key.type != Key.SHIFT) {
                    listener.onKeyTap(p.key);
                    markChord();
                }''',
'''                } else if (p.key.type != Key.SHIFT) {
                    listener.onKeyTap(p.key);
                    if (layout != null) adaptive.onTap(p.key,p.downX,layout.kind);
                    markChord();
                }''','tap learning')

sub('''        String custom = customLongPress(k);
        if (custom != null) {''',
'''        // Samsung-style spacebar trackpad: hold, then drag to move the caret.
        // Ignore previously configured "copy" or "select" actions for this key.
        if (k.type == Key.SPACE) {
            p.mode = CURSOR;
            p.heldSpaceCursor = true;
            p.cursorSlot = FunctionSwipes.SPACE;
            p.cursorAnchorX = p.lastX;
            p.cursorAnchorY = p.lastY;
            adaptive.clearRecent();
            if (listener != null) listener.onGesture();
            invalidate();
            return;
        }
        String custom = customLongPress(k);
        if (custom != null) {''','held space trackpad')

k.write_text(s,encoding="utf-8")

p=base/"NewSwipeIME.java"
s=p.read_text(encoding="utf-8")
def change(old,new,label):
    global s
    count=s.count(old)
    assert count==1,(label,count)
    s=s.replace(old,new,1)

change('''    private TextView translateQuickButton;''',
'''    private IconButton translateQuickButton;''','translate icon button type')

# Recreate the icon using exactly the same button factory as other toolbar icons.
begin=s.index('''        translateQuickButton = new TextView(this);''')
end=s.index('''        toolSpacer = new View(this);''',begin)
s=s[:begin]+'''        translateQuickButton = toolButton(Icons.TRANSLATE, "번역", v -> openTranslationPanel());
        bar.addView(translateQuickButton);
'''+s[end:]

change('''        toolbar.addView(translateQuickButton,
                new LinearLayout.LayoutParams(Ui.dp(this, 47), toolbarHeight));''',
'''        toolbar.addView(translateQuickButton,
                new LinearLayout.LayoutParams(Ui.dp(this, 40), toolbarHeight));''','40dp translate icon')

change('''        keyboard.setLongPressActions(com.alternative_studios.newswipe.keyboard.LongPressActions.actions(prefs));''',
'''        keyboard.setLongPressActions(com.alternative_studios.newswipe.keyboard.LongPressActions.actions(prefs));
        keyboard.setAdaptiveActive(!passwordField && learnAllowed);''','apply dynamic settings')

change('''        learnAllowed = (info.imeOptions & EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING) == 0;''',
'''        learnAllowed = (info.imeOptions & EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING) == 0;
        keyboard.setAdaptiveActive(!passwordField && learnAllowed);''','skip sensitive fields')

# Moving the cursor invalidates the immediately preceding correction sequence.
change('''    public void onCursorStart() {
        forgetCursorEdges();
    }''',
'''    public void onCursorStart() {
        forgetCursorEdges();
        if (keyboard != null) keyboard.resetAdaptivePending();
    }''','cursor movement clear')

p.write_text(s,encoding="utf-8")

p=base/"keyboard/Icons.java"
s=p.read_text(encoding="utf-8")
assert '    public static final int TRANSLATE' not in s
s=s.replace('''    public static final int SELECT_ALL = 44;''',
'''    public static final int SELECT_ALL = 44;
    /** On-keyboard translation tool, sized like clipboard/voice/settings icons. */
    public static final int TRANSLATE = 45;''',1)
needle='''            case SELECT_ALL:
'''
assert s.count(needle)==1
s=s.replace(needle,'''            case TRANSLATE:
                // Two overlapping speech/translation cards, simple thin 24px icon.
                oval.set(2.5f, 3f, 16f, 15.5f);
                c.drawRoundRect(oval, 2.5f, 2.5f, p);
                path.moveTo(6.5f, 15.5f);
                path.lineTo(5.5f, 18f);
                path.lineTo(10.5f, 15.5f);
                c.drawPath(path, p);
                oval.set(9.5f, 9f, 22f, 21f);
                c.drawRoundRect(oval, 2.5f, 2.5f, p);
                // A pair of short arrows denotes language conversion.
                c.drawLine(5.5f, 7.3f, 12.5f, 7.3f, p);
                c.drawLine(10.2f, 5.5f, 12.5f, 7.3f, p);
                c.drawLine(10.2f, 9.1f, 12.5f, 7.3f, p);
                c.drawLine(18.5f, 16.7f, 12.6f, 16.7f, p);
                c.drawLine(14.8f, 14.9f, 12.6f, 16.7f, p);
                c.drawLine(14.8f, 18.5f, 12.6f, 16.7f, p);
                break;
'''+needle,1)
p.write_text(s,encoding="utf-8")

p=base/"Prefs.java"
s=p.read_text(encoding="utf-8")
needle='''    public static final String LEARN_WORDS = "learn_words";'''
assert s.count(needle)==1
s=s.replace(needle,needle+'''
    /** Only aggregate mis-tap corrections; no typed text or coordinates stored. */
    public static final String ADAPTIVE_TOUCH = "adaptive_touch_enabled";''',1)
p.write_text(s,encoding="utf-8")

p=base/"SettingsActivity.java"
s=p.read_text(encoding="utf-8")
needle='''        // 자동 완성: 서비스(Autofill with Google, 삼성 패스 등)의 제안을 도구 막대 자리에 칩으로 (Android 11 이상).'''
assert s.count(needle)==1
s=s.replace(needle,'''        LinearLayout touchLearning = section("터치 오타 학습");
        touchLearning.addView(toggle("터치 영역 자동 보정",
                "잘못 누른 글자를 바로 지우고 옆 글자로 고친 패턴을 학습해, "
                + "글자 키의 터치 판정 경계만 조금씩 자동 조절합니다. "
                + "키 크기·보이는 위치는 바꾸지 않으며 개인정보·입력 문장은 저장하지 않습니다.",
                Prefs.ADAPTIVE_TOUCH, prefs.raw().getBoolean(Prefs.ADAPTIVE_TOUCH, true)));
        touchLearning.addView(button("터치 학습 초기화", v -> {
            com.alternative_studios.newswipe.keyboard.AdaptiveTouch.reset(this);
            Toast.makeText(this, "터치 학습을 초기화했습니다", Toast.LENGTH_SHORT).show();
        }));
        touchLearning.addView(note("비밀번호 입력칸과 개인정보 학습 금지 입력칸에서는 동작하지 않습니다. "
                + "충분한 수정 사례가 쌓인 키부터 작은 범위로 적용됩니다."));

'''+needle,1)
p.write_text(s,encoding="utf-8")
print("Applied translation icon, Samsung-style space hold cursor and personalized safe touch areas.")
