# 저장소 개요

이 저장소에는 서로 의존하지 않는 세 프로젝트가 함께 있습니다.

| 프로젝트 | 위치 | 설명 |
|---|---|---|
| 모바일 파일 정리 도구 | 루트 (`organize.py`, `migrate.py`, `iphone_migrate.py`) | 아래 "모바일 기기 데이터 마이그레이션 & 정리 도구" 참고 |
| MAARS 플랫폼 | `src/`, `test/`, `docs/` 등 | 부동산 금융 백엔드·프론트엔드 (Node/TypeScript) |
| AVM 프로젝트 | `avm_project/` | Loan4U 자동감정가 모델 (Python) — 상세는 [`avm_project/README.md`](./avm_project/README.md) |

에이전트 작업 원칙(파이썬 퍼스트, 오류 분류 규약, AVM 전용 코드 표준)은 [`CLAUDE.md`](./CLAUDE.md)를 참고하세요.

---

## 모바일 기기 데이터 마이그레이션 & 정리 도구

휴대폰(iPhone 13 Pro, Android)에서 내보낸 파일을 **종류별 + 날짜별**로 자동 분류하고, 파일명을 정리하며, 중복 파일을 제거합니다.

### 세 가지 스크립트

| 스크립트 | 용도 | 대상 |
|----------|------|------|
| `organize.py` | 기본 파일 정리 | 모든 기기 (일반) |
| `migrate.py` | 모바일 마이그레이션 | Android (ADB) 또는 로컬 폴더 |
| `iphone_migrate.py` | iPhone 전용 | iPhone 13 Pro (HEIC, Live Photo 지원) |

### 주요 기능

**모든 스크립트 공통**
- **종류별 분류**: 사진, 동영상, 음악, 문서, 압축파일, APK, 기타
- **날짜별 분류**: `카테고리/YYYY/MM/` 구조로 정리
- **파일명 정리**: `YYYYMMDD_HHMMSS_원본이름.확장자` 형식으로 통일
- **중복 제거**: MD5 해시로 동일 파일 감지 후 자동 삭제
- **EXIF 날짜**: 사진의 실제 촬영일 기준 정렬 (Pillow 설치 시)

**iPhone 전용 (`iphone_migrate.py`)**
- **HEIC/HEIF** 포맷 완벽 지원
- **Live Photo** 자동 감지: HEIC + MOV 쌍 → `라이브포토/` 폴더로 분리
- **슬로모션**: `SloMo` 파일명 패턴 인식 → `슬로모션/` 폴더
- **타임랩스**: `TimeLapse` 패턴 인식 → `타임랩스/` 폴더
- **카테고리별 통계**: `iphone_migration_report.json` 자동 생성

**Android 전용 (`migrate.py`)**
- **ADB 직접 연결**: USB 디버깅으로 기기 파일 자동 추출
- **로컬 폴더 지원**: 기존 백업 폴더 정리
- **상세 보고서**: `migration_report.json` 생성

### 설치

**필수 요구사항**
- Python 3.10 이상
- macOS, Linux, Windows

**의존성 설치**
```bash
pip install Pillow   # 선택 사항 (EXIF 날짜 사용 시 권장)
```

### 사용법

**1️⃣ iPhone 13 Pro (macOS에서 실행)**
```bash
# 1. 저장소 클론
git clone https://github.com/eugene-eungkwon-kim/-
cd -

# 2. iPhone을 USB-C로 연결
# 3. 사진 앱에서 전체 내보내기 또는 Finder에서 DCIM 폴더 복사

# 4. 미리보기
python iphone_migrate.py ~/Desktop/iPhone_내보내기 ~/Desktop/정리결과 --dry-run

# 5. 실제 실행
python iphone_migrate.py ~/Desktop/iPhone_내보내기 ~/Desktop/정리결과
```

**2️⃣ Android (ADB 사용, Windows/Mac/Linux)**
```bash
# 1. Android SDK 설치
# 2. 기기를 USB로 연결 → 개발자 옵션 활성화 → USB 디버깅 허용

# 3. 미리보기
python migrate.py --android ./마이그레이션결과 --dry-run

# 4. 실제 실행
python migrate.py --android ./마이그레이션결과
```

**3️⃣ 로컬 폴더 정리 (어떤 기기든 가능)**
```bash
# 기본 정리
python organize.py /path/to/phone_files ./정리결과

# 또는 migrate.py 사용
python migrate.py --source /path/to/phone_files ./정리결과

# 미리보기
python organize.py /path/to/phone_files ./정리결과 --dry-run
```

### 결과 구조

```
정리결과/
├── 사진/
│   ├── 2024/01/
│   │   ├── 20240115_143022_IMG_1234.heic
│   │   └── 20240120_090500_photo.jpg
│   └── 2025/03/
├── 동영상/
│   └── 2024/05/
├── 라이브포토/        (iPhone에서 HEIC+MOV 쌍)
│   └── 2024/03/
├── 슬로모션/          (iPhone SloMo 영상)
├── 타임랩스/          (iPhone TimeLapse 영상)
├── 음악/
├── 문서/
├── 압축파일/
├── APK/
├── 기타/
├── iphone_migration_report.json   (iPhone: 통계)
└── migration_report.json           (Android: 통계)
```

### 옵션

| 옵션 | 설명 |
|------|------|
| `--dry-run` | 미리보기 모드 (파일 실제 변경 없음) |
| `--android` | ADB로 Android 기기에서 직접 가져오기 (migrate.py) |
| `--source` | 로컬 폴더 경로 지정 (migrate.py) |

### 주의사항

1. **백업 필수**: 원본 파일은 **이동**됩니다. 반드시 미리 백업하세요.
2. **미리보기 권장**: `--dry-run` 옵션으로 먼저 결과를 확인하세요.
3. **중복 제거**: MD5 해시로 동일 파일을 감지하며, **원본만 남기고 나머지는 삭제**합니다.
4. **저장 공간**: 정리 전 충분한 여유 공간 필요 (원본 용량의 2배 이상)

### 상세 기능

**Live Photo (iPhone)** — HEIC 및 해당 MOV 파일이 **같은 이름**일 때 자동 감지:
```
DCIM/100APPLE/IMG_0001.HEIC  + IMG_0001.MOV  → 라이브포토/2024/01/
```

**파일명 충돌 처리** — 같은 날짜, 같은 이름의 다른 파일:
```
20240115_143022_photo.jpg
20240115_143022_photo_1.jpg  (충돌)
20240115_143022_photo_2.jpg  (충돌)
```

**EXIF 날짜** (Pillow 설치 시) — 사진의 실제 촬영일 기준으로 분류 → 더 정확한 정렬

### 버그 수정 이력

- ✅ 파일명 충돌 시 `file_1_2_3` 형태 무한 증가 → 수정
- ✅ `_getexif()` deprecated → `getexif()` API로 교체
- ✅ Live Photo 크로스-디렉토리 감지 검증 완료

---

## MAARS 플랫폼

`src/` 아래에 MAARS(부동산 금융) 백엔드·프론트엔드가 통째로 들어 있습니다. 위 파이썬 도구, 아래 AVM 프로젝트와 서로 의존하지 않는 별개 프로젝트입니다.

**요구사항:** Node 18 또는 20, `maars_test`라는 이름의 PostgreSQL 데이터베이스, Redis (테스트·알림 기능에 필요). 접속 정보 기본값은 `localhost:5432`·사용자 `postgres`·비밀번호 없음이며, 다르면 `PG_HOST`/`PG_PORT`/`PG_USER`/`PG_PASSWORD`로 재정의한다. 전체 환경변수 목록은 `.github/workflows/test.yml` 참고.

```bash
createdb maars_test   # 최초 1회
npm ci

# 테스트
REDIS_URL=redis://localhost:6379 npm run test:ci

# 타입 체크
npm run type-check

# API 서버 + 프론트엔드 동시 실행
npm run dev:all
```

무엇이 있는지 한눈에 보려면:

- `src/server/app.ts` — Fastify 라우트 전체와 인증·권한 방식
- `src/notifications/` — 실시간 알림(SSE) 파이프라인: 판정 → 저장 → 팬아웃 → 스트림
- `docs/` — 마이그레이션·성능·캐싱 설계 문서
- `PERFORMANCE.md` — 성능 기준선과 목표치

`src/db/migrations/`의 마이그레이션은 SQLite/PostgreSQL 양쪽에서 그대로 유효한 SQL 부분집합으로 쓰고, `src/db/migrationRunner.ts`의 변환기가 타임스탬프 기본값과 부동소수 타입만 치환한다 — 새 마이그레이션을 추가할 때 참고할 것.

---

## AVM 프로젝트

Loan4U 자동감정가 모델(AVM) 개발 프로젝트입니다. 파이프라인·API·테스트는 동작하지만, **아직 실거래 데이터로 검증되지 않았습니다.**

자세한 현재 상태, 남은 작업, 알려진 한계는 [`avm_project/README.md`](./avm_project/README.md)와 `avm_project/docs/LIMITATIONS.md`를 참고하세요. 이 프로젝트에서 작업하는 에이전트는 `CLAUDE.md`의 "AVM 프로젝트 전용" 절과 `avm_project/README.md`의 "Claude 에이전트 주목" 절을 먼저 읽어야 합니다.

---

## 문의

버그 또는 기능 요청: GitHub Issues

MIT License (모바일 파일 정리 도구 기준 — MAARS·AVM은 각 프로젝트 문서 참고)
