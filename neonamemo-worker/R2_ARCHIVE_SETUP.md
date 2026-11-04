# 너나메모 R2 저장 및 안전한 로컬 백업 정책 (v4.2 준비)
2026-11-04

## 현재 상태
- Worker src/index.js: `FILES_R2`라는 R2 버킷 binding이 있으면 파일 암호화 조각을 R2에 저장. 없으면 기존 KV에 그대로 저장한다.
- Worker `GET /v1/share/r2/usage`: `x-nnm-workspace-key` 헤더 필수. R2가 연결돼 있으면 이번 페이지의 `scannedBytes`, `scannedObjects`, `cursor`, `hasMore`를 반환. 모든 페이지를 합산해야 정확한 사용량이다.
- 이미 KV에 저장된 사진·보고서 조각은 **읽을 때 R2로 복사**되지만 KV 원본은 그대로 남는다. 전체 자동 이관은 아직 완료되지 않았다.
- Worker의 파일 삭제 API와 Android 자동 아카이브는 **아직 구현되지 않았다**. 백업 검증 없이 원본을 삭제하면 안 된다.
- 앱에서 쓰는 `x-nnm-workspace-key`는 APK에서 추출 가능하므로, 관리자 기능과 삭제 기능의 인증으로 사용하지 말고 별도 소유자 인증을 요구한다.

## 최초 설정 (Cloudflare 계정 소유자가 수행)
1. Cloudflare Dashboard > R2 Object Storage > Create bucket
2. 이름 `neonamemo-files`; storage class **Standard**; Public Access **OFF**.
3. `neonamemo-worker/wrangler.jsonc`에 다음 `r2_buckets` 선언을 추가하고 main으로 배포한다:
```json
"r2_buckets": [
  {"binding": "FILES_R2", "bucket_name": "neonamemo-files"}
]
```
4. `/v1/share/r2/usage` 응답에서 `enabled: true`를 확인한다.
5. 사진 1장 업로드 및 다른 기기 원본 다운로드, 복호화 체크섬과 R2 용량을 점검한다.
6. 기존 KV 파일은 검증 전 삭제하지 않는다.

## 90% 관리 기준
- 무료 요금제의 10 GB-month는 무료 포함 저장량이며 강제 상한이 아니다.
- 사용자 정의 백업 경고선: 저장 중인 파일 데이터 **9,000,000,000 bytes** (9 GB).
- 매번 전체 버킷을 조회하지 않고, 사용자가 저장량 화면을 열거나 주기적으로 백그라운드 조회할 때 R2 객체 목록의 모든 페이지를 순회해 합산한다.
- 9GB 도달 시 푸시/화면 경고. **자동 삭제 금지**.

## 휴대폰 전체 백업(미구현)
1. 소유자만 시작 가능한 Android SAF 백업. 선택한 폴더에 1GB 이하 분할 아카이브와 manifest.json 작성.
2. manifest에는 파일 ID, 복원 대상 업무 ID, 원본 파일명, MIME, 크기, SHA-256, 원래 업무의 주소/제목/촬영일, 아카이브 파트명을 기재한다.
3. 암호화된 아카이브를 만든다. 개인정보 보호를 위해 암호를 APK나 공개 소스에 하드코딩하지 않는다.
4. 백업 끝나면 파일 수/크기/해시를 다시 읽어 전체 일치 검증한다. 최소 한 곳 이상 별도 보조 백업 권장.
5. 모든 항목 검증이 성공해야 'R2 원본 정리' 액션을 소유자에게 표시한다.
6. 삭제는 소유자 인증+확인 후 배치 실행. 해당 사진의 업무 기록/주소/제목/검색 목록/썸네일은 보존하고 상태를 `보관됨 (로컬)`로 표시한다.
7. 동료의 과거 사진 접근은 막히므로, 복원 버튼으로 지정 사진을 R2에 재업로드하는 경로를 구현해야 한다.

## 유의
- R2 bucket을 아직 만들지 않았거나 binding을 추가하지 않았을 때 기존 KV에 계속 업로드되므로, **R2 이전이 끝났다고 안내하지 말 것**.
- KV와 R2는 단일 스토리지 한도를 공유하지 않으므로 이전 과정에서 두 저장소 사용량을 따로 관리한다.
- R2 Standard 기준 무료 10 GB-month, 무료 Class A 100만, Class B 1,000만. 사용량 초과 시 과금 가능.
