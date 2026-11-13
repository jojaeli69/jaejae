package com.alternative_studios.newswipe;

import android.content.Context;
import android.content.SharedPreferences;
import android.os.Handler;
import android.os.Looper;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.KeyStore;
import java.util.function.Consumer;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

/**
 * Explicit, user-configured online DeepL translation.
 *
 * The API key is encrypted by Android Keystore. Only the source text of an
 * explicit Translate-button action is transmitted. Passwords, clipboard
 * history, IME keystrokes and SMS are never accessed here.
 * No unapproved keyless web/scraping endpoints are used.
 */
public final class DeepLTranslate {
    private static final String PREF = "newswipe_online_translation";
    private static final String ALIAS = "newswipe.deepl.user_api.v1";
    private static final String KEY_CIPHERTEXT = "key_ciphertext";
    private static final String KEY_IV = "key_iv";
    private static final String USE_ONLINE = "deepl_online";
    private static final String LEGACY_FREE = "deepl_legacy_free";
    private static final Handler MAIN = new Handler(Looper.getMainLooper());
    private static final int MAX_RESPONSE_BYTES = 256 * 1024;

    private DeepLTranslate() {}

    private static SharedPreferences prefs(Context c) {
        return c.getApplicationContext().getSharedPreferences(PREF, Context.MODE_PRIVATE);
    }

    public static boolean hasKey(Context c) {
        SharedPreferences p = prefs(c);
        return !p.getString(KEY_CIPHERTEXT, "").isEmpty()
                && !p.getString(KEY_IV, "").isEmpty();
    }

    public static boolean enabled(Context c) {
        return hasKey(c) && prefs(c).getBoolean(USE_ONLINE, false);
    }

    public static boolean legacyFree(Context c) {
        return prefs(c).getBoolean(LEGACY_FREE, false);
    }

    public static void setEnabled(Context c, boolean value) {
        prefs(c).edit().putBoolean(USE_ONLINE, value && hasKey(c)).apply();
    }

    private static SecretKey aesKey() throws Exception {
        KeyStore ks = KeyStore.getInstance("AndroidKeyStore");
        ks.load(null);
        SecretKey stored = (SecretKey) ks.getKey(ALIAS, null);
        if (stored != null) return stored;
        KeyGenerator gen = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore");
        gen.init(new KeyGenParameterSpec.Builder(
                ALIAS, KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .setUserAuthenticationRequired(false)
                .build());
        return gen.generateKey();
    }

    public static void saveKey(Context c, String rawKey, boolean freeEndpoint) throws Exception {
        String secret = rawKey == null ? "" : rawKey.trim();
        if (secret.length() < 12 || secret.length() > 512
                || !secret.matches("[A-Za-z0-9:_-]+")) {
            throw new IllegalArgumentException("DeepL API 키 형식을 확인해 주세요.");
        }
        Cipher enc = Cipher.getInstance("AES/GCM/NoPadding");
        enc.init(Cipher.ENCRYPT_MODE, aesKey());
        byte[] cipherText = enc.doFinal(secret.getBytes(StandardCharsets.UTF_8));
        prefs(c).edit()
                .putString(KEY_CIPHERTEXT, Base64.encodeToString(cipherText, Base64.NO_WRAP))
                .putString(KEY_IV, Base64.encodeToString(enc.getIV(), Base64.NO_WRAP))
                .putBoolean(LEGACY_FREE, freeEndpoint || secret.endsWith(":fx"))
                .putBoolean(USE_ONLINE, true)
                .apply();
    }

    public static void clearKey(Context c) {
        prefs(c).edit().remove(KEY_CIPHERTEXT).remove(KEY_IV)
                .putBoolean(USE_ONLINE, false).apply();
    }

    private static String decryptKey(Context c) throws Exception {
        SharedPreferences p = prefs(c);
        String data = p.getString(KEY_CIPHERTEXT, "");
        String iv = p.getString(KEY_IV, "");
        if (data.isEmpty() || iv.isEmpty()) throw new IllegalStateException("DeepL API 키가 없습니다.");
        Cipher dec = Cipher.getInstance("AES/GCM/NoPadding");
        dec.init(Cipher.DECRYPT_MODE, aesKey(),
                new GCMParameterSpec(128, Base64.decode(iv, Base64.NO_WRAP)));
        return new String(dec.doFinal(Base64.decode(data, Base64.NO_WRAP)), StandardCharsets.UTF_8);
    }

    /** Call only after a user's explicit Translate action; never from typing events. */
    public static void translate(Context context, String text, String from, String to,
            Consumer<String> success, Consumer<String> failure) {
        Context app = context.getApplicationContext();
        new Thread(() -> {
            try {
                if (!enabled(app)) throw new IllegalStateException("DeepL 온라인 번역 설정을 확인해 주세요.");
                String apiKey = decryptKey(app);
                String result = request(app, apiKey, text, from, to);
                MAIN.post(() -> success.accept(result));
            } catch (Exception e) {
                // Never log source text, response body or API key.
                String message = messageFor(e);
                MAIN.post(() -> failure.accept(message));
            }
        }, "NewSwipe-DeepL-Translate").start();
    }

    private static String lang(String code, boolean target) {
        if ("ko".equalsIgnoreCase(code)) return "KO";
        if ("ja".equalsIgnoreCase(code)) return "JA";
        if ("zh".equalsIgnoreCase(code)) return target ? "ZH-HANS" : "ZH";
        return target ? "EN-US" : "EN";
    }

    private static String request(Context app, String key, String source,
            String from, String to) throws Exception {
        if (source == null || source.trim().isEmpty())
            throw new IllegalArgumentException("번역할 문장이 없습니다.");
        boolean free = legacyFree(app) || key.endsWith(":fx");
        URL endpoint = new URL(free
                ? "https://api-free.deepl.com/v2/translate"
                : "https://api.deepl.com/v2/translate");
        HttpURLConnection connection = (HttpURLConnection) endpoint.openConnection();
        try {
            connection.setRequestMethod("POST");
            connection.setConnectTimeout(12000);
            connection.setReadTimeout(25000);
            connection.setDoOutput(true);
            connection.setInstanceFollowRedirects(false);
            connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            connection.setRequestProperty("Accept", "application/json");
            connection.setRequestProperty("Authorization", "DeepL-Auth-Key " + key);

            JSONObject payload = new JSONObject();
            payload.put("text", new JSONArray().put(source));
            payload.put("source_lang", lang(from, false));
            payload.put("target_lang", lang(to, true));
            payload.put("model_type", "prefer_quality_optimized");
            payload.put("split_sentences", "nonewlines");
            payload.put("preserve_formatting", true);
            byte[] body = payload.toString().getBytes(StandardCharsets.UTF_8);
            connection.setFixedLengthStreamingMode(body.length);
            try (OutputStream out = connection.getOutputStream()) {
                out.write(body);
            }
            int status = connection.getResponseCode();
            if (status != HttpURLConnection.HTTP_OK) {
                switch (status) {
                    case 400: throw new IllegalStateException("DeepL 요청 오류 · 언어/설정 확인");
                    case 401: throw new IllegalStateException("DeepL API 키 인증 실패");
                    case 403: throw new IllegalStateException("DeepL API 키 또는 요금제·엔드포인트 확인");
                    case 413: throw new IllegalStateException("번역 문장이 너무 깁니다");
                    case 429: throw new IllegalStateException("DeepL 요청이 너무 많아요 · 잠시 후 재시도");
                    case 456: throw new IllegalStateException("DeepL 무료 한도 또는 이용 한도 초과");
                    default: throw new IllegalStateException("DeepL 서버 응답 오류 (" + status + ")");
                }
            }
            JSONObject json;
            try (InputStream in = connection.getInputStream()) {
                json = new JSONObject(readBounded(in));
            }
            String translated = json.getJSONArray("translations").getJSONObject(0)
                    .getString("text");
            if (translated.trim().isEmpty())
                throw new IllegalStateException("DeepL에서 빈 번역 결과가 도착했습니다.");
            return translated;
        } finally {
            connection.disconnect();
        }
    }

    private static String readBounded(InputStream in) throws Exception {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        byte[] block = new byte[4096];
        int n;
        while ((n = in.read(block)) != -1) {
            if (bytes.size() + n > MAX_RESPONSE_BYTES)
                throw new IllegalStateException("번역 응답 크기 초과");
            bytes.write(block, 0, n);
        }
        return bytes.toString("UTF-8");
    }

    private static String messageFor(Exception e) {
        if (e instanceof IllegalStateException || e instanceof IllegalArgumentException)
            return e.getMessage() == null ? "번역 설정 오류" : e.getMessage();
        if (e instanceof java.net.SocketTimeoutException) return "DeepL 서버 응답 시간 초과";
        if (e instanceof java.net.UnknownHostException) return "인터넷 연결을 확인해 주세요";
        if (e instanceof javax.crypto.AEADBadTagException)
            return "저장된 DeepL API 키를 다시 등록해 주세요";
        return "온라인 번역 연결 실패 · 인터넷 및 API 설정 확인";
    }
}
