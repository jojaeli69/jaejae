package com.alternative_studios.newswipe.keyboard;

/**
 * Pure and deterministic math for balanced learned touch boundaries.
 *
 * The rendered keys NEVER change size, padding, center, height, row position,
 * or relative proportions. Adjacent keys share one reversible boundary.
 */
public final class TouchBiasMath {
    public static final int MIN_EVIDENCE = 4;
    public static final float MAX_FRACTION = 0.10f;
    private TouchBiasMath() {}

    public static float clamp(float n, float low, float high) {
        return Math.max(low, Math.min(high, n));
    }

    /** A low-confidence correction only changes the boundary by a fraction of a pixel. */
    public static float offset(float score, int observations, float smallerKeyWidth) {
        if (observations < MIN_EVIDENCE || smallerKeyWidth <= 0) return 0f;
        float confidence = clamp((observations - MIN_EVIDENCE + 1) / 12f, 0f, 1f);
        return clamp(score, -1f, 1f) * confidence * MAX_FRACTION * smallerKeyWidth;
    }

    public static float accumulate(float oldScore, int direction) {
        if (direction != -1 && direction != 1) return clamp(oldScore, -1f, 1f);
        return clamp(oldScore * 0.92f + direction * 0.08f, -1f, 1f);
    }

    /**
     * Is x in the ONLY region affected by shifting a shared border?
     * Returns false for all taps elsewhere in the key.
     */
    public static boolean inChangedStrip(float x, float originalBorder, float delta) {
        if (delta == 0f) return false;
        float adjusted = originalBorder + delta;
        return x >= Math.min(originalBorder, adjusted)
                && x < Math.max(originalBorder, adjusted);
    }

    public static boolean onRight(float x, float originalBorder, float delta) {
        return x >= originalBorder + delta;
    }
}
