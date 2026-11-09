package com.alternative_studios.newswipe.clipboard;

import java.io.File;
import java.nio.file.Files;
import java.util.List;

/** JVM integration checks for persisted clipboard history and retention. */
public final class ClipboardLimitsTest {
    private static void require(boolean yes, String reason) {
        if (!yes) throw new AssertionError(reason);
    }

    private static boolean contains(List<ClipboardHistory.Item> entries, String content) {
        for (ClipboardHistory.Item entry : entries)
            if (content.equals(entry.text)) return true;
        return false;
    }

    public static void main(String[] args) throws Exception {
        long now = 1_800_000_000_000L;
        long hour = 60L * 60 * 1000;
        require(ClipboardHistory.MAX_ITEMS == 50, "expected total 50 slots");
        require(ClipboardHistory.EXPIRE_MS == 120 * hour, "expected 120-hour retention");

        File dir = Files.createTempDirectory("newswipe-clip-tests").toFile();
        ClipboardHistory noPins = new ClipboardHistory(new File(dir, "normal.txt"));
        for (int i = 0; i < 60; i++) noPins.add("item-" + i, now + i);
        List<ClipboardHistory.Item> list = noPins.items(now + 60);
        require(list.size() == 50, "must keep 50 most recent text entries");
        require(contains(list, "item-59") && !contains(list,"item-0"),
                "must trim oldest text records");
        noPins.release();
        require(noPins.items(now + 60).size() == 50, "50 items persist to disk");

        ClipboardHistory pins = new ClipboardHistory(new File(dir, "pins.txt"));
        for (int i = 0; i < 10; i++) pins.add("pin-" + i, now + i);
        for (int i = 0; i < 10; i++) {
            ClipboardHistory.Item selected = null;
            for (ClipboardHistory.Item e: pins.items(now + 100))
                if (e.text.equals("pin-" + i)) selected = e;
            require(selected != null && pins.setPinned(selected, true), "pin failed");
        }
        for (int i = 0; i < 60; i++) pins.add("normal-" + i, now + 100 + i);
        list = pins.items(now + 160);
        require(list.size() == 50, "pinned records should count within total 50");
        int pinned = 0;
        for (ClipboardHistory.Item item : list) if (item.pinned) pinned++;
        require(pinned == 10, "all ten pinned entries retained");
        require(contains(list, "normal-59") && !contains(list,"normal-0"),
                "normal entries must yield to pinned entries");

        ClipboardHistory expires = new ClipboardHistory(new File(dir, "expiry.txt"));
        expires.add("120h", now);
        require(contains(expires.items(now + 119*hour), "120h"),
                "keep entry at 119 hours");
        require(contains(expires.items(now + 120*hour), "120h"),
                "keep entry until end of 120th hour");
        require(!contains(expires.items(now + 120*hour + 1), "120h"),
                "expire immediately after 120 hours");

        ClipboardHistory pinnedExpiry = new ClipboardHistory(new File(dir,"pin-expiry.txt"));
        pinnedExpiry.add("important",now);
        require(pinnedExpiry.setPinned(pinnedExpiry.items(now).get(0),true), "pin important");
        require(contains(pinnedExpiry.items(now + 150*hour), "important"),
                "pinned entry should survive 5-day expiry");

        System.out.println("Clipboard retention test passed: 50 total including pins, 120 hours, persistence, pinned exceptions");
    }
}
