# QuietRings GTS 4 Mini watchface — QR test builds

Latest test build: **v2.0.0**, file `QuietRings_GTS4Mini_DIALOG_v2.0.zpk`.

## Changes
- Completely rebuilt 0–9 time digit assets from the shared original GTS 4 source 86×142 using one direct 74×122 proportional render into the same 78×126 canvas with 2px uniform padding.
- Normal and AOD numerical silhouettes and positions are identical (normal white, AOD subdued gray).
- Both time rows moved down 3px as a unified group to better balance date, time and three rings.
- Previously approved Wednesday glyph, day/month typography, battery/heart/steps and sensor refresh code preserved.
- 1,440 legal times and 10,000 two-row patterns pass geometric boundary tests; all 20 raster asset round-trips pass.
- JavaScript syntax, asset TGA Dialog headers and nested ZPK ZIP CRC verified.

**Experimental release: no actual GTS 4 Mini hardware rendering or AOD transition confirmation yet.** This is not a firmware image.

Zepp dev-mode QR payload:
`watchface://raw.githubusercontent.com/jojaeli69/jaejae/quierrings-gts4mini-qr-test-20261111/QuietRings_GTS4Mini_DIALOG_v2.0.zpk`

Past v1.1–v1.8 builds are retained for rollback.
