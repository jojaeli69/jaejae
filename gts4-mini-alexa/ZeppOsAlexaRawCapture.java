/*
 * Experimental GTS 4 mini Alexa BLE capture helper.
 * Copyright (c) 2026. AGPL-3.0-or-later, matching Gadgetbridge.
 * Explicitly opt-in one-shot capture; saves unmodified 0x05 BLE frames.
 * NOT PCM. Does not call undocumented watch recorder or upload data.
 */
package nodomain.freeyourgadget.gadgetbridge.service.devices.huami.zeppos.services;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;

final class ZeppOsAlexaRawCapture {
    static final byte[] MAGIC = "G4MVBLE1".getBytes(StandardCharsets.US_ASCII);
    static final long MAX_DURATION_MS = 20_000L;
    static final int MAX_PACKET_BYTES = 4096;
    static final int MAX_SESSION_BYTES = 2 * 1024 * 1024;

    private boolean armed;
    private boolean running;
    private boolean pendingExport;
    private FileOutputStream output;
    private File outputFile;
    private long startMs;
    private int frameCount;
    private int byteCount;
    private String lastResult = "idle";

    synchronized void armOnce() {
        closeAndDiscard();
        armed = true;
        lastResult = "ARMED for next Alexa session";
    }
    synchronized boolean isArmed() { return armed; }
    synchronized boolean isRunning() { return running; }
    synchronized String getLastResult() { return lastResult; }

    synchronized boolean onAlexaStart(final File dir, final long now) {
        if (!armed) return false;
        armed = false;
        closeAndDiscard();
        if (dir == null || (!dir.exists() && !dir.mkdirs()) || !dir.isDirectory()) {
            lastResult = "Cannot create capture directory";
            return false;
        }
        try {
            outputFile = File.createTempFile("gtsmini-alexa-" + now + "-", ".g4mv", dir);
            output = new FileOutputStream(outputFile);
            output.write(MAGIC);
            put64(now);
            startMs = now;
            frameCount = 0;
            byteCount = 0;
            running = true;
            pendingExport = false;
            lastResult = "WAITING for voice packets";
            return true;
        } catch (IOException e) {
            closeAndDiscard();
            lastResult = "Unable to create local file";
            return false;
        }
    }

    synchronized boolean onVoiceData(final byte[] bytes, final long now) {
        if (!running || output == null) return false;
        if (bytes == null || bytes.length < 2 || (bytes[0] & 255) != 5) return false;
        if (now < startMs || now - startMs > MAX_DURATION_MS ||
                bytes.length > MAX_PACKET_BYTES || byteCount + bytes.length > MAX_SESSION_BYTES) {
            finish("limit reached");
            return false;
        }
        try {
            put32(bytes.length);
            put64(now - startMs);
            output.write(bytes);
            frameCount++;
            byteCount += bytes.length;
            lastResult = "Frames " + frameCount + " bytes " + byteCount;
            return true;
        } catch (IOException e) {
            closeAndDiscard();
            lastResult = "Local storage write failed";
            return false;
        }
    }

    synchronized File onAlexaEnd() {
        if (running) finish("Alexa ended");
        if (pendingExport && outputFile != null) {
            pendingExport = false;
            return outputFile;
        }
        return null;
    }

    private void finish(final String reason) {
        if (!running) return;
        running = false;
        closeOutput();
        if (frameCount == 0) {
            if (outputFile != null) outputFile.delete();
            outputFile = null;
            pendingExport = false;
            lastResult = "NO VOICE FRAMES";
        } else {
            pendingExport = true;
            lastResult = reason + ": " + frameCount + " raw frames, codec unknown";
        }
    }
    private void closeOutput() {
        if (output != null) {
            try { output.flush(); output.close(); } catch (IOException ignored) {}
            output = null;
        }
    }
    private void closeAndDiscard() {
        running = false;
        pendingExport = false;
        closeOutput();
        if (outputFile != null) { outputFile.delete(); outputFile = null; }
        frameCount = 0;
        byteCount = 0;
    }
    private void put32(int n) throws IOException {
        for (int i = 0; i < 4; i++) output.write((n >>> (8 * i)) & 255);
    }
    private void put64(long n) throws IOException {
        for (int i = 0; i < 8; i++) output.write((int) ((n >>> (8 * i)) & 255));
    }
}
