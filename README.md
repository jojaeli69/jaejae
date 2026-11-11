# QuietRings GTS 4 Mini — experimental watchface QR releases

Latest: **v1.8** (`QuietRings_GTS4Mini_DIALOG_v1.8.zpk`)

### Why AOD looked misaligned even with matching 78×126 and identical coordinates
- The v1.7 AOD digit art had been separately resized and differed from the normal screen's exact rasterized glyph masks (131–299 differing pixels per digit for an alpha threshold of 128).
- v1.8 copies each normal digit's *exact* raster geometry and alpha data into its AOD counterpart, converting only the RGB palette to subdued gray (approximately 75/254).
- Normal and AOD use the same Zepp OS IMG_TIME widget coordinates: hour (159,83), minute (159,222), 2px spacing. Same sizes 78×126.
- Original normal glyphs, screen code, health widgets, AOD widget code and all other assets are unmodified, aside from app version metadata.
- All 10 normal/AOD alpha masks match exactly; 1,440 valid time configurations checked; ZIPs verified.
- **This does not rule out firmware-controlled AOD positional shift or burn-in mitigation. Actual GTS 4 Mini hardware test is still required.**

Install via Zepp developer-mode QR test:
`watchface://raw.githubusercontent.com/jojaeli69/jaejae/quierrings-gts4mini-qr-test-20261111/QuietRings_GTS4Mini_DIALOG_v1.8.zpk`

Previous v1.1–v1.7 builds retained for rollback.
