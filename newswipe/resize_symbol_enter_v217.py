from pathlib import Path
root=Path("app/src/main/java/com/alternative_studios/newswipe")
path=root/"keyboard/KeyboardLayout.java"
text=path.read_text(encoding="utf-8")
before='''            // User-approved proportions (ten width units):
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
            centered.add(fn(Key.ENTER, "", 1.80f));'''
after='''            // V2.1.7: reduce oversized Enter and expand cramped !#1/가/ABC.
            // Keep globe + comma, and keep spacebar long (4/10 units).
            // Measured left edge to space: 3.25; right edge: 2.75.
            // The spacebar's geometric center is just 0.25 unit right of
            // the board center, far less obvious than its old Enter imbalance.
            // 1.15 + 1.05 + 1.05 + 4.00 + 1.25 + 1.50 = 10.00.
            List<Key> centered = new ArrayList<>();
            centered.add(fn(modeType, modeLabel, 1.15f));
            centered.add(fn(Key.LANGUAGE, "", 1.05f));
            centered.add(slotChar(",", prefs, popupFor(prefs, true, ",", COMMA_POPUP), 1.05f));
            centered.add(spaceKey(span - 6.00f));
            centered.add(slotChar(".", prefs, popupFor(prefs, true, ".", periodPopup(false)), 1.25f));
            centered.add(fn(Key.ENTER, "", 1.50f));'''
assert text.count(before)==1, "Missing v2.1.6 layout"
text=text.replace(before,after,1)
path.write_text(text,encoding="utf-8")
code=path.read_text(encoding="utf-8")
vals=[1.15,1.05,1.05,4.00,1.25,1.50]
assert abs(sum(vals)-10)<1e-7
assert abs((sum(vals[:3])+vals[3]/2)-5.0)<0.26
for marker in ['centered.add(fn(modeType, modeLabel, 1.15f));','centered.add(fn(Key.LANGUAGE, "", 1.05f));','centered.add(spaceKey(span - 6.00f));','centered.add(fn(Key.ENTER, "", 1.50f));']:
    assert marker in code,marker
# The previous release's adaptive mode-label shrinking now has much more room
# to render !#1/ABC at a readable size without overlapping the globe key.
view=(root/"keyboard/KeyboardView.java").read_text(encoding="utf-8")
assert 'iconSize(iconSize * 1.20f, 26, iconMax)' in view
assert 'float available = Math.max(dp(12), r.width() - dp(3));' in view
print("NewSwipe 2.1.7: symbol 1.15, globe 1.05, comma 1.05, space 4.00, period 1.25, enter 1.50; existing features kept.")
