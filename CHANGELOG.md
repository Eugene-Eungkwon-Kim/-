# 변경 이력 (CHANGELOG)

코드 수정·기능 추가 작업을 최신순으로 정리한 목록입니다.
모바일에서 보기 좋은 웹 버전: [`updates.html`](updates.html)

---

## 2026-08-17

### 🔋 배터리 효율 진단 스크립트 추가 (`c017c94`)
- `battery.py` 신규 추가 — 배터리 소모 원인 측정 및 조치 제시 (**읽기 전용**, 설정 변경 없음)
- **Android (ADB)**: `dumpsys battery`로 잔량·건강·온도·전압, `dumpsys batterystats`로
  항목별 추정 소모(mAh), partial wakelock, `dumpsys deviceidle`로 Doze 예외 앱,
  화면 밝기·자동 꺼짐 설정 조회
- **iPhone (libimobiledevice)**: `idevicediagnostics ioregentry AppleSmartBattery`로
  충전 사이클, 설계 대비 실제 용량으로 **배터리 성능 최대치(%)** 산출
- **조치 엔진**: 측정값에 근거해 우선순위(높음/보통)를 붙여 제시 —
  성능 최대치 80% 미만 시 교체 권고, 40°C 이상 발열 경고, 화면·셀룰러·GPS 최대 소모원 지목,
  Doze 예외 앱 및 wakelock 보유 앱 지적
- **기기 없이 사용**: `--advice`로 화면·백그라운드·네트워크·충전 습관·점검 체크리스트 출력
- `test_battery.py` 추가 — 실제 `dumpsys`/`ioregentry` 출력 형식을 픽스처로
  파서·조치 로직을 기기 없이 검증 (34개 항목)
- 한글 출력 품질: 터미널 표시 폭 기준 정렬(한글 2칸), 받침에 따른 주격 조사 이/가 선택
  (숫자·영문자는 읽는 소리로 판단 — `4`=사→가, `1`=일→이, `GPS`=에스→가)
- `run.py`에 `battery` 서브명령 연결

### 🧽 저장공간 정리 스크립트 추가 (`2b3c038`)
- `cleanup.py` 신규 추가 — 용량 분석 및 중복·캐시 정리로 공간 회수
- **분석 리포트**: 카테고리별 용량 비중, 용량 상위 폴더, 대용량 파일 목록
- **중복 탐지**: 같은 크기 파일만 해시하는 2단계 방식으로 전체 해시보다 빠름
- **원본 보존 우선순위**: 카메라 폴더(DCIM 등)와 오래된 파일을 원본으로 유지하고,
  `(1)`·`_copy`·`사본` 등 사본 패턴을 삭제 후보로 분류
- **캐시 정리**: `.thumbnails`, `cache`, `thumbdata`, `.trashed` 등 안전 삭제 대상 탐지
- **빈 폴더 정리**: 하위까지 비어 있는 폴더를 중첩 단계까지 탐지
- **안전 설계**: 기본은 읽기 전용 분석, 삭제는 `--apply` 명시 필요.
  대용량 파일은 목록만 제시하고 **자동 삭제하지 않음**. 대상 폴더 밖 경로는 삭제 차단
- `--android`: ADB로 기기 용량 리포트만 출력 (읽기 전용, `--apply`와 동시 사용 차단)
- `cleanup_report.json` 보고서 생성
- `run.py`에 `cleanup` 서브명령 연결

## 2026-08-10

### 🎛️ 통합 실행 스크립트 추가 (`d6acea2`)
- `run.py` 신규 추가 — 네 개 스크립트를 서브명령 하나로 실행
- `organize` / `migrate` / `iphone` / `realestate` 서브명령 제공
- 각 스크립트의 옵션(`--dry-run`, `--android`, `--source` 등)을 그대로 전달

### 🏢 부동산 실거래가 수집 스크립트 추가 (`7d2d88d`)
- `fetch_realestate.py` 신규 추가 (Loan4u / AVM 용)
- 국토교통부 아파트 매매 실거래가 API(data.go.kr) 연동
- 지역코드(`--lawd`) + 기간(`--start`~`--end`) 범위 월별 순회 조회
- 결과를 한글 컬럼 CSV(`utf-8-sig`)로 저장, 거래금액 콤마 제거 정규화
- 인증키는 `--key` 또는 환경변수 `DATA_GO_KR_KEY`로 지정
- 월별 요청 간 대기(`--delay`, 기본 0.3초) 및 네트워크·응답 오류 개별 처리

### 🧹 scratchpad 임시 디렉토리 gitignore 추가 (`4256316`)

## 2026-06-18

### 📖 종합 README 작성 (`ae5f9c1`)
- 세 스크립트(`organize.py`, `migrate.py`, `iphone_migrate.py`) 통합 사용 가이드 작성
- 설치 방법, 기기별 사용법, 결과 폴더 구조, 주의사항 문서화

### 🐛 버그 수정 (`3c03da6`)
- **파일명 충돌 카운터 수정**: 충돌 시 `file_1_2_3` 형태로 접미사가 무한히 길어지던 버그 수정 (3개 스크립트 모두)
- **deprecated API 교체**: Pillow `_getexif()` → `getexif()`
- **미사용 import 제거**: `os`, `subprocess` 정리
- `iphone_migrate.py`: 미사용 `LIVE_PHOTO_PATTERN` 삭제
- `iphone_migrate.py`: 라이브포토 카테고리의 `.mov` 확장자 중복 등록 제거

### 📱 iPhone 13 Pro 전용 스크립트 추가 (`defae8d`)
- `iphone_migrate.py` 신규 추가
- HEIC/HEIF 포맷 지원, Live Photo(HEIC+MOV 쌍) 자동 감지
- 슬로모션·타임랩스 파일명 패턴 인식 및 별도 폴더 분류
- 카테고리별 통계를 담은 `iphone_migration_report.json` 생성

## 2026-06-10

### 🤖 Android 마이그레이션 스크립트 추가 (`80c323b`, `6fee4b8`)
- `migrate.py` 신규 추가
- ADB 직접 연결로 Android 기기에서 파일 자동 추출 (`--android`)
- 로컬 백업 폴더 정리 지원 (`--source`)
- `migration_report.json` 보고서 생성
- `migration_output` gitignore 추가

## 2026-05-31

### 🗂️ 기본 파일 정리 스크립트 추가 (`47c7718`, `773f609`)
- `organize.py` 신규 추가
- 종류별(사진/동영상/음악/문서/압축/APK/기타) + 날짜별(`YYYY/MM`) 자동 분류
- 파일명 `YYYYMMDD_HHMMSS_원본이름` 형식 통일, MD5 해시 기반 중복 제거
- EXIF 촬영일 기준 정렬 (Pillow 설치 시)
- 테스트 결과물 gitignore 추가

---

*최종 갱신: 2026-08-17*
