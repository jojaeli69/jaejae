from pathlib import Path

# Photo-only layout refinement. Text cells, clipping history, retention,
# pinning, paste actions and application identity are intentionally unchanged.
path = Path("app/src/main/java/com/alternative_studios/newswipe/clipboard/ClipboardPanel.java")
source = path.read_text(encoding="utf-8")

def replace_once(before, after, label):
    global source
    n = source.count(before)
    assert n == 1, (label, n)
    source = source.replace(before, after, 1)

# Image cells must use their intrinsic thumbnail height; otherwise the
# original zero-height/weight layout compresses the larger image back down.
replace_once(
    "card.addView(imageView(item), new LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));",
    "card.addView(imageView(item), new LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));",
    "image content cell"
)

# V2.0.6 had forced photographs to max 43dp (placeholder 36dp), in addition
# to tying them to two lines of text. Let photo cells use up to 96dp height
# with a 72dp loading placeholder, preserving the original aspect ratio.
replace_once(
    "ImageView img = new ThumbView(c, Math.min(maxContentHeight(),\n                Ui.dp(c, 43)), Ui.dp(c, 36));",
    "ImageView img = new ThumbView(c, Ui.dp(c, 96), Ui.dp(c, 72));",
    "photo preview height"
)

assert "new ThumbView(c, Ui.dp(c, 96), Ui.dp(c, 72))" in source
assert "private static final int MAX_LINES = 2;" in source
assert "private static final float TEXT_SP = 12.3f;" in source
assert source.count("card.setOnClickListener(v -> listener.onClipPasteImage(item));") == 1
path.write_text(source, encoding="utf-8")
print("NewSwipe v2.1.1: clipboard photo thumbs increased up to 96dp; text density and paste handling preserved.")
