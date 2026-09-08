# 🚀 Phase C 고속 진행: 외장하드 직접 읽기

**다운로드 30분 생략 가능**

---

## 📊 **수정된 전체 흐름**

```
기존 흐름:
  데이터 다운로드 (30분)
       ↓
  데이터 검증 (5분)
       ↓
  모델 재학습 (2-4시간)
       ↓
  배포 (10분)

⬇️ 

외장하드 직접 읽기 흐름:
  Step 0: 외장하드에서 읽기 (5분) ⭐ NEW
       ↓
  Step 2: 데이터 검증 (5분)
       ↓
  Step 3: 모델 재학습 (2-4시간)
       ↓
  Step 4: 배포 (10분)

⏱️ 총 소요 시간: 2시간 30분 (30분 단축!)
```

---

## 🚀 **실행 명령어 (외장하드 버전)**

### **Step 0: 외장하드에서 데이터 읽기 (5분)**

```bash
# 외장하드 자동 감지 및 파일 선택
python avm_project/scripts/phase_c_step0_read_external_drive.py

# 💡 대화형 프로세스:
# 1. 외장하드 드라이브 목록 표시
# 2. 경로 입력
# 3. CSV 파일 자동 검색
# 4. 파일 선택 (번호 입력)
# 5. avm_project/data/raw/real_estate_2024.csv로 자동 복사
```

**예상 대화**:
```
🔍 외장하드 자동 감지
✅ 감지된 드라이브 (4개):
  1. C:\
     용량: 512.0GB  여유: 256.0GB
  2. D:\
     용량: 2000.0GB  여유: 1500.0GB
  3. E:\
     용량: 1000.0GB  여유: 800.0GB
  4. F:\
     용량: 500.0GB  여유: 400.0GB

📝 외장하드 경로 입력
외장하드 경로를 입력하세요: D:\

🔎 CSV 파일 검색: D:\
✅ 발견된 CSV 파일 (3개):

  1. real_estate_2024.csv (450.5MB)
     경로: D:\data\real_estate_2024.csv
  2. seoul_apt_2024.csv (120.3MB)
     경로: D:\seoul_apt_2024.csv
  3. busan_apt_2024.csv (80.1MB)
     경로: D:\busan_apt_2024.csv

📋 파일 선택
선택 (번호 입력, 예: 1): 1

✅ 선택: real_estate_2024.csv

📂 파일 복사 중...
   원본: D:\data\real_estate_2024.csv
   대상: avm_project/data/raw/real_estate_2024.csv
   크기: 450.5MB
   예상 시간: 1-3분

✅ 복사 완료!
   저장: avm_project/data/raw/real_estate_2024.csv
   크기: 450.5MB

✅ Step 0 완료!

다음 단계:
  python avm_project/scripts/phase_c_step2_validate_and_preprocess.py
```

---

### **Step 2: 데이터 검증 (5분)**

```bash
python avm_project/scripts/phase_c_step2_validate_and_preprocess.py

# 예상 결과:
# ✅ 파일 로드
# ✅ 컬럼명 표준화
# ✅ 누수 컬럼 제거
# ✅ 14-point 검증 통과
# ✅ 정제 데이터 저장
```

---

### **Step 3: 모델 재학습 (2-4시간)**

```bash
python avm_project/scripts/phase_c_step3_retrain_models.py

# 실시간 모니터링:
tail -f output/retrain_results_*.json
```

---

### **Step 4: API 배포 (10분)**

#### **옵션 1: 로컬 개발 서버** (권장)
```bash
python -m uvicorn avm_project.scripts.api_server:app --reload --port 8000
```

#### **옵션 2: Docker**
```bash
cd avm_project
docker build -t avm-model .
docker run -p 8000:8000 avm-model
```

---

## 📋 **외장하드 데이터 요구사항**

| 항목 | 기준 | 자동 처리 |
|------|------|---------|
| **파일 형식** | CSV | ✅ 자동 감지 |
| **컬럼명** | 거래금액, 거래일, 면적, 지역 | ✅ 자동 매핑 |
| **행 수** | ≥ 5,000 | ✅ 자동 검증 |
| **결측치** | < 5% | ✅ 자동 정제 |
| **누수 컬럼** | 없음 | ✅ 자동 제거 |

---

## 🎯 **외장하드 경로 예시**

### **Windows**
```
D:\                           (드라이브 루트)
D:\부동산데이터\              (폴더)
D:\avm_data\real_estate.csv   (파일)
F:\backup\data_2024.csv       (다른 드라이브)
```

### **macOS**
```
/Volumes/외장하드/
/Volumes/드라이브명/data/real_estate.csv
```

### **Linux**
```
/mnt/외장하드/
/media/사용자명/드라이브/data.csv
```

---

## ⚡ **예상 소요 시간 (외장하드 버전)**

| 단계 | 시간 | 누적 |
|------|------|------|
| Step 0: 외장하드 읽기 | 5분 | 5분 |
| Step 2: 데이터 검증 | 5분 | 10분 |
| Step 3: 모델 재학습 | 2-4시간 | 2시간 15분 ~ 4시간 15분 |
| Step 4: API 배포 | 10분 | 2시간 25분 ~ 4시간 25분 |

**✅ 다운로드 30분 절약!**

---

## ✅ **완료 체크리스트 (외장하드 버전)**

```
- [ ] Step 0: 외장하드에서 파일 읽기 완료
- [ ] Step 2: 데이터 검증 통과 (점수 ≥ 12/14)
- [ ] Step 3: 모델 재학습 완료 (R² ≥ 0.80)
- [ ] Step 4: API 배포 (헬스체크 통과)
- [ ] 테스트: 예측 동작 확인
- [ ] 모니터링: 대시보드 접속 확인

✅ 모두 완료 → 프로덕션 준비 완료!
```

---

## 🔍 **Step 0 상세 설명**

### **기능**
1. ✅ **자동 드라이브 감지**
   - Windows: C:, D:, E:, F: ... 자동 검사
   - macOS/Linux: df 명령어로 마운트 확인

2. ✅ **CSV 파일 자동 검색**
   - 재귀 검색 (모든 하위 폴더)
   - 크기 순 정렬
   - 상위 20개 표시

3. ✅ **대화형 파일 선택**
   - 번호 입력으로 선택
   - 선택된 파일 확인

4. ✅ **자동 복사**
   - 진행 상황 표시
   - 검증: 크기 확인
   - 저장 위치: `avm_project/data/raw/real_estate_2024.csv`

---

## 🚨 **문제 해결**

### **Q: 외장하드가 감지되지 않음**

```bash
# A: 다음을 확인하세요:

# Windows:
# 1. 외장하드 연결 확인
# 2. 윈도우 탐색기에서 드라이브 보임 확인
# 3. 직접 경로 입력 (예: D:\)

# macOS:
# 1. 외장하드 연결
# 2. df -h 명령어로 확인
# 3. /Volumes/드라이브명 입력

# Linux:
# df -h
# /mnt/... 또는 /media/... 입력
```

### **Q: CSV 파일을 찾을 수 없음**

```bash
# A: 다음을 확인하세요:
# 1. 경로가 정확한가? (인용부호 제거)
# 2. CSV 파일이 있는가?
# 3. 권한이 있는가? (읽기 전용 확인)

# 수동으로 경로 지정:
python -c "
from pathlib import Path
csv_files = list(Path('D:/').rglob('*.csv'))
for f in csv_files[:10]:
    print(f)
"
```

### **Q: 복사 실패**

```bash
# A: 다음을 확인하세요:
# 1. 디스크 공간 충분한가?
# 2. 쓰기 권한이 있는가?
# 3. 파일이 열려있는가? (닫기)

# 수동 복사:
cp "/source/path/file.csv" "avm_project/data/raw/real_estate_2024.csv"
```

---

## 💡 **팁**

### **빠른 시작**
```bash
# 모두 한 번에:
python avm_project/scripts/phase_c_step0_read_external_drive.py && \
python avm_project/scripts/phase_c_step2_validate_and_preprocess.py && \
python avm_project/scripts/phase_c_step3_retrain_models.py
```

### **백그라운드 실행** (재학습이 오래 걸릴 때)
```bash
# Unix/Linux/macOS:
nohup python avm_project/scripts/phase_c_step3_retrain_models.py > retrain.log 2>&1 &

# Windows (PowerShell):
Start-Process -NoNewWindow -FilePath python -ArgumentList "avm_project/scripts/phase_c_step3_retrain_models.py"
```

### **진행 상황 모니터링**
```bash
# 실시간 출력 크기 모니터링:
watch -n 10 "ls -lh avm_project/models/ | tail -5"

# 결과 파일 모니터링:
tail -f output/*.json
```

---

## ✨ **외장하드 버전의 장점**

| 항목 | 온라인 다운로드 | 외장하드 읽기 |
|------|----------------|-------------|
| **시간** | 30분~1시간 | 5분 ⭐ |
| **속도** | 인터넷 속도 | SSD 속도 (빠름) ⭐ |
| **안정성** | 네트워크 의존 | 로컬 파일 ⭐ |
| **편의성** | URL 필요 | 경로만 입력 ⭐ |
| **재시도** | 처음부터 | 즉시 ⭐ |

---

## 🎊 **최종 정리**

```
✅ 외장하드에 부동산 데이터가 있다면:

Step 0만 실행:
  python avm_project/scripts/phase_c_step0_read_external_drive.py

그 다음 바로:
  Step 2 → Step 3 → Step 4

총 2시간 30분 안에 배포 가능! 🚀
```

---

**작성**: 2026-06-18  
**상태**: 🟢 **즉시 사용 가능**  
**권장**: 외장하드 데이터가 있으면 이 방법 사용
