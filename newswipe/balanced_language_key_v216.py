from pathlib import Path

root = Path("app/src/main/java/com/alternative_studios/newswipe")

def only(path, before, after, tag):
    body = path.read_text(encoding="utf-8")
    assert body.count(before) == 1, (tag, body.count(before))
    path.write_text(body.replace(before, after, 1), encoding="utf-8")

layout = root / "keyboard/KeyboardLayout.java"
only(
    layout,
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
    '''            // User-approved proportions (ten width units):
            // symbol 0.75 / language 1.05 / comma 1.05 /
            // space 4.30 / period 1.05 / enter 1.80.
            // The combined side widths are both exactly 2.85 units,
            // so the spacebar is geometrically centered.
            // Keep every dedicated key and preserve all tap actions.
            List<Key> centered = new ArrayList<>();
            centered.add(fn(modeType, modeLabel, 0.75f));
            centered.add(fn(Key.LANGUAGE, "", 1.05f));
            centered.add(slotChar(",", prefs, popupFor(prefs, true, ",", COMMA_POPUP), 1.05f));
            centered.add(spaceKey(span - 5.70f));
            centered.add(slotChar(".", prefs, popupFor(prefs, true, ".", periodPopup(false)), 1.05f));
            centered.add(fn(Key.ENTER, "", 1.80f));''',
    "approved user proportions for bottom row"
)

view = root / "keyboard/KeyboardView.java"
only(
    view,
    '''            case Key.LANGUAGE:
                Icons.draw(c, Icons.GLOBE, cx, cy, iconSize(iconSize, 22, iconMax), icon);
                return;''',
    '''            case Key.LANGUAGE:
                // Galaxy-style language toggle: slightly larger for visual
                // parity with the neighboring punctuation and Enter keys.
                // iconMax still limits size to the actual hitbox.
                Icons.draw(c, Icons.GLOBE, cx, cy,
                        iconSize(iconSize * 1.20f, 26, iconMax), icon);
                return;''',
    "larger language-switch key icon"
)
only(
    view,
    '''        text.setTextSize(longLabel ? spLabel : glyphSize);
        drawCentered(c, label, cx, bottomComma ? cy - dp(3) : bottomPeriod ? cy - dp(2) : cy);''',
    '''        text.setTextSize(longLabel ? spLabel : glyphSize);
        // A 0.75-unit symbol key is narrow. Fit its !#1/ABC label to
        // the visible key face rather than letting it overlap neighbors.
        if (k.type == Key.TO_SYMBOLS || k.type == Key.TO_LETTERS) {
            float textWidth = text.measureText(label);
            float available = Math.max(dp(12), r.width() - dp(3));
            if (textWidth > available) text.setTextSize(text.getTextSize() * available / textWidth);
        }
        drawCentered(c, label, cx, bottomComma ? cy - dp(3) : bottomPeriod ? cy - dp(2) : cy);''',
    "fit small symbol-key labels to their actual available width"
)

code = layout.read_text(encoding="utf-8")
render = view.read_text(encoding="utf-8")
a=[0.75,1.05,1.05,4.30,1.05,1.80]
assert abs(sum(a)-10)<1e-7
assert abs(sum(a[:3])-sum(a[-2:]))<1e-7
assert 'centered.add(fn(Key.LANGUAGE, "", 1.05f));' in code
assert 'centered.add(spaceKey(span - 5.70f));' in code
assert 'iconSize(iconSize * 1.20f, 26, iconMax)' in render
assert 'if (bottomComma) glyphSize *= 1.30f;' in render
print("NewSwipe 2.1.6: exact 0.75/1.05/1.05/4.30/1.05/1.80, language icon +20%, text fitted; symmetric row.")
