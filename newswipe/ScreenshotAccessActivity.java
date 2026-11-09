package com.alternative_studios.newswipe;

import android.Manifest;
import android.app.Activity;
import android.os.Build;
import android.os.Bundle;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

/** Explicit permission onboarding for recent Samsung screenshots, not background spying. */
public final class ScreenshotAccessActivity extends Activity {
    private TextView status;

    @Override protected void onCreate(Bundle saved) {
        super.onCreate(saved);
        setTitle("캡처 사진 빠른 붙여넣기");
        LinearLayout root=new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        int p=(int)(20*getResources().getDisplayMetrics().density+.5f);
        root.setPadding(p,p,p,p);
        TextView description=new TextView(this);
        description.setTextSize(16);
        description.setText("삼성 갤럭시가 캡처를 사진첩에만 저장하는 경우에도 "
                +"NewSwipe가 95초 이내의 최신 스크린샷을 찾아 붙여넣기 버튼으로 표시합니다.\n\n"
                +"이를 위해 사진 전체 접근 권한이 필요합니다. 사진을 백그라운드에서 훑거나 "
                +"서버로 업로드하지 않습니다. 클립보드에 있는 사진은 별도 사진 접근 권한 없이도 "
                +"붙여넣을 수 있습니다.\n\n"
                +"사진 권한을 주지 않아도 기존 키보드 기능은 그대로 동작합니다.");
        root.addView(description);
        status=new TextView(this);
        LinearLayout.LayoutParams sl=new LinearLayout.LayoutParams(-1,-2);
        sl.topMargin=p;
        root.addView(status,sl);
        Button request=new Button(this);
        request.setText("최근 캡처 사진 접근 허용");
        request.setOnClickListener(v -> {
            if (RecentScreenshot.allowed(this)) refresh();
            else if (Build.VERSION.SDK_INT >= 33)
                requestPermissions(new String[]{Manifest.permission.READ_MEDIA_IMAGES}, 771);
            else requestPermissions(new String[]{Manifest.permission.READ_EXTERNAL_STORAGE}, 771);
        });
        root.addView(request);
        Button exit=new Button(this);
        exit.setText("설정 완료");
        exit.setOnClickListener(v -> finish());
        root.addView(exit);
        setContentView(root);
        refresh();
    }

    private void refresh() {
        if (status==null) return;
        status.setText(RecentScreenshot.allowed(this)
                ? "사진 접근 허용됨 · 새로운 스크린샷을 촬영해 테스트해 주세요."
                : "사진 접근이 제한됨 · 클립보드 이미지 붙여넣기는 계속 지원합니다.");
    }
    @Override protected void onResume() {super.onResume();refresh();}
    @Override public void onRequestPermissionsResult(int code,String[] perms,int[] granted) {
        super.onRequestPermissionsResult(code,perms,granted);
        if (code==771) refresh();
    }
}
