package com.alternative_studios.newswipe.keyboard;

import android.content.Context;
import android.content.SharedPreferences;
import android.content.res.Configuration;
import android.os.SystemClock;

/**
 * Stable, on-device, privacy-preserving adaptive hit testing.
 *
 * A correction is observed only when an adjacent letter is typed immediately
 * after Backspace; only corrections physically close to their common border
 * contribute. Each key pair has ONE shared boundary so keys cannot overlap,
 * drift apart or become visually unequal. Drawing geometry is never modified.
 */
public final class AdaptiveTouch {
    public static final String PREF_ENABLED = "adaptive_touch_enabled";
    private static final String PREF_FILE = "newswipe_touch_bias_v202";
    private static final int MAX_OBSERVATIONS = 96;
    private static final long DELETE_WINDOW_MS = 1600L;
    private static final long REPLACE_WINDOW_MS = 1800L;

    private final Context context;
    private final SharedPreferences settings;
    private final SharedPreferences saved;
    private boolean active;
    private Key last;
    private float lastX;
    private int lastKind;
    private long lastTime;
    private Key erased;
    private float erasedX;
    private int erasedKind;
    private long erasedAt;

    public AdaptiveTouch(Context context) {
        this.context = context.getApplicationContext();
        this.settings = context.getSharedPreferences("settings", Context.MODE_PRIVATE);
        this.saved = context.getSharedPreferences(PREF_FILE, Context.MODE_PRIVATE);
        setActive(true);
    }

    public void setActive(boolean fieldAllowsLearning) {
        active = fieldAllowsLearning && settings.getBoolean(PREF_ENABLED, true);
        clearRecent();
    }

    public void clearRecent() {
        last = null;
        erased = null;
    }

    public static void reset(Context context) {
        context.getSharedPreferences(PREF_FILE, Context.MODE_PRIVATE).edit().clear().apply();
        // Clear v2.0.1's obsolete one-sided bias record as well.
        context.getSharedPreferences("newswipe_touch_bias", Context.MODE_PRIVATE)
                .edit().clear().apply();
    }

    private static boolean letter(Key key) {
        return key != null && key.type == Key.CHAR
                && key.output != null && key.output.length() == 1
                && Character.isLetter(key.output.charAt(0)) && !key.isHidden();
    }

    /** Store only layout kind + orientation + adjacent key IDs; never typed text. */
    private String pairId(Key left, Key right, int layoutKind) {
        int orientation = context.getResources().getConfiguration().orientation;
        return orientation + "_" + layoutKind + "_"
                + Integer.toHexString(left.output.charAt(0)) + "_"
                + Integer.toHexString(right.output.charAt(0));
    }

    private float border(Key left, Key right) {
        return (left.rect.right + right.rect.left) * .5f;
    }

    private float delta(Key left, Key right, int layoutKind) {
        String prefix = pairId(left, right, layoutKind);
        int evidence = saved.getInt(prefix + "_count", 0);
        float direction = saved.getFloat(prefix + "_score", 0f);
        float width = Math.min(left.rect.width(), right.rect.width());
        return TouchBiasMath.offset(direction, evidence, width);
    }

    /**
     * Resolve the exact same border from both sides.
     *
     * Only a narrow strip (at most 10% of a key) can change its interpretation.
     * Key rectangles/labels/fonts/row geometry stay precisely as designed.
     */
    public Key choose(Key base, KeyboardLayout.Row row, float x, int kind) {
        if (!active || !letter(base) || row == null) return base;
        Key[] keys = row.keys;
        int at = -1;
        for (int i = 0; i < keys.length; ++i) {
            if (keys[i] == base) { at = i; break; }
        }
        if (at < 0) return base;
        for (int neighbor = Math.max(0, at - 1);
             neighbor <= Math.min(keys.length - 1, at + 1); neighbor++) {
            if (neighbor == at || Math.abs(neighbor - at) != 1) continue;
            Key other = keys[neighbor];
            if (!letter(other)) continue;
            Key left = neighbor < at ? other : base;
            Key right = neighbor < at ? base : other;
            float gap = right.rect.left - left.rect.right;
            float smallestWidth = Math.min(left.rect.width(), right.rect.width());
            if (smallestWidth < 5f || gap > smallestWidth * .22f) continue;
            float original = border(left, right);
            float shift = delta(left, right, kind);
            if (TouchBiasMath.inChangedStrip(x, original, shift)) {
                return TouchBiasMath.onRight(x, original, shift) ? right : left;
            }
        }
        return base;
    }

    /**
     * Only physical tap events are observed. No text, sentence, clipboard,
     * password, raw touch history or word sequence is stored.
     */
    public void onTap(Key key, float x, int layoutKind) {
        if (!active || key == null) return;
        long now = SystemClock.uptimeMillis();
        if (key.type == Key.DELETE) {
            if (last != null && now - lastTime <= DELETE_WINDOW_MS) {
                erased = last;
                erasedX = lastX;
                erasedKind = lastKind;
                erasedAt = now;
            } else {
                erased = null;
            }
            last = null;
            return;
        }
        if (!letter(key)) {
            clearRecent();
            return;
        }
        if (erased != null && layoutKind == erasedKind
                && erased != key && now - erasedAt <= REPLACE_WINDOW_MS) {
            recordCorrection(erased, key, erasedX, layoutKind);
        }
        erased = null;
        last = key;
        lastX = x;
        lastTime = now;
        lastKind = layoutKind;
    }

    private void recordCorrection(Key mistaken, Key intended, float rawX, int kind) {
        // Reject deletes followed by arbitrary letters and non-adjacent keys.
        float h = Math.min(mistaken.rect.height(), intended.rect.height());
        float w = Math.min(mistaken.rect.width(), intended.rect.width());
        if (h < 5f || w < 5f
                || Math.abs(mistaken.rect.centerY() - intended.rect.centerY()) > h * .24f) {
            return;
        }
        Key left = mistaken.rect.centerX() < intended.rect.centerX() ? mistaken : intended;
        Key right = left == mistaken ? intended : mistaken;
        float spacing = right.rect.left - left.rect.right;
        float centerDistance = right.rect.centerX() - left.rect.centerX();
        if (spacing > w * .22f || centerDistance > w * 1.40f) return;

        float edge = border(left, right);
        // Only touches right around the shared border suggest a true mistap.
        // An intentional delete/rewrite from the middle of a key is ignored.
        if (Math.abs(rawX - edge) > w * .22f) return;

        // Wrong left -> intended right: shift border left. Reverse is positive.
        int direction = mistaken == left ? -1 : +1;
        String name = pairId(left, right, kind);
        float old = saved.getFloat(name + "_score", 0f);
        int observations = Math.min(MAX_OBSERVATIONS,
                saved.getInt(name + "_count", 0) + 1);
        float newScore = TouchBiasMath.accumulate(old, direction);
        saved.edit().putInt(name + "_count", observations)
                .putFloat(name + "_score", newScore).apply();
    }
}
