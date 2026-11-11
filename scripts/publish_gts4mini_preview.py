from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import io, json, hashlib
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/'GTS4Mini_BatteryLink_v1_Official.zpk'
ZPK=ROOT/'GTS4Mini_BatteryLink_v1_1_Preview.zpk'
ZAB=ROOT/'GTS4Mini_BatteryLink_v1_1_Preview.zab'
def rewrite(data, replacements):
    result=io.BytesIO()
    with ZipFile(io.BytesIO(data)) as source, ZipFile(result,'w') as target:
        for info in source.infolist():
            target.writestr(info,replacements.get(info.filename,source.read(info.filename)))
    return result.getvalue()
def patch(data):
    with ZipFile(io.BytesIO(data)) as f:
        config=json.loads(f.read('app.json'))
    if config['packageInfo']['mode'] not in ('production','preview'):
        raise ValueError('Unexpected mode')
    config['packageInfo']['mode']='preview'
    return rewrite(data,{'app.json':json.dumps(config,ensure_ascii=False,separators=(',',':')).encode()})
data=SOURCE.read_bytes()
with ZipFile(io.BytesIO(data)) as z:
    fixes={p:patch(z.read(p)) for p in ['device.zip','app-side.zip']}
ZPK.write_bytes(rewrite(data,fixes))
md5=hashlib.md5(ZPK.read_bytes()).hexdigest()
manifest={'configVersion':'v2','zpks':[{'name':md5+'.zpk','version':{'code':1,'name':'1.0.0'},'appType':'app','platforms':[{'screenType':'square','screenResolution':'336x384','cpuPlatform':'DIALOG'}],'md5':md5}],'bundleInfo':{'zpm':'3.5.0'}}
with ZipFile(ZAB,'w',ZIP_DEFLATED) as f:
    f.writestr(md5+'.zpk',ZPK.read_bytes())
    f.writestr('manifest.json',json.dumps(manifest,separators=(',',':')))
for p in [ZPK,ZAB]:
    with ZipFile(p) as f: assert f.testzip() is None
    print(p.name,p.stat().st_size,hashlib.sha256(p.read_bytes()).hexdigest())
with ZipFile(ZPK) as z:
    for n in ['device.zip','app-side.zip']:
        with ZipFile(io.BytesIO(z.read(n))) as inner:
            assert json.loads(inner.read('app.json'))['packageInfo']['mode']=='preview'
