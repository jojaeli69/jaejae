from pathlib import Path
p=Path('app/src/main/java/com/alternative_studios/newswipe/NewSwipeIME.java')
s=p.read_text()
def sub(a,b,label):
 global s
 count=s.count(a)
 assert count==1,(label,count)
 s=s.replace(a,b,1)

sub('    private ClipboardHistory clipHistory;', '''    private ClipboardHistory clipHistory;
    private Uri quickImageUri;
    private long quickImageCopiedAt;
    private long lastClipboardStamp = -1L;
    private int pasteInputGeneration;
''', 'fields')
sub('''        refreshBottomInset(null);
        if (root != null) root.requestApplyInsets();''','''        refreshBottomInset(null);
        refreshFreshClipboard();
        if (root != null) root.requestApplyInsets();''','onWindowShown')
sub('''            } else {
                pasteClipChip();
            }
        });''','''            } else if (quickImageReady()) {
                pasteQuickImage();
            } else {
                pasteClipChip();
            }
        });''','chip click')
sub('''        super.onStartInputView(info, restarting);
        windowHidden = false;''','''        super.onStartInputView(info, restarting);
        pasteInputGeneration++;
        windowHidden = false;''','generation')
sub('''        refreshToolbarVisibility();   // 입력란이 바뀌면 복사한 내용 칩의 가림 여부도 다시 정한다 (비밀번호 입력란)
        applyTopSlotVisibility();''','''        refreshToolbarVisibility();   // 입력란이 바뀌면 복사한 내용 칩의 가림 여부도 다시 정한다 (비밀번호 입력란)
        applyTopSlotVisibility();
        refreshFreshClipboard();''','onStartInputView')
sub('suggestBar.setVisibility(!otpReady() && suggestions.length > 0','suggestBar.setVisibility(!otpReady() && !quickImageReady() && suggestions.length > 0','suggest visibility')
sub('''        boolean otp = otpReady() && !candidatesShown();
        if (otp && suggestBar != null) suggestBar.setVisibility(View.GONE);
        if (!otp) applySuggestBarVisibility();''','''        boolean otp = otpReady() && !candidatesShown();
        boolean image = !otp && !candidatesShown() && quickImageReady();
        boolean quick = otp || image;
        if (quick && suggestBar != null) suggestBar.setVisibility(View.GONE);
        if (!quick) applySuggestBarVisibility();''','quick priority')
sub('boolean editing = !otp && !candidates && editShowing();','boolean editing = !quick && !candidates && editShowing();','editing')
sub('''if (autofillBar != null && autofill != null && (candidates || autofillHiddenForCandidates)) {
            autofillBar.setVisibility(!otp && !candidates && autofill.shown()''','''if (autofillBar != null && autofill != null) {
            autofillBar.setVisibility(!quick && !candidates && autofill.shown()''','autofill')
sub('boolean suggesting = !otp && (','boolean suggesting = !quick && (','suggesting')
sub('toolbar.setVisibility(panel == PANEL_SEARCH || !(on || suggesting)','toolbar.setVisibility(panel == PANEL_SEARCH || !(on || suggesting || quick)','show toolbar')
sub('boolean chip = otp || (!suggesting && on && clipChipShowing());','boolean chip = quick || (!suggesting && on && clipChipShowing());','chip priority')
sub('''                } else {
                    boolean masked = clipChipPreview == null || passwordField;
                    clipChip.setLabel(masked ? "••••••" : clipChipPreview);
                    clipChip.setContentDescription(masked ? "복사한 내용 붙여넣기" : "붙여넣기: " + clipChipPreview);
                }
            }
            clipChipSlot.setVisibility''','''                } else if (image) {
                    clipChip.setLabel("사진 붙여넣기");
                    clipChip.setContentDescription("복사한 사진 바로 붙여넣기");
                } else {
                    boolean masked = clipChipPreview == null || passwordField;
                    clipChip.setLabel(masked ? "••••••" : clipChipPreview);
                    clipChip.setContentDescription(masked ? "복사한 내용 붙여넣기" : "붙여넣기: " + clipChipPreview);
                }
            }
            clipChipSlot.setVisibility''','image label')
sub('''    private boolean otpReady() {
        if (panel != PANEL_KEYBOARD || passwordField || !prefs.smsOtpConsent()) return false;
        String current = OtpCodeSession.fresh();
        if (otpCode != null && current == null) otpCode = null;
        return otpCode != null || otpConsentIntent != null;
    }''','''    private boolean otpReady() {
        if (panel != PANEL_KEYBOARD || passwordField || !prefs.smsOtpConsent()) return false;
        String current = OtpCodeSession.fresh();
        if (otpCode != null && current == null) otpCode = null;
        return otpCode != null || otpConsentIntent != null;
    }

    private boolean quickImageReady() {
        return panel == PANEL_KEYBOARD && !passwordField && quickImageUri != null
                && clipChipActive && prefs.clipboardChip();
    }

    private void offerQuickImage(Uri uri) {
        if (uri == null) return;
        quickImageUri = uri;
        quickImageCopiedAt = System.currentTimeMillis();
        clipChipActive = true;
        clipChipPreview = null;
        main.removeCallbacks(expireClipChip);
        main.postDelayed(expireClipChip, CLIP_CHIP_MS);
        refreshToolbarVisibility();
    }

    /** Clipboard reads are denied while the keyboard is hidden on Android 10+. */
    private void refreshFreshClipboard() {
        if (clipboard == null || !prefs.clipboardChip()) return;
        try {
            ClipDescription d = clipboard.getPrimaryClipDescription();
            if (d == null || d.getTimestamp() <= 0 || d.getTimestamp() == lastClipboardStamp) return;
            long age = System.currentTimeMillis() - d.getTimestamp();
            if (age >= 0 && age < CLIP_CHIP_MS) onPrimaryClipChanged();
        } catch (RuntimeException ignored) { }
    }

    /** Image history is saved on the same serial IO queue before this reads it. */
    private void pasteQuickImage() {
        Uri original = quickImageUri;
        long copiedAt = quickImageCopiedAt;
        final int gen = pasteInputGeneration;
        dismissClipChip();
        if (original == null) return;
        runIo(() -> {
            ClipboardHistory.Item newest = null;
            for (ClipboardHistory.Item entry : clipHistory.items(System.currentTimeMillis())) {
                if (entry.isImage() && (newest == null || entry.time > newest.time)) newest = entry;
            }
            final ClipboardHistory.Item item = newest != null && newest.time >= copiedAt - 5000 ? newest : null;
            main.post(() -> {
                if (gen != pasteInputGeneration || windowHidden || passwordField || panel != PANEL_KEYBOARD) return;
                if (item != null) pasteImage(item);
                else Toast.makeText(this, "사진을 읽지 못했습니다. 갤러리에서 다시 복사해 주세요.", Toast.LENGTH_SHORT).show();
            });
        });
    }''','helper methods')
sub('''    private void offerClipChip(CharSequence text, boolean sensitive) {
        // 비밀번호 입력란에서''','''    private void offerClipChip(CharSequence text, boolean sensitive) {
        quickImageUri = null;
        // 비밀번호 입력란에서''','text copy')
sub('''        clipChipActive = false;
        clipChipPreview = null;
        refreshToolbarVisibility();''','''        clipChipActive = false;
        clipChipPreview = null;
        quickImageUri = null;
        refreshToolbarVisibility();''','dismiss')
sub('''        boolean sensitive = extras != null && extras.getBoolean(SENSITIVE_EXTRA, false);
        ClipData.Item first = clip.getItemAt(0);
        if (chip) {
            // 방금 복사한 텍스트를 칩으로 띄운다. 비밀번호처럼 민감한 정보도 붙여 넣을 수 있게 하되 내용은 가린다.
            if (first.getUri() == null && first.getText() != null) offerClipChip(first.getText(), sensitive);
            else dismissClipChip();
        }''','''        boolean sensitive = extras != null && extras.getBoolean(SENSITIVE_EXTRA, false);
        if (desc != null && desc.getTimestamp() > 0) lastClipboardStamp = desc.getTimestamp();
        ClipData.Item first = clip.getItemAt(0);
        String copiedImage = imageMime(desc, first.getUri());
        if (chip) {
            if (copiedImage != null && !sensitive && history && prefs.clipboardImages()) {
                offerQuickImage(first.getUri());
            } else if (first.getUri() == null && first.getText() != null) {
                offerClipChip(first.getText(), sensitive);
            } else {
                dismissClipChip();
            }
        }''','image clip listener')
sub('''        String imageMime = imageMime(desc, first.getUri());
        if (imageMime != null) {
            if (prefs.clipboardImages()) saveClipImage(first.getUri(), imageMime);''','''        String imageMime = copiedImage;
        if (imageMime != null) {
            if (prefs.clipboardImages()) saveClipImage(first.getUri(), imageMime);''','image mime')
p.write_text(s)
print('Patched direct photo clipboard paste into OTP-capable NewSwipe')
