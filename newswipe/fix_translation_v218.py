from pathlib import Path
pkg=Path("app/src/main/java/com/alternative_studios/newswipe")
panel=pkg/"KeyboardTranslatePanel.java"
ime=pkg/"NewSwipeIME.java"

def patch(path, before, after, label):
    source=path.read_text(encoding="utf-8")
    n=source.count(before)
    assert n==1,(label,n)
    path.write_text(source.replace(before,after,1),encoding="utf-8")

# V2.0.0 tried to infer a touch on the host editor from onUpdateSelection.
# Android IMEs also receive delayed/stale selection updates during composition
# and when the host app adjusts the cursor. This wrongly switches the keyboard
# into host editing, so the same keys stop entering the translator.
patch(ime,
'''        // Touching or selecting previously translated English in the host editor
        // automatically releases the keys back to normal editing, without closing
        // the translation controls. Ignore startup/composition transient updates.
        if (translationInputMode() && newSelStart >= 0 && newSelEnd >= 0
                && (newSelStart != oldSelStart || newSelEnd != oldSelEnd)
                && android.os.SystemClock.uptimeMillis() - translationOpenedAt > 400
                && candidatesStart < 0 && candidatesEnd < 0) {
            translationEditingHost = true;
            translationPanel.setHostEditing(true);
        }''',
'''        // Do NOT auto-switch the keyboard to host editing on a selection
        // notification. On One UI, some editors deliver these notifications
        // asynchronously while the translator is focused. The old heuristic
        // silently stole all subsequent typing from the translation sheet.
        // The explicit "본문 수정" action and translation-result commit still
        // switch to host editing safely when the user requests it.''',
"accidental translation input loss on selection events")

# Keep a failed-to-insert result available through a deliberate copy action;
# never silently discard the result or overwrite the user's clipboard.
patch(panel,
'''    private int generation;
    private boolean translating;''',
'''    private int generation;
    private boolean translating;
    private String pendingCopyResult;''',
"pending failed insertion text")

patch(panel,
'''        generation++;
        translating=false;
        submitButton.setEnabled(true);
        if(translator!=null) {''',
'''        generation++;
        translating=false;
        pendingCopyResult = null;
        submitButton.setText("번역");
        submitButton.setEnabled(true);
        if(translator!=null) {''',
"reset copy state on new source or panel close")

patch(panel,
'''    public void onEnter() {
        flushHangul();
        String input=source();''',
'''    public void onEnter() {
        if (pendingCopyResult != null) {
            try {
                ClipboardManager clipboard = (ClipboardManager) getContext()
                        .getSystemService(Context.CLIPBOARD_SERVICE);
                if (clipboard == null) throw new IllegalStateException("Clipboard unavailable");
                clipboard.setPrimaryClip(ClipData.newPlainText("NewSwipe 번역 결과", pendingCopyResult));
                status.setText("번역 결과를 복사했어요");
                Toast.makeText(getContext(), "번역 결과 복사 완료 · 입력창에 붙여넣으세요",
                        Toast.LENGTH_LONG).show();
            } catch (RuntimeException error) {
                status.setText("복사 실패");
                Toast.makeText(getContext(), "번역 결과 복사 실패: " + error.getClass().getSimpleName(),
                        Toast.LENGTH_LONG).show();
            }
            return;
        }
        flushHangul();
        String input=source();''',
"copy fallback only when needed")

patch(panel,
'''        status.setText("번역 준비 중 · 최초 사용 시 언어 모델 다운로드");''',
'''        status.setText("번역 언어 모델 확인 중…");
        // The first Korean/English model pair can require an internet download.
        // Do not mandate Wi-Fi: mobile network is allowed by DownloadConditions.''',
"realistic model status")

patch(panel,
'''                            } else {
                                translating=false;
                                submitButton.setEnabled(true);
                                status.setText("원래 입력칸이 바뀌었습니다. 다시 선택해 주세요");
                            }''',
'''                            } else {
                                translating=false;
                                pendingCopyResult = result;
                                submitButton.setText("복사");
                                submitButton.setEnabled(true);
                                status.setText("입력창에 삽입 실패 · 복사 버튼을 눌러주세요");
                                Toast.makeText(getContext(),
                                        "번역은 완료됐지만 입력창에 넣지 못했어요. '복사'를 눌러주세요.",
                                        Toast.LENGTH_LONG).show();
                            }''',
"translation result must remain accessible when commit failed")

patch(panel,
'''                        }).addOnFailureListener(e -> failure(token,"번역 오류 · 다시 시도해 주세요"));
                    })
                    .addOnFailureListener(e -> failure(token,"언어 모델 다운로드 실패 · 인터넷을 확인해 주세요"));
        } catch(RuntimeException | LinkageError e) {
            failure(token,"번역 기능을 실행할 수 없습니다");
        }''',
'''                        }).addOnFailureListener(e -> failure(token,
                                "번역 처리 실패", e));
                    })
                    .addOnFailureListener(e -> failure(token,
                            "언어 모델 다운로드 실패", e));
        } catch(RuntimeException | LinkageError e) {
            failure(token, "번역 기능 초기화 실패", e);
        }''',
"show real ML Kit exception diagnostics")

patch(panel,
'''    private void failure(int token, String message) {
        if(token!=generation)return;
        translating=false;
        status.setText(message);
        submitButton.setEnabled(!source().trim().isEmpty());
        if(translator!=null) {translator.close();translator=null;}
    }''',
'''    /** Show actionable errors instead of hiding a long message in a one-line strip. */
    private void failure(int token, String message, Throwable cause) {
        if (token != generation) return;
        translating = false;
        String detail;
        if (cause instanceof com.google.mlkit.common.MlKitException) {
            int errorCode = ((com.google.mlkit.common.MlKitException) cause).getErrorCode();
            detail = "ML Kit 오류 코드 " + errorCode;
        } else if (cause != null) {
            detail = cause.getClass().getSimpleName();
        } else {
            detail = "알 수 없는 오류";
        }
        String visible = message + " · " + detail;
        android.util.Log.w("NewSwipeTranslate", visible, cause);
        status.setText(visible);
        submitButton.setText("재시도");
        submitButton.setEnabled(!source().trim().isEmpty());
        Toast.makeText(getContext(), visible
                + " · 인터넷과 Google Play 서비스를 확인하고 다시 눌러주세요",
                Toast.LENGTH_LONG).show();
        if (translator != null) {
            translator.close();
            translator = null;
        }
    }''',
"diagnostic errors and retry button")

# A clear visual cue should remain after retry or a newly edited source.
patch(panel,
'''        submitButton.setEnabled(!empty && !translating);
        if (!translating) status.setText(empty''',
'''        submitButton.setEnabled(!empty && !translating);
        if (!translating && pendingCopyResult == null) status.setText(empty''',
"keep pending copy feedback from being overwritten")

p=panel.read_text(encoding="utf-8")
s=ime.read_text(encoding="utf-8")
assert "if (translationInputMode() && newSelStart" not in s
assert "private boolean translationInputMode()" in s
assert 'translationPanel.onTypeText(s, tap, korean && lettersLayout());' in s
assert "void onToggleHostEditing()" in s
assert "pendingCopyResult = result" in p
assert "ML Kit 오류 코드 " in p
assert 'ClipboardManager clipboard = ' in p
assert "com.google.mlkit.nl.translate.Translation" in p
print("NewSwipe 2.1.8: stabilized translation typing, detailed model errors and a copy fallback if insertion fails.")
