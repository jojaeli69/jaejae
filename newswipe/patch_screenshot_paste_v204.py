from pathlib import Path
from textwrap import dedent

src=Path("app/src/main/java/com/alternative_studios/newswipe")
(src/"RecentScreenshot.java").write_bytes(Path("../newswipe/RecentScreenshot.java").read_bytes())
(src/"ScreenshotAccessActivity.java").write_bytes(Path("../newswipe/ScreenshotAccessActivity.java").read_bytes())

manifest=Path("app/src/main/AndroidManifest.xml")
s=manifest.read_text(encoding="utf-8")
def replace_manifest(a,b):
 global s
 n=s.count(a)
 assert n==1,("manifest",n,a)
 s=s.replace(a,b,1)
replace_manifest('''<uses-permission android:name="android.permission.RECEIVE_SMS" />''',
'''<uses-permission android:name="android.permission.RECEIVE_SMS" />
    <!-- Optional explicit gallery permission: needed only if Samsung doesn't
         place freshly captured screenshots on the system clipboard. -->
    <uses-permission android:name="android.permission.READ_MEDIA_IMAGES" />
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" android:maxSdkVersion="32" />''')
replace_manifest('''        <activity
            android:name=".SmsDirectSetupActivity"''',
'''        <activity
            android:name=".ScreenshotAccessActivity"
            android:exported="false"
            android:label="최근 캡처 사진 접근" />
        <activity
            android:name=".SmsDirectSetupActivity"''')
manifest.write_text(s,encoding="utf-8")

settings=src/"SettingsActivity.java"
s=settings.read_text(encoding="utf-8")
assert s.count('''        clip.addView(toggle("방금 복사한 내용 붙여넣기",''')==1
s=s.replace('''        clip.addView(toggle("방금 복사한 내용 붙여넣기",
                "방금 복사한 텍스트를 도구 막대에 1분 간 보여 주어 빠르게 붙여 넣을 수 있게 합니다.",''',
'''        clip.addView(toggle("방금 복사한 내용 붙여넣기",
                "방금 복사한 텍스트와 캡처 사진을 도구 막대에 1분 간 보여 주어 빠르게 붙여 넣습니다.",''',1)
needle='''        clip.addView(trashButton("클립보드 기록 모두 지우기",'''
assert s.count(needle)==1
s=s.replace(needle,'''        clip.addView(button("최근 캡처 사진 바로 붙여넣기 · 최초 1회 권한 설정",
                v -> startActivity(new Intent(this, ScreenshotAccessActivity.class))));
        clip.addView(note("삼성 화면 캡처가 클립보드에 없어도, 허용 시 새 스크린샷을 찾아 "
                + "사진 붙여넣기 버튼으로 표시합니다. 새로 캡처한 사진만 확인하며 "
                + "권한을 주지 않아도 클립보드 사진 붙여넣기는 사용할 수 있습니다."));
'''+needle,1)
settings.write_text(s,encoding="utf-8")

p=src/"NewSwipeIME.java"
s=p.read_text(encoding="utf-8")
def sub(old,new,label):
 global s
 n=s.count(old)
 assert n==1,(label,n,old[:120])
 s=s.replace(old,new,1)

sub('''    private Uri quickImageUri;
    private long quickImageCopiedAt;''',
'''    private Uri quickImageUri;
    private String quickImageMime;
    private boolean quickImageFromScreenshot;
    private String lastImageClipboardKey;
    private String lastRecentScreenshotKey;
    private long quickImageCopiedAt;''','image fields')

sub('''        refreshFreshClipboard();
        if (root != null) root.requestApplyInsets();''',
'''        refreshFreshClipboard();
        checkRecentScreenshot();
        if (root != null) root.requestApplyInsets();''','window shown')

sub('''        refreshFreshClipboard();''',
'''        refreshFreshClipboard();
        checkRecentScreenshot();''','extra screenshot hook') if False else None

# onStartInputView contains a separate refreshFreshClipboard call.
sub('''        applyTopSlotVisibility();
        refreshFreshClipboard();''',
'''        applyTopSlotVisibility();
        refreshFreshClipboard();
        checkRecentScreenshot();''','focus latest screenshot')

start=s.index('''    private boolean quickImageReady() {''')
end=s.index('''    private boolean otpReady()''',start) if False else -1
# replace complete helper region, bounded by the next existing method after pasteQuickImage
end=s.index('''    /** 방금 복사한 텍스트로 칩을 띄운다''',start) if '''    /** 방금 복사한 텍스트로 칩을 띄운다''' in s[start:] else -1
# Helpers reside immediately before other methods, so identify "private void offerClipChip" or current original.
if end<0:
    end=s.index('''    private void offerClipChip(''',start)
    # Preserve the javadoc that precedes offerClipChip by cutting only to it.
    j=s.rfind('''    /**''',start,end)
    if j>=start:end=j
assert end>start,("helper region bounds",start,end)
s=s[:start]+dedent('''\
    private boolean quickImageReady() {
        return panel == PANEL_KEYBOARD && !passwordField && quickImageUri != null
                && clipChipActive && prefs.clipboardChip();
    }

    private void offerQuickImage(Uri uri, String mime, boolean screenshot) {
        if (uri == null || mime == null || !mime.startsWith("image/")) return;
        quickImageUri=uri;
        quickImageMime=mime;
        quickImageFromScreenshot=screenshot;
        quickImageCopiedAt=System.currentTimeMillis();
        clipChipActive=true;
        clipChipPreview=null;
        main.removeCallbacks(expireClipChip);
        main.postDelayed(expireClipChip,CLIP_CHIP_MS);
        refreshToolbarVisibility();
    }

    /**
     * Android 10+ hides clipboard contents from background apps.
     * Always re-check once the IME becomes foreground, even when Samsung
     * omits the clipboard timestamp.
     */
    private void refreshFreshClipboard() {
        if (clipboard == null || !prefs.clipboardChip()) return;
        try {
            ClipData data=clipboard.getPrimaryClip();
            if (data == null || data.getItemCount()==0) return;
            ClipDescription description=data.getDescription();
            long stamp=description==null?0L:description.getTimestamp();
            if (stamp>0L) {
                if (stamp==lastClipboardStamp) return;
                long age=System.currentTimeMillis()-stamp;
                if (age<0L || age>CLIP_CHIP_MS) return;
            } else {
                Uri image=firstImageUri(data);
                String marker=image==null?null:image.toString();
                if (marker!=null && marker.equals(lastImageClipboardKey)) return;
            }
            onPrimaryClipChanged();
        } catch (RuntimeException ignored) {
            // On Android 15+ the foreground keyboard may still have a restricted clipboard.
        }
    }

    /** Samsung can include text + URI or put the image URI in an Intent item. */
    private Uri firstImageUri(ClipData data) {
        if (data==null) return null;
        for (int i=0;i<data.getItemCount();i++) {
            ClipData.Item item=data.getItemAt(i);
            Uri uri=item.getUri();
            if (uri==null && item.getIntent()!=null) uri=item.getIntent().getData();
            if (uri!=null && imageMime(data.getDescription(),uri)!=null) return uri;
        }
        return null;
    }

    private void checkRecentScreenshot() {
        if (!prefs.clipboardChip() || !RecentScreenshot.allowed(this)
                || panel!=PANEL_KEYBOARD || passwordField || quickImageReady()) return;
        final int gen=pasteInputGeneration;
        runIo(() -> {
            RecentScreenshot.Result r=RecentScreenshot.latest(this,System.currentTimeMillis());
            main.post(() -> {
                if (r==null || gen!=pasteInputGeneration || panel!=PANEL_KEYBOARD
                        || passwordField || windowHidden || quickImageReady()) return;
                String marker=r.uri.toString();
                if (marker.equals(lastRecentScreenshotKey)) return;
                lastRecentScreenshotKey=marker;
                offerQuickImage(r.uri,r.mime,true);
            });
        });
    }

    /** Copy only after the user taps the image chip; don't race clipboard history IO. */
    private void pasteQuickImage() {
        final Uri original=quickImageUri;
        final String mime=quickImageMime;
        final boolean gallery=quickImageFromScreenshot;
        final int gen=pasteInputGeneration;
        dismissClipChip();
        if (original==null || mime==null) return;
        runIo(() -> {
            String known=ClipImageProvider.idOf(this,original);
            String id=known!=null && ClipboardHistory.original(clipHistory.imageDir(),known).isFile()
                    ? known : ClipImages.save(getContentResolver(),original,
                            clipHistory.imageDir(),getCacheDir());
            if (id!=null && prefs.clipboardHistory() && prefs.clipboardImages()) {
                clipHistory.addImage(id,mime,System.currentTimeMillis());
            }
            final String finalId=id;
            main.post(() -> {
                if (gen!=pasteInputGeneration || windowHidden || passwordField
                        || panel!=PANEL_KEYBOARD) return;
                if (finalId!=null) {
                    pasteImageById(finalId,mime);
                } else {
                    Toast.makeText(this,
                            gallery ? "캡처 사진을 읽을 수 없습니다. 사진 권한을 확인해 주세요."
                                    : "클립보드 이미지 접근이 제한됐습니다. 최근 캡처 사진 접근을 허용해 보세요.",
                            Toast.LENGTH_LONG).show();
                    checkRecentScreenshot();
                }
            });
        });
    }

'''),s[start:end].split("    private boolean quickImageReady()")[0] if False else '')+s[end:]
# dedent produces leading 0 chars because embedded four spaces? dedent removes four,
# re-indent into Java class scope.
# (Handled separately by content above after dedent, fix any top-level helpers)
new_begin=s.index('private boolean quickImageReady()')
new_end=s.index('    /**',new_begin) if False else s.index('    private void offerClipChip(',new_begin)
# Keep Javadoc if any; inject exactly four spaces before nonempty lines not yet class-indented.
new_block=s[new_begin:new_end]
# if dedent yields 0-indent methods, ensure Java formatting but syntax allows indentation 0.
# We deliberately avoid brittle formatting transforms.
p.write_text(s,encoding="utf-8")
print("Integrated clipboard refresh, Samsung multi-item images, screenshot gallery fallback and direct image-paste path.")
