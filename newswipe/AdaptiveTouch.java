package com.alternative_studios.newswipe.keyboard;

import android.content.Context;
import android.content.SharedPreferences;
import android.os.SystemClock;

/**
 * Optional local adaptation of effective hit boundaries.
 *
 * Learns only from an immediately followed Backspace + different adjacent key.
 * No text strings, sequences or touch coordinates are persisted: only bounded
 * aggregate horizontal offsets and sample counts for each key in a layout.
 * Never changes visible key geometry or special-key hit areas.
 */
public final class AdaptiveTouch {
    public static final String PREF_ENABLED = "adaptive_touch_enabled";
    private static final String PREF_FILE = "newswipe_touch_bias";
    private static final float MAX_BOUNDARY_SHIFT = 0.11f;
    private static final int MIN_SAMPLES = 4;
    private static final int MAX_SAMPLES = 96;
    private final SharedPreferences settings;
    private final SharedPreferences saved;
    private boolean eligible;
    private boolean enabled;

    private Key lastKey;
    private float lastX;
    private int lastKind;
    private long lastTapAt;
    private Key pendingWrong;
    private float wrongX;
    private int wrongKind;
    private long deletedAt;

    public AdaptiveTouch(Context context) {
        settings = context.getSharedPreferences("settings", Context.MODE_PRIVATE);
        saved = context.getSharedPreferences(PREF_FILE, Context.MODE_PRIVATE);
        enabled = settings.getBoolean(PREF_ENABLED, true);
        eligible = enabled;
    }

    public void setActive(boolean on) {
        enabled = settings.getBoolean(PREF_ENABLED, true);
        eligible = enabled && on;
        clearRecent();
    }

    public void clearRecent() {
        lastKey = null;
        pendingWrong = null;
    }

    public static void reset(Context context) {
        context.getSharedPreferences(PREF_FILE, Context.MODE_PRIVATE).edit().clear().apply();
    }

    private static boolean letter(Key k) {
        if (k == null || k.type != Key.CHAR || k.output == null || k.output.length() != 1) return false;
        char c = k.output.charAt(0);
        return Character.isLetter(c) || (c >= 'ㄱ' && c <= 'ㅣ');
    }

    private static String name(int kind, Key key) {
        // No typed words or contents ever saved. Only layout + physical key label.
        return kind + "_" + Integer.toHexString(key.output.charAt(0));
    }

    private float learned(Key key, int kind) {
        String name = name(kind, key);
        int count = saved.getInt(name + "_n", 0);
        return count < MIN_SAMPLES ? 0f : saved.getFloat(name + "_x", 0f);
    }

    /** Apply small bounded adjustments only at boundaries between adjacent letter keys. */
    public Key choose(Key base, KeyboardLayout.Row row, float x, int kind) {
        if (!eligible || !letter(base) || row == null) return base;
        int at = -1;
        for (int i = 0; i < row.keys.length; i++) {
            if (row.keys[i] == base) { at = i; break; }
        }
        if (at < 0) return base;
        Key candidate = base;
        // Evaluate each immediate physical neighbor. Hidden keys and special keys excluded.
        for (int step : new int[]{-1, 1}) {
            int near = at + step;
            if (near < 0 || near >= row.keys.length) continue;
            Key other = row.keys[near];
            if (!letter(other) || other.rect.width() < 1 || base.rect.width() < 1) continue;
            float sharedEdge = step < 0 ? base.rect.left : base.rect.right;
            float minWidth = Math.min(base.rect.width(), other.rect.width());
            float delta = (learned(base,kind)*base.rect.width()
                    + learned(other,kind)*other.rect.width())*.5f;
            delta = Math.max(-minWidth*MAX_BOUNDARY_SHIFT,
                    Math.min(minWidth*MAX_BOUNDARY_SHIFT, delta));
            float shiftedEdge = sharedEdge + delta;
            if (step < 0 && x < shiftedEdge && x >= sharedEdge
                    && delta > 0) candidate = other;
            if (step < 0 && x >= shiftedEdge && x < sharedEdge
                    && delta < 0) candidate = base; // keep base
            if (step > 0 && x >= shiftedEdge && x < sharedEdge
                    && delta < 0) candidate = other;
            // Boundary also moves into the neighbor; base should expand there.
            if (step < 0 && x < sharedEdge && x >= shiftedEdge
                    && delta < 0) candidate = base;
            if (step > 0 && x >= sharedEdge && x < shiftedEdge
                    && delta > 0) candidate = base;
        }
        // If the standard hit box selects the neighbor, apply inverse adjustment.
        // The loop above handles the expanded region for the base; no special keys.
        return candidate;
    }

    /**
     * Registered at tap release, after the IME processed the key.
     * Backspace + adjacent replacement is a weak but useful correction signal.
     */
    public void onTap(Key key, float x, int kind) {
        if (!eligible) return;
        long now = SystemClock.uptimeMillis();
        if (key.type == Key.DELETE) {
            if (lastKey != null && now-lastTapAt < 1800) {
                pendingWrong = lastKey;
                wrongX = lastX;
                wrongKind = lastKind;
                deletedAt = now;
            } else pendingWrong = null;
            lastKey = null;
            return;
        }
        if (letter(key)) {
            if (pendingWrong != null && wrongKind == kind && now-deletedAt < 2000
                    && pendingWrong != key && letter(pendingWrong)) {
                learn(pendingWrong, key, wrongX, kind);
            }
            pendingWrong = null;
            lastKey = key;
            lastX = x;
            lastKind = kind;
            lastTapAt = now;
        } else {
            clearRecent();
        }
    }

    private void learn(Key mistaken, Key intended, float x, int kind) {
        // Restrict to same row and adjacent character positions only.
        float rowDistance = Math.abs(mistaken.rect.centerY()-intended.rect.centerY());
        float height = Math.min(mistaken.rect.height(), intended.rect.height());
        float distance = Math.abs(mistaken.rect.centerX()-intended.rect.centerX());
        float width = Math.min(mistaken.rect.width(), intended.rect.width());
        if (rowDistance > height*.25f || distance > width*1.45f || width < 5) return;
        float normalized = (x-intended.rect.centerX())/intended.rect.width();
        // Only samples near the intended key's border suggest a mistouch.
        if (Math.abs(normalized) < .38f || Math.abs(normalized) > .83f) return;
        normalized = Math.max(-.5f, Math.min(.5f, normalized));
        String name = name(kind, intended);
        int count = Math.min(MAX_SAMPLES, saved.getInt(name + "_n", 0)+1);
        float previous = saved.getFloat(name + "_x", 0f);
        // EMA learns gradually; change the effective boundary by at most 11%.
        float next = previous*.80f + normalized*.20f;
        saved.edit().putInt(name+"_n",count).putFloat(name+"_x",next).apply();
    }
}
