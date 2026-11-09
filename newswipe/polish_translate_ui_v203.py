from pathlib import Path

src = Path("app/src/main/java/com/alternative_studios/newswipe")
panel = src/"KeyboardTranslatePanel.java"
s = panel.read_text(encoding="utf-8")

def change(old,new,label):
    global s
    count=s.count(old)
    assert count==1,(label,count)
    s=s.replace(old,new,1)

# Keep the original NewSwipe design and colors, give each pill breathing room.
change("        setPadding(dp(8), dp(5), dp(8), dp(5));",
       "        setPadding(dp(11), dp(8), dp(11), dp(9));",
       "panel outer padding")

change("        languages.addView(back, new LayoutParams(dp(38), dp(37)));",
       """        LayoutParams backParams = new LayoutParams(dp(38), dp(37));
        backParams.rightMargin = dp(7);
        languages.addView(back, backParams);""",
       "back chip margin")

change("        languages.addView(fromButton, new LayoutParams(0, dp(37), 1f));",
       """        LayoutParams fromParams = new LayoutParams(0, dp(37), 1f);
        fromParams.rightMargin = dp(7);
        languages.addView(fromButton, fromParams);""",
       "from chip margin")

change("        languages.addView(swap, new LayoutParams(dp(40), dp(37)));",
       """        LayoutParams swapParams = new LayoutParams(dp(40), dp(37));
        swapParams.rightMargin = dp(7);
        languages.addView(swap, swapParams);""",
       "swap chip margin")

change("        addView(languages, new LayoutParams(LayoutParams.MATCH_PARENT, dp(39)));",
       "        addView(languages, new LayoutParams(LayoutParams.MATCH_PARENT, dp(45)));",
       "language row vertical spacing")

change("        addView(entryRow, new LayoutParams(LayoutParams.MATCH_PARENT, dp(46)));",
       "        addView(entryRow, new LayoutParams(LayoutParams.MATCH_PARENT, dp(52)));",
       "entry row vertical spacing")

# Footer includes the new '본문 수정' action from v2.0.0; ensure all action pills
# are spaced evenly, including the two right-aligned actions and edit toggle.
change("        footer.addView(editModeButton, new LayoutParams(dp(74), dp(27)));",
       """        LayoutParams editParams = new LayoutParams(dp(74), dp(27));
        editParams.leftMargin = dp(5);
        footer.addView(editModeButton, editParams);""",
       "edit button margin")

change("        footer.addView(paste, new LayoutParams(dp(65), dp(27)));",
       """        LayoutParams pasteParams = new LayoutParams(dp(65), dp(27));
        pasteParams.leftMargin = dp(5);
        footer.addView(paste, pasteParams);""",
       "paste button margin")

change("        footer.addView(clear, new LayoutParams(dp(49), dp(27)));",
       """        LayoutParams clearParams = new LayoutParams(dp(49), dp(27));
        clearParams.leftMargin = dp(5);
        footer.addView(clear, clearParams);""",
       "clear button margin")

change("        addView(footer, new LayoutParams(LayoutParams.MATCH_PARENT, dp(29)));",
       "        addView(footer, new LayoutParams(LayoutParams.MATCH_PARENT, dp(34)));",
       "footer row vertical spacing")

panel.write_text(s,encoding="utf-8")

# Fix actual missing rounded background: existing NewSwipe toolbar styling loop
# skips the newly introduced Translate button, which is not in ToolbarButtons.ALL.
ime = src/"NewSwipeIME.java"
s = ime.read_text(encoding="utf-8")
def patch(old,new,label):
    global s
    count=s.count(old)
    assert count==1,(label,count)
    s=s.replace(old,new,1)

patch('''        translateQuickButton = toolButton(Icons.TRANSLATE, "번역", v -> openTranslationPanel());
        bar.addView(translateQuickButton);''',
'''        translateQuickButton = toolButton(Icons.TRANSLATE, "번역", v -> openTranslationPanel());
        // Same rounded chip, pressed ripple and neumorphic styling as mic/clipboard.
        translateQuickButton.setToolbarStyle(theme, toolbarHeight);
        bar.addView(translateQuickButton);''',
"initial rounded translate chip")

patch('''            ((IconButton) v).setToolbarStyle(theme, toolbarHeight);
        }
        if (searchBar != null) {''',
'''            ((IconButton) v).setToolbarStyle(theme, toolbarHeight);
        }
        // Translate is an additional tool button; keep its responsive size,
        // icon stroke, inset and rounded background exactly in sync.
        if (translateQuickButton != null) {
            ViewGroup.LayoutParams tlp = translateQuickButton.getLayoutParams();
            if (tlp != null && (tlp.width != width || tlp.height != toolbarHeight)) {
                tlp.width = width;
                tlp.height = toolbarHeight;
                translateQuickButton.setLayoutParams(tlp);
            }
            translateQuickButton.setIconSize(icon);
            translateQuickButton.setToolbarStyle(theme, toolbarHeight);
        }
        if (searchBar != null) {''',
"resize and style on settings changes")

patch('''        toolbar.addView(translateQuickButton,
                new LinearLayout.LayoutParams(Ui.dp(this, 40), toolbarHeight));''',
'''        toolbar.addView(translateQuickButton,
                new LinearLayout.LayoutParams(
                        Math.round(Ui.dp(this, 40) * prefs.toolButtonSize() / 100f),
                        toolbarHeight));''',
"respect toolbar button size when reordering")

ime.write_text(s,encoding="utf-8")

icons=src/"keyboard/Icons.java"
s=icons.read_text(encoding="utf-8")
head=s.index("            case TRANSLATE:")
tail=s.index("            case SELECT_ALL:",head)
assert tail>head
new_icon='''            case TRANSLATE:
                // Minimal 'A ⇄ 가' translation mark: two-language glyphs and
                // two fine direction arrows instead of stacked busy rectangles.
                android.graphics.Typeface savedTypeface = p.getTypeface();
                float savedTextSize = p.getTextSize();
                p.setStyle(Paint.Style.FILL);
                p.setTypeface(android.graphics.Typeface.create(
                        "sans-serif-medium", android.graphics.Typeface.NORMAL));
                p.setTextSize(11.6f);
                c.drawText("A", 2.7f, 11.3f, p);
                p.setTextSize(10.8f);
                c.drawText("가", 13.0f, 20.7f, p);
                p.setTypeface(savedTypeface);
                p.setTextSize(savedTextSize);
                p.setStyle(Paint.Style.STROKE);
                p.setStrokeWidth(1.5f);
                path.moveTo(11.5f, 7.2f);
                path.lineTo(20.5f, 7.2f);
                path.moveTo(17.9f, 4.7f);
                path.lineTo(20.5f, 7.2f);
                path.lineTo(17.9f, 9.7f);
                path.moveTo(12.5f, 16.7f);
                path.lineTo(3.5f, 16.7f);
                path.moveTo(6.1f, 14.2f);
                path.lineTo(3.5f, 16.7f);
                path.lineTo(6.1f, 19.2f);
                c.drawPath(path, p);
                break;
'''
s=s[:head]+new_icon+s[tail:]
icons.write_text(s,encoding="utf-8")

assert "translateQuickButton.setToolbarStyle(theme, toolbarHeight);" in ime.read_text(encoding="utf-8")
assert "fromParams.rightMargin = dp(7)" in panel.read_text(encoding="utf-8")
assert "savedTypeface" in icons.read_text(encoding="utf-8")
print("v2.0.3 NewSwipe translator UI: symmetric chip gaps, row breathing room, matching rounded toolbar chip, clean vector translation icon.")
