package com.alternative_studios.newswipe.keyboard;

public final class TouchBiasMathTest {
    private static void require(boolean condition, String why) {
        if (!condition) throw new AssertionError(why);
    }

    private static void close(float actual, float expected, String why) {
        require(Math.abs(actual - expected) < .00001f,
                why + ": actual=" + actual + ", expected=" + expected);
    }

    public static void main(String[] args) {
        close(TouchBiasMath.offset(1f, 3, 80), 0f, "no action before evidence");
        close(TouchBiasMath.offset(1f, 4, 80), 8f/12f, "gentle early learning");
        close(TouchBiasMath.offset(-1f, 25, 80), -8f, "negative cap");
        close(TouchBiasMath.offset(1f, 25, 80), 8f, "positive cap");
        close(TouchBiasMath.offset(200f, 96, 80), 8f, "strict maximum ten percent");
        close(TouchBiasMath.offset(-200f, 96, 80), -8f, "strict negative maximum");
        close(TouchBiasMath.offset(1f, 96, 0), 0f, "no invalid dimension");
        float center = 100f, left = -8f, right = 8f;
        require(TouchBiasMath.inChangedStrip(96f, center, left), "left border is adjusted");
        require(TouchBiasMath.onRight(96f, center, left), "left shift gives room to right key");
        require(TouchBiasMath.inChangedStrip(104f, center, right), "right border is adjusted");
        require(!TouchBiasMath.onRight(104f, center, right), "right shift gives room to left key");
        require(!TouchBiasMath.inChangedStrip(50f, center, left), "no changes to key center");
        require(!TouchBiasMath.inChangedStrip(150f, center, right), "no changes away from border");
        require(!TouchBiasMath.inChangedStrip(100f, center, 0f), "zero correction is inert");
        require(TouchBiasMath.accumulate(0f, -1) < 0f, "left-to-right fix shifts left");
        require(TouchBiasMath.accumulate(0f, +1) > 0f, "right-to-left fix shifts right");
        require(TouchBiasMath.accumulate(.7f, -1) < .7f, "opposite corrections rebalance");
        System.out.println("Balanced adaptive touch: 16 edge, confidence, symmetry and proportion checks passed");
    }
}
