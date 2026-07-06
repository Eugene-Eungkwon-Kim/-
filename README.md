# 모바일 기기 데이터 마이그레이션 & 정리 도구

휴대폰(iPhone 13 Pro, Android)에서 내보낸 파일을 **종류별 + 날짜별**로 자동 분류하고, 파일명을 정리하며, 중복 파일을 제거합니다.

---

## 📋 세 가지 스크립트

| 스크립트 | 용도 | 대상 |
|----------|------|------|
| `organize.py` | 기본 파일 정리 | 모든 기기 (일반) |
| `migrate.py` | 모바일 마이그레이션 | Android (ADB) 또는 로컬 폴더 |
| `iphone_migrate.py` | iPhone 전용 | iPhone 13 Pro (HEIC, Live Photo 지원) |

---

## ✨ 주요 기능

### 모든 스크립트 공통
- **종류별 분류**: 사진, 동영상, 음악, 문서, 압축파일, APK, 기타
- **날짜별 분류**: `카테고리/YYYY/MM/` 구조로 정리
- **파일명 정리**: `YYYYMMDD_HHMMSS_원본이름.확장자` 형식으로 통일
- **중복 제거**: MD5 해시로 동일 파일 감지 후 자동 삭제
- **EXIF 날짜**: 사진의 실제 촬영일 기준 정렬 (Pillow 설치 시)

### iPhone 전용 (`iphone_migrate.py`)
- **HEIC/HEIF** 포맷 완벽 지원
- **Live Photo** 자동 감지: HEIC + MOV 쌍 → `라이브포토/` 폴더로 분리
- **슬로모션**: `SloMo` 파일명 패턴 인식 → `슬로모션/` 폴더
- **타임랩스**: `TimeLapse` 패턴 인식 → `타임랩스/` 폴더
- **카테고리별 통계**: `iphone_migration_report.json` 자동 생성

### Android 전용 (`migrate.py`)
- **ADB 직접 연결**: USB 디버깅으로 기기 파일 자동 추출
- **로컬 폴더 지원**: 기존 백업 폴더 정리
- **상세 보고서**: `migration_report.json` 생성

---

## 🚀 설치

### 필수 요구사항
- Python 3.10 이상
- macOS, Linux, Windows

### 의존성 설치
```bash
pip install Pillow   # 선택 사항 (EXIF 날짜 사용 시 권장)
```

---

## 💻 사용법

### 1️⃣ iPhone 13 Pro

**macOS에서 실행:**
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

### 2️⃣ Android (ADB 사용)

**Windows/Mac/Linux에서 실행:**
```bash
# 1. Android SDK 설치
# 2. 기기를 USB로 연결 → 개발자 옵션 활성화 → USB 디버깅 허용

# 3. 미리보기
python migrate.py --android ./마이그레이션결과 --dry-run

# 4. 실제 실행
python migrate.py --android ./마이그레이션결과
```

### 3️⃣ 로컬 폴더 정리

**어떤 기기든 가능:**
```bash
# 기본 정리
python organize.py /path/to/phone_files ./정리결과

# 또는 migrate.py 사용
python migrate.py --source /path/to/phone_files ./정리결과

# 미리보기
python organize.py /path/to/phone_files ./정리결과 --dry-run
```

---

## 📁 결과 구조

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

---

## ⚙️ 옵션

| 옵션 | 설명 |
|------|------|
| `--dry-run` | 미리보기 모드 (파일 실제 변경 없음) |
| `--android` | ADB로 Android 기기에서 직접 가져오기 (migrate.py) |
| `--source` | 로컬 폴더 경로 지정 (migrate.py) |

---

## ⚠️ 주의사항

1. **백업 필수**: 원본 파일은 **이동**됩니다. 반드시 미리 백업하세요.
2. **미리보기 권장**: `--dry-run` 옵션으로 먼저 결과를 확인하세요.
3. **중복 제거**: MD5 해시로 동일 파일을 감지하며, **원본만 남기고 나머지는 삭제**합니다.
4. **저장 공간**: 정리 전 충분한 여유 공간 필요 (원본 용량의 2배 이상)

---

## 🔍 상세 기능

### Live Photo (iPhone)
HEIC 및 해당 MOV 파일이 **같은 이름**일 때 자동 감지:
```
DCIM/100APPLE/IMG_0001.HEIC  + IMG_0001.MOV  → 라이브포토/2024/01/
```

### 파일명 충돌 처리
같은 날짜, 같은 이름의 다른 파일:
```
20240115_143022_photo.jpg
20240115_143022_photo_1.jpg  (충돌)
20240115_143022_photo_2.jpg  (충돌)
```

### EXIF 날짜 (Pillow 설치 시)
사진의 실제 촬영일 기준으로 분류 → 더 정확한 정렬

---

## 🐛 변경 이력 (버그 수정 & 업데이트)

전체 수정 작업 내역은 최신순으로 정리되어 있습니다:

- 📄 **[CHANGELOG.md](CHANGELOG.md)** — 전체 변경 이력 (마크다운)
- 📱 **[updates.html](updates.html)** — 모바일 브라우저용 반응형 리스팅 페이지

최근 주요 수정 사항:
- ✅ 파일명 충돌 시 `file_1_2_3` 형태 무한 증가 → 수정
- ✅ `_getexif()` deprecated → `getexif()` API로 교체
- ✅ Live Photo 크로스-디렉토리 감지 검증 완료
- ✅ 미사용 import 및 `LIVE_PHOTO_PATTERN` 정리

---

## 📝 라이센스

MIT

---

## 💬 문의

버그 또는 기능 요청: GitHub Issues
