package dev.gts4.rebootprobe;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothGatt;
import android.bluetooth.BluetoothGattCallback;
import android.bluetooth.BluetoothGattCharacteristic;
import android.bluetooth.BluetoothGattDescriptor;
import android.bluetooth.BluetoothGattService;
import android.bluetooth.BluetoothManager;
import android.bluetooth.BluetoothProfile;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.InputType;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import org.bouncycastle.asn1.sec.SECNamedCurves;
import org.bouncycastle.asn1.x9.X9ECParameters;
import org.bouncycastle.math.ec.ECPoint;

import java.io.ByteArrayOutputStream;
import java.math.BigInteger;
import java.security.SecureRandom;
import java.util.ArrayDeque;
import java.util.Arrays;
import java.util.Locale;
import java.util.Set;
import java.util.UUID;
import javax.crypto.Cipher;
import javax.crypto.spec.SecretKeySpec;

/**
 * GTS4 experimental authenticated reboot probe (Gadgetbridge-protocol compatible).
 * DEVICE REBOOT IS NOT GUARANTEED. No vendor firmware flashing or pairing reset.
 * Does not persist the Huami auth key; does not transmit it over the Internet.
 */
public class MainActivity extends Activity {
        private static final UUID TX = UUID.fromString("00000016-0000-3512-2118-0009af100700");
    private static final UUID RX = UUID.fromString("00000017-0000-3512-2118-0009af100700");
    private static final UUID CCCD = UUID.fromString("00002902-0000-1000-8000-00805f9b34fb");
    private static final int AUTH_ENDPOINT = 0x0082;
    private static final int BATTERY_ENDPOINT = 0x0029;
    private final Handler ui = new Handler(Looper.getMainLooper());
    private final ArrayDeque<Command> queue = new ArrayDeque<>();
    private final SecureRandom rng = new SecureRandom();
    private BluetoothAdapter adapter;
    private BluetoothGatt gatt;
    private BluetoothGattCharacteristic tx, rx;
    private TextView log;
    private EditText keyField;
    private Button authButton, batteryButton;
    private StringBuilder logLines = new StringBuilder();
    private boolean notificationsReady=false, authenticated=false, busy=false;
    private BigInteger privateScalar;
    private long encryptedSequence=0;
    private boolean currentEncrypted=false;
    private byte[] secretKey=null, sharedSessionKey=null;
    private int writeHandle=0, mtu=23;
    private int partialHandle=-1, expectedLength, currentType;
    private ByteArrayOutputStream partial=null;
    private boolean disposed=false;

    private static final class Command {
        final BluetoothGattCharacteristic ch;
        final byte[] bytes;
        final String type;
        Command(BluetoothGattCharacteristic c,byte[] b,String t) {ch=c;bytes=b;type=t;}
    }

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        LinearLayout root=new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(18,24,18,24);
        ScrollView page=new ScrollView(this); page.addView(root);
        TextView head=new TextView(this);
        head.setText("GTS 4 Mini 충전상태 진단 v1.0\n\nHuami 인증 후 배터리 조회(0x0029)만 수행. 펌웨어·페어링 설정은 변경하지 않습니다. Zepp 동시 연결은 미검증이며 충돌할 수 있습니다.");
        head.setTextSize(16);root.addView(head);
        Button paired=button(root,"1. 페어링 기기 표시");
        authButton=button(root,"2. 인증 시작 (키 입력 후)");authButton.setEnabled(false);
        batteryButton=button(root,"3. Mini 충전상태 읽기 (인증 후)");
        batteryButton.setEnabled(false);
        keyField=new EditText(this);
        keyField.setHint("Huami 인증키 32자리 HEX (기기에서만 사용)");
        keyField.setSingleLine(true);
        keyField.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        root.addView(keyField,3);
        Button copy=button(root,"로그 복사 (인증키 제외)");
        log=new TextView(this);
        log.setTextSize(12);
        log.setTextIsSelectable(true);
        root.addView(log);
        setContentView(page);
        BluetoothManager manager=(BluetoothManager)getSystemService(Context.BLUETOOTH_SERVICE);
        adapter=manager==null?null:manager.getAdapter();
        paired.setOnClickListener(v->showPaired(root));
        authButton.setOnClickListener(v->beginAuth());
        batteryButton.setOnClickListener(v->new AlertDialog.Builder(this)
            .setTitle("GTS 4 Mini 배터리 상태 읽기")
            .setMessage("인증된 Huami 세션에서 배터리 요청 0x0029/0x03을 1회 전송해요. 다른 앱(Zepp)의 연결에 영향이 있을 수 있어요. 펌웨어 명령은 보내지 않아요.")
            .setNegativeButton("취소",null).setPositiveButton("읽기",(d,w)->sendBatteryRequest()).show());
        copy.setOnClickListener(v->{
            ClipboardManager cm=(ClipboardManager)getSystemService(Context.CLIPBOARD_SERVICE);
            cm.setPrimaryClip(ClipData.newPlainText("GTS4 Mini Charge Diagnostics",logLines.toString()));
            append("진단 로그 복사됨. 인증키는 기록하지 않음.");
        });
        permission();
        append("시작: 인증키는 메모리에서만 사용하고 서버로 보내지 않음.");
    }
    private Button button(LinearLayout p,String name) {
        Button b=new Button(this);b.setText(name);p.addView(b);return b;
    }
    private void append(String value) {
        ui.post(()->{
            if(disposed)return;
            logLines.append(value).append('\n');
            log.setText(logLines.toString());
            android.util.Log.i("MiniChargeAuthProbe",value);
        });
    }
    private void permission(){
        if(Build.VERSION.SDK_INT>=31){
            if(checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT)!=PackageManager.PERMISSION_GRANTED)
                requestPermissions(new String[]{Manifest.permission.BLUETOOTH_CONNECT},100);
        }else if(checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)!=PackageManager.PERMISSION_GRANTED)
            requestPermissions(new String[]{Manifest.permission.ACCESS_FINE_LOCATION},100);
    }
    private boolean permissionReady() {
        return Build.VERSION.SDK_INT <31 || checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT)==PackageManager.PERMISSION_GRANTED;
    }
    private void showPaired(LinearLayout root) {
        if(!permissionReady()) {permission();return;}
        if(adapter==null||!adapter.isEnabled()){append("휴대폰 블루투스를 켜야 해.");return;}
        Set<BluetoothDevice> paired=adapter.getBondedDevices();
        append("페어링 기기 수 "+paired.size());
        for(BluetoothDevice dev:paired){
            String name=dev.getName();
            // Avoid controls for unrelated peripherals.
            if(name==null||!name.toLowerCase(Locale.US).replaceAll("[^a-z0-9]", "").contains("gts4mini"))continue;
            Button row=button(root,(name==null?"이름 없음":name)+" · 연결");
            row.setOnClickListener(v->connect(dev));
        }
        append("GTS 4 Mini가 목록에 없다면 기존 Zepp 페어링을 유지하고 Bluetooth 설정을 확인하세요.");
    }
    private void cleanSecrets() {
        if(secretKey!=null)Arrays.fill(secretKey,(byte)0);
        if(sharedSessionKey!=null)Arrays.fill(sharedSessionKey,(byte)0);
        secretKey=null;sharedSessionKey=null;privateScalar=null;
    }
    private void connect(BluetoothDevice dev){
        if(!permissionReady())return;
        if(gatt!=null){try{gatt.disconnect();gatt.close();}catch(Exception ignored){}}
        clearConnectionState();
        append("GTS 4 Mini 별도 인증 세션 연결 시도; Zepp와 충돌할 수 있습니다.");
        gatt=dev.connectGatt(this,false,callbacks,BluetoothDevice.TRANSPORT_LE);
    }
    private void clearConnectionState(){
        cleanSecrets();
        notificationsReady=false;authenticated=false;busy=false;queue.clear();
        tx=null;rx=null;partial=null;partialHandle=-1;currentEncrypted=false;encryptedSequence=0;
        ui.post(()->{authButton.setEnabled(false);batteryButton.setEnabled(false);});
    }
    private BluetoothGattCharacteristic getChar(BluetoothGatt bg,UUID id) {
        for(BluetoothGattService svc:bg.getServices()){
            BluetoothGattCharacteristic c=svc.getCharacteristic(id);
            if(c!=null)return c;
        }
        return null;
    }
    private final BluetoothGattCallback callbacks=new BluetoothGattCallback(){
        @Override public void onConnectionStateChange(BluetoothGatt bg,int status,int state){
            if(state==BluetoothProfile.STATE_CONNECTED && status==BluetoothGatt.GATT_SUCCESS) {
                append("BLE 연결됨. 서비스 검색");
                bg.discoverServices();
            } else if(state==BluetoothProfile.STATE_DISCONNECTED){
                append("연결 종료 status="+status);
                clearConnectionState();
            } else append("BLE 상태="+state+" status="+status);
        }
        @Override public void onServicesDiscovered(BluetoothGatt bg,int status){
            if(status!=0){append("GATT 서비스 검색 실패="+status);return;}
            tx=getChar(bg,TX);rx=getChar(bg,RX);
            append("Huami 2021 특성 확인 TX="+(tx!=null)+" RX="+(rx!=null));
            if(tx==null||rx==null){append("인증에 필요한 Huami 2021 특성을 찾지 못함.");return;}
            BluetoothGattDescriptor cc=rx.getDescriptor(CCCD);
            if(cc==null){append("0x17 알림 CCCD 누락");return;}
            if(!bg.setCharacteristicNotification(rx,true)) {append("알림 등록 실패");return;}
            try{
                if(Build.VERSION.SDK_INT>=33){
                    int ret=bg.writeDescriptor(cc,BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE);
                    append("인증 알림 구독 요청="+ret);
                }else{
                    cc.setValue(BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE);
                    append("인증 알림 구독 요청="+bg.writeDescriptor(cc));
                }
            }catch(Exception e){append("알림 설정 예외: "+e.getClass().getSimpleName());}
        }
        @Override public void onDescriptorWrite(BluetoothGatt bg,BluetoothGattDescriptor desc,int status) {
            if(CCCD.equals(desc.getUuid())&&RX.equals(desc.getCharacteristic().getUuid())){
                notificationsReady=status==0;
                append("0x17 인증 알림 구독 status="+status);
                ui.post(()->authButton.setEnabled(notificationsReady));
            }
        }
        @Override public void onCharacteristicChanged(BluetoothGatt bg,BluetoothGattCharacteristic c,byte[] value){
            onIncoming(c,value);
        }
        @SuppressWarnings("deprecation")
        @Override public void onCharacteristicChanged(BluetoothGatt bg,BluetoothGattCharacteristic c){
            if(Build.VERSION.SDK_INT<33)onIncoming(c,c.getValue());
        }
        @Override public void onCharacteristicWrite(BluetoothGatt bg,BluetoothGattCharacteristic c,int status){
            
            if(status!=0)append("쓰기 오류: "+status);
            synchronized(queue) {busy=false; if(status!=0)queue.clear();}
            nextWrite();
        }
        @Override public void onMtuChanged(BluetoothGatt bg,int mtuValue,int status){
            if(status==0)mtu=mtuValue;
            append("MTU="+mtu);
        }
    };
    private void onIncoming(BluetoothGattCharacteristic c,byte[] value) {
        if(!RX.equals(c.getUuid())||value==null||value.length<5)return;
        if((value[0]&255)!=3) {append("0x17 비프레임 이벤트 "+hex(value,16));return;}
        int flags=value[1]&255,handle=value[3]&255,count=value[4]&255;
        boolean first=(flags&1)!=0,last=(flags&2)!=0,needsAck=(flags&4)!=0,encrypted=(flags&8)!=0;
        int start=5;
        if(first) {
            if(value.length<11)return;
            expectedLength=(value[5]&255)|((value[6]&255)<<8)|((value[7]&255)<<16)|((value[8]&255)<<24);
            currentType=(value[9]&255)|((value[10]&255)<<8);
            if(expectedLength<0||expectedLength>16384){append("과도한 프레임 길이 차단: "+expectedLength);return;}
            currentEncrypted=encrypted;
            partial=new ByteArrayOutputStream();
            partialHandle=handle;start=11;
        }
        if(partial==null||partialHandle!=handle)return;
        partial.write(value,start,value.length-start);
        if(needsAck)enqueue(new Command(rx,new byte[]{4,0,(byte)handle,1,(byte)count},"chunk ACK"));
        if(last){
            byte[] bytes=partial.toByteArray();
            partial=null;partialHandle=-1;
            if(currentEncrypted) {
                try {bytes=decryptPayload(bytes,expectedLength,handle);}
                catch(Exception e){append("Huami 암호화 응답 검증 실패: "+e.getClass().getSimpleName());return;}
            }
            if(bytes.length!=expectedLength){append("응답 길이 불일치 "+bytes.length+" vs "+expectedLength);return;}
            if(currentType==AUTH_ENDPOINT)processAuth(bytes);
            else if(currentType==BATTERY_ENDPOINT)processBattery(bytes);
            else append("다른 endpoint=0x"+Integer.toHexString(currentType)+" (무시)");
        }
    }
    private void beginAuth(){
        if(!notificationsReady||tx==null){append("인증 채널 준비 안됨");return;}
        cleanSecrets();
        String raw=keyField.getText().toString().trim().replace(" ","");
        if(raw.startsWith("0x")||raw.startsWith("0X"))raw=raw.substring(2);
        if(!raw.matches("[0-9a-fA-F]{32}")){append("인증키는 16바이트(HEX 32자리)여야 함.");return;}
        secretKey=new byte[16];
        for(int i=0;i<16;i++)secretKey[i]=(byte)Integer.parseInt(raw.substring(i*2,i*2+2),16);
        // Do not persist, log, or copy sensitive key.
        keyField.setText("");
        authenticated=false;
        ui.post(()->batteryButton.setEnabled(false));
        try{
            X9ECParameters ec=SECNamedCurves.getByName("sect163r2");
            if(ec==null)throw new IllegalStateException("B-163 curve unavailable");
            do {
                privateScalar=new BigInteger(ec.getN().bitLength(),rng);
            }while(privateScalar.signum()==0||privateScalar.compareTo(ec.getN())>=0);
            ECPoint p=ec.getG().multiply(privateScalar).normalize();
            byte[] publicXY=new byte[48];
            System.arraycopy(le24(p.getAffineXCoord().toBigInteger()),0,publicXY,0,24);
            System.arraycopy(le24(p.getAffineYCoord().toBigInteger()),0,publicXY,24,24);
            byte[] request=new byte[52];
            request[0]=4;request[1]=2;request[2]=0;request[3]=2;
            System.arraycopy(publicXY,0,request,4,48);
            append("ECDH B-163 공개키 전송 시작 (비밀키 기록하지 않음)");
            sendAuthPayload(request);
        }catch(Exception e){append("키교환 준비 오류: "+e.getClass().getSimpleName()+" "+e.getMessage());cleanSecrets();}
    }
    private static byte[] le24(BigInteger b) {
        byte[] src=b.toByteArray(),out=new byte[24];
        for(int i=0;i<src.length&&i<24;i++)out[i]=src[src.length-1-i];
        return out;
    }
    private static BigInteger fromLe24(byte[] raw,int start){
        byte[] reversed=new byte[24];
        for(int i=0;i<24;i++)reversed[23-i]=raw[start+i];
        return new BigInteger(1,reversed);
    }
    private static byte[] encryptBlock(byte[] value,byte[] key) throws Exception {
        Cipher c=Cipher.getInstance("AES/ECB/NoPadding");
        c.init(Cipher.ENCRYPT_MODE,new SecretKeySpec(key,"AES"));
        return c.doFinal(value);
    }
    private void processAuth(byte[] payload){
        if(payload.length<3)return;
        if((payload[0]&255)==0x10 && (payload[1]&255)==4 && (payload[2]&255)==1){
            if(payload.length<67){append("인증 challenge 길이 짧음 "+payload.length);return;}
            if(secretKey==null||privateScalar==null){append("키교환 상태 없음");return;}
            try{
                X9ECParameters ec=SECNamedCurves.getByName("sect163r2");
                BigInteger x=fromLe24(payload,19), y=fromLe24(payload,43);
                ECPoint remote=ec.getCurve().createPoint(x,y);
                if(remote.isInfinity()||!remote.isValid())throw new IllegalArgumentException("원격 공개키 검증 실패");
                ECPoint shared=remote.multiply(privateScalar).normalize();
                byte[] s=le24(shared.getAffineXCoord().toBigInteger());
                sharedSessionKey=new byte[16];
                for(int i=0;i<16;i++)sharedSessionKey[i]=(byte)(s[i+8]^secretKey[i]);
                encryptedSequence=((long)(s[0]&255))|(((long)(s[1]&255))<<8)|(((long)(s[2]&255))<<16)|(((long)(s[3]&255))<<24);
                byte[] nonce=Arrays.copyOfRange(payload,3,19);
                byte[] answer=new byte[33];answer[0]=5;
                System.arraycopy(encryptBlock(nonce,secretKey),0,answer,1,16);
                System.arraycopy(encryptBlock(nonce,sharedSessionKey),0,answer,17,16);
                append("기기 챌린지 수신 및 AES 응답 전송");
                sendAuthPayload(answer);
                Arrays.fill(nonce,(byte)0);Arrays.fill(answer,(byte)0);Arrays.fill(s,(byte)0);
            }catch(Exception e){append("챌린지 처리 실패: "+e.getClass().getSimpleName()+" "+e.getMessage());cleanSecrets();}
        }else if((payload[0]&255)==0x10&&(payload[1]&255)==5&&(payload[2]&255)==1){
            authenticated=true;
            append("Mini 인증 응답 10 05 01 수신. 배터리 상태 읽기 버튼 사용 가능.");
            ui.post(()->batteryButton.setEnabled(true));
        }else if((payload[0]&255)==0x10&&(payload[1]&255)==5){
            append("인증 거부: 응답 코드="+(payload[2]&255));
            cleanSecrets();
        }else{
            append("인증 메시지 타입 "+hex(payload,12));
        }
    }
    private void sendAuthPayload(byte[] payload){
        if(tx==null)return;
        writeHandle=(writeHandle+1)&255;
        int left=payload.length,count=0;
        boolean first=true;
        while(left>0){
            int head=first?11:5;
            int max=Math.max(1,mtu-3-head);
            int n=Math.min(max,left);
            byte[] frame=new byte[head+n];
            frame[0]=3;
            frame[1]=(byte)((first?1:0)|(left<=n?6:0));
            frame[2]=0;frame[3]=(byte)writeHandle;frame[4]=(byte)count;
            if(first){
                frame[5]=(byte)payload.length;
                frame[6]=(byte)(payload.length>>8);
                frame[7]=(byte)(payload.length>>16);
                frame[8]=(byte)(payload.length>>24);
                frame[9]=(byte)AUTH_ENDPOINT;
                frame[10]=(byte)(AUTH_ENDPOINT>>8);
            }
            System.arraycopy(payload,payload.length-left,frame,head,n);
            enqueue(new Command(tx,frame,"auth-frame"));
            left-=n;count++;first=false;
        }
    }
    private void enqueue(Command command){
        synchronized(queue){queue.addLast(command);}
        nextWrite();
    }
    @SuppressWarnings("deprecation")
    private void nextWrite(){
        Command c;
        synchronized(queue){
            if(busy||queue.isEmpty())return;
            c=queue.removeFirst();busy=true;
        }
        try{
            if(gatt==null){synchronized(queue){busy=false;queue.clear();}return;}
            int type= ((c.ch.getProperties()&BluetoothGattCharacteristic.PROPERTY_WRITE)!=0) ?
               BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT:BluetoothGattCharacteristic.WRITE_TYPE_NO_RESPONSE;
            if(Build.VERSION.SDK_INT>=33){
                int result=gatt.writeCharacteristic(c.ch,c.bytes,type);
                if(result!=0){append("writeCharacteristic 실패 rc="+result+" type="+c.type);synchronized(queue){busy=false;queue.clear();}}
            }else{
                c.ch.setWriteType(type);c.ch.setValue(c.bytes);
                if(!gatt.writeCharacteristic(c.ch)){append("writeCharacteristic 거절 type="+c.type);synchronized(queue){busy=false;queue.clear();}}
            }
        }catch(Exception e){append("쓰기 예외: "+e.getClass().getSimpleName());synchronized(queue){busy=false;queue.clear();}}
    }
    /** Reuse only the verified Huami 2021 AES/ECDH session to request battery.
     * Never send firmware, reboot, unpair, or settings commands.
     */
    private void sendBatteryRequest() {
        if(!authenticated || sharedSessionKey==null || tx==null) {append("Huami 인증 먼저 필요");return;}
        try {
            sendEncryptedPayload(BATTERY_ENDPOINT,new byte[]{0x03});
            append("배터리 endpoint=0x0029 / request=0x03 전송 (응답 대기)");
        }catch(Exception e){append("배터리 조회 오류: "+e.getClass().getSimpleName());}
    }
    private static byte[] deriveKey(byte[] session,int handle) {
        byte[] key=new byte[16];
        for(int i=0;i<16;i++)key[i]=(byte)(session[i]^handle);
        return key;
    }
    private byte[] decryptPayload(byte[] cipherText,int length,int handle) throws Exception {
        if(sharedSessionKey==null||cipherText.length%16!=0||length<0||length+8>cipherText.length)
            throw new IllegalArgumentException("Bad encrypted Huami battery frame");
        Cipher c=Cipher.getInstance("AES/ECB/NoPadding");
        byte[] k=deriveKey(sharedSessionKey,handle);
        try{
            c.init(Cipher.DECRYPT_MODE,new SecretKeySpec(k,"AES"));
            byte[] decoded=c.doFinal(cipherText);
            java.util.zip.CRC32 crc=new java.util.zip.CRC32();
            crc.update(decoded,0,length+4);
            long expected=((long)decoded[length+4]&255)|(((long)decoded[length+5]&255)<<8)|
              (((long)decoded[length+6]&255)<<16)|(((long)decoded[length+7]&255)<<24);
            if(crc.getValue()!=expected)throw new IllegalArgumentException("CRC32 mismatch");
            return Arrays.copyOf(decoded,length);
        }finally{Arrays.fill(k,(byte)0);}
    }
    private void sendEncryptedPayload(int endpoint,byte[] data) throws Exception {
        int handle=writeHandle=(writeHandle+1)&255;
        int plainLength=data.length;
        int padded=(plainLength+8+15)&~15;
        byte[] pt=new byte[padded];
        System.arraycopy(data,0,pt,0,plainLength);
        long seq=encryptedSequence++ & 0xFFFFFFFFL;
        for(int i=0;i<4;i++)pt[plainLength+i]=(byte)(seq>>(8*i));
        java.util.zip.CRC32 crc=new java.util.zip.CRC32();
        crc.update(pt,0,plainLength+4);
        long v=crc.getValue();
        for(int i=0;i<4;i++)pt[plainLength+4+i]=(byte)(v>>(8*i));
        byte[] k=deriveKey(sharedSessionKey,handle);
        Cipher enc=Cipher.getInstance("AES/ECB/NoPadding");
        enc.init(Cipher.ENCRYPT_MODE,new SecretKeySpec(k,"AES"));
        byte[] cipher=enc.doFinal(pt);
        Arrays.fill(k,(byte)0);
        Arrays.fill(pt,(byte)0);
        int left=cipher.length,count=0;
        while(left>0){
            boolean first=count==0;
            int head=first?11:5;
            int n=Math.min(Math.max(1,mtu-3-head),left);
            byte[] frame=new byte[head+n];
            frame[0]=3;
            frame[1]=(byte)((first?1:0)|(left<=n?6:0)|8);
            frame[2]=0;frame[3]=(byte)handle;frame[4]=(byte)count;
            if(first){
                frame[5]=(byte)plainLength;
                frame[6]=(byte)(plainLength>>8);
                frame[7]=(byte)(plainLength>>16);
                frame[8]=(byte)(plainLength>>24);
                frame[9]=(byte)endpoint;
                frame[10]=(byte)(endpoint>>8);
            }
            System.arraycopy(cipher,cipher.length-left,frame,head,n);
            enqueue(new Command(tx,frame,"battery-read-only"));
            left-=n;count++;
        }
        Arrays.fill(cipher,(byte)0);
    }
    private void processBattery(byte[] payload){
        // Reply is: 0x04, reserved, battery percentage, state.
        if(!authenticated||payload==null||payload.length<4||(payload[0]&255)!=0x04){
            append("배터리 응답 미확인: 프레임 형식 불일치");return;
        }
        int percent=payload[2]&255,raw=payload[3]&255;
        if(percent>100){append("배터리 응답 범위 오류");return;}
        String state=raw==1?"충전 중":raw==0?"충전 중 아님":"알 수 없음(값="+raw+")";
        append("Huami 실제 배터리 상태: "+percent+"% · "+state+" / raw="+raw);
        if(percent==100)append("100% 확인. '완충/충전 완료' 플래그는 아직 별도 확인 필요.");
        append("시험 성공: ChargeStatus endpoint=0x0029. 다음 단계 Battery Trio 통합 가능.");
    }
    private static String hex(byte[] b,int limit){
        StringBuilder out=new StringBuilder();
        for(int i=0;i<b.length&&i<limit;i++)out.append(String.format(Locale.US,"%02X ",b[i]&255));
        return out.toString().trim();
    }
    @Override protected void onDestroy(){
        disposed=true;cleanSecrets();if(gatt!=null){try{gatt.disconnect();gatt.close();}catch(Exception ignored){}gatt=null;}
        super.onDestroy();
    }
}
