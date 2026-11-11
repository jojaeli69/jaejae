# QuietRings GTS 4 Mini (QR preview builds)

Latest: v1.4 (`QuietRings_GTS4Mini_DIALOG_v1.4.zpk`)

## Changes in v1.4

- Keep the user's approved Wednesday glyph X/Y position unchanged
- Reduce upper/lower time row gap to 10 px (v1.2: 6 px, v1.3: 17 px)
- Keep three rings and all 224 core Dialog assets byte-identical
- Foreground-only, 5-second fallback time/battery/step/HR polling in addition to existing sensor events
- Force immediate re-read on watchface resume; stop timer and listeners on pause/destroy
- Source and compiled JS have passed syntax and mocked lifecycle/time/battery update tests
- Note: hardware battery sample frequency cannot be overridden by the watchface.

This is an experimental preview ZPK for Zepp OS 1.0 Amazfit GTS 4 Mini (336x384).
Actual v1.4 installation and update latency on hardware are not yet verified.
v1.1/v1.2/v1.3 builds remain available for rollback.

Developer mode QR URL:
`watchface://raw.githubusercontent.com/jojaeli69/jaejae/quierrings-gts4mini-qr-test-20261111/QuietRings_GTS4Mini_DIALOG_v1.4.zpk`
