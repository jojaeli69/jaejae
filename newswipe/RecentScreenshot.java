package com.alternative_studios.newswipe;

import android.Manifest;
import android.content.ContentUris;
import android.content.Context;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.net.Uri;
import android.os.Build;
import android.provider.MediaStore;

/**
 * Only queries screenshots the user captured in the last 90 seconds.
 * Media queries happen only while the IME is visible, with user's full
 * photo-library permission. Never scans uploads or contacts or all photos.
 */
public final class RecentScreenshot {
    private RecentScreenshot() {}

    public static final class Result {
        public final Uri uri;
        public final String mime;
        public final long captured;
        public Result(Uri uri, String mime, long captured) {
            this.uri=uri; this.mime=mime; this.captured=captured;
        }
    }

    public static boolean allowed(Context c) {
        if (Build.VERSION.SDK_INT >= 33) {
            return c.checkSelfPermission(Manifest.permission.READ_MEDIA_IMAGES)
                    == PackageManager.PERMISSION_GRANTED;
        }
        return Build.VERSION.SDK_INT >= 29
                && c.checkSelfPermission(Manifest.permission.READ_EXTERNAL_STORAGE)
                    == PackageManager.PERMISSION_GRANTED;
    }

    public static boolean isScreenshot(String displayName, String relativePath) {
        String name = displayName == null ? "" : displayName.toLowerCase(java.util.Locale.ROOT);
        String dir = relativePath == null ? "" : relativePath.toLowerCase(java.util.Locale.ROOT);
        return name.startsWith("screenshot") || name.startsWith("스크린샷")
                || name.startsWith("screen_shot")
                || dir.contains("/screenshots/") || dir.endsWith("/screenshots")
                || dir.contains("/스크린샷/") || dir.endsWith("/스크린샷");
    }

    public static Result latest(Context c, long nowMs) {
        if (!allowed(c)) return null;
        long minimumSeconds = nowMs / 1000 - 95;
        String[] projection = {
                MediaStore.Images.Media._ID,
                MediaStore.Images.Media.DISPLAY_NAME,
                MediaStore.Images.Media.RELATIVE_PATH,
                MediaStore.Images.Media.MIME_TYPE,
                MediaStore.Images.Media.DATE_ADDED
        };
        try (Cursor found=c.getContentResolver().query(
                MediaStore.Images.Media.EXTERNAL_CONTENT_URI, projection,
                MediaStore.Images.Media.DATE_ADDED + " >= ?",
                new String[]{Long.toString(minimumSeconds)},
                MediaStore.Images.Media.DATE_ADDED+" DESC")) {
            if (found == null) return null;
            int id = found.getColumnIndexOrThrow(MediaStore.Images.Media._ID);
            int name = found.getColumnIndexOrThrow(MediaStore.Images.Media.DISPLAY_NAME);
            int path = found.getColumnIndexOrThrow(MediaStore.Images.Media.RELATIVE_PATH);
            int mime = found.getColumnIndexOrThrow(MediaStore.Images.Media.MIME_TYPE);
            int added = found.getColumnIndexOrThrow(MediaStore.Images.Media.DATE_ADDED);
            int inspected=0;
            while (found.moveToNext() && inspected++ < 30) {
                String type=found.getString(mime);
                if (type == null || !type.startsWith("image/")) continue;
                if (!isScreenshot(found.getString(name),found.getString(path))) continue;
                long capturedMs=found.getLong(added)*1000L;
                if (capturedMs > nowMs+15000L || nowMs-capturedMs>95000L) continue;
                return new Result(ContentUris.withAppendedId(
                        MediaStore.Images.Media.EXTERNAL_CONTENT_URI,found.getLong(id)),
                        type,capturedMs);
            }
        } catch (RuntimeException deniedOrUnavailable) {
            // Vendor providers may refuse even granted permissions; leave clipboard path active.
        }
        return null;
    }
}
