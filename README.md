# QuietRings GTS 4 Mini — experimental Zepp QR builds

Latest: **v1.9** — `QuietRings_GTS4Mini_DIALOG_v1.9.zpk`

### Fix: irregular digit 5
The v1.8 digit 5 was inherited from the v1.6 conversion and had undergone repeated downscaling. Its shoulder and lower curve looked less natural than the original. We re-rendered **only digit 5** from the original GTS4 source PNG (86×142) directly into the 78×126 Mini display size once, with high-quality sampling and Dialog-native TGA palette output.

Both normal `t5.png` and AOD `a5.png` use the same raster alpha mask; AOD remains dark gray. All other numeric glyphs, coordinates, sensors, watchface JS, and AOD code are unchanged. Device app.json and app-side metadata have been incremented to version 1.9.0 (code 10).

Validated: new normal/AOD alpha masks are identical, image round-trip through Dialog TGA, unchanged watchface JS, ZIP integrity and 12 representative number-5 time examples. **Not verified on actual GTS 4 Mini hardware yet**.

Zepp developer mode experimental QR:
`watchface://raw.githubusercontent.com/jojaeli69/jaejae/quierrings-gts4mini-qr-test-20261111/QuietRings_GTS4Mini_DIALOG_v1.9.zpk`

Previous versions v1.1–v1.8 preserved for rollback.
