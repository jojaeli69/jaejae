package com.alternative_studios.newswipe;

import android.content.Context;
import android.icu.util.ULocale;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.os.CancellationSignal;
import android.view.translation.TranslationManager;
import android.view.translation.TranslationContext;
import android.view.translation.TranslationSpec;
import android.view.translation.TranslationRequest;
import android.view.translation.TranslationRequestValue;
import android.view.translation.TranslationResponse;
import android.view.translation.TranslationResponseValue;
import android.view.translation.Translator;

import java.util.Collections;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;
import java.util.function.Consumer;

/**
 * Optional Android 12+ on-device translation-service bridge.
 *
 * This uses the OS PUBLIC TranslationManager API, not a Samsung-private
 * keyboard API. The OS may use an OEM service; the caller cannot insist
 * that it is Samsung's Galaxy AI Writing Assist.
 * Never uploads text itself, logs source text, or accesses SMS/passwords.
 * If the service is absent, fails, or stalls: report failure so the existing
 * ML Kit translator can be used with the SAME keyboard UI and insert path.
 */
public final class AndroidSystemTranslate {
    private AndroidSystemTranslate() {}

    private static final long TIMEOUT_MS = 12000L;
    private static final Handler MAIN = new Handler(Looper.getMainLooper());

    public static void translate(Context context, String original,
            String from, String to, Consumer<String> success,
            Consumer<String> unavailable) {
        final Context app = context.getApplicationContext();
        if (Build.VERSION.SDK_INT < 31 || original == null || original.trim().isEmpty()) {
            MAIN.post(() -> unavailable.accept("시스템 번역 서비스 미지원"));
            return;
        }
        final AtomicBoolean finished = new AtomicBoolean(false);
        final AtomicReference<Translator> active = new AtomicReference<>();
        final CancellationSignal cancel = new CancellationSignal();
        final Runnable fallback = () -> {
            if (!finished.compareAndSet(false, true)) return;
            cancel.cancel();
            Translator translator = active.getAndSet(null);
            if (translator != null) translator.destroy();
            unavailable.accept("시스템 번역 사용 불가");
        };
        MAIN.postDelayed(fallback, TIMEOUT_MS);
        new Thread(() -> {
            try {
                TranslationManager manager = app.getSystemService(TranslationManager.class);
                if (manager == null) {
                    MAIN.post(fallback);
                    return;
                }
                TranslationSpec source = new TranslationSpec(
                        ULocale.forLanguageTag(from), TranslationSpec.DATA_FORMAT_TEXT);
                TranslationSpec target = new TranslationSpec(
                        ULocale.forLanguageTag(to), TranslationSpec.DATA_FORMAT_TEXT);
                TranslationContext config = new TranslationContext.Builder(source, target).build();
                manager.createOnDeviceTranslator(config, app.getMainExecutor(), translator -> {
                    if (finished.get()) {
                        if (translator != null) translator.destroy();
                        return;
                    }
                    if (translator == null) {
                        MAIN.post(fallback);
                        return;
                    }
                    active.set(translator);
                    try {
                        TranslationRequest request = new TranslationRequest.Builder()
                                .setTranslationRequestValues(Collections.singletonList(
                                        TranslationRequestValue.forText(original)))
                                .build();
                        translator.translate(request, cancel, app.getMainExecutor(), response -> {
                            if (finished.get()) return;
                            try {
                                TranslationResponseValue translated =
                                        response.getTranslationResponseValues().get(0);
                                if (response.getTranslationStatus()
                                        != TranslationResponse.TRANSLATION_STATUS_SUCCESS
                                        || translated == null
                                        || translated.getStatusCode()
                                        != TranslationResponseValue.STATUS_SUCCESS
                                        || translated.getText() == null
                                        || translated.getText().toString().trim().isEmpty()) {
                                    MAIN.post(fallback);
                                    return;
                                }
                                String result = translated.getText().toString();
                                if (finished.compareAndSet(false, true)) {
                                    MAIN.removeCallbacks(fallback);
                                    Translator toDestroy = active.getAndSet(null);
                                    if (toDestroy != null) toDestroy.destroy();
                                    success.accept(result);
                                }
                            } catch (RuntimeException error) {
                                MAIN.post(fallback);
                            }
                        });
                    } catch (RuntimeException error) {
                        MAIN.post(fallback);
                    }
                });
            } catch (RuntimeException | LinkageError error) {
                MAIN.post(fallback);
            }
        }, "NewSwipe-System-Translate").start();
    }
}
