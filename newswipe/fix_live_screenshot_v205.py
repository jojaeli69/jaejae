from pathlib import Path

src=Path("app/src/main/java/com/alternative_studios/newswipe")
ime=src/"NewSwipeIME.java"
s=ime.read_text(encoding="utf-8")

def replace(a,b,label):
    global s
    n=s.count(a)
    assert n==1,(label,n,a[:140])
    s=s.replace(a,b,1)

# Remove the One Hand toolbar icon, without disabling user one-hand mode
# in Settings. User asked to free the toolbar space.
replace('''        oneHandButton = toolButton(Icons.ONE_HAND, "한 손 모드", v -> toggleOneHand());
        bar.addView(oneHandButton);''',
'''        oneHandButton = toolButton(Icons.ONE_HAND, "한 손 모드", v -> toggleOneHand());
        // No one-hand toolbar button: preserve space for clipboard/translate/paste.
        // One-hand mode remains available from the full keyboard settings.''',
'remove one-hand initial toolbar icon')

replace('''        for (String id : order[0]) toolbar.addView(toolButtonOf(id));''',
'''        for (String id : order[0]) {
            if (!ToolbarButtons.ONE_HAND.equals(id)) toolbar.addView(toolButtonOf(id));
        }''','remove one-hand from custom left toolbar order')
replace('''        for (String id : order[1]) toolbar.addView(toolButtonOf(id));''',
'''        for (String id : order[1]) {
            if (!ToolbarButtons.ONE_HAND.equals(id)) toolbar.addView(toolButtonOf(id));
        }''','remove one-hand from custom right toolbar order')

replace('''    private String lastRecentScreenshotKey;''',
'''    private String lastRecentScreenshotKey;
    private android.database.ContentObserver screenshotObserver;
    private final Runnable screenshotScanRunnable = this::checkRecentScreenshot;''',
'visible-only content observer fields')

replace('''private void checkRecentScreenshot() {
        if (!prefs.clipboardChip() || !RecentScreenshot.allowed(this)
                || panel!=PANEL_KEYBOARD || passwordField || quickImageReady()) return;''',
'''    private void checkRecentScreenshot() {
        if (!prefs.clipboardChip() || !RecentScreenshot.allowed(this)
                || panel!=PANEL_KEYBOARD || passwordField || windowHidden) return;''',
'do not skip newer screenshot when photo chip holds old content')

replace('''                if (r==null || gen!=pasteInputGeneration || panel!=PANEL_KEYBOARD
                        || passwordField || windowHidden || quickImageReady()) return;
                String marker=r.uri.toString();
                if (marker.equals(lastRecentScreenshotKey)) return;
                lastRecentScreenshotKey=marker;
                offerQuickImage(r.uri,r.mime,true);''',
'''                if (r==null || gen!=pasteInputGeneration || panel!=PANEL_KEYBOARD
                        || passwordField || windowHidden) return;
                String marker=r.uri.toString();
                if (marker.equals(lastRecentScreenshotKey)) return;
                // A newer user-copied image should take priority over an older screenshot.
                if (quickImageReady() && !quickImageFromScreenshot
                        && quickImageCopiedAt > r.captured + 1000L) return;
                lastRecentScreenshotKey=marker;
                offerQuickImage(r.uri,r.mime,true);''',
'allow newer screenshot replace old photo chip')

# Monitor gallery saves only when keyboard is showing and the user has granted
# full image access. No persistent background service and no broad media polling.
anchor='''private void checkRecentScreenshot() {'''
assert s.count(anchor)==1
s=s.replace(anchor,'''    /** Only listen for new screenshot files while this keyboard is visible. */
    private void startScreenshotObserver() {
        if (screenshotObserver != null || !RecentScreenshot.allowed(this)) return;
        screenshotObserver = new android.database.ContentObserver(main) {
            @Override public void onChange(boolean selfChange) {
                scheduleScreenshotScan();
            }
            @Override public void onChange(boolean selfChange, Uri changed) {
                scheduleScreenshotScan();
            }
        };
        try {
            getContentResolver().registerContentObserver(
                    android.provider.MediaStore.Images.Media.EXTERNAL_CONTENT_URI,
                    true, screenshotObserver);
        } catch (RuntimeException denied) {
            screenshotObserver = null;
        }
    }

    private void stopScreenshotObserver() {
        main.removeCallbacks(screenshotScanRunnable);
        if (screenshotObserver == null) return;
        try {
            getContentResolver().unregisterContentObserver(screenshotObserver);
        } catch (RuntimeException ignored) { }
        screenshotObserver = null;
    }

    private void scheduleScreenshotScan() {
        if (windowHidden || !RecentScreenshot.allowed(this)) return;
        main.removeCallbacks(screenshotScanRunnable);
        // Samsung Gallery/MediaProvider may publish the image after a short delay.
        main.postDelayed(screenshotScanRunnable, 650L);
        main.postDelayed(() -> {
            if (!windowHidden) checkRecentScreenshot();
        }, 1850L);
    }

'''+anchor,1)

replace('''        windowHidden = false;
        refreshHwToolbar();''',
'''        windowHidden = false;
        startScreenshotObserver();
        scheduleScreenshotScan();
        refreshHwToolbar();''','resume screenshot watch onWindowShown')

replace('''        pasteInputGeneration++;
        windowHidden = false;''',
'''        pasteInputGeneration++;
        windowHidden = false;
        startScreenshotObserver();
        scheduleScreenshotScan();''','start screenshot watch on input focus')

replace('''    public void onWindowHidden() {
        if (translateMode()) closeTranslationPanel();''',
'''    public void onWindowHidden() {
        stopScreenshotObserver();
        if (translateMode()) closeTranslationPanel();''','stop watcher when keyboard hides')

replace('''    public void onDestroy() {
        if (translationPanel != null) translationPanel.dismiss();''',
'''    public void onDestroy() {
        stopScreenshotObserver();
        if (translationPanel != null) translationPanel.dismiss();''','stop watcher on destroy')

ime.write_text(s,encoding="utf-8")

# Partial photo access is not sufficient for reliably detecting arbitrary new screenshots.
manifest=Path("app/src/main/AndroidManifest.xml")
s=manifest.read_text(encoding="utf-8")
needle='''    <uses-permission android:name="android.permission.READ_MEDIA_IMAGES" />'''
assert s.count(needle)==1
s=s.replace(needle,needle+'''
    <uses-permission android:name="android.permission.READ_MEDIA_VISUAL_USER_SELECTED" />''',1)
manifest.write_text(s,encoding="utf-8")

assert s.count('READ_MEDIA_VISUAL_USER_SELECTED')==1
assert 'oneHandButton' in ime.read_text(encoding="utf-8")  # preserved object
assert 'bar.addView(oneHandButton)' not in ime.read_text(encoding="utf-8")
assert 'startScreenshotObserver();' in ime.read_text(encoding="utf-8")
assert 'pasteImageById' in ime.read_text(encoding="utf-8")
print("v2.0.5: screenshot MediaStore watcher while visible, retry delayed saves, remove one-hand toolbar button.")
