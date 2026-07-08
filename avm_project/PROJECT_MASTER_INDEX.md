# 📚 AVM + VWorld 프로젝트 마스터 인덱스

**프로젝트**: NPL AVM 실거래 + VWorld 멀티레이어 통합  
**기간**: 2026-07-03 ~ 2026-08-17 (46일)  
**전략**: 하이브리드 순차-병렬  
**상태**: 🟢 Phase 1 시작 준비 완료  

---

## 📑 **문서 네비게이션**

### **1. 프로젝트 계획 (읽기 우선순위)**

| 문서 | 목적 | 대상 | 읽기 시간 |
|------|------|------|---------|
| **[PROJECT_SEQUENCING_ANALYSIS.md](PROJECT_SEQUENCING_ANALYSIS.md)** | 전체 전략 (순차 vs 병렬 vs 하이브리드) | PM, 리더 | 20분 |
| **[PHASE1_TEAM_EXECUTION_GUIDE.md](PHASE1_TEAM_EXECUTION_GUIDE.md)** | 11일 상세 일정 (Day-by-day) | 모든 팀 | 30분 |
| **[TEAM_QUICK_START_KIT.md](TEAM_QUICK_START_KIT.md)** | 5분 시작 가이드 (명령어 포함) | 모든 팀 | 5분 |

### **2. 기술 사양서 (참고용)**

| 문서 | 용도 | 대상 | 상태 |
|------|------|------|------|
| **[AVM_REAL_DATA_COLLECTION_SPECIFICATION.md](AVM_REAL_DATA_COLLECTION_SPECIFICATION.md)** | 데이터/API 기술 사양 | DE, Data Eng | ✅ 완료 |
| **[AVM_REAL_DATA_COLLECTION_WBS.md](AVM_REAL_DATA_COLLECTION_WBS.md)** | 작업 분해도 (6단계 20항목) | PM, MLE, QA | ✅ 완료 |
| **[AVM_REAL_DATA_COLLECTION_EXECUTION_PLAN.md](AVM_REAL_DATA_COLLECTION_EXECUTION_PLAN.md)** | 실행 계획서 (11일 상세) | 모든 팀 | ✅ 완료 |
| **[DOCUMENT_REVIEW_FINDINGS.md](DOCUMENT_REVIEW_FINDINGS.md)** | 문서 검수 결과 (TIER 분류) | 품질 담당 | ✅ 완료 |
| **[C_STAGE_COMPLETION_SUMMARY.md](C_STAGE_COMPLETION_SUMMARY.md)** | C단계 완료 보고 | PM, 경영진 | ✅ 완료 |

### **3. 코드 & 스크립트 (실행용)**

| 파일 | 기능 | 상태 | 위치 |
|------|------|------|------|
| **fetch_transactions_parallel.py** | 국토부 실거래 병렬 수집 | ✅ 완료 | `scripts/` |
| **vworld_multi_layer_collector.py** | VWorld 14레이어 통합 수집 (준비 중) | ⏳ Phase 1 | `vworld_multi_layer_collector/` |

---

## 🗓️ **프로젝트 타임라인**

```
2026-07-03                2026-07-13             2026-08-17
   (시작)                 (배포)                  (완료)
   │                        │                       │
   ├─ Phase 1 ────────────┼─ Phase 2 ───────────┤ Phase 3 ──┤
   │ (병렬 준비)           │ (AVM 배포)         │ (통합)     │
   │ AVM + VWorld         │ VWorld 집중         │ Final    │
   │ 11일                  │ 7일                 │ 29일      │
   └────────────────────────────────────────────────────────┘

리소스:
  07-03~13: 8/10 (AVM 6 + VWorld 2)
  07-13~20: 7/10 (AVM 2 + VWorld 5)
  07-20~08-17: 6/10 (감소, 완성 단계)
```

---

## 📊 **프로젝트 메트릭**

### **AVM 프로젝트**

| 항목 | 목표 | 현재 | 진행률 |
|------|------|------|--------|
| 실거래 데이터 | 850K+ 건 | 0 | 0% |
| 모델 R² | >0.94 | 0.949 | - |
| MAPE | <10.5% | 11.2% | - |
| 배포 | Production | 준비 중 | 90% |

### **VWorld 프로젝트**

| 항목 | 목표 | 현재 | 진행률 |
|------|------|------|--------|
| 레이어 정의 | 14개 | 14개 ✅ | 100% |
| Registry | 완성 | 초안 | 20% |
| Parser | 5개+ | 0 | 0% |
| Endpoint Probe | 13개 | 0 | 0% |

---

## 🎯 **주요 마일스톤**

```
✅ 완료:
   ├─ AVM SPECIFICATION (3,000줄)
   ├─ AVM WBS (2,500줄)
   ├─ AVM EXECUTION_PLAN (3,500줄)
   ├─ VWorld Rev.4 기획서
   ├─ fetch_transactions_parallel.py (500줄)
   ├─ 문서 검수 (TIER 1/2/3 분류)
   └─ Phase 1 상세 계획

⏳ 진행 중:
   ├─ 07-03: Phase 1 시작 (팀 8명)
   ├─ 07-04: Pilot 수집
   ├─ 07-05~07: 전국 데이터 수집
   ├─ 07-08~10: 모델 재학습
   └─ 07-11~13: 배포

🔮 예정:
   ├─ Phase 2 (07-13~20): VWorld 집중 개발
   ├─ Phase 3 (07-20~08-17): 통합 및 마무리
   └─ 최종 완료 (08-17)
```

---

## 📖 **문서 읽기 경로**

### **PM / 리더 (첫 시작)**
```
1. PROJECT_SEQUENCING_ANALYSIS.md (20분)
   └─ 왜 하이브리드 전략인지 이해
   
2. PHASE1_TEAM_EXECUTION_GUIDE.md (30분)
   └─ 11일 일정 파악
   
3. TEAM_QUICK_START_KIT.md (5분)
   └─ 팀과 함께 시작
```

### **AVM Team (개발자)**
```
1. TEAM_QUICK_START_KIT.md (5분)
   └─ 즉시 실행 준비
   
2. AVM_REAL_DATA_COLLECTION_SPECIFICATION.md (필요시)
   └─ 데이터 품질 기준 확인
   
3. PHASE1_TEAM_EXECUTION_GUIDE.md (필요시)
   └─ 일정 확인
```

### **VWorld Team (설계자)**
```
1. TEAM_QUICK_START_KIT.md (5분)
   └─ 시작 지침
   
2. VWorld 기획서 (Rev.4) (1시간)
   └─ 14개 레이어 이해
   
3. PROJECT_SEQUENCING_ANALYSIS.md (20분)
   └─ Phase 전략 이해
```

---

## 🔗 **빠른 링크**

### **즉시 필요한 것**
- ⚡ [팀 즉시 실행 키트 (5분)](TEAM_QUICK_START_KIT.md)
- ⚡ [Phase 1 Day-by-day 일정](PHASE1_TEAM_EXECUTION_GUIDE.md)
- ⚡ [하이브리드 전략 이해](PROJECT_SEQUENCING_ANALYSIS.md)

### **기술 사양 (참고)**
- 📘 [AVM 사양서](AVM_REAL_DATA_COLLECTION_SPECIFICATION.md)
- 📘 [AVM WBS](AVM_REAL_DATA_COLLECTION_WBS.md)
- 📘 [AVM 실행계획](AVM_REAL_DATA_COLLECTION_EXECUTION_PLAN.md)

### **코드**
- 🐍 [fetch_transactions_parallel.py](scripts/fetch_transactions_parallel.py)
- 🐍 [vworld_multi_layer_collector.py (준비 중)](vworld_multi_layer_collector/)

---

## 📋 **문서 상태 체크**

```
【 AVM 프로젝트 】

✅ SPECIFICATION (2.4 데이터 품질 + 2.5 API 최적화 포함)
✅ WBS (4.4.0 하드웨어 사양 포함)
✅ EXECUTION_PLAN (DAY 11 Blue-Green 15단계 상세화)
✅ 검수 완료 (TIER 1 모두 개선)
✅ fetch_transactions_parallel.py (500줄 완성)

【 VWorld 프로젝트 】

✅ 기획서 Rev.4 (14개 레이어 정의)
⏳ Registry seed (작성 중)
⏳ Parser 초안 (작성 대기)
⏳ Endpoint probe CLI (작성 대기)

【 프로세스 】

✅ 순서 분석 (하이브리드 전략 결정)
✅ Phase 1 상세 계획 (Day-by-day)
✅ 팀 실행 키트 (Quick Start)
⏳ 모니터링 대시보드 (작성 중)
⏳ 최종 인덱스 (이 문서)
```

---

## 🚀 **지금 시작하기**

```
【 Step 1: 문서 읽기 】
1. PROJECT_SEQUENCING_ANALYSIS.md (20분)
2. PHASE1_TEAM_EXECUTION_GUIDE.md (30분)
3. TEAM_QUICK_START_KIT.md (5분)

【 Step 2: 팀 배치 】
- AVM Team (6명): API 키 신청, Pilot 준비
- VWorld Team (2명): Registry 설계, Probe CLI

【 Step 3: 09:30 AM Standup 】
- Slack #avm-vworld-phase1
- Daily 진행 상황 보고

【 Step 4: 실행 】
07-03: 시작
07-13: AVM 배포
08-17: 완료
```

---

**문서 정리 완료!** 📚

모든 팀이 이 인덱스에서 필요한 문서를 찾을 수 있습니다. ✅

