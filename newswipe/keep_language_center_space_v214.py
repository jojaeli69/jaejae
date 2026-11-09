from pathlib import Path

base = Path("app/src/main/java/com/alternative_studios/newswipe")

def replace_once(path, before, after, tag):
    text = path.read_text(encoding="utf-8")
    count = text.count(before)
    assert count == 1, (tag, count)
    path.write_text(text.replace(before, after, 1), encoding="utf-8")

layout = base / "keyboard/KeyboardLayout.java"

old = '''            // Widths: 1.3 | 1.0 | 5.4 | 1.0 | 1.3 = 10.0.
            // Both groups are precisely 2.3 units, centering the 5.4-unit
            // spacebar (vs. ~4 units with the extra visible globe key).
            // Hold the symbol-mode key to switch languages in this preset.
            List<Key> centered = new ArrayList<>();
            centered.add(fn(modeType, modeLabel, 1.3f));
            centered.add(slotChar(",", prefs, popupFor(prefs, true, ",", COMMA_POPUP), 1f));
            centered.add(spaceKey(span - 4.6f));
            centered.add(slotChar(".", prefs, popupFor(prefs, true, ".", periodPopup(false)), 1f));
            centered.add(fn(Key.ENTER, "", 1.3f));
            return new Row(fnRowHeight(prefs), centered.toArray(new Key[0]));'''

new = '''            // Keep EVERY everyday key: !#1, language, comma, space,
            // period and enter. Neither the globe nor comma is sacrificed.
            // Left total 1.05 + 0.85 + 0.80 = 2.70 units.
            // Right total 1.00 + 1.70 = 2.70 units.
            // Spacebar is centered (4.60 of 10.00 units) without dropping
            // the dedicated language-switch button.
            List<Key> centered = new ArrayList<>();
            centered.add(fn(modeType, modeLabel, 1.05f));
            centered.add(fn(Key.LANGUAGE, "", 0.85f));
            centered.add(slotChar(",", prefs, popupFor(prefs, true, ",", COMMA_POPUP), 0.80f));
            centered.add(spaceKey(span - 5.40f));
            centered.add(slotChar(".", prefs, popupFor(prefs, true, ".", periodPopup(false)), 1.00f));
            centered.add(fn(Key.ENTER, "", 1.70f));
            return new Row(fnRowHeight(prefs), centered.toArray(new Key[0]));'''
replace_once(layout, old, new, "centered row without globe")
replace_once(
    layout,
    '''                && prefs.bottomKeyShown(BottomKeys.SPACE)
                && prefs.bottomKeyShown(BottomKeys.PERIOD)''',
    '''                && prefs.bottomKeyShown(BottomKeys.SPACE)
                && prefs.bottomKeyShown(BottomKeys.GLOBE)
                && prefs.bottomKeyShown(BottomKeys.COMMA)
                && prefs.bottomKeyShown(BottomKeys.PERIOD)''',
    "honor separate language & comma visibility preferences"
)

# With a physical language button available again, restore the previous
# custom/normal press actions. Do not rewire !#1 to language switching.
actions = base / "keyboard/LongPressActions.java"
replace_once(
    actions,
    '''        // The wide, symmetric bottom row omits the separate globe key.
        // Keep language switching reachable: hold !#1/가/ABC. Respect
        // explicit non-default custom mode long-press assignments.
        if (prefs != null && prefs.centeredSpacebar()
                && SwipeAction.EMOJI_OPEN.equals(out[MODE])) out[MODE] = SwipeAction.LANGUAGE;
        return out;''',
    '''        // A dedicated language-switch key is always present in the
        // centered preset; preserve the user's original long-press bindings.
        return out;''',
    "restore normal long-press actions"
)

settings = base / "SettingsActivity.java"
replace_once(
    settings,
    '''                    + "별도 한/영 전환키 대신 왼쪽 아래 !#1/가/ABC 키를 길게 눌러 언어를 전환합니다. "
                    + "끄면 원래 기능키 순서·유무 설정을 그대로 사용합니다.",''',
    '''                    + "한/영 전환키(🌐)와 쉼표 키(,)를 모두 남긴 채 스페이스바를 중앙에 배치합니다. "
                    + "끄면 기존 기능키 순서·유무 설정을 그대로 사용합니다.",''',
    "accurate settings explanation"
)

# Static assertions: no hidden globe or opportunistic removal, symmetric
# left and right group proportions, and the established symbol-page fix.
text = layout.read_text(encoding="utf-8")
assert 'centered.add(fn(Key.LANGUAGE, "", 0.85f));' in text
assert 'centered.add(spaceKey(span - 5.40f));' in text
assert text.index('centered.add(fn(Key.LANGUAGE') < text.index('centered.add(spaceKey')
assert text.count("samsungSymbols(back, prefs, five,") == 2
assert abs((1.05 + 0.85 + 0.80) - (1.00 + 1.70)) < 1e-8
assert abs((1.05 + 0.85 + 0.80 + 4.60 + 1.00 + 1.70) - 10) < 1e-8
print("NewSwipe 2.1.4: dedicated Korean/English globe key retained, comma retained, 46% centered spacebar, Samsung symbol pages retained")
