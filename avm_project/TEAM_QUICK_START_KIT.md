# 팀 즉시 실행 키트 (Quick Start)

**버전**: 1.0  
**작성일**: 2026-07-03  
**상태**: 🟢 READY TO GO  

---

## 🚀 **팀별 시작 가이드 (5분 안내)**

### **AVM Team (6명)**

#### **준비물 확인** (2분)
```bash
# 1. 프로젝트 폴더 이동
cd F:\NPL전례\avm_project

# 2. 환경 확인
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('✓' if os.getenv('KOREA_API_KEY') else '⚠️ API_KEY 미설정')"

# 3. 스크립트 테스트
python scripts/fetch_transactions_parallel.py --help
```

#### **실행 명령어** (즉시 복사/붙여넣기 가능)

**Pilot 수집** (07-04, 일일 10:00 AM)
```bash
python scripts/fetch_transactions_parallel.py \
  --year 2026 --month 6 \
  --sido 경기도 \
  --workers 3 \
  --checkpoint data/collection_checkpoint.json
```

**전국 수집** (07-05, 토요일 10:00 AM)
```bash
python scripts/fetch_transactions_parallel.py \
  --months 12 \
  --workers 3 \
  --checkpoint data/collection_checkpoint.json
```

**중단 후 재개** (필요 시)
```bash
python scripts/fetch_transactions_parallel.py \
  --months 12 \
  --workers 3 \
  --checkpoint data/collection_checkpoint.json
```

#### **검증 SQL** (복사 가능)

```sql
-- 기본 통계
SELECT COUNT(*) as total_records,
       COUNT(DISTINCT sgg_code) as unique_regions,
       MIN(contract_year||'-'||contract_month) as earliest,
       MAX(contract_year||'-'||contract_month) as latest
FROM transactions;

-- 데이터 샘플
SELECT * FROM transactions LIMIT 10;

-- 중복 확인
SELECT COUNT(*) as duplicate_count
FROM (SELECT transaction_key FROM transactions 
      GROUP BY transaction_key HAVING COUNT(*) > 1);
```

---

### **VWorld Team (2명)**

#### **준비물 확인** (2분)
```bash
# 1. 기획서 다운로드
# F:\NPL전례\avm_project\ 또는 C:\Users\eungk\OneDrive\Documents\AVM\docs\
# vworld_search20_geocoder_wfs_wms_multi_layer_integrated_db_plan_20260707_rev4.md

# 2. Python 환경 확인
python --version  # 3.8+
pip list | grep -E "requests|tqdm"
```

#### **즉시 시작할 작업**

**1. registry seed 초안** (10분)
```python
# vworld_multi_layer_collector/config/rev4_registry.seed.json
{
  "version": "rev4",
  "created_at": "2026-07-03",
  "layers": [
    {
      "layer_id": "search20",
      "api_kind": "search",
      "endpoint": "https://api.vworld.kr/req/search",
      "status": "pending_probe"
    },
    # ... 14개 레이어 정의
  ]
}
```

**2. endpoint probe CLI skeleton** (30분)
```bash
mkdir -p vworld_multi_layer_collector/{scripts,parsers,config}

# vworld_multi_layer_collector.py skeleton
python scripts/vworld_multi_layer_collector.py probe-endpoints \
  --profile rev4 \
  --key-prompt \
  --output config/rev4_registry.probed.json
```

---

## 📋 **팀별 Day-1 체크리스트**

### **AVM Team Checklist (07-03)**

```
□ 09:00 - 킥오프 미팅 참석
□ 09:30 - Daily standup 첫 미팅
□ 10:00 - API 키 신청 시작 (DE Lead)
□ 10:00 - fetch_transactions_parallel.py 테스트 (DE)
□ 10:30 - 환경 최종 검증
□ 13:00 - Pilot 수집 준비 완료
□ 17:00 - 일일 종료 보고 (Slack)

완료 기준:
✓ API 키 신청됨
✓ fetch_transactions_parallel.py 실행 확인됨
✓ Pilot 수집 준비 (07-04 실행 대기)
```

### **VWorld Team Checklist (07-03)**

```
□ 09:00 - 킥오프 미팅 참석
□ 09:30 - Daily standup 첫 미팅
□ 10:00 - 기획서 숙독 시작
□ 11:00 - registry seed 구조 설계
□ 13:00 - registry seed v1 초안 작성
□ 14:00 - probe CLI skeleton 개발
□ 16:00 - 코드 review & test
□ 17:00 - Phase 1 완료 계획 정리

완료 기준:
✓ registry seed v1 완성
✓ probe CLI skeleton 완성
✓ 14개 레이어 정의됨
```

---

## 🔔 **Daily Standup 템플릿 (매일 09:30 AM)**

```
【 Slack 메시지 형식 】

**AVM Team Report:**
- 진행: [진도 %] (수집 건수 or 모델 진행)
- 블로커: [없음 / 상세 설명]
- 오늘 일정: [주요 마일스톤]

**VWorld Team Report:**
- 진행: [진도 %] (parser 개수 or registry 항목)
- 블로커: [없음 / 상세 설명]
- 오늘 일정: [주요 마일스톤]

예시:
---
**AVM Team:**
- 진행: 10% (Pilot 준비 중)
- 블로커: API 키 신청 대기 (24시간)
- 오늘: Pilot 수집 실행 (10:00 AM)

**VWorld Team:**
- 진행: 20% (registry seed 작성 중)
- 블로커: 없음
- 오늘: probe CLI skeleton 완성
---
```

---

## 📊 **실행 상태 추적 (간단)**

```
【 Google Sheets 또는 CSV 】

Day | AVM 진행 | AVM 블로커 | VWorld 진행 | VWorld 블로커
----|---------|-----------|-----------|---------------
07-03| 준비   | API_KEY   | 설계      | 없음
07-04| Pilot  | 검증      | Registry  | 없음
07-05| 수집   | 없음      | Parser    | 없음
...

또는 간단히 Slack 스레드에 기록
```

---

## ⚡ **긴급 상황 대응**

### **API 키 미발급 (24시간 초과)**
```
1. 백업 계정으로 신청된 키 사용
2. 또는 VWorld 개발을 먼저 진행
3. Slack에 PM 보고
```

### **수집 중 오류 발생**
```
1. 로그 확인: tail -f data/fetch_transactions_parallel.log
2. 체크포인트 있으면 자동 재개됨
3. 3회 재시도 후 실패하면 보고
```

### **모델 학습 시간 초과**
```
1. 예상: 20시간, 최악: 25시간
2. 하드웨어 부족하면 배치 크기 감소
3. GPU 있으면 XGBoost GPU 버전 사용
```

---

## 📞 **빠른 연락처**

```
Project Manager: [지정 필요]
AVM Team Lead: [지정 필요]
VWorld Lead: [지정 필요]
Slack: #avm-vworld-phase1

긴급 문제: [연락처 기록]
```

---

## ✅ **지금 바로 할 것**

```
1️⃣ Slack 채널 입장: #avm-vworld-phase1
2️⃣ 09:30 AM standup 미팅 참석
3️⃣ 자신의 역할 확인
4️⃣ 준비물 확인 실행

【 AVM Team 】
python scripts/fetch_transactions_parallel.py --help

【 VWorld Team 】
기획서 다운로드 및 숙독 시작
```

---

**준비됨! 시작하자!** 🚀

