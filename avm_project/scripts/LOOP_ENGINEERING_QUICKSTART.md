# Loop Engineering Quick Start
## 루프 엔지니어링 빠른 시작 가이드

**5분 안에 자동화 설정하기**

---

## 🚀 빠른 설정 (Linux/Mac)

### 1단계: 스크립트 실행
```bash
chmod +x scripts/setup_cron_automation.sh
./scripts/setup_cron_automation.sh
```

### 2단계: 프롬프트 따르기
```
선택 1: 주간 (목요일 10:00) - 엔터 누르기
선택 2: API 키 설정 (선택사항)
선택 3: 테스트 실행 (선택사항)
```

### 3단계: 확인
```bash
crontab -l | grep avm_orchestrator
```

---

## 🪟 빠른 설정 (Windows)

### 1단계: Task Scheduler 열기
```
Windows Key + R → taskschd.msc → Enter
```

### 2단계: 작업 생성
```
Create Basic Task
  이름: AVM Loop Engineering
  트리거: 매주 목요일 10:00
  작업: python.exe
  인수: C:\path\to\avm_project\scripts\avm_orchestrator.py
```

### 3단계: 저장 및 확인

---

## 📋 기본 명령어

### 수동 실행
```bash
python3 scripts/avm_orchestrator.py
```

### 특정 날짜로 실행
```bash
python3 scripts/avm_orchestrator.py --start-date 202401 --end-date 202406
```

### 로그 확인
```bash
tail -f logs/cron_execution.log
```

### 최신 리포트 확인
```bash
cat output/orchestration_report_*.json | jq .
```

---

## 🔧 트러블슈팅

### Cron이 실행되지 않음?
```bash
# 1. Crontab 확인
crontab -l

# 2. 환경 변수 설정
export DATAGOVKR_API_KEY="your-api-key"
echo "export DATAGOVKR_API_KEY='your-api-key'" >> ~/.bashrc

# 3. Crontab 재설정
crontab -e
# 다음 추가
DATAGOVKR_API_KEY=your-api-key
0 10 * * 4 /usr/bin/python3 /full/path/to/avm_orchestrator.py
```

### Python 모듈 없음?
```bash
pip3 install -r requirements-minimal.txt
```

### API 403 오류?
```bash
# 1. Data.go.kr에서 API 상태 확인
# 2. API 키 재발급
# 3. 환경 변수 업데이트
export DATAGOVKR_API_KEY="new-api-key"
```

---

## 📊 모니터링

### 실시간 로그 모니터링
```bash
tail -f logs/cron_execution.log
```

### 오류 확인
```bash
grep "ERROR" logs/*.log
```

### 성공 메시지
```bash
grep "✅" logs/*.log
```

### 최신 데이터 확인
```bash
ls -lht data/processed/*.csv | head -1
```

### 모델 성능 확인
```bash
cat output/orchestration_report_*.json | jq '.model_training.results'
```

---

## 🗓️ 스케줄 옵션

### Linux/Mac (Cron)
```bash
# 매주 목요일 10:00 (기본값)
0 10 * * 4

# 매일 10:00
0 10 * * *

# 매월 1일 10:00
0 10 1 * *

# 매주 월요일과 금요일 10:00
0 10 * * 1,5
```

### Windows (Task Scheduler)
```
Triggers:
  - Weekly: Thursday, 10:00 AM
  - Daily: 10:00 AM
  - Monthly: First day, 10:00 AM
  - Custom: Advanced scheduling
```

---

## 📁 생성된 파일들

```
logs/
├── avm_orchestration_YYYYMMDD_HHMMSS.log  # 상세 실행 로그
└── cron_execution.log                      # Cron 실행 로그

output/
├── orchestration_report_YYYYMMDD_HHMMSS.json  # 실행 리포트
└── processed_data_*.csv

data/
├── raw/
│   └── *.csv                               # 수집된 데이터
└── processed/
    └── processed_*.csv                     # 전처리된 데이터

models/
└── *.pkl                                   # 학습된 모델 파일
```

---

## 📈 예상 실행 결과

```
✅ 오케스트레이션 시작
  ├─ ✅ 데이터 수집: 1234개 레코드
  ├─ ✅ 전처리: 1234 × 30 컬럼
  └─ ✅ 모델 학습: 4개 모델
      ├─ Linear Regression: R² = 0.82
      ├─ Random Forest: R² = 0.86
      ├─ Decision Tree: R² = 0.79
      └─ Gradient Boosting: R² = 0.87
  
✅ 오케스트레이션 완료!
```

---

## 🔗 관련 문서

- [상세 가이드](../docs/LOOP_ENGINEERING_GUIDE.md)
- [데이터 수집 가이드](../docs/KOREAN_REAL_ESTATE_DATA_COLLECTION.md)
- [AVM 완전 가이드](../docs/AVM_COMPLETE_GUIDE.md)

---

## ⚡ 팁

1. **API 키 안전 관리**
   ```bash
   # 환경 변수로 설정 (권장)
   export DATAGOVKR_API_KEY="your-api-key"
   
   # 또는 .bashrc/.zshrc에 추가
   echo "export DATAGOVKR_API_KEY='your-api-key'" >> ~/.bashrc
   ```

2. **정기적인 로그 정리**
   ```bash
   # 30일 이상 된 로그 자동 삭제
   0 0 * * * find /path/to/logs -mtime +30 -delete
   ```

3. **모니터링 자동화**
   ```bash
   # 주간 리포트 메일로 전송 (추가 스크립트 필요)
   0 9 * * 1 python3 /path/to/send_report.py
   ```

4. **성능 추적**
   ```bash
   # 모든 실행 결과를 CSV로 통합
   python3 -c "
   import json
   from pathlib import Path
   reports = Path('output').glob('orchestration_report_*.json')
   for r in reports:
       print(json.load(open(r)))
   " > model_performance_history.csv
   ```

---

**시작하기:** `./scripts/setup_cron_automation.sh`
