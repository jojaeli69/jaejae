from pathlib import Path

root=Path("app/src/main/java/com/alternative_studios/newswipe")
ime=root/"NewSwipeIME.java"
s=ime.read_text(encoding="utf-8")

def once(old,new,name):
    global s
    count=s.count(old)
    assert count==1,(name,count)
    s=s.replace(old,new,1)

# Regression in v2.2.1: it moved both chips into a new TextView, but the
# only click handler calls the TEXT-ONLY pasteClipChip(). For image clipboard
# items, clipChipPreview is null and this method silently does nothing.
once('''        eventCopiedPreview.setOnClickListener(v -> {
            feedback.onToolbar();
            pasteClipChip();
        });''',
'''        eventCopiedPreview.setOnClickListener(v -> {
            feedback.onToolbar();
            // Clipboard photos and screenshots must use the image URI
            // transfer path, NOT pasteClipChip() (which only handles text).
            if (quickImageReady()) {
                pasteQuickImage();
            } else {
                pasteClipChip();
            }
        });''',
"route photo and text presses to their respective paste handlers")

old='''        boolean inline = panel == PANEL_KEYBOARD && autofillShowing()
                && !candidatesVisible;
        boolean copied = panel == PANEL_KEYBOARD && !inline && clipChipShowing();
        if (autofillBar != null) autofillBar.setVisibility(inline ? View.VISIBLE : View.GONE);
        if (copied) {
            boolean secret = passwordField || clipChipPreview == null;
            eventCopiedPreview.setText(secret ? "복사한 내용 · 미리보기 숨김" : clipChipPreview);
            eventCopiedPreview.setContentDescription(
                    secret ? "복사한 내용 붙여넣기" : "복사한 내용 붙여넣기: " + clipChipPreview);
        }
        eventCopiedPreview.setVisibility(copied ? View.VISIBLE : View.GONE);
        int next = (inline || copied) ? View.VISIBLE : View.GONE;'''

new='''        // Existing screenshot/URI pipeline marks a copied photo with
        // quickImageReady(). That state also sets clipChipActive and sets
        // clipChipPreview=null, so the old text-only row swallowed the photo.
        // Prioritize the photo action over inline autofill when both exist.
        boolean image = panel == PANEL_KEYBOARD && quickImageReady();
        boolean inline = panel == PANEL_KEYBOARD && !image && autofillShowing()
                && !candidatesVisible;
        boolean copied = panel == PANEL_KEYBOARD && !image && !inline && clipChipShowing();
        if (autofillBar != null) autofillBar.setVisibility(inline ? View.VISIBLE : View.GONE);
        if (image) {
            eventCopiedPreview.setText("사진 붙여넣기");
            eventCopiedPreview.setCompoundDrawablePadding(Ui.dp(this, 8));
            eventCopiedPreview.setContentDescription("최근 복사한 이미지 또는 캡처 사진 붙여넣기");
        } else if (copied) {
            boolean secret = passwordField || clipChipPreview == null;
            eventCopiedPreview.setText(secret ? "복사한 내용 · 미리보기 숨김" : clipChipPreview);
            eventCopiedPreview.setContentDescription(
                    secret ? "복사한 내용 붙여넣기" : "복사한 내용 붙여넣기: " + clipChipPreview);
        }
        eventCopiedPreview.setVisibility(image || copied ? View.VISIBLE : View.GONE);
        // A second row must ONLY appear for copied text, copied photo/
        // screenshot, or a real inline Autofill suggestion.
        int next = (inline || image || copied) ? View.VISIBLE : View.GONE;'''
once(old,new,"restore explicit image preview and correct click route")
ime.write_text(s,encoding="utf-8")

# Avoid an uncaught failure from a revoked Samsung/gallery URI on the
# background IO thread. ClipImages.save() usually returns null on such an
# error; keep this path defensive as the clipboard provider may revoke URI
# grants after a screen transition.
s=ime.read_text(encoding="utf-8")
old='''            String id=known!=null && ClipboardHistory.original(clipHistory.imageDir(),known).isFile()
                    ? known : ClipImages.save(getContentResolver(),original,
                            clipHistory.imageDir(),getCacheDir());'''
new='''            String id=null;
            try {
                id=known!=null && ClipboardHistory.original(clipHistory.imageDir(),known).isFile()
                        ? known : ClipImages.save(getContentResolver(),original,
                                clipHistory.imageDir(),getCacheDir());
            } catch (RuntimeException denied) {
                android.util.Log.w("NewSwipeImage", "Cannot read clipboard image URI", denied);
            }'''
assert s.count(old)==1,("defensive uri access",s.count(old))
s=s.replace(old,new,1)
ime.write_text(s,encoding="utf-8")

s=ime.read_text(encoding="utf-8")
assert 'if (quickImageReady()) {\n                pasteQuickImage();' in s
assert 'boolean image = panel == PANEL_KEYBOARD && quickImageReady();' in s
assert 'eventCopiedPreview.setText("사진 붙여넣기");' in s
assert 'int next = (inline || image || copied) ? View.VISIBLE : View.GONE;' in s
assert 'if (autofillBar != null) autofillBar.setVisibility(inline ? View.VISIBLE : View.GONE);' in s
assert 'eventCopiedPreview.setText(secret ? "복사한 내용 · 미리보기 숨김" : clipChipPreview);' in s
assert 'pasteImageById(finalId,mime);' in s
assert 'input.commitContent(image,' in s
assert 'boolean image = panel == PANEL_KEYBOARD && quickImageReady();' in s
print("NewSwipe v2.2.2: restore image quick-paste in conditional preview row; protect revoked image URIs; keep text/autofill unchanged.")
