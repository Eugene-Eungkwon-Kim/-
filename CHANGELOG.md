# 변경 이력 (CHANGELOG)

코드 수정·기능 추가 작업을 최신순으로 정리한 목록입니다.
모바일에서 보기 좋은 웹 버전: [`updates.html`](updates.html)

---

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
