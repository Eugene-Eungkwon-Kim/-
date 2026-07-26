# AVM Loop Engineering Guide
## 자동 데이터 수집 및 모델 재학습 자동화 가이드

**작성일:** 2026-06-12  
**버전:** 1.0  
**상태:** 자동화 시스템 구현 완료

---

## 📋 목차
1. [개요](#개요)
2. [아키텍처](#아키텍처)
3. [Linux/Mac 설정 (Cron)](#linuxmac-설정-cron)
4. [Windows 설정 (Task Scheduler)](#windows-설정-task-scheduler)
5. [실행 및 모니터링](#실행-및-모니터링)
6. [트러블슈팅](#트러블슈팅)

---

## 개요

### Loop Engineering이란?
Loop Engineering은 다음 3단계를 자동으로 반복 실행하는 시스템입니다:
1. **Data Collection Loop** - Data.go.kr API에서 최신 부동산 데이터 수집
2. **Preprocessing Loop** - 수집된 데이터 정제 및 특성 엔지니어링
3. **Model Training Loop** - 최신 데이터로 머신러닝 모델 재학습

### 목표
- ✅ 매주 자동으로 최신 데이터 수집
- ✅ 수집된 데이터로 자동 전처리
- ✅ 전처리된 데이터로 모델 자동 재학습
- ✅ 모든 실행 결과를 로그로 기록
- ✅ 오류 발생 시 자동 복구

### 예상 효과
```
시간 투입: 0 시간 (완전 자동화)
데이터 신선도: 항상 최신 (주간 업데이트)
모델 정확성: 지속적 개선 (최신 데이터로 재학습)
장기 효과: 시간이 지날수록 모델 성능 증가
```

---

## 아키텍처

### 시스템 구성도
```
┌─────────────────────────────────────────────────────────┐
│          Cron Job (Linux/Mac) or Task Scheduler (Windows) │
│                    주간 자동 실행                       │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│        avm_orchestrator.py - 오케스트레이션               │
│        (전체 파이프라인 조정 및 로깅)                    │
└────────┬──────────────────┬──────────────────┬───────────┘
         │                  │                  │
         ▼                  ▼                  ▼
    ┌─────────────┐  ┌──────────────┐  ┌──────────────┐
    │Data         │  │Data          │  │Model         │
    │Collection   │  │Preprocessing │  │Training      │
    │(수집)      │  │(전처리)      │  │(학습)       │
    └─────────────┘  └──────────────┘  └──────────────┘
         │                  │                  │
         ▼                  ▼                  ▼
    ┌─────────────┐  ┌──────────────┐  ┌──────────────┐
    │Data.go.kr   │  │Sample CSV    │  │Model Files   │
    │API          │  │Raw Data      │  │Metrics JSON  │
    └─────────────┘  └──────────────┘  └──────────────┘
         │                  │                  │
         └──────────────────┴──────────────────┘
                     │
                     ▼
         ┌──────────────────────────┐
         │ Report & Logging         │
         │ - orchestration_report   │
         │ - avm_orchestration_log  │
         │ - cron_execution_log     │
         └──────────────────────────┘
```

### 데이터 흐름
```
Step 1: Data Collection
  Data.go.kr API → CSV 파일 (raw_data)
  - 부동산 실거래 정보
  - 전월세 데이터
  - 공시지가 정보

Step 2: Preprocessing
  CSV → Processed CSV + Features
  - 결측값 처리
  - 이상값 탐지 및 제거
  - 데이터 정규화
  - 파생 특성 생성

Step 3: Model Training
  Processed Data → Trained Models
  - Linear Regression
  - Decision Tree
  - Random Forest
  - Gradient Boosting
  - (Optional) XGBoost, LightGBM

Step 4: Evaluation
  Models → Performance Metrics
  - R² Score
  - RMSE, MAE
  - Cross-validation scores
  - JSON 리포트 생성
```

### 파일 구조
```
avm_project/
├── scripts/
│   ├── avm_orchestrator.py          # 오케스트레이션 메인 스크립트
│   ├── setup_cron_automation.sh      # Cron 설정 스크립트
│   ├── data_collection_handler.py    # 데이터 수집
│   ├── data_preprocessing.py         # 데이터 전처리
│   ├── model_development.py          # 모델 학습
│   └── ...
│
├── data/
│   ├── raw/                         # 수집된 원본 데이터
│   │   └── *.csv
│   └── processed/                   # 전처리된 데이터
│       └── processed_*.csv
│
├── models/                          # 학습된 모델 파일
│   └── *.pkl
│
├── output/                          # 결과 및 리포트
│   ├── orchestration_report_*.json  # 자동화 실행 리포트
│   └── *.csv
│
├── logs/                            # 로그 파일
│   ├── avm_orchestration_*.log      # 상세 실행 로그
│   └── cron_execution.log           # Cron 실행 로그
│
└── config/
    └── avm_config.json              # 프로젝트 설정
```

---

## Linux/Mac 설정 (Cron)

### 방법 1: 자동 설정 스크립트 (권장)

#### Step 1: 스크립트에 실행 권한 부여
```bash
chmod +x avm_project/scripts/setup_cron_automation.sh
```

#### Step 2: 설정 스크립트 실행
```bash
./avm_project/scripts/setup_cron_automation.sh
```

#### Step 3: 프롬프트에 따라 설정
```
1) 스케줄 선택 (기본값: 매주 목요일 10:00)
2) API 키 설정 (선택사항)
3) 테스트 실행 (선택사항)
```

### 방법 2: 수동 설정

#### Step 1: Cron 편집 열기
```bash
crontab -e
```

#### Step 2: 다음 줄을 추가
```bash
# AVM Loop Engineering - Weekly execution (Thursday 10:00 AM)
0 10 * * 4 cd /home/user/-/avm_project && python3 scripts/avm_orchestrator.py >> logs/cron_execution.log 2>&1
```

#### Cron 스케줄 옵션
```
매주 (목요일 10:00):         0 10 * * 4
매일 (10:00):               0 10 * * *
격주 (목요일 10:00):        0 10 * * 4 (manual alternation)
매월 첫 목요일 (10:00):     0 10 ? * 5 (alternative syntax)
```

#### Step 3: 설정 확인
```bash
crontab -l | grep avm_orchestrator
```

### Cron 표현식 설명
```
┌───────────── minute (0 - 59)
│ ┌───────────── hour (0 - 23)
│ │ ┌───────────── day of month (1 - 31)
│ │ │ ┌───────────── month (1 - 12)
│ │ │ │ ┌───────────── day of week (0 - 6, Sunday=0, Thursday=4)
│ │ │ │ │
│ │ │ │ │
0 10 * * 4  ← 매주 목요일 10:00 AM
```

---

## Windows 설정 (Task Scheduler)

### Step 1: Task Scheduler 열기
```
Press: Windows Key + R
Type: taskschd.msc
Press: Enter
```

### Step 2: 새 작업 생성
1. 오른쪽 메뉴에서 "Create Basic Task" 선택
2. 이름: `AVM Loop Engineering`
3. 설명: `Automated AVM data collection and model retraining`

### Step 3: 트리거 설정
1. "Triggers" 탭 → "New"
2. 시작 설정:
   - 반복: `Weekly`
   - 요일: `Thursday`
   - 시간: `10:00`
   - 반복 간격: `1` (주)

### Step 4: 작업 설정
1. "Actions" 탭 → "New"
2. 프로그램: `python.exe` 또는 `python3.exe`
3. 인수: `C:\path\to\avm_project\scripts\avm_orchestrator.py`
4. 시작 위치: `C:\path\to\avm_project`

### Step 5: 설정 확인
1. "Conditions" 탭
   - 전원 설정 확인
   - "Wake the computer to run this task" 체크 (선택사항)

2. "Settings" 탭
   - "Run the task as soon as possible after a scheduled start is missed" 체크
   - "If the task fails, restart every:" 설정 (예: 15분)

### Step 6: 테스트 실행
1. 작업 선택 후 마우스 우클릭
2. "Run" 선택
3. 로그 확인: `C:\path\to\avm_project\output\orchestration_report_*.json`

---

## 실행 및 모니터링

### 수동 실행
```bash
cd /home/user/-/avm_project
python3 scripts/avm_orchestrator.py
```

### 특정 날짜 범위로 실행
```bash
# 2024년 6월 데이터만 수집
python3 scripts/avm_orchestrator.py --start-date 202406 --end-date 202406

# 2024년 1월~6월 데이터
python3 scripts/avm_orchestrator.py --start-date 202401 --end-date 202406
```

### 로그 모니터링

#### 최근 실행 로그 확인
```bash
# 마지막 100줄 보기
tail -100 logs/avm_orchestration_*.log

# 실시간 모니터링
tail -f logs/cron_execution.log
```

#### 모든 로그 검색
```bash
# 오류 찾기
grep "ERROR" logs/*.log

# 성공 메시지 찾기
grep "✅" logs/*.log

# 특정 날짜의 로그
ls -lt logs/avm_orchestration_*.log | head -1
```

### 리포트 확인

#### JSON 리포트 보기
```bash
# 최신 리포트
cat output/orchestration_report_*.json | jq .

# 모든 리포트 목록
ls -lt output/orchestration_report_*.json
```

#### 리포트 내용
```json
{
  "timestamp": "20260612_100000",
  "status": "success",
  "data_collection": {
    "status": "success",
    "records": 1234
  },
  "preprocessing": {
    "status": "success",
    "samples": 1234,
    "features": 30
  },
  "model_training": {
    "status": "success",
    "models_trained": 4,
    "results": {
      "Linear Regression": {
        "r2_score": 0.8234,
        "rmse": 125000,
        "mae": 95000
      },
      "Random Forest": {
        "r2_score": 0.8567,
        "rmse": 105000,
        "mae": 75000
      }
    }
  }
}
```

### Cron 실행 로그 확인 (Linux/Mac)

#### 시스템 로그에서 Cron 확인
```bash
# Mac
log show --predicate 'process == "cron"' --last 1h

# Linux
grep CRON /var/log/syslog | tail -20
```

#### 직접 로그 모니터링
```bash
# Cron 실행 로그 보기
tail -f logs/cron_execution.log

# 특정 실행의 상세 로그
cat logs/avm_orchestration_YYYYMMDD_HHMMSS.log
```

---

## 트러블슈팅

### 문제 1: Cron 작업이 실행되지 않음

#### 진단
```bash
# Cron 데몬 확인
ps aux | grep cron

# Crontab 확인
crontab -l

# Cron 로그 확인
grep "avm_orchestrator" /var/log/syslog
```

#### 해결방법
```bash
# 1. Crontab 문법 확인
crontab -l | crontab -

# 2. 전체 경로 사용
0 10 * * 4 /usr/bin/python3 /full/path/to/avm_orchestrator.py

# 3. 환경 변수 설정
0 10 * * 4 . $HOME/.bash_profile; cd /path/to/avm_project && python3 scripts/avm_orchestrator.py

# 4. Cron 데몬 재시작
sudo service cron restart  # Linux
sudo launchctl stop com.vixie.cron  # Mac (older)
```

### 문제 2: API 403 Forbidden 오류

#### 진단
```bash
# 로그에서 403 오류 확인
grep "403" logs/*.log

# API 키 확인
echo $DATAGOVKR_API_KEY
```

#### 해결방법
```bash
# 1. API 키 확인
# Data.go.kr 포털 → 마이페이지 → API 관리

# 2. 환경 변수 설정
export DATAGOVKR_API_KEY="your-api-key"
echo "export DATAGOVKR_API_KEY='your-api-key'" >> ~/.bashrc

# 3. Crontab에 환경 변수 설정
# Crontab 편집
crontab -e

# 다음 추가
DATAGOVKR_API_KEY=your-api-key
0 10 * * 4 python3 /path/to/avm_orchestrator.py
```

### 문제 3: Python 모듈 import 오류

#### 진단
```bash
# Python 경로 확인
which python3

# 모듈 확인
python3 -c "from scripts.data_collection_handler import KoreanRealEstateDataCollector"
```

#### 해결방법
```bash
# 1. 필수 패키지 설치
pip3 install -r avm_project/requirements-minimal.txt

# 2. Python 경로 확인 (Crontab에서)
crontab -e
# 다음 추가
0 10 * * 4 /usr/bin/python3 /full/path/to/scripts/avm_orchestrator.py
```

### 문제 4: 디스크 공간 부족

#### 진단
```bash
# 디스크 사용량 확인
du -sh avm_project/
df -h /

# 로그 크기 확인
du -sh logs/
```

#### 해결방법
```bash
# 1. 로그 파일 정리
find logs/ -mtime +30 -delete  # 30일 이상 된 로그 삭제

# 2. 오래된 데이터 정리
find data/raw/ -mtime +60 -delete  # 60일 이상 된 원본 데이터 삭제

# 3. 로그 로테이션 설정 (Crontab)
crontab -e
# 추가
0 0 * * * find /path/to/avm_project/logs -mtime +30 -delete
```

### 문제 5: 메모리 부족으로 인한 중단

#### 해결방법
```bash
# 1. 한 번에 수집하는 데이터 양 제한
# avm_config.json 수정
{
  "data_collection": {
    "batch_size": 1000,
    "max_records_per_request": 1000
  }
}

# 2. 스케줄 조정 (야간 또는 시스템 부하 낮은 시간)
# Crontab 변경
0 2 * * 4  # 새벽 2시 실행

# 3. 메모리 제한 설정
# Bash 스크립트 생성
#!/bin/bash
ulimit -v 2000000  # 2GB 제한
python3 /path/to/avm_orchestrator.py
```

### 문제 6: 모델 학습 실패

#### 진단
```bash
# 전처리된 데이터 확인
ls -lh data/processed/

# 모델 학습 로그 확인
grep "Model" logs/avm_orchestration_*.log
```

#### 해결방법
```bash
# 1. 데이터 최소 요구사항 확인
# avm_config.json
{
  "model_training": {
    "min_samples": 100,
    "min_features": 5
  }
}

# 2. 모델별 트러블슈팅
# - Linear Regression: 피처 수가 샘플 수보다 많은지 확인
# - Random Forest: 메모리 부족 가능성, tree 수 감소
# - Gradient Boosting: 학습률 조정, iteration 수 감소
```

---

## 모니터링 대시보드 (선택사항)

### Cron 실행 자동 리포트
```bash
# 매일 실행 현황 리포트 메일로 전송
0 9 * * * python3 /path/to/scripts/send_report.py
```

### 성능 추적
```bash
# 모델 성능 CSV로 저장
cat output/orchestration_report_*.json | \
  jq '.model_training.results' | \
  >> output/model_performance_tracking.csv
```

### 웹 대시보드 (고급)
```bash
# FastAPI를 사용한 실시간 대시보드
cd avm_project
python3 -m scripts.dashboard_server --port 8000
# 방문: http://localhost:8000/dashboard
```

---

## 요약

| 항목 | 설정 |
|------|------|
| **Linux/Mac** | Cron: `0 10 * * 4` (매주 목요일 10:00) |
| **Windows** | Task Scheduler: 매주 목요일 10:00 |
| **자동화 스크립트** | `avm_orchestrator.py` |
| **설정 스크립트** | `setup_cron_automation.sh` |
| **로그 위치** | `logs/avm_orchestration_*.log` |
| **리포트 위치** | `output/orchestration_report_*.json` |
| **모니터링** | `tail -f logs/cron_execution.log` |

---

## 다음 단계

1. ✅ Loop Engineering 설정 완료
2. 📊 자동화 실행 모니터링
3. 📈 모델 성능 지표 추적
4. 🔄 주간 리포트 검토
5. 🎯 모델 정확성 지속적 개선

---

**마지막 업데이트:** 2026-06-12  
**문의:** 프로젝트 매니저 또는 기술 팀
