# QuietRings GTS4 Mini QR watchface builds

Latest: **v1.5** (file `QuietRings_GTS4Mini_DIALOG_v1.5.zpk`)

- Target: GTS 4 Mini Zepp OS 1.0, 336x384 Dialog image codec
- Existing v1.4 Wednesday label, widgets and 226 Dialog image resources preserved byte-for-byte
- Fixed unequal spacing due to digit 1 / digit 4 pixel extents: digit pair visible horizontal gap now uniformly 6px; previous 0–36px
- 2-row time spacing revised to 8–9px visible blank gap (was 10–11px)
- Verified all 100 two-digit patterns, 10,000 possible pair-of-pair combinations, and 1,440 valid 24h times
- Original source JS and bundled runtime JS also executed in mock Zepp environment across 1,440 times each (2,880 row assertions per variant)
- This remains unofficial: actual watch rendering and battery/clock latency still need physical device testing.

Install via Zepp developer-mode watchface scanner:
`watchface://raw.githubusercontent.com/jojaeli69/jaejae/quierrings-gts4mini-qr-test-20261111/QuietRings_GTS4Mini_DIALOG_v1.5.zpk`

Previous v1.1/v1.2/v1.3/v1.4 ZPK retained for rollback.
