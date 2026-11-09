from pathlib import Path

p=Path("app/src/main/java/com/alternative_studios/newswipe/clipboard/ClipboardPanel.java")
s=p.read_text(encoding="utf-8")

def swap(before,after,why):
 global s
 n=s.count(before)
 assert n==1,(why,n)
 s=s.replace(before,after,1)

# No change to the underlying clipboard storage and privacy / expiry behavior.
# This is a presentation-only update: keep the two-column card layout and edit controls.
swap('''    private static final float TEXT_SP = 14;
    private static final int MAX_LINES = 4;''',
'''    private static final float TEXT_SP = 12.3f;
    private static final int MAX_LINES = 2;''',
"smaller text and fewer lines")

swap('''    private static final int GAP_DP = 6;''',
'''    private static final int GAP_DP = 4;''',
"compact card spacing")

swap('''    private static final int CELL_DP = 190;''',
'''    private static final int CELL_DP = 165;''',
"responsive columns and no squeezed narrow text")

swap('''        int p = Ui.dp(context, 8);
        l.setPadding(p, 0, p, p);''',
'''        int p = Ui.dp(context, 6);
        l.setPadding(p, 0, p, p);''',
"edge margins")

swap('''        boolean split = splitPinned && enabled && !items.isEmpty();
        setSplit(split);''',
'''        boolean split = splitPinned && enabled && !items.isEmpty();
        title.setText(enabled && !items.isEmpty()
                ? "클립보드 · " + items.size() : "클립보드");
        setSplit(split);''',
"item count")

swap('''        int p = Ui.dp(c, 10);
        card.setPadding(p, p, p, item == null ? p : 0);''',
'''        int p = Ui.dp(c, 7);
        card.setPadding(p, Ui.dp(c, 6), p, item == null ? p : 0);
        card.setMinimumHeight(Ui.dp(c, 52));''',
"compact card padding and minimum hit area")

swap('''            t.setTextSize(TypedValue.COMPLEX_UNIT_SP, TEXT_SP);
            t.setMaxLines(MAX_LINES);
            t.setEllipsize(TextUtils.TruncateAt.END);
            card.addView(t, new LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));
            card.setOnClickListener(v -> listener.onClipPaste(text));''',
'''            t.setTextSize(TypedValue.COMPLEX_UNIT_SP, TEXT_SP);
            t.setIncludeFontPadding(false);
            t.setLineSpacing(0f, 1.03f);
            t.setMaxLines(MAX_LINES);
            t.setEllipsize(TextUtils.TruncateAt.END);
            card.addView(t, new LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));
            card.setOnClickListener(v -> listener.onClipPaste(text));
            // Long press reveals more of a truncated entry without leaving
            // the compact multi-item panel or pasting into another app.
            card.setOnLongClickListener(v -> {
                String preview = text.length() > 190 ? text.substring(0, 190) + "…" : text;
                android.widget.Toast.makeText(c, preview,
                        android.widget.Toast.LENGTH_LONG).show();
                return true;
            });''',
"preview on long-press")

swap('''            barLp.rightMargin = -Ui.dp(c, 6);''',
'''            barLp.rightMargin = -Ui.dp(c, 4);''',
"align smaller toolbar icon")

swap('''            bar.addView(pin, new LayoutParams(Ui.dp(c, 36), Ui.dp(c, 36)));''',
'''            pin.setIconSize(Ui.dp(c, 17));
            bar.addView(pin, new LayoutParams(Ui.dp(c, 29), Ui.dp(c, 28)));''',
"compact pin button")

swap('''            bar.addView(trash, new LayoutParams(Ui.dp(c, 36), Ui.dp(c, 36)));''',
'''            trash.setIconSize(Ui.dp(c, 17));
            bar.addView(trash, new LayoutParams(Ui.dp(c, 29), Ui.dp(c, 28)));''',
"compact trash button")

swap('''        ImageView img = new ThumbView(c, maxContentHeight(), Ui.dp(c, 56));''',
'''        ImageView img = new ThumbView(c, Math.min(maxContentHeight(),
                Ui.dp(c, 43)), Ui.dp(c, 36));''',
"restrict image thumb height")

swap('''        t.setTextSize(TypedValue.COMPLEX_UNIT_SP, 12.5f);''',
'''        t.setTextSize(TypedValue.COMPLEX_UNIT_SP, 10.8f);''',
"hint smaller font")

swap('''        int p = Ui.dp(getContext(), 16);
        t.setPadding(p, p, p, p);''',
'''        int h = Ui.dp(getContext(), 12);
        int v = Ui.dp(getContext(), 9);
        t.setPadding(h, v, h, v);''',
"footer smaller padding")

# Use 2 columns on typical S25 portrait, scaling to more only on wide screens.
# Explicit max columns prevents dangerously narrow items for long Korean text.
swap('''        return Math.max(2, Math.min(8, widthDp / CELL_DP));''',
'''        return Math.max(2, Math.min(5, widthDp / CELL_DP));''',
"responsive compact layout")

# Avoid unnecessary animations when scrolling many cards: preserve reorder animation
# when pinning/deleting, but let ScrollView recycle normal scroll freely.
assert s.count("card.setMinimumHeight(Ui.dp(c, 52));")==1
assert s.count("private static final int MAX_LINES = 2;")==1
assert s.count("pin.setIconSize(Ui.dp(c, 17));")==1

p.write_text(s,encoding="utf-8")
print("Compact clipboard UI: 2 text lines, 12.3sp, 4dp card gaps, 28dp actions, 43dp image thumbs, long-press preview.")
