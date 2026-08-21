# 📅 주간 자동화 가이드

**작성일:** 2026-06-19  
**버전:** v1.0  
**상태:** 🟢 활성

---

## 📋 목차

1. [개요](#개요)
2. [요구사항](#요구사항)
3. [자동화 구성](#자동화-구성)
4. [Linux/Mac 설정](#linuxmac-설정)
5. [Windows 설정](#windows-설정)
6. [모니터링](#모니터링)
7. [문제 해결](#문제-해결)
8. [로그 확인](#로그-확인)

---

## 개요

### 주간 자동화란?

매주 정해진 시간(목요일 10:00)에 다음을 자동으로 실행합니다:

```
1. 데이터 로드 (real_estate_2024.csv)
2. 6개 모델 학습 (LR, DT, RF, GB, XGBoost, LightGBM)
3. 앙상블 생성 (Meta learner)
4. 성능 평가
5. 결과 저장 (JSONL 형식)
6. 성능 저하 확인 및 알림
```

### 목표

- ✅ 매주 자동 모델 재학습
- ✅ 성능 모니터링
- ✅ 데이터 품질 유지
- ✅ 자동 알림 시스템

---

## 요구사항

### 1. 필수 파일

```
avm_project/
├─ scripts/
│  ├─ weekly_retrain_scheduler.py (250줄)
│  └─ performance_monitor.py (250줄)
├─ config/
│  └─ schedule_config.json (설정 파일)
├─ logs/
│  ├─ weekly_retrain.log
│  ├─ performance_monitor.log
│  └─ retrain_history.jsonl
└─ data/
   └─ raw/real_estate_2024.csv (데이터)
```

### 2. 필수 패키지

```bash
pip install -r avm_project/requirements.txt
```

패키지:
- pandas
- numpy
- scikit-learn
- xgboost
- lightgbm
- joblib

### 3. 디렉토리 권한

```bash
# 로그 디렉토리 생성
mkdir -p avm_project/logs

# 모델 디렉토리 생성
mkdir -p avm_project/models

# 실행 권한 (Linux/Mac)
chmod +x avm_project/scripts/weekly_retrain_scheduler.py
chmod +x avm_project/scripts/performance_monitor.py
```

---

## 자동화 구성

### 전체 파이프라인

```
Cron/Task Scheduler
    ↓
weekly_retrain_scheduler.py 실행
    ├─ load_data()
    ├─ train_models()
    ├─ create_ensemble()
    ├─ save_models()
    ├─ save_results()
    └─ send_alert()
    ↓
retrain_history.jsonl 기록
    ↓
performance_monitor.py 자동 실행 (24시간마다)
    ├─ load_history()
    ├─ calculate_trend()
    ├─ check_alerts()
    └─ generate_report()
    ↓
로그 파일 생성
```

### 설정 파일

`avm_project/config/schedule_config.json`:

```json
{
  "schedule": {
    "type": "weekly",
    "day_of_week": "thursday",
    "hour": 10,
    "minute": 0,
    "timezone": "Asia/Seoul"
  },
  "performance_threshold": 0.95,
  "alert_config": {
    "enable_email": false,
    "enable_slack": false
  }
}
```

---

## Linux/Mac 설정

### 1단계: Cron 작업 추가

```bash
# Cron 편집 열기
crontab -e
```

### 2단계: Cron 명령어 추가

```bash
# 매주 목요일 10:00에 실행
0 10 * * 4 cd /home/user/-/avm_project && /usr/bin/python3 scripts/weekly_retrain_scheduler.py >> logs/weekly_retrain.cron.log 2>&1

# 매일 11:00에 모니터링 실행
0 11 * * * cd /home/user/-/avm_project && /usr/bin/python3 scripts/performance_monitor.py >> logs/performance_monitor.cron.log 2>&1
```

### 3단계: 저장 및 확인

```bash
# 저장: Ctrl+X, Y, Enter (nano) 또는 :wq (vim)

# 추가된 작업 확인
crontab -l

# 결과:
# 0 10 * * 4 cd /home/user/-/avm_project && /usr/bin/python3 scripts/weekly_retrain_scheduler.py >> logs/weekly_retrain.cron.log 2>&1
# 0 11 * * * cd /home/user/-/avm_project && /usr/bin/python3 scripts/performance_monitor.py >> logs/performance_monitor.cron.log 2>&1
```

### 4단계: 테스트

```bash
# 수동 테스트 (Cron 실행 전)
cd /home/user/-/avm_project
python3 scripts/weekly_retrain_scheduler.py

# 모니터링 테스트
python3 scripts/performance_monitor.py

# 로그 확인
tail -f logs/weekly_retrain.log
tail -f logs/performance_monitor.log
```

### 5단계: Cron 로그 확인

```bash
# macOS
log stream --predicate 'process == "cron"'

# Linux
grep CRON /var/log/syslog

# 또는 파일 확인
tail -f /home/user/-/avm_project/logs/weekly_retrain.cron.log
```

---

## Windows 설정

### 1단계: 작업 스케줄러 열기

```
방법 1: 검색
  - Windows 검색: "작업 스케줄러" 검색
  
방법 2: 명령어
  - Win+R: taskschd.msc 입력
```

### 2단계: 기본 작업 만들기

```
1. 작업 스케줄러 열기
2. 작업 > 기본 작업 만들기
3. 이름: "AVM Weekly Retrain"
4. 설명: "매주 목요일 10:00에 AVM 모델 재학습"
5. 다음 클릭
```

### 3단계: 트리거 설정

```
1. "트리거" 탭
2. "새로 만들기" 클릭
3. 설정:
   - 작업 시작: 일정에 따라
   - 주간
   - 반복: 매주
   - 요일: 목요일
   - 시간: 10:00:00
4. 확인
```

### 4단계: 작업 설정

```
1. "작업" 탭
2. "새로 만들기" 클릭
3. 설정:
   - 작업: 프로그램 시작
   - 프로그램/스크립트: python.exe
   - 인수 추가: C:\path\to\avm_project\scripts\weekly_retrain_scheduler.py
   - 시작 위치: C:\path\to\avm_project
4. 확인
```

### 5단계: 조건 설정

```
1. "조건" 탭
2. 전원:
   - "컴퓨터가 AC 전원으로 실행 중일 때만 작업 시작" 체크
3. 네트워크:
   - 필요에 따라 설정
```

### 6단계: 설정 확인

```
1. "설정" 탭
2. "작업을 실행한 후에 제한 시간 동안 재시도" 체크
   - 제한 시간: 1시간
   - 재시도 간격: 10분
3. 확인
```

### 7단계: 테스트

```bash
# PowerShell (관리자 권한)
Set-Location C:\path\to\avm_project
python.exe scripts/weekly_retrain_scheduler.py

# 또는 Python IDE에서 직접 실행
```

### 8단계: 작업 실행 확인

```
1. 작업 스케줄러 > 작업 라이브러리
2. "AVM Weekly Retrain" 선택
3. 마우스 우클릭 > "실행"
4. 로그 파일 확인: logs/weekly_retrain.log
```

---

## 모니터링

### 1. 자동 모니터링

매일 11:00에 `performance_monitor.py`가 자동으로 실행되어:
- 최신 재학습 결과 로드
- R² 점수 확인
- 성능 추세 계산
- 알림 필요 여부 판단
- 리포트 생성

### 2. 수동 모니터링

```bash
# 언제든 수동으로 실행
cd /home/user/-/avm_project
python3 scripts/performance_monitor.py
```

### 3. 로그 파일 확인

```bash
# 재학습 로그
tail -100 logs/weekly_retrain.log

# 모니터링 로그
tail -100 logs/performance_monitor.log

# 실행 기록 (JSONL)
tail -10 logs/retrain_history.jsonl

# 예제 출력:
# {"timestamp": "2026-06-19T10:00:00", "models": {...}, "ensemble": {"r2": 0.8420, ...}, "status": "success"}
```

---

## 문제 해결

### 문제 1: Cron이 실행되지 않음

**확인 사항:**

```bash
# 1. Cron 서비스 확인
sudo systemctl status cron  # Linux
sudo launchctl list | grep cron  # macOS

# 2. 경로 확인
which python3
# /usr/bin/python3 (또는 다른 경로)

# 3. Cron 환경 변수 확인
crontab -e
# 맨 위에 다음 추가:
# SHELL=/bin/bash
# PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
# PYTHONPATH=/home/user/-/avm_project

# 4. 권한 확인
chmod 755 /home/user/-/avm_project/scripts/weekly_retrain_scheduler.py
chmod 755 /home/user/-/avm_project/scripts/performance_monitor.py
```

### 문제 2: "ModuleNotFoundError"

```bash
# 1. Python 패키지 설치
pip3 install -r /home/user/-/avm_project/requirements.txt

# 2. Cron의 Python 경로 명시
# Cron에서 전체 경로 사용:
/usr/bin/python3 /home/user/-/avm_project/scripts/weekly_retrain_scheduler.py
```

### 문제 3: 데이터 파일을 찾을 수 없음

```bash
# Cron에서 상대 경로 대신 절대 경로 사용
# ❌ 잘못된 예:
cd /home/user/-/avm_project && python3 scripts/weekly_retrain_scheduler.py

# ✅ 올바른 예:
cd /home/user/-/avm_project && /usr/bin/python3 /home/user/-/avm_project/scripts/weekly_retrain_scheduler.py >> /home/user/-/avm_project/logs/weekly_retrain.cron.log 2>&1
```

### 문제 4: 권한 거부 오류

```bash
# Linux/Mac에서 실행 권한 추가
chmod +x /home/user/-/avm_project/scripts/weekly_retrain_scheduler.py

# Windows에서는 Python 경로 확인
where python.exe
```

### 문제 5: Cron 로그가 비어있음

```bash
# 1. 로그 파일 생성 확인
touch /home/user/-/avm_project/logs/weekly_retrain.cron.log
chmod 666 /home/user/-/avm_project/logs/weekly_retrain.cron.log

# 2. 디렉토리 권한 확인
chmod 755 /home/user/-/avm_project/logs

# 3. 간단한 테스트 Cron 추가
0 * * * * echo "Cron works" >> /home/user/-/avm_project/logs/test.log

# 4. 1시간 후 확인
cat /home/user/-/avm_project/logs/test.log
```

---

## 로그 확인

### 1. 재학습 로그

```
파일: logs/weekly_retrain.log

내용:
================================================================================
📊 주간 모델 재학습 시작
================================================================================
2026-06-19 10:00:00 - INFO - 데이터 로드 완료: 5000행
2026-06-19 10:00:02 - INFO - 데이터 분할: 70% 훈련, 15% 검증, 15% 테스트
2026-06-19 10:05:30 - INFO - [xgboost] R² = 0.8420, RMSE = 55,800,000
2026-06-19 10:10:00 - INFO - 앙상블 R² = 0.8450, RMSE = 55,200,000
2026-06-19 10:10:15 - INFO - 결과 저장 완료: logs/retrain_history.jsonl
================================================================================
📊 재학습 완료 요약
================================================================================
```

### 2. 모니터링 로그

```
파일: logs/performance_monitor.log

내용:
================================================================================
📊 성능 모니터링 리포트
================================================================================
✅ 최신 재학습: 2026-06-19T10:00:00

📈 앙상블 모델 성능:
  R² = 0.8450
  RMSE = 55,200,000원
  MAE = 42,500,000원

📊 R² 추세:
  방향: ↑ 상승
  변화율: 0.12%
  최신값: 0.8450
  이전값: 0.8420

✅ 모든 지표 정상
================================================================================
```

### 3. 실행 기록 (JSONL)

```
파일: logs/retrain_history.jsonl

형식:
{"timestamp": "2026-06-19T10:00:00", "models": {"xgboost": {"r2": 0.8420, "rmse": 55800000, "mae": 42500000}, ...}, "ensemble": {"r2": 0.8450, "rmse": 55200000, "mae": 42300000}, "status": "success"}
```

---

## 다음 단계

1. **설정 완료**
   - Cron 또는 Task Scheduler 설정
   - 로그 디렉토리 생성
   - 패키지 설치 확인

2. **테스트 실행**
   - 수동으로 스크립트 실행
   - 로그 파일 생성 확인
   - 모니터링 실행

3. **자동화 검증**
   - 정해진 시간에 자동 실행 확인
   - 로그 파일에 기록 확인
   - 성능 지표 트렌드 모니터링

4. **알림 설정 (선택)**
   - Email 알림 (향후)
   - Slack 알림 (향후)
   - SMS 알림 (향후)

---

## 체크리스트

```
설정 전:
[ ] Python 3.7+ 설치 확인
[ ] 필수 패키지 설치 (pip install -r requirements.txt)
[ ] 로그 디렉토리 생성 (mkdir -p logs)
[ ] 모델 디렉토리 생성 (mkdir -p models)

설정 후:
[ ] Cron/Task Scheduler 등록
[ ] 수동 테스트 실행
[ ] 로그 파일 생성 확인
[ ] 모니터링 실행 확인

운영 중:
[ ] 주간 로그 확인
[ ] 성능 지표 모니터링
[ ] 알림 설정 (필요시)
[ ] 모델 성능 추세 분석
```

---

**작성자:** AI Development Team  
**최종 수정:** 2026-06-19  
**라이선스:** MIT
