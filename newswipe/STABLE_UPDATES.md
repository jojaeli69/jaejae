# NewSwipe 고정 업데이트 채널 (v2.1.0 준비)

## 목적
- 업데이트 이후 키보드 설정, 오타 학습, 클립보드 기록을 유지할 수 있도록 고정 패키지 ID와 개인 서명을 재사용
- 고정 패키지: `com.alternative_studios.newswipe.personal`
- 릴리스 서명: 각 빌드마다 생성되는 임시 debug.keystore 사용 금지
- 동일 앱에 덮어쓰기 설치: 고정 package ID + 기존과 동일한 서명 인증서 + 증가하는 versionCode

## 초기 전환
기존 v2.0.7 TEST 패키지 `com.alternative_studios.newswipe.clip5days`는 GitHub Actions 실행 시 생성된 임시 디버그 키로 서명됐습니다.
이전 v2.0.5와도 인증서가 다른 사실을 검사했습니다.
따라서 기존 v2.0.7을 인증서가 다른 새 APK로 덮어쓸 수는 없습니다.
고정 채널 첫 버전을 한 번만 별도로 설치한 뒤, 구버전 설정에서 '설정 내보내기' → 새 앱에서 '설정 가져오기'를 사용하십시오.
설정 백업에는 선택한 학습 단어 및 텍스트 클립보드 기록을 담을 수 있지만 클립보드 이미지와 Android의 시스템 권한/기본 키보드 지정은 이전되지 않습니다.

## 1회 설정: 개인 서명 키를 GitHub Secrets에 안전하게 저장
1. ChatGPT에서 생성한 `NewSwipe_Stable_Signing_Key.p12`와 비밀번호 파일을 별도 안전한 곳에 백업합니다.
2. GitHub 저장소 Settings → Secrets and variables → Actions → New repository secret:
   - `NEWSWIPE_SIGNING_KEYSTORE_B64`: `NewSwipe_Stable_Key_Base64.txt` 파일 내용 전체
   - `NEWSWIPE_SIGNING_PASSWORD`: `NewSwipe_Stable_Signing_Password.txt` 내용
3. GitHub Actions → `NewSwipe stable in-place update signing` → Run workflow에서 최초 릴리스 APK를 빌드할 수 있습니다.
4. 향후 기능 추가 시 릴리스 버전 코드만 올리고 같은 패키지 및 동일 개인 키로 서명합니다.

서명 키와 비밀번호를 공개 GitHub 저장소·이슈·커밋·릴리스·로그에 올리지 마세요.

## GitHub 준비된 빌드 워크플로
`.github/workflows/newswipe-stable-release.yml`
키 비밀값이 아직 등록되지 않았으면 보안을 위해 빌드를 실패시킵니다. 임시/공용 debug key로 릴리스 APK를 생성하지 않습니다.

## 검증 절차
- 신규 버전의 package ID가 이전 안정판과 정확히 일치하는지 확인
- `apksigner verify --print-certs`로 서명 지문이 기존 안정판과 정확히 일치하는지 확인
- versionCode 증가 확인
- 설치 시 Android에서 '업데이트'로 표시되는지 확인
- 기존 사용자 데이터 및 클립보드 보존 실기기 테스트
