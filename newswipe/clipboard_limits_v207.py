from pathlib import Path

root = Path("app/src/main/java/com/alternative_studios/newswipe")
history = root/"clipboard/ClipboardHistory.java"
s = history.read_text(encoding="utf-8")

def one(old, new, label):
    global s
    count = s.count(old)
    assert count == 1, (label, count)
    s = s.replace(old, new, 1)

one(''' * 클립보드 기록. 최근 30개(그중 이미지는 5개)를 앱 전용 저장소에 보관하고,
 * 고정하지 않은 항목은 24시간이 지나면 지운다.''',
''' * 클립보드 기록. 전체 최대 50개(고정 항목 포함, 그중 이미지는 최대 5개)를 앱 전용 저장소에 보관하고,
 * 고정하지 않은 항목은 120시간(5일)이 지나면 지운다.''', "history docs")

one('''    public static final int MAX_ITEMS = 30;
    public static final long EXPIRE_MS = 24L * 60 * 60 * 1000;''',
'''    /** 고정 항목을 포함해 전체 클립보드 기록 최대 50개. */
    public static final int MAX_ITEMS = 50;
    /** 고정하지 않은 항목은 120시간(5일) 후 자동 삭제. */
    public static final long EXPIRE_MS = 120L * 60 * 60 * 1000;''', "history limits")

one('''     * 이미지는 고정하지 않은 것 중 최근 MAX_IMAGES개만 남기고, MAX_ITEMS에도 함께 센다.''',
'''     * 이미지는 고정하지 않은 것 중 최근 MAX_IMAGES개만 남긴다.
     * 전체 MAX_ITEMS에는 고정 항목까지 포함하여 50개를 넘지 않게 한다.''', "trim docs")

one('''        int unpinned = 0;
        int images = 0;
        for (int i = 0; i < items.size(); i++) {''',
'''        int unpinned = 0;
        int images = 0;
        // Fixed items must count against the overall 50-slot quota.
        // Preserve already-pinned entries ahead of ordinary history.
        final int maxUnpinned = Math.max(0, MAX_ITEMS - pinnedCount());
        for (int i = 0; i < items.size(); i++) {''', "cap includes pins")

one('''            if (now - it.time > EXPIRE_MS || unpinned >= MAX_ITEMS || it.isImage() && images >= MAX_IMAGES) {''',
'''            if (now - it.time > EXPIRE_MS || unpinned >= maxUnpinned
                    || (it.isImage() && images >= MAX_IMAGES)) {''', "trim quota")

history.write_text(s, encoding="utf-8")

settings = root/"SettingsActivity.java"
s = settings.read_text(encoding="utf-8")
assert s.count('고정하지 않은 항목은 24시간 뒤 지워집니다.')==1
s=s.replace('고정하지 않은 항목은 24시간 뒤 지워집니다.',
            '고정하지 않은 항목은 120시간(5일) 뒤 지워집니다.',1)
settings.write_text(s, encoding="utf-8")

panel=root/"clipboard/ClipboardPanel.java"
s=panel.read_text(encoding="utf-8")
assert s.count('"개)이며, 24시간 후 삭제됩니다. 핀 버튼으로 최대 "')==1
s=s.replace('"개)이며, 24시간 후 삭제됩니다. 핀 버튼으로 최대 "',
            '"개)입니다. 고정하지 않은 항목은 120시간(5일) 후 삭제되며, 최대 "',1)
# Existing concatenation concludes with "개까지 고정..." and now reads as intended.
s=s.replace('"개까지 고정할 수 있습니다.";', '"개까지 고정할 수 있습니다.";',1)
panel.write_text(s, encoding="utf-8")

ime=root/"NewSwipeIME.java"
s=ime.read_text(encoding="utf-8")
if s.count('24시간이 지난 클립보드 항목'):
    s=s.replace('24시간이 지난 클립보드 항목','120시간이 지난 클립보드 항목',1)
ime.write_text(s,encoding="utf-8")

assert 'MAX_ITEMS = 50' in history.read_text(encoding="utf-8")
assert 'EXPIRE_MS = 120L * 60 * 60 * 1000' in history.read_text(encoding="utf-8")
assert 'maxUnpinned = Math.max(0, MAX_ITEMS - pinnedCount())' in history.read_text(encoding="utf-8")
assert '24시간 후 삭제' not in panel.read_text(encoding="utf-8")
print("Clipboard history set to 50 entries including pinned, with 120-hour expiry for unpinned items. Image limit remains 5.")
