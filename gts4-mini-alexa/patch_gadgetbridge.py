#!/usr/bin/env python3
"""Patch pinned Gadgetbridge 0.83.0 mirror to capture opt-in Alexa BLE raw packets.
No firmware modification, no microphone start call; on-device Alexa is started manually.
"""
import argparse
from pathlib import Path
import shutil

SERVICE = Path("app/src/main/java/nodomain/freeyourgadget/gadgetbridge/service/devices/huami/zeppos/services/ZeppOsAlexaService.java")
SETTINGS = Path("app/src/main/res/xml/devicesettings_huami2021_alexa.xml")
COORDINATOR = Path("app/src/main/java/nodomain/freeyourgadget/gadgetbridge/devices/huami/zeppos/ZeppOsCoordinator.java")
CUSTOMIZER = Path("app/src/main/java/nodomain/freeyourgadget/gadgetbridge/devices/huami/zeppos/ZeppOsSettingsCustomizer.java")

def replace_once(s, before, after):
    count = s.count(before)
    if count != 1:
        raise RuntimeError("Patch anchor mismatch: " + repr(before[:100]) + " occurrences=" + str(count))
    return s.replace(before, after)

def patch_java(s):
    s = replace_once(s, "import android.os.Handler;", """import android.os.Handler;
import android.os.Build;
import android.os.Environment;
import android.content.ContentValues;
import android.net.Uri;
import android.provider.MediaStore;
import java.io.FileInputStream;
import java.io.InputStream;
import java.io.OutputStream;""")
    s = replace_once(s,
        "    final ByteArrayOutputStream voiceBuffer = new ByteArrayOutputStream();",
        """    final ByteArrayOutputStream voiceBuffer = new ByteArrayOutputStream();

    // User must explicitly arm capture in Alexa debug settings.
    private final ZeppOsAlexaRawCapture rawCapture = new ZeppOsAlexaRawCapture();""")
    s = replace_once(s,
        '        switch (config) {\n            case DeviceSettingsPreferenceConst.PREF_VOICE_SERVICE_LANGUAGE:',
        '''        switch (config) {
            case "zepp_os_alexa_btn_capture_once":
                rawCapture.armOnce();
                GB.toast("GTS mini: capture armed for next Alexa session", Toast.LENGTH_SHORT, GB.INFO);
                return true;
            case DeviceSettingsPreferenceConst.PREF_VOICE_SERVICE_LANGUAGE:''')
    s = replace_once(s,
        '        LOG.info("Alexa starting: var1={}, var2={}, var3={}, var4={}, params={}", var1, var2, var3, var4, params);',
        '''        LOG.info("Alexa starting: var1={}, var2={}, var3={}, var4={}, params={}", var1, var2, var3, var4, params);
        if (rawCapture.isArmed()) {
            if (rawCapture.onAlexaStart(getContext().getExternalFilesDir("AlexaRawProbe"), System.currentTimeMillis())) {
                LOG.info("GTS mini: voice capture started");
                GB.toast("GTS mini: Alexa BLE capture started", Toast.LENGTH_SHORT, GB.INFO);
            } else {
                LOG.warn("GTS mini: capture failed: {}", rawCapture.getLastResult());
            }
        }''')
    s = replace_once(s,
        '''    private void handleEnd(final byte[] payload) {
        voiceBuffer.reset();
        // TODO do something else?
    }''',
        '''    private void handleEnd(final byte[] payload) {
        final java.io.File capture = rawCapture.onAlexaEnd();
        if (capture != null) {
            boolean exported = exportToDownloads(capture);
            LOG.info("GTS mini Alexa: {} (exported={})", rawCapture.getLastResult(), exported);
            GB.toast(exported ? "GTS mini: raw packets saved in Downloads/GTSmini"
                    : "GTS mini: captured, export unavailable", Toast.LENGTH_LONG, GB.INFO);
        } else if (rawCapture.getLastResult().contains("NO VOICE FRAMES")) {
            GB.toast("GTS mini: NO VOICE FRAMES", Toast.LENGTH_LONG, GB.INFO);
        }
        voiceBuffer.reset();
    }''')
    s = replace_once(s,
        '''    private void handleVoiceData(final byte[] payload) {
        LOG.info("Got {} bytes of voice data", payload.length);
        // TODO
    }''',
        '''    // Export an explicitly requested private raw capture, never to a remote server.
    // G4MVBLE1 is a custom packet container, NOT a playable audio format.
    private boolean exportToDownloads(final java.io.File inputFile) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) return false;
        final ContentValues values = new ContentValues();
        values.put(MediaStore.MediaColumns.DISPLAY_NAME, inputFile.getName());
        values.put(MediaStore.MediaColumns.MIME_TYPE, "application/octet-stream");
        values.put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS + "/GTSmini");
        values.put(MediaStore.MediaColumns.IS_PENDING, 1);
        Uri uri = null;
        try {
            uri = getContext().getContentResolver().insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values);
            if (uri == null) return false;
            try (InputStream in = new FileInputStream(inputFile);
                 OutputStream out = getContext().getContentResolver().openOutputStream(uri)) {
                if (out == null) throw new IOException("Null downloads output stream");
                byte[] block = new byte[8192];
                int len;
                while ((len = in.read(block)) != -1) out.write(block, 0, len);
            }
            final ContentValues done = new ContentValues();
            done.put(MediaStore.MediaColumns.IS_PENDING, 0);
            getContext().getContentResolver().update(uri, done, null, null);
            return true;
        } catch (Exception ex) {
            LOG.warn("GTS mini: raw voice export failure", ex);
            if (uri != null) getContext().getContentResolver().delete(uri, null, null);
            return false;
        }
    }

    private void handleVoiceData(final byte[] payload) {
        // Keep packet framing to permit later independent codec analysis.
        if (rawCapture.isRunning()) rawCapture.onVoiceData(payload, System.currentTimeMillis());
        LOG.debug("Alexa BLE voice packet length {}", payload.length);
    }''')
    return s

def patch_xml(s):
    return replace_once(s,
        '            <Preference\n                android:key="zepp_os_alexa_btn_trigger"',
        '''            <Preference
                android:key="zepp_os_alexa_btn_capture_once"
                android:title="GTS mini: Capture next Alexa voice once"
                android:summary="Opt in once; saves raw packets (not WAV) to Downloads/GTSmini, 20s max" />

            <Preference
                android:key="zepp_os_alexa_btn_trigger"''')

def patch_coordinator(s):
    # Gadgetbridge normally exposes Alexa debug settings only with the experimental
    # flag and a capabilities response. This diagnostic build keeps the Alexa
    # screen available even when capabilities have not yet been negotiated.
    return replace_once(s,
        "        if (supportsAlexa(device)) {\n            developer.add(R.xml.devicesettings_huami2021_alexa);\n        }",
        "        // Diagnostic only: always show Alexa settings for opt-in BLE voice test.\n        developer.add(R.xml.devicesettings_huami2021_alexa);")


def patch_customizer(s):
    # Preference clicks are NOT automatic. Without this registration the
    # new button appears but does nothing.
    return replace_once(s,
        '                handler.findPreference("zepp_os_alexa_btn_trigger"),',
        '                handler.findPreference("zepp_os_alexa_btn_capture_once"),\n'
        '                handler.findPreference("zepp_os_alexa_btn_trigger"),')


def apply(root, dry):
    j = root / SERVICE
    x = root / SETTINGS
    helper = j.parent / "ZeppOsAlexaRawCapture.java"
    coordinator = root / COORDINATOR
    customizer = root / CUSTOMIZER
    assert all(p.exists() for p in (j,x,coordinator,customizer)), "Upstream file paths changed"
    assert not helper.exists(), "Already patched"
    js = patch_java(j.read_text(encoding="utf-8"))
    xs = patch_xml(x.read_text(encoding="utf-8"))
    cs = patch_coordinator(coordinator.read_text(encoding="utf-8"))
    ss = patch_customizer(customizer.read_text(encoding="utf-8"))
    assert "rawCapture.onVoiceData" in js and "capture_once" in xs
    assert 'handler.findPreference("zepp_os_alexa_btn_capture_once")' in ss
    if dry:
        print("PATCH_DRY_RUN_OK: source anchors verified")
        return
    j.write_text(js, encoding="utf-8")
    x.write_text(xs, encoding="utf-8")
    coordinator.write_text(cs, encoding="utf-8")
    customizer.write_text(ss, encoding="utf-8")
    shutil.copy2(Path(__file__).with_name("ZeppOsAlexaRawCapture.java"), helper)
    print("PATCH_OK",j,x,helper,sep="\n")

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("source",type=Path)
    parser.add_argument("--dry-run",action="store_true")
    args=parser.parse_args()
    apply(args.source,args.dry_run)
