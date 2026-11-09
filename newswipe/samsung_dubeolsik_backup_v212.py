from pathlib import Path

ROOT = Path("app/src/main/java/com/alternative_studios/newswipe")

def patch(path, old, new, why):
    src = path.read_text(encoding="utf-8")
    count = src.count(old)
    assert count == 1, (str(path), why, "expected exactly one match", count)
    path.write_text(src.replace(old, new, 1), encoding="utf-8")

prefs = ROOT / "Prefs.java"
patch(prefs,
      'return sp.getString(KOREAN_LAYOUT, null);',
      'return sp.getString(KOREAN_LAYOUT, KOREAN_LAYOUT_DUBEOLSIK);',
      "NewSwipe personal version defaults to standard Korean two-set layout unless an explicit preference exists")
patch(prefs,
      'public boolean periodComma() { return sp.getBoolean(PERIOD_COMMA, true); }',
      'public boolean periodComma() { return sp.getBoolean(PERIOD_COMMA, false); }',
      "comma key is visible by default, honoring previously saved explicit user choices")

bottom = ROOT / "keyboard/BottomKeys.java"
patch(bottom,
      'public static final String[] DEFAULT_ORDER = {MODE, COMMA, GLOBE, SPACE, PERIOD, ENTER, EMOJI, CLIPBOARD, CURSOR, VOICE};',
      'public static final String[] DEFAULT_ORDER = {MODE, GLOBE, COMMA, SPACE, PERIOD, ENTER, EMOJI, CLIPBOARD, CURSOR, VOICE};',
      "Samsung ordering: symbol, Korean/English switch, comma, space, period, enter")
patch(bottom,
      'return !COMMA.equals(id) && !EMOJI.equals(id) && !CLIPBOARD.equals(id) && !CURSOR.equals(id) && !VOICE.equals(id);',
      'return !EMOJI.equals(id) && !CLIPBOARD.equals(id) && !CURSOR.equals(id) && !VOICE.equals(id);',
      "matching default comma visibility")

layout = ROOT / "keyboard/KeyboardLayout.java"
source = layout.read_text(encoding="utf-8")
n = source.count('" ?123"')
assert n == 0, n
n = source.count('"?123"')
assert n >= 5, ("unexpected symbol toggle count", n)
source = source.replace('"?123"', '"!#1"')
assert 'return qwertyLayout(KOREAN, DUBEOLSIK_ROWS, DUBEOLSIK_POPUPS, true, prefs)' in source
layout.write_text(source, encoding="utf-8")

backup = ROOT / "SettingsBackup.java"
patch(backup,
      'return new ComponentName(context, context.getPackageName() + ".LauncherAlias");',
      '''// The launcher alias is built from the Java namespace, not the customized
        // applicationId (.personal). The two differ in the stable APK.
        return new ComponentName(context, SettingsActivity.class.getPackage().getName() + ".LauncherAlias");''',
      "fix launcher alias name when applicationId differs from source namespace")
patch(backup,
      '''        return context.getPackageManager().getComponentEnabledSetting(launcherAlias(context))
                != PackageManager.COMPONENT_ENABLED_STATE_DISABLED;''',
      '''        try {
            return context.getPackageManager().getComponentEnabledSetting(launcherAlias(context))
                    != PackageManager.COMPONENT_ENABLED_STATE_DISABLED;
        } catch (IllegalArgumentException e) {
            // Missing/renamed launcher alias must never prevent settings backup.
            return true;
        }''',
      "ignore stale alias on export")
patch(backup,
      '''        context.getPackageManager().setComponentEnabledSetting(launcherAlias(context),
                shown ? PackageManager.COMPONENT_ENABLED_STATE_ENABLED
                        : PackageManager.COMPONENT_ENABLED_STATE_DISABLED,
                PackageManager.DONT_KILL_APP);''',
      '''        try {
            context.getPackageManager().setComponentEnabledSetting(launcherAlias(context),
                    shown ? PackageManager.COMPONENT_ENABLED_STATE_ENABLED
                            : PackageManager.COMPONENT_ENABLED_STATE_DISABLED,
                    PackageManager.DONT_KILL_APP);
        } catch (IllegalArgumentException ignored) {
            // Older or re-packaged installations may lack the alias.
            // The rest of the imported settings should still be restored.
        }''',
      "do not abort import for renamed launcher alias")

picker = ROOT / "SettingsImport.java"
patch(picker,
      '''        activity.startActivityForResult(
                new Intent(Intent.ACTION_OPEN_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE).setType("*/*"),
                requestCode);''',
      '''        Intent choose = new Intent(Intent.ACTION_GET_CONTENT);
        choose.setType("*/*");
        choose.addCategory(Intent.CATEGORY_OPENABLE);
        choose.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        try {
            activity.startActivityForResult(Intent.createChooser(choose, "NewSwipe 설정 백업 파일 선택"), requestCode);
        } catch (android.content.ActivityNotFoundException e) {
            Toast.makeText(activity, "백업 파일을 선택할 파일 관리자를 찾지 못했습니다.", Toast.LENGTH_LONG).show();
        }''',
      "Samsung One UI compatible import picker with visible error")

activity = ROOT / "SettingsActivity.java"
src = activity.read_text(encoding="utf-8")
start = src.index('    private void startExport(boolean withWords, boolean withEmoji, boolean withClipboard, char[] password) {')
end = src.index('\n    @Override\n    protected void onActivityResult(', start)
old = src[start:end]
assert old.count('startActivityForResult(i, REQ_EXPORT);') == 1
replacement = '''    private void startExport(boolean withWords, boolean withEmoji, boolean withClipboard, char[] password) {
        // Android 10+ can save into Downloads through MediaStore, no extra storage
        // permission and no vendor-dependent CREATE_DOCUMENT picker needed.
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) {
            if (exportPassword != null) java.util.Arrays.fill(exportPassword, '\\\\0');
            exportPassword = password;
            exportWithWords = withWords;
            exportWithEmoji = withEmoji;
            exportWithClipboard = withClipboard;
            Intent i = new Intent(Intent.ACTION_CREATE_DOCUMENT)
                    .addCategory(Intent.CATEGORY_OPENABLE)
                    .setType("application/json")
                    .putExtra(Intent.EXTRA_TITLE, "newswipe-settings-"
                            + new java.text.SimpleDateFormat("yyyyMMdd-HHmm", java.util.Locale.US)
                            .format(new java.util.Date()) + ".json");
            try {
                startActivityForResult(i, REQ_EXPORT);
            } catch (android.content.ActivityNotFoundException e) {
                if (exportPassword != null) java.util.Arrays.fill(exportPassword, '\\\\0');
                exportPassword = null;
                Toast.makeText(this, "파일 저장 앱이 없어 설정을 내보낼 수 없습니다", Toast.LENGTH_LONG).show();
            }
            return;
        }

        final String fileName = "newswipe-settings-"
                + new java.text.SimpleDateFormat("yyyyMMdd-HHmmss", java.util.Locale.US)
                .format(new java.util.Date()) + ".json";
        final android.content.Context app = getApplicationContext();
        Toast.makeText(this, "설정을 다운로드 폴더에 저장하는 중입니다…", Toast.LENGTH_SHORT).show();
        new Thread(() -> {
            android.net.Uri uri = null;
            String feedback;
            try {
                android.content.ContentValues values = new android.content.ContentValues();
                values.put(android.provider.MediaStore.MediaColumns.DISPLAY_NAME, fileName);
                values.put(android.provider.MediaStore.MediaColumns.MIME_TYPE, "application/json");
                values.put(android.provider.MediaStore.MediaColumns.RELATIVE_PATH,
                        android.os.Environment.DIRECTORY_DOWNLOADS + "/NewSwipe/");
                values.put(android.provider.MediaStore.MediaColumns.IS_PENDING, 1);
                uri = app.getContentResolver().insert(android.provider.MediaStore.Downloads.EXTERNAL_CONTENT_URI, values);
                if (uri == null) throw new java.io.IOException("다운로드 파일을 만들지 못했습니다");
                SettingsBackup.export(app, uri, withWords, withEmoji, withClipboard, password);
                android.content.ContentValues finished = new android.content.ContentValues();
                finished.put(android.provider.MediaStore.MediaColumns.IS_PENDING, 0);
                app.getContentResolver().update(uri, finished, null, null);
                feedback = "설정 내보내기 완료: 다운로드/NewSwipe/" + fileName;
            } catch (Exception e) {
                if (uri != null) {
                    try { app.getContentResolver().delete(uri, null, null); }
                    catch (Exception ignored) { }
                }
                feedback = "설정 내보내기 실패: " + e.getMessage();
            } finally {
                if (password != null) java.util.Arrays.fill(password, '\\\\0');
            }
            final String message = feedback;
            runOnUiThread(() -> {
                if (!isFinishing() && !isDestroyed())
                    Toast.makeText(this, message, Toast.LENGTH_LONG).show();
            });
        }, "newswipe-settings-export").start();
    }
'''
# Python escapes: produce Java char literal '\\0' rather than '\\\\0'
replacement = replacement.replace(chr(92) * 2 + '0', chr(92) + '0')
assert "Arrays.fill(password, '" + chr(92) + "0');" in replacement
assert chr(92) * 2 + '0' not in replacement
src = src[:start] + replacement + src[end:]
assert 'MediaStore.Downloads.EXTERNAL_CONTENT_URI' in src
assert 'SettingsImport.onPicked(this, uri' in src
activity.write_text(src, encoding="utf-8")

# Keep standard key order as supplied by Dubeolsik.rows() and preserve all
# explicit keyboard customizations, user dictionary and existing clipboard data.
assert '"!#1"' in layout.read_text(encoding="utf-8")
print("NewSwipe 2.1.2: Samsung-style two-set defaults, comma and symbol row, robust backup import and Downloads export.")
