# QuietRings GTS4 Mini experimental QR builds

Latest: **v1.7** (`QuietRings_GTS4Mini_DIALOG_v1.7.zpk`)

## AOD and normal visual size unified
- GTS 4 Mini 336x384, Zepp OS 1.0, Dialog native image assets
- Normal clock: same v1.6 assets, logic and positions (78x126 per digit)
- AOD clock resized from 85x140 to 78x126 per digit, retaining subdued AOD gray color palette
- AOD `IMG_TIME` positions now match normal `IMG_TIME`: hour x159/y83, minute x159/y222, digit spacing 2px
- Original normal screen/date/Wednesday and ring positions, plus event/polling behavior, unchanged
- All 10 AOD native Dialog TGA images re-encoded and decoded successfully
- 1,440 time configurations checked geometrically, both JS versions syntax validated, nested ZIP integrity verified
- Unofficial experimental ZPK; actual GTS4 Mini AOD transition and brightness **not yet hardware-tested**

Zepp Developer Mode QR URL:
`watchface://raw.githubusercontent.com/jojaeli69/jaejae/quierrings-gts4mini-qr-test-20261111/QuietRings_GTS4Mini_DIALOG_v1.7.zpk`

Previous v1.1–v1.6 builds retained for rollback.
