from pathlib import Path

gradle=Path("app/build.gradle.kts")
s=gradle.read_text(encoding="utf-8")
assert s.count('isMinifyEnabled = true')==1
assert s.count('isShrinkResources = true')==1

# Release-only NPE in ML Kit translation happens while constructing a Translator,
# before any network/model download. R8 whole-program shrinking can strip/
# rename the component factories which ML Kit locates by component discovery.
# Disable both optimizations for this trustworthy recovery release, instead
# of weakening obfuscation for just the app's own code. User settings remain
# in the same com.alternative_studios.newswipe.personal package.
s=s.replace('isMinifyEnabled = true',
'''// ML Kit Translation.getClient() crashes with NullPointerException
            // in the previously minified release APK. Full ML Kit/Firebase
            // component discovery must survive unchanged. Release v2.1.9
            // deliberately uses the complete library until a device run
            // confirms shrink-safe keep rules.
            isMinifyEnabled = false''',1)
s=s.replace('isShrinkResources = true',
'''// Resource shrinking requires minification; also keep component
            // metadata/resources for SDK registrars and model-loading paths.
            isShrinkResources = false''',1)
gradle.write_text(s,encoding="utf-8")

# Add explicit non-mangle policy as a long-term guard if shrinking is re-enabled.
rules=Path("app/proguard-rules.pro")
body=rules.read_text(encoding="utf-8")
assert "-repackageclasses" in body
body += """
# ML Kit translation relies on manifest-registered/component-registered types.
# These are also used from generated code and by SDK internals, not always by
# statically visible app references.
-keep class com.google.mlkit.** { *; }
-keep class com.google.firebase.components.** { *; }
-keep class com.google.android.gms.internal.mlkit_translate.** { *; }
-keepattributes *Annotation*,Signature,InnerClasses,EnclosingMethod
"""
rules.write_text(body,encoding="utf-8")

panel=Path("app/src/main/java/com/alternative_studios/newswipe/KeyboardTranslatePanel.java")
p=panel.read_text(encoding="utf-8")
old='''            final Translator active=Translation.getClient(config);
            translator=active;
            active.downloadModelIfNeeded(new DownloadConditions.Builder().build())'''
new='''            final Translator active;
            try {
                active = Translation.getClient(config);
            } catch (RuntimeException | LinkageError initError) {
                // Distinguish a broken SDK component factory from model errors.
                failure(token, "ML Kit 번역 엔진 생성 실패", initError);
                return;
            }
            translator=active;
            active.downloadModelIfNeeded(new DownloadConditions.Builder().build())'''
assert p.count(old)==1,('translator getClient boundary',p.count(old))
p=p.replace(old,new,1)
panel.write_text(p,encoding="utf-8")

# Validate actual merged manifest (provider + registrars) in the CI workflow.
# These are not redundant: missing one causes a null ML Kit Translator factory.
manifest=Path("app/src/main/AndroidManifest.xml").read_text(encoding="utf-8")
assert 'android.permission.INTERNET' in manifest
assert 'com.google.mlkit.nl.translate' in gradle.read_text(encoding="utf-8")
assert 'isMinifyEnabled = false' in gradle.read_text(encoding="utf-8")
assert 'isShrinkResources = false' in gradle.read_text(encoding="utf-8")
assert 'ML Kit 번역 엔진 생성 실패' in panel.read_text(encoding="utf-8")
print("NewSwipe v2.1.9: release R8 minify/resource shrink disabled; ML Kit registrars preserved; translator creation errors isolated.")
