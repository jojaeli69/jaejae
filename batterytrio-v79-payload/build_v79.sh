#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
SDK="${ANDROID_SDK_ROOT:-$ANDROID_HOME}"
BT="$SDK/build-tools/35.0.0"
PLATFORM="$SDK/platforms/android-35/android.jar"
OUT="$ROOT/.build"
rm -rf "$OUT"
mkdir -p "$OUT/rescompiled" "$OUT/gen" "$OUT/classes" "$OUT/dex"
while IFS= read -r -d '' f; do "$BT/aapt2" compile "$f" -o "$OUT/rescompiled"; done < <(find "$ROOT/app/src/main/res" -type f -print0)
mapfile -d '' FLATS < <(find "$OUT/rescompiled" -name '*.flat' -print0)
"$BT/aapt2" link -o "$OUT/resources.apk" -I "$PLATFORM" \
  --manifest "$ROOT/app/src/main/AndroidManifest.xml" \
  --rename-manifest-package org.example.galaxybatterybridge.history \
  --java "$OUT/gen" --min-sdk-version 28 --target-sdk-version 34 "${FLATS[@]}"
find "$ROOT/app/src/main/java" "$OUT/gen" -name '*.java' > "$OUT/sources.txt"
javac -source 17 -target 17 -encoding UTF-8 -cp "$PLATFORM" -d "$OUT/classes" @"$OUT/sources.txt"
mapfile -d '' CLASSFILES < <(find "$OUT/classes" -name '*.class' -print0)
"$BT/d8" --min-api 28 --lib "$PLATFORM" --output "$OUT/dex" "${CLASSFILES[@]}"
cp "$OUT/resources.apk" "$OUT/unsigned.apk"
(cd "$OUT/dex" && zip -q -u "$OUT/unsigned.apk" classes.dex)
python3 "$ROOT/align_apk.py" "$OUT/unsigned.apk" "$OUT/aligned.apk"
KEY="${GTS4_SIGNING_KEY:?Missing signing key}"
"$BT/apksigner" sign --ks "$KEY" --ks-key-alias gts4-test --ks-pass pass:changeit --key-pass pass:changeit --out "$ROOT/BatteryTrioMini_v79.apk" "$OUT/aligned.apk"
"$BT/apksigner" verify --verbose --print-certs "$ROOT/BatteryTrioMini_v79.apk"
"$BT/aapt2" dump badging "$ROOT/BatteryTrioMini_v79.apk" | sed -n "1,12p"
