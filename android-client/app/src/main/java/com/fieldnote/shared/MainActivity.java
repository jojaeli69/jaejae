package com.fieldnote.shared;
import android.app.Activity;
import android.os.*;
import android.Manifest;
import android.content.*;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.net.Uri;
import android.provider.*;
import android.webkit.*;
import android.widget.Toast;
import android.util.Base64;
import org.json.*;
import java.io.*;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

public class MainActivity extends Activity {
  private final int VOICE=201, FILES=202, CAMERA=203, CONTACT=204, CALLS=205, LOCATION=206;
  private WebView web;
  private String kind="photo";
  private Uri photoUri;
  private File tempDir;
  private final ConcurrentHashMap<String,File> originals=new ConcurrentHashMap<>();
  private final ConcurrentHashMap<String,File> saving=new ConcurrentHashMap<>();
  private final ConcurrentHashMap<String,String[]> saveLabels=new ConcurrentHashMap<>();
  private void toast(String msg){runOnUiThread(()->Toast.makeText(this,msg,Toast.LENGTH_SHORT).show());}
  private void js(String cmd){runOnUiThread(()->web.evaluateJavascript(cmd,null));}
  private void emit(String fn,String s){js("window."+fn+"("+JSONObject.quote(s)+")");}
  @Override public void onCreate(Bundle b){super.onCreate(b);
    tempDir=new File(getFilesDir(),"nnm-transfer");tempDir.mkdirs();
    // Keep the image destination if Android recreates us during camera use.
    String lastUri=b==null?null:b.getString("nnm.cameraUri");
    if(lastUri==null)lastUri=getPreferences(MODE_PRIVATE).getString("nnm.cameraUri",null);
    if(lastUri!=null)try{photoUri=Uri.parse(lastUri);}catch(Exception ignored){}
    kind=b==null?getPreferences(MODE_PRIVATE).getString("nnm.cameraKind","photo"):b.getString("nnm.cameraKind","photo");
    web=new WebView(this);setContentView(web);
    WebSettings st=web.getSettings();st.setJavaScriptEnabled(true);st.setDomStorageEnabled(true);
    st.setDatabaseEnabled(true);st.setAllowContentAccess(true);st.setGeolocationEnabled(true);
    web.addJavascriptInterface(new NativeFiles(),"NeonaNative");
    web.setWebChromeClient(new WebChromeClient(){
      @Override public void onGeolocationPermissionsShowPrompt(String origin,GeolocationPermissions.Callback callback){
        callback.invoke(origin,checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)==PackageManager.PERMISSION_GRANTED,false);
      }
      @Override public void onPermissionRequest(PermissionRequest request){
        runOnUiThread(()->{
          if(checkSelfPermission(Manifest.permission.RECORD_AUDIO)!=PackageManager.PERMISSION_GRANTED){request.deny();return;}
          ArrayList<String> allowed=new ArrayList<>();
          for(String r:request.getResources())if(PermissionRequest.RESOURCE_AUDIO_CAPTURE.equals(r))allowed.add(r);
          if(allowed.isEmpty())request.deny();else request.grant(allowed.toArray(new String[0]));
        });
      }
    });
    web.setWebViewClient(new WebViewClient(){
      @Override public WebResourceResponse shouldInterceptRequest(WebView w,WebResourceRequest req){
        Uri uri=req.getUrl();
        if(!"https".equals(uri.getScheme())||!"appassets.androidplatform.net".equals(uri.getHost()))return null;
        String path=uri.getPath();if(path==null||path.equals("/"))path="/index.html";
        if(path.contains(".."))return null;
        String file=path.substring(1);
        try{
          String mime=file.endsWith(".html")?"text/html":file.endsWith(".png")?"image/png":"application/octet-stream";
          return new WebResourceResponse(mime,"UTF-8",getAssets().open(file));
        }catch(Exception ex){return new WebResourceResponse("text/plain","UTF-8",new ByteArrayInputStream(new byte[0]));}
      }
      @Override public boolean shouldOverrideUrlLoading(WebView w,WebResourceRequest req){
        Uri uri=req.getUrl();
        if("fieldnote".equals(uri.getScheme())){runOnUiThread(()->route(uri));return true;}
        if("https".equals(uri.getScheme())&&"appassets.androidplatform.net".equals(uri.getHost()))return false;
        if("http".equals(uri.getScheme())||"https".equals(uri.getScheme())){try{startActivity(new Intent(Intent.ACTION_VIEW,uri));}catch(Exception ignored){}}
        return true;
      }
    });
    web.loadUrl("https://appassets.androidplatform.net/index.html");
  }
  private void route(Uri uri){
    String host=uri.getHost();if(host==null)return;
    switch(host){
      case "pick-photo":pick("photo");break;case "pick-report":pick("report");break;case "pick-other":pick("other");break;
      case "camera-photo":camera("photo");break;case "camera-report":camera("report");break;case "voice":voice();break;case "location":location();break;
      case "choose-contact":contact();break;case "recent-calls":calls();break;
      case "open-attachment":openExternal(uri.getQueryParameter("uri"));break;
      case "exit":finish();break;
    }
  }
  private void pick(String k){kind=k;
  if("photo".equals(k)){
    // Android Photo Picker: native gallery with single-tap multi-selection.
    if(Build.VERSION.SDK_INT>=33){
      try{
        Intent images=new Intent(MediaStore.ACTION_PICK_IMAGES);
        images.setType("image/*");
        images.putExtra(MediaStore.EXTRA_PICK_IMAGES_MAX,Math.min(100,MediaStore.getPickImagesMaxLimit()));
        startActivityForResult(images,FILES);
        return;
      }catch(Exception ignored){}
    }
    Intent fallback=new Intent(Intent.ACTION_GET_CONTENT);
    fallback.setType("image/*");fallback.addCategory(Intent.CATEGORY_OPENABLE);
    fallback.putExtra(Intent.EXTRA_ALLOW_MULTIPLE,true);
    try{startActivityForResult(Intent.createChooser(fallback,"사진 여러 장 선택"),FILES);}
    catch(Exception e){toast("갤러리를 열지 못했어");}
    return;
  }
  Intent i=new Intent(Intent.ACTION_OPEN_DOCUMENT);
  i.addCategory(Intent.CATEGORY_OPENABLE);i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
  i.setType("*/*");i.putExtra(Intent.EXTRA_ALLOW_MULTIPLE,true);
  if("report".equals(k))i.putExtra(Intent.EXTRA_MIME_TYPES,new String[]{"application/pdf","image/*","application/msword","application/vnd.openxmlformats-officedocument.wordprocessingml.document","application/vnd.ms-excel","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet","application/haansofthwp","application/x-hwp"});
  try{startActivityForResult(i,FILES);}catch(Exception ex){toast("보고서·파일 선택기를 열지 못했어");}
}
  private void rememberCamera(){
    getPreferences(MODE_PRIVATE).edit()
      .putString("nnm.cameraUri",photoUri==null?null:photoUri.toString())
      .putString("nnm.cameraKind",kind).apply();
  }
  @Override protected void onSaveInstanceState(Bundle bundle){
    if(photoUri!=null)bundle.putString("nnm.cameraUri",photoUri.toString());
    bundle.putString("nnm.cameraKind",kind);
    super.onSaveInstanceState(bundle);
  }
  private void camera(String k){
    kind=k;
    try{
      ContentValues v=new ContentValues();
      v.put(MediaStore.Images.Media.DISPLAY_NAME,"너나메모_"+System.currentTimeMillis()+".jpg");
      v.put(MediaStore.Images.Media.MIME_TYPE,"image/jpeg");
      if(Build.VERSION.SDK_INT>=29)
        v.put(MediaStore.Images.Media.RELATIVE_PATH,Environment.DIRECTORY_PICTURES+"/너나메모");
      // Do not set IS_PENDING=1: the system camera runs as another app.
      photoUri=getContentResolver().insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI,v);
      if(photoUri==null){toast("사진 저장 위치를 만들 수 없어");return;}
      rememberCamera();
      Intent intent=new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
      intent.putExtra(MediaStore.EXTRA_OUTPUT,photoUri);
      intent.setClipData(ClipData.newRawUri("NeonaMemo camera output",photoUri));
      intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION|Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
      for(android.content.pm.ResolveInfo info:getPackageManager().queryIntentActivities(intent,PackageManager.MATCH_DEFAULT_ONLY)){
        if(info.activityInfo!=null)try{
          grantUriPermission(info.activityInfo.packageName,photoUri,
            Intent.FLAG_GRANT_READ_URI_PERMISSION|Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
        }catch(Exception ignored){}
      }
      startActivityForResult(intent,CAMERA);
    }catch(Exception e){
      android.util.Log.e("NeonaMemoCamera","Camera intent failed",e);
      toast("카메라 실행 실패");
      if(photoUri!=null){discardPhoto(photoUri);photoUri=null;rememberCamera();}
    }
  }
  private void discardPhoto(Uri uri){
    try{getContentResolver().delete(uri,null,null);}
    catch(Exception e){android.util.Log.w("NeonaMemoCamera","Cannot remove empty photo",e);}
  }
  private boolean photoHasData(Uri uri){
    try(InputStream input=getContentResolver().openInputStream(uri)){
      return input!=null&&input.read()!=-1;
    }catch(Exception e){android.util.Log.w("NeonaMemoCamera","Camera output not readable",e);return false;}
  }
  private void finishCamera(int result){
    final Uri uri=photoUri;final String currentKind=kind;
    photoUri=null;rememberCamera();
    if(uri==null){toast("사진 저장 위치가 사라졌어. 다시 촬영해줘");return;}
    new Thread(()->{
      if(result==RESULT_OK){
        boolean ready=false;
        for(int i=0;i<10;i++){
          if(photoHasData(uri)){ready=true;break;}
          try{Thread.sleep(220);}catch(InterruptedException ignored){Thread.currentThread().interrupt();break;}
        }
        if(ready)importFiles(Collections.singletonList(uri),currentKind);
        else {discardPhoto(uri);toast("사진이 저장되지 않았어. 다시 촬영해줘");}
      } else if(!photoHasData(uri))discardPhoto(uri);
      else toast("촬영이 취소됐어. 갤러리에서 사진을 선택할 수 있어");
      try{revokeUriPermission(uri,Intent.FLAG_GRANT_READ_URI_PERMISSION|Intent.FLAG_GRANT_WRITE_URI_PERMISSION);}
      catch(Exception ignored){}
    },"NNM-ReturnFromCamera").start();
  }
  private void voice(){try{
    Intent i=new Intent("android.speech.action.RECOGNIZE_SPEECH");
    i.putExtra("android.speech.extra.LANGUAGE_MODEL","free_form");
    i.putExtra("android.speech.extra.LANGUAGE","ko-KR");startActivityForResult(i,VOICE);
  }catch(Exception e){js("window.nativeVoiceError()");}}
  private void location(){if(checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)!=PackageManager.PERMISSION_GRANTED){
    requestPermissions(new String[]{Manifest.permission.ACCESS_FINE_LOCATION,Manifest.permission.ACCESS_COARSE_LOCATION},LOCATION);return;}
    js("window.nativeGeoPermissionResult(true)");
  }
  private void contact(){try{startActivityForResult(new Intent(Intent.ACTION_PICK,ContactsContract.CommonDataKinds.Phone.CONTENT_URI),CONTACT);}
    catch(Exception e){toast("연락처 열기 실패");}}
  private void calls(){if(checkSelfPermission(Manifest.permission.READ_CALL_LOG)!=PackageManager.PERMISSION_GRANTED){
    requestPermissions(new String[]{Manifest.permission.READ_CALL_LOG},CALLS);return;}
    deliverCalls();
  }
  private void deliverCalls(){JSONArray out=new JSONArray();String reason="empty";
    try(Cursor c=getContentResolver().query(CallLog.Calls.CONTENT_URI,new String[]{CallLog.Calls.NUMBER,CallLog.Calls.DATE,CallLog.Calls.TYPE},null,null,CallLog.Calls.DATE+" DESC")){
      if(c!=null)while(c.moveToNext()&&out.length()<30){JSONObject j=new JSONObject();
        j.put("number",c.getString(0));j.put("when",String.valueOf(c.getLong(1)));
        int t=c.getInt(2);j.put("type",t==1?"수신":t==2?"발신":"부재중");out.put(j);}
    }catch(Exception e){reason="security";}
    js("window.nativeRecentCallResult("+JSONObject.quote(Uri.encode(out.toString()))+","+JSONObject.quote(reason)+")");
  }
  private void openExternal(String source){try{Uri uri=Uri.parse(source);String mime=getContentResolver().getType(uri);
    Intent i=new Intent(Intent.ACTION_VIEW).setDataAndType(uri,mime==null?"*/*":mime);
    i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);startActivity(Intent.createChooser(i,"원본 열기"));
  }catch(Exception e){toast("원본을 열 수 없어");}}
  private String filename(Uri uri){try(Cursor c=getContentResolver().query(uri,new String[]{OpenableColumns.DISPLAY_NAME},null,null,null)){
      if(c!=null&&c.moveToFirst())return c.getString(0);
    }catch(Exception ignored){}return "첨부_"+System.currentTimeMillis();
  }
  private void importFiles(List<Uri> files,String fileKind){new Thread(()->{
    JSONArray result=new JSONArray();
    for(Uri uri:files){String id=UUID.randomUUID().toString();File temp=new File(tempDir,id);
      try(InputStream input=getContentResolver().openInputStream(uri);OutputStream output=new FileOutputStream(temp)){
        if(input==null)throw new IOException("Cannot read original");
        byte[] bytes=new byte[65536];long total=0;int n;
        while((n=input.read(bytes))!=-1){total+=n;if(total>24*1024*1024)throw new IOException("Large file");output.write(bytes,0,n);}
        String mime=getContentResolver().getType(uri),name=filename(uri);
        JSONObject obj=new JSONObject();obj.put("id",id);obj.put("kind",fileKind);obj.put("name",name);
        obj.put("size",total);obj.put("mime",mime==null?"application/octet-stream":mime);obj.put("storage","android-local");
        originals.put(id,temp);result.put(obj);
      }catch(Exception e){temp.delete();}
    }
    if(result.length()>0)emit("nativeAttachmentPicked",Uri.encode(result.toString()));
    else toast("원본을 읽을 수 없어 · 최대 24MB 지원");
  }).start();}
  @Override protected void onActivityResult(int code,int result,Intent data){super.onActivityResult(code,result,data);
    if(code==FILES){if(result==RESULT_OK&&data!=null){ArrayList<Uri> all=new ArrayList<>();
        if(data.getClipData()!=null){for(int i=0;i<data.getClipData().getItemCount();i++)all.add(data.getClipData().getItemAt(i).getUri());}
        else if(data.getData()!=null)all.add(data.getData());
        if(!all.isEmpty())importFiles(all,kind);}return;}
    if(code==CAMERA){finishCamera(result);return;}
    if(code==VOICE){if(result==RESULT_OK&&data!=null){ArrayList<String> s=data.getStringArrayListExtra("android.speech.extra.RESULTS");
        if(s!=null&&!s.isEmpty()){emit("nativeVoiceResult",Uri.encode(s.get(0)));return;}}
      js("window.nativeVoiceError()");return;}
    if(code==CONTACT){if(result==RESULT_OK&&data!=null)try(Cursor c=getContentResolver().query(data.getData(),new String[]{ContactsContract.CommonDataKinds.Phone.NUMBER},null,null,null)){
      if(c!=null&&c.moveToFirst())emit("nativeContactSelected",c.getString(0));}catch(Exception ignored){} }
  }
  @Override public void onRequestPermissionsResult(int request,String[] permissions,int[] results){super.onRequestPermissionsResult(request,permissions,results);
    if(request==LOCATION)js("window.nativeGeoPermissionResult("+(results.length>0&&results[0]==PackageManager.PERMISSION_GRANTED)+")");
    if(request==CALLS){if(results.length>0&&results[0]==PackageManager.PERMISSION_GRANTED)deliverCalls();
      else js("window.nativeRecentCallResult('[]','denied')");}
  }
  @Override public void onBackPressed(){js("if(window.handleDeviceBack)window.handleDeviceBack();else window.history.back()");}
  private final class NativeFiles {
    @JavascriptInterface public String readChunk(String id,int index){
      if(id==null||!id.matches("[a-fA-F0-9-]{36}")||index<0||index>=512)return "";
      File f=originals.get(id);if(f==null)return "";
      try(RandomAccessFile raf=new RandomAccessFile(f,"r")){
        long start=(long)index*65536;if(start>=raf.length())return "";
        raf.seek(start);byte[] bytes=new byte[(int)Math.min(65536,raf.length()-start)];raf.readFully(bytes);
        return Base64.encodeToString(bytes,Base64.NO_WRAP);
      }catch(Exception e){return "";}
    }
    @JavascriptInterface public void clearTemp(String id){File f=originals.remove(id);if(f!=null)f.delete();}
    @JavascriptInterface public boolean saveBegin(String id,String name,String mime){
      if(id==null||!id.matches("[a-fA-F0-9-]{36}"))return false;
      try{File f=new File(tempDir,"save-"+id);if(f.exists())f.delete();if(!f.createNewFile())return false;
        saving.put(id,f);saveLabels.put(id,new String[]{name==null?"첨부파일":name.replace('/','_').replace('\\','_'),mime==null?"application/octet-stream":mime});return true;
      }catch(Exception e){return false;}
    }
    @JavascriptInterface public boolean saveChunk(String id,String base64){File f=saving.get(id);
      if(f==null||base64==null||base64.length()>250000)return false;
      try(FileOutputStream out=new FileOutputStream(f,true)){out.write(Base64.decode(base64,Base64.DEFAULT));return f.length()<=24*1024*1024;}
      catch(Exception e){return false;}
    }
    @JavascriptInterface public boolean saveFinish(String id){File f=saving.remove(id);String[] meta=saveLabels.remove(id);
      if(f==null||meta==null)return false;
      try{
        ContentValues cv=new ContentValues();cv.put(MediaStore.Downloads.DISPLAY_NAME,meta[0]);cv.put(MediaStore.Downloads.MIME_TYPE,meta[1]);
        cv.put(MediaStore.Downloads.RELATIVE_PATH,Environment.DIRECTORY_DOWNLOADS+"/너나메모");cv.put(MediaStore.Downloads.IS_PENDING,1);
        Uri uri=getContentResolver().insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI,cv);if(uri==null)return false;
        try(InputStream input=new FileInputStream(f);OutputStream output=getContentResolver().openOutputStream(uri)){
          if(output==null)throw new IOException("Cannot write original");byte[] data=new byte[65536];int n;
          while((n=input.read(data))!=-1)output.write(data,0,n);
        }
        cv.clear();cv.put(MediaStore.Downloads.IS_PENDING,0);getContentResolver().update(uri,cv,null,null);
        toast("원본 다운로드 완료");return true;
      }catch(Exception e){toast("파일 저장 실패");return false;}finally{f.delete();}
    }
  }
}
