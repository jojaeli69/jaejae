# QuietRings GTS 4 Mini preview builds

Latest: **v1.6** — `QuietRings_GTS4Mini_DIALOG_v1.6.zpk`

### Main fix
Normal watchface previously created 4 independent IMG widgets and positioned each time digit with JavaScript. AOD already uses the native Zepp `IMG_TIME` widget. v1.6 converts normal time to one native `IMG_TIME` widget as well and proportionally resizes only the 10 normal time digits from 85×140 to 78×126 in native Dialog format. AOD widget & assets are unchanged, Wednesday/date/rings/metrics unchanged. Vertical gap 13px.

### Verification
- Decoded and re-encoded all 10 resized Dialog assets; correct 78×126 native header/palette and transparent borders
- 1,440 clock value layouts geometrically checked
- Actual compressed watchface JS executed in a Zepp-like mock with normal and AOD native widgets; lifecycle and sensors checked
- ZPK ZIP integrity and preserved AOD resource binary equality verified
- **Real GTS 4 Mini v1.6 on-device rendering not yet verified**

QR test URL:
`watchface://raw.githubusercontent.com/jojaeli69/jaejae/quierrings-gts4mini-qr-test-20261111/QuietRings_GTS4Mini_DIALOG_v1.6.zpk`

Older v1.1–v1.5 ZPKs remain available for rollback.
