from pathlib import Path

root = Path("app/src/main/java/com/alternative_studios/newswipe")

def replace_one(path, before, after, label):
    text = path.read_text(encoding="utf-8")
    count = text.count(before)
    assert count == 1, (label, count)
    path.write_text(text.replace(before, after, 1), encoding="utf-8")

prefs = root / "Prefs.java"
replace_one(
    prefs,
    '    public static final String PERIOD_CHAR = "bottom_period_char";',
    '    public static final String CENTERED_SPACEBAR = "centered_spacebar"; // 2-set: long centered space, mode long-press changes language\n'
    '    public static final String PERIOD_CHAR = "bottom_period_char";',
    "setting key"
)
replace_one(
    prefs,
    '    public boolean periodComma() { return sp.getBoolean(PERIOD_COMMA, false); }',
    '    public boolean periodComma() { return sp.getBoolean(PERIOD_COMMA, false); }\n'
    '    public boolean centeredSpacebar() { return sp.getBoolean(CENTERED_SPACEBAR, true); }',
    "setting getter"
)

layout = root / "keyboard/KeyboardLayout.java"
source = layout.read_text(encoding="utf-8")

def change(before, after, label):
    global source
    count = source.count(before)
    assert count == 1, (label, count)
    source = source.replace(before, after, 1)

change(
    '''    private static KeyboardLayout symbols(String back, Prefs prefs, boolean five) {
        List<Row> rows = new ArrayList<>();''',
    '''    private static KeyboardLayout symbols(String back, Prefs prefs, boolean five) {
        if (prefs != null && prefs.koreanDubeolsik()) return samsungSymbols(back, prefs, five, false);
        List<Row> rows = new ArrayList<>();''',
    "real first symbol page"
)
change(
    '''    private static KeyboardLayout symbols2(String back, Prefs prefs, boolean five) {
        List<Row> rows = new ArrayList<>();''',
    '''    private static KeyboardLayout symbols2(String back, Prefs prefs, boolean five) {
        if (prefs != null && prefs.koreanDubeolsik()) return samsungSymbols(back, prefs, five, true);
        List<Row> rows = new ArrayList<>();''',
    "real second symbol page"
)

marker = "    public static KeyboardLayout symbols2(boolean korean, Prefs prefs) {"
assert source.count(marker) == 1
samsung_symbols = r'''
    /**
     * Galaxy/Samsung-style Korean QWERTY symbol ordering.
     * Previously v2.1.2 changed only the !#1 button LABEL while leaving the
     * actual original symbol positions untouched.
     *
     * Both pages now use a familiar number row, punctuation/operator row and
     * 1/2 page switch with 7 keys + delete. Existing popup edits still apply.
     * With a separate number row enabled, the extra operator row is shown.
     */
    private static KeyboardLayout samsungSymbols(String back, Prefs prefs,
                                                   boolean five, boolean second) {
        List<Row> rows = new ArrayList<>();
        rows.add(charRow(new String[]{"1", "2", "3", "4", "5", "6", "7", "8", "9", "0"},
                new String[][]{null, null, null, null, null, null, null, null, null, null},
                five ? numberRowHeight(prefs) : 1f));
        if (five) {
            rows.add(charRow(second
                    ? new String[]{"<", ">", "[", "]", "{", "}", "\\", "|", "♡", "☆"}
                    : new String[]{"+", "×", "÷", "=", "/", "_", "<", ">", "♡", "☆"},
                    new String[][]{null, null, null, null, null, null, null, null, null, null}));
        }
        rows.add(charRow(second
                ? new String[]{"€", "£", "¥", "°", "※", "★", "☆", "÷", "×", "="}
                : new String[]{"!", "@", "#", "~", "%", "^", "&", "*", "(", ")"},
                new String[][]{null, null, null, null, null, null, null, null, null, null}));
        List<Key> r3 = new ArrayList<>();
        r3.add(fn(Key.SYMBOL_PAGE, second ? "2/2" : "1/2", 1.5f));
        String[] s3 = second
                ? new String[]{"_", "/", "+", "©", "®", "…", "₩"}
                : new String[]{"-", "'", "\"", ":", ";", ",", "?"};
        String[][] p3 = second
                ? new String[][]{null, {"\\"}, {"±"}, null, null, {"·"}, {"$", "€", "£"}}
                : new String[][]{{"–", "—"}, {"‘", "’"}, {"“", "”"}, null, null, {"‚"}, {"¿"}};
        for (int i = 0; i < s3.length; i++) r3.add(ch(s3[i], p3[i]));
        r3.add(fn(deleteKey(prefs) ? Key.DELETE : Key.SPACER, "", 1.5f));
        rows.add(gridSides(r3, prefs));
        applySymbolPopups(rows, prefs);
        finishSymbols(rows, back, prefs);
        return new KeyboardLayout(second ? SYMBOLS_2 : SYMBOLS, 10, rows);
    }

'''
source = source.replace(marker, samsung_symbols + marker, 1)

# 2-set portrait can be switched to a genuinely centered, wide spacebar.
# Use symmetric functional keys on both sides, not unequal width calculations.
# All legacy bottom-key settings remain intact and return immediately when
# the new toggle is disabled.
change(
    '''        float span = to - from;
        List<Key> keys = new ArrayList<>();
        int spaceAt = bottomKeys(modeType, modeLabel, prefs, emojiKey, keys);''',
    '''        float span = to - from;
        if (prefs != null && prefs.koreanDubeolsik() && prefs.centeredSpacebar()
                && !prefs.splitView() && span >= 9.95f
                && prefs.bottomKeyShown(BottomKeys.MODE)
                && prefs.bottomKeyShown(BottomKeys.SPACE)
                && prefs.bottomKeyShown(BottomKeys.PERIOD)
                && prefs.bottomKeyShown(BottomKeys.ENTER)) {
            // Widths: 1.3 | 1.0 | 5.4 | 1.0 | 1.3 = 10.0.
            // Both groups are precisely 2.3 units, centering the 5.4-unit
            // spacebar (vs. ~4 units with the extra visible globe key).
            // Hold the symbol-mode key to switch languages in this preset.
            List<Key> centered = new ArrayList<>();
            centered.add(fn(modeType, modeLabel, 1.3f));
            centered.add(slotChar(",", prefs, popupFor(prefs, true, ",", COMMA_POPUP), 1f));
            centered.add(spaceKey(span - 4.6f));
            centered.add(slotChar(".", prefs, popupFor(prefs, true, ".", periodPopup(false)), 1f));
            centered.add(fn(Key.ENTER, "", 1.3f));
            return new Row(fnRowHeight(prefs), centered.toArray(new Key[0]));
        }
        List<Key> keys = new ArrayList<>();
        int spaceAt = bottomKeys(modeType, modeLabel, prefs, emojiKey, keys);''',
    "symmetric centered spacebar"
)
assert "new String[]{\"!\", \"@\", \"#\", \"~\", \"%\"" in source
assert 'r3.add(fn(Key.SYMBOL_PAGE, second ? "2/2" : "1/2", 1.5f));' in source
assert 'centered.add(spaceKey(span - 4.6f));' in source
layout.write_text(source, encoding="utf-8")

long_press = root / "keyboard/LongPressActions.java"
replace_one(
    long_press,
    '''        for (int i = 0; i < t.length; i++) out[i] = t[i][DIR];
        return out;''',
    '''        for (int i = 0; i < t.length; i++) out[i] = t[i][DIR];
        // The wide, symmetric bottom row omits the separate globe key.
        // Keep language switching reachable: hold !#1/가/ABC. Respect
        // explicit non-default custom mode long-press assignments.
        if (prefs != null && prefs.koreanDubeolsik() && prefs.centeredSpacebar()
                && SwipeAction.EMOJI_OPEN.equals(out[MODE])) out[MODE] = SwipeAction.LANGUAGE;
        return out;''',
    "language switching remains reachable"
)

settings = root / "SettingsActivity.java"
replace_one(
    settings,
    '''            LinearLayout landscape = section("가로 모드");
            landscape.addView(button("가로 모드 키보드 사용자화", v -> openSection(LANDSCAPE_AREA)));''',
    '''            LinearLayout bottomLayout = section("스페이스바 배치");
            bottomLayout.addView(toggle("스페이스바 중앙 확대",
                    "두벌식 세로 자판에서 스페이스바를 좌우 대칭으로 넓힙니다. "
                    + "별도 한/영 전환키 대신 왼쪽 아래 !#1/가/ABC 키를 길게 눌러 언어를 전환합니다. "
                    + "끄면 원래 기능키 순서·유무 설정을 그대로 사용합니다.",
                    Prefs.CENTERED_SPACEBAR, prefs.centeredSpacebar()));
            LinearLayout landscape = section("가로 모드");
            landscape.addView(button("가로 모드 키보드 사용자화", v -> openSection(LANDSCAPE_AREA)));''',
    "setting is user-toggleable"
)
print("NewSwipe 2.1.3: real Samsung-style two-page symbol maps + symmetrical 54% wide spacebar and language fallback.")
