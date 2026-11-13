from pathlib import Path

p=Path("app/src/main/java/com/alternative_studios/newswipe/NewSwipeIME.java")
s=p.read_text(encoding="utf-8")

def one(old,new,reason):
    global s
    n=s.count(old)
    assert n==1,(reason,n)
    s=s.replace(old,new,1)

# The OTP chip previously lived in the toolbar's clipChipSlot.
# v2.2.1 intentionally hides the old slot but forgot to move OTP handling
# into the replacement event-preview row. Reuse the existing click handler
# so we preserve its SMS approval, code entry, focus and expiry safeguards.
one('''        eventCopiedPreview.setOnClickListener(v -> {
            feedback.onToolbar();
            // Clipboard photos and screenshots must use the image URI
            // transfer path, NOT pasteClipChip() (which only handles text).
            if (quickImageReady()) {
                pasteQuickImage();
            } else {
                pasteClipChip();
            }
        });''',
'''        eventCopiedPreview.setOnClickListener(v -> {
            if (otpReady()) {
                // Delegate to the original tested OTP chip action. It handles
                // an available code OR a pending SMS User Consent dialog.
                if (clipChip != null) clipChip.performClick();
                return;
            }
            feedback.onToolbar();
            if (quickImageReady()) {
                pasteQuickImage();
            } else {
                pasteClipChip();
            }
        });''',
"restore OTP-specific action on new preview bar")

one('''        boolean image = panel == PANEL_KEYBOARD && quickImageReady();
        boolean inline = panel == PANEL_KEYBOARD && !image && autofillShowing()
                && !candidatesVisible;
        boolean copied = panel == PANEL_KEYBOARD && !image && !inline && clipChipShowing();
        if (autofillBar != null) autofillBar.setVisibility(inline ? View.VISIBLE : View.GONE);
        if (image) {
            eventCopiedPreview.setText("사진 붙여넣기");
            eventCopiedPreview.setCompoundDrawablePadding(Ui.dp(this, 8));
            eventCopiedPreview.setContentDescription("최근 복사한 이미지 또는 캡처 사진 붙여넣기");
        } else if (copied) {''',
'''        // OTP is a form of autofill. It must remain available in numeric
        // editors even when regular text suggestions are disabled.
        // The legacy OTP button was hidden when v2.2.1 added this row.
        boolean otp = panel == PANEL_KEYBOARD && !candidatesVisible && otpReady();
        boolean image = !otp && panel == PANEL_KEYBOARD && quickImageReady();
        boolean inline = !otp && panel == PANEL_KEYBOARD && !image && autofillShowing()
                && !candidatesVisible;
        boolean copied = panel == PANEL_KEYBOARD && !otp && !image
                && !inline && clipChipShowing();
        if (autofillBar != null) autofillBar.setVisibility(inline ? View.VISIBLE : View.GONE);
        if (otp) {
            String current = OtpCodeSession.fresh();
            if (current == null) current = otpCode;
            boolean approval = current == null && otpConsentIntent != null;
            eventCopiedPreview.setText(approval
                    ? "문자 인증번호 확인 · 탭하여 승인"
                    : current == null ? "인증번호 자동 입력" : "인증번호 " + current + " · 탭하여 입력");
            eventCopiedPreview.setContentDescription(approval
                    ? "문자 인증번호 사용 승인"
                    : "수신된 인증번호를 입력란에 자동 입력");
        } else if (image) {
            eventCopiedPreview.setText("사진 붙여넣기");
            eventCopiedPreview.setCompoundDrawablePadding(Ui.dp(this, 8));
            eventCopiedPreview.setContentDescription("최근 복사한 이미지 또는 캡처 사진 붙여넣기");
        } else if (copied) {''',
"add OTP as priority in event row without breaking copied image/text/inline autofill")

one('''        eventCopiedPreview.setVisibility(image || copied ? View.VISIBLE : View.GONE);
        // A second row must ONLY appear for copied text, copied photo/
        // screenshot, or a real inline Autofill suggestion.
        int next = (inline || image || copied) ? View.VISIBLE : View.GONE;''',
'''        eventCopiedPreview.setVisibility(otp || image || copied ? View.VISIBLE : View.GONE);
        // Only SMS OTP autofill, normal inline autofill, or newly copied
        // text/photo can show the second row. Word suggestions cannot.
        int next = (otp || inline || image || copied) ? View.VISIBLE : View.GONE;''',
"show event row only for OTP, autofill, or clipboard events")

p.write_text(s,encoding="utf-8")
checks=[
 'boolean otp = panel == PANEL_KEYBOARD && !candidatesVisible && otpReady();',
 'if (clipChip != null) clipChip.performClick();',
 'int next = (otp || inline || image || copied) ? View.VISIBLE : View.GONE;',
 'eventCopiedPreview.setVisibility(otp || image || copied ? View.VISIBLE : View.GONE);',
 'String current = OtpCodeSession.fresh();',
 'if (quickImageReady()) {',
 'pasteQuickImage();',
 'pasteClipChip();',
 'eventPreviewRow.setVisibility(View.GONE);',
]
src=p.read_text(encoding="utf-8")
for check in checks: assert check in src,check
assert "otpReady()" in src and "otpConsentIntent" in src
assert '|| autofillShowing()' in src
assert 'return sp.getBoolean' not in src
print("NewSwipe 2.2.4: restore OTP suggestion/consent and tap-to-fill in conditional row; image, text, Samsung Pass maintained.")
