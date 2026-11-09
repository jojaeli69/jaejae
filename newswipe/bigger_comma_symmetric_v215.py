from pathlib import Path

root = Path("app/src/main/java/com/alternative_studios/newswipe")

def replace_once(path, old, new, label):
    data = path.read_text(encoding="utf-8")
    matches = data.count(old)
    assert matches == 1, (label, matches)
    path.write_text(data.replace(old, new, 1), encoding="utf-8")

layout = root / "keyboard/KeyboardLayout.java"
replace_once(
    layout,
    '''            // Left total 1.05 + 0.85 + 0.80 = 2.70 units.
            // Right total 1.00 + 1.70 = 2.70 units.
            // Spacebar is centered (4.60 of 10.00 units) without dropping
            // the dedicated language-switch button.
            List<Key> centered = new ArrayList<>();
            centered.add(fn(modeType, modeLabel, 1.05f));
            centered.add(fn(Key.LANGUAGE, "", 0.85f));
            centered.add(slotChar(",", prefs, popupFor(prefs, true, ",", COMMA_POPUP), 0.80f));
            centered.add(spaceKey(span - 5.40f));
            centered.add(slotChar(".", prefs, popupFor(prefs, true, ".", periodPopup(false)), 1.00f));
            centered.add(fn(Key.ENTER, "", 1.70f));''',
    '''            // Screenshot-driven adjustment: the comma was only 0.8 units
            // wide (narrower than the period). Now both punctuation keys are
            // 1.15 units. Preserve the dedicated Korean/English switch.
            // Left: 0.9 + 0.8 + 1.15 = 2.85 units.
            // Right: 1.15 + 1.7 = 2.85 units.
            // Space: 4.30 units, geometrically centered on 10.0 units.
            List<Key> centered = new ArrayList<>();
            centered.add(fn(modeType, modeLabel, 0.90f));
            centered.add(fn(Key.LANGUAGE, "", 0.80f));
            centered.add(slotChar(",", prefs, popupFor(prefs, true, ",", COMMA_POPUP), 1.15f));
            centered.add(spaceKey(span - 5.70f));
            centered.add(slotChar(".", prefs, popupFor(prefs, true, ".", periodPopup(false)), 1.15f));
            centered.add(fn(Key.ENTER, "", 1.70f));''',
    "larger comma key while preserving all six bottom buttons"
)

# The comma glyph itself looks very small due to its low typographic height.
# Improve only the visual presentation of comma and full stop in gray
# function-key rows; the actual committed characters/touch hitboxes are intact.
view = root / "keyboard/KeyboardView.java"
replace_once(
    view,
    '''        text.setTextSize(longLabel ? spLabel : layout.kind == KeyboardLayout.NUMBER ? spNumber : spChar);
        drawCentered(c, label, cx, cy);''',
    '''        boolean bottomComma = k.grayStyle && ",".equals(label) && ",".equals(k.slot());
        boolean bottomPeriod = k.grayStyle && ".".equals(label) && ".".equals(k.slot());
        float glyphSize = layout.kind == KeyboardLayout.NUMBER ? spNumber : spChar;
        // Comma/period occupy very little ink in a full-height font box.
        // Scale + optical lift affects rendering only; typing still inserts
        // the exact same comma/period and accepts existing popup overrides.
        if (bottomComma) glyphSize *= 1.30f;
        else if (bottomPeriod) glyphSize *= 1.17f;
        text.setTextSize(longLabel ? spLabel : glyphSize);
        drawCentered(c, label, cx, bottomComma ? cy - dp(3) : bottomPeriod ? cy - dp(2) : cy);''',
    "increase optical comma punctuation size on bottom row"
)

# Layout invariants to defend against a subsequent accidental globe-key drop.
code = layout.read_text(encoding="utf-8")
viewcode = view.read_text(encoding="utf-8")
assert 'centered.add(fn(Key.LANGUAGE, "", 0.80f));' in code
assert 'centered.add(slotChar(",", prefs, popupFor(prefs, true, ",", COMMA_POPUP), 1.15f));' in code
assert 'centered.add(spaceKey(span - 5.70f));' in code
assert abs((0.9 + 0.8 + 1.15) - (1.15 + 1.70)) < 0.00001
assert abs((0.9 + 0.8 + 1.15 + 4.3 + 1.15 + 1.7) - 10) < 0.00001
assert "if (bottomComma) glyphSize *= 1.30f" in viewcode
print("NewSwipe v2.1.5: comma/period 1.15 units each, comma glyph 130%, symmetric 43%-width spacebar, Korean/English key retained")
