# Phase 13.5 WBS (Work Breakdown Structure)
## 자동화 루프 & 지속적 개선

**기간**: 2026-07-24 ~ 2026-08-06 (14일, Week 4-5, 병렬 진행 가능)  
**팀**: Claude Agent (1명) + Cron Scheduler (자동)  
**주요 마일스톤**: Cron 설정 (Day 1), 첫 재학습 (Day 8-9), 모니터링 운영 (Day 10-14)

---

## 1. 전체 작업 분해

```
Phase 13.5 (14일 × 6h = 84시간, 병렬 진행 시 40시간)
│
├─ 1. Cron 자동화 구성 (8h)
│  ├─ 1.1 AutomationEngine 클래스 작성 (2h)
│  ├─ 1.2 Bash 스크립트 작성 (3h)
│  ├─ 1.3 Cron 작업 등록 (1h)
│  └─ 1.4 스크립트 테스트 (2h)
│
├─ 2. 모니터링 & 알림 시스템 (12h)
│  ├─ 2.1 Prometheus 메트릭 정의 (2h)
│  ├─ 2.2 AlertManager 규칙 작성 (2h)
│  ├─ 2.3 Slack/Email/SMS 통합 (3h)
│  ├─ 2.4 Grafana 대시보드 구성 (3h)
│  └─ 2.5 알림 테스트 (2h)
│
├─ 3. A/B 테스팅 인프라 (6h)
│  ├─ 3.1 ABTestingManager 클래스 (2h)
│  ├─ 3.2 트래픽 분산 로직 (1.5h)
│  ├─ 3.3 통계 검정 구현 (1.5h)
│  └─ 3.4 테스팅 UI (1h)
│
├─ 4. 롤백 & Contingency (6h)
│  ├─ 4.1 자동 롤백 스크립트 (2h)
│  ├─ 4.2 헬스체크 시스템 (2h)
│  ├─ 4.3 롤백 테스트 (1h)
│  └─ 4.4 Incident response 가이드 (1h)
│
├─ 5. 특성 드리프트 감지 (4h)
│  ├─ 5.1 FeatureDriftDetector 클래스 (1.5h)
│  ├─ 5.2 이상 탐지 로직 (1.5h)
│  └─ 5.3 드리프트 알림 (1h)
│
├─ 6. 주간 자동 재학습 실행 (10h)
│  ├─ 6.1 첫 재학습 실행 (2h, 실제 수행)
│  ├─ 6.2 결과 검증 (1.5h)
│  ├─ 6.3 모델 배포 결정 (1h)
│  ├─ 6.4 배포 실행 (0.5h)
│  ├─ 6.5 배포 후 모니터링 (2h)
│  ├─ 6.6 2번째 재학습 (2h)
│  └─ 6.7 재학습 프로세스 최적화 (1.5h)
│
├─ 7. 모니터링 운영 (12h)
│  ├─ 7.1 Prometheus/Grafana 모니터링 (3h)
│  ├─ 7.2 일일 성능 리포트 (2h)
│  ├─ 7.3 이상 탐지 & 조사 (2h)
│  ├─ 7.4 알림 규칙 미세조정 (2h)
│  ├─ 7.5 로그 분석 (2h)
│  └─ 7.6 성능 최적화 (1h)
│
├─ 8. 문서화 & 가이드 (10h)
│  ├─ 8.1 운영 매뉴얼 작성 (2h)
│  ├─ 8.2 Runbook 작성 (2h)
│  ├─ 8.3 트러블슈팅 가이드 (2h)
│  ├─ 8.4 자동화 가이드 (2h)
│  └─ 8.5 API 문서 업데이트 (2h)
│
└─ 9. QA & 최종 검증 (8h)
   ├─ 9.1 자동화 프로세스 재검증 (2h)
   ├─ 9.2 장애 조치 테스트 (2h)
   ├─ 9.3 성능 SLA 검증 (2h)
   └─ 9.4 Phase 14 준비 확인 (2h)
```

---

## 2. 일일 진행 계획

### Week 4 (2026-07-24 ~ 2026-07-28): 기초 자동화 구축

#### Day 1 (2026-07-24): Cron 자동화 기초

```
시간    작업                          담당    상태    산출물
─────────────────────────────────────────────────────────
09:00   1.1 AutomationEngine 작성      Claude  ✓      python 클래스
10:30   1.2 Bash 스크립트 작성         Claude  ✓      run_weekly_retraining.sh
12:00   Lunch (1h)
13:00   1.3 Cron 작업 등록             Claude  ✓      /etc/cron.d/avm-automation
14:00   1.4 로컬 테스트                Claude  ✓      드라이런 성공
15:00   Daily Standup & Log
15:30   End of Day 1
```

**Day 1 산출물**:
- ✅ AutomationEngine 클래스 (<50 lines/method)
- ✅ run_weekly_retraining.sh (완전 구현)
- ✅ Cron 작업 등록 완료
- ✅ 로컬 테스트 통과

---

#### Day 2-3 (2026-07-25~26): 모니터링 시스템

```
시간    작업                          담당    상태    산출물
─────────────────────────────────────────────────────────
Day 2:
09:00   2.1 Prometheus 메트릭          Claude  ✓      metrics.py
10:30   2.2 AlertManager 규칙          Claude  ✓      alerting_rules.yml
12:00   Lunch
13:00   2.3 Slack/Email 통합           Claude  ✓      notification.py
15:00   Daily Standup
15:30   End of Day 2

Day 3:
09:00   2.4 Grafana 대시보드            Claude  ✓      dashboard config
11:00   2.5 알림 통합 테스트            Claude  ✓      테스트 알림 전송
12:00   Lunch
13:00   모니터링 시스템 QA             Claude  ✓      최종 검증
15:00   Daily Standup
15:30   End of Day 3
```

**Day 2-3 산출물**:
- ✅ Prometheus metrics 정의
- ✅ AlertManager 규칙
- ✅ Slack/Email/SMS 통합
- ✅ Grafana 대시보드 (기본)
- ✅ 알림 시스템 동작 확인

---

#### Day 4-5 (2026-07-27~28): A/B 테스팅 & 롤백

```
Day 4:
09:00   3.1 ABTestingManager           Claude  ✓      python 클래스
11:00   3.2 트래픽 분산 로직            Claude  ✓      router 구현
12:00   Lunch
13:00   3.3 통계 검정                  Claude  ✓      t-test 구현
15:00   3.4 테스팅 UI                  Claude  ✓      간단한 대시보드

Day 5:
09:00   4.1 자동 롤백 스크립트          Claude  ✓      rollback.sh
11:00   4.2 헬스체크 시스템            Claude  ✓      healthcheck.py
12:00   Lunch
13:00   4.3 롤백 드라이 런             Claude  ✓      테스트 성공
14:30   4.4 Incident 가이드            Claude  ✓      마크다운 문서
15:30   Daily Standup
16:00   End of Week 4
```

**Week 4 산출물**:
- ✅ 완전 자동화 시스템 (Cron+Script)
- ✅ 모니터링 & 알림 (Prometheus/Grafana/Slack)
- ✅ A/B 테스팅 인프라
- ✅ 자동 롤백 메커니즘
- ✅ 모든 시스템 로컬 테스트 완료

---

### Week 5 (2026-07-29 ~ 2026-08-06): 실제 운영 & 최적화

#### Day 8 (2026-07-29): 첫 재학습 실행

```
시간    작업                          담당    상태    산출물
─────────────────────────────────────────────────────────
09:00   5.1 드리프트 감지 코드          Claude  ✓      drift_detector.py
10:30   5.2 이상 탐지 통합             Claude  ✓      anomaly detection
11:30   준비 작업 완료 검증            Claude  ✓      모든 시스템 ready
12:00   Lunch
13:00   [scheduled] 첫 주간 재학습 시작 Cron   🚀     데이터 수집 중...
13:30   모니터링 시작                  Claude  ✓      대시보드 활성화
14:30   재학습 진행 상황 추적          Claude  ⏳     실시간 모니터링
15:30   Daily Standup
16:00   End of Day 8
```

**Day 8 산출물**:
- ✅ 드리프트 감지 시스템 완성
- ✅ 첫 주간 재학습 시작 (수동 트리거)
- 📊 실시간 모니터링 대시보드
- 📋 재학습 로그

---

#### Day 9 (2026-07-30): 첫 재학습 완료 & 결과 검증

```
시간    작업                          담당    상태    산출물
─────────────────────────────────────────────────────────
09:00   첫 재학습 완료 확인            Claude  ⏳     결과 검증 중
10:00   6.2 결과 분석                  Claude  ✓      R² 점수 확인
11:00   6.3 모델 배포 결정             Claude  ✓      deployment_decision.json
12:00   Lunch
13:00   6.4 모델 배포 실행             Claude  ✓      새 모델 배포 (if R²>0.84)
13:30   6.5 배포 후 모니터링           Claude  ⏳     health checks
14:30   A/B 테스팅 검증               Claude  ✓      old vs new 비교
15:30   Daily Standup
16:00   End of Day 9
```

**Day 9 산출물**:
- ✅ 첫 재학습 결과 보고서
- ✅ 모델 배포 완료 (또는 hold 결정)
- ✅ A/B 테스팅 데이터
- 📊 배포 후 성능 비교

---

#### Day 10-11 (2026-07-31 ~ 2026-08-01): 모니터링 운영

```
Day 10:
09:00   7.1 Prometheus/Grafana 모니터링 Claude ✓     대시보드 운영
11:00   7.2 일일 성능 리포트            Claude ✓     자동 생성
12:00   Lunch
13:00   7.3 이상 탐지 & 조사           Claude ⏳     drift 모니터링
15:30   Daily Standup

Day 11:
09:00   7.4 알림 규칙 미세조정         Claude ✓     false positive 감소
11:00   7.5 로그 분석                  Claude ✓     주간 로그 검토
12:00   Lunch
13:00   7.6 성능 최적화                Claude ✓     Cron 스크립트 개선
15:30   Daily Standup
```

**Day 10-11 산출물**:
- ✅ Prometheus/Grafana 운영 중
- ✅ 자동 일일 성능 리포트
- ✅ 알림 규칙 최적화
- 📊 주간 모니터링 요약

---

#### Day 12-13 (2026-08-02~03): 문서화

```
Day 12:
09:00   8.1 운영 매뉴얼                Claude ✓     manual.md
11:00   8.2 Runbook                    Claude ✓     runbook.md
12:00   Lunch
13:00   8.3 트러블슈팅 가이드          Claude ✓     troubleshooting.md
15:30   Daily Standup

Day 13:
09:00   8.4 자동화 가이드              Claude ✓     automation_guide.md
11:00   8.5 API 문서 업데이트          Claude ✓     swagger update
12:00   Lunch
13:00   문서 최종 리뷰                 Claude ✓     모든 문서 검증
15:30   Daily Standup
```

**Day 12-13 산출물**:
- ✅ 운영 매뉴얼 (4장)
- ✅ Runbook (troubleshooting)
- ✅ 자동화 가이드
- ✅ API 문서 (Swagger)

---

#### Day 14 (2026-08-04): 최종 검증 & 이관

```
시간    작업                          담당    상태    산출물
─────────────────────────────────────────────────────────
09:00   9.1 자동화 프로세스 재검증      Claude ✓     최종 드라이런
11:00   9.2 장애 조치 테스트            Claude ✓     failover 검증
12:00   Lunch
13:00   9.3 성능 SLA 검증              Claude ✓     모든 지표 확인
14:00   9.4 Phase 14 준비               Claude ✓     다음 단계 계획
15:00   최종 QA & 인수                Claude ✓     운영 이관 완료
16:00   Daily Standup & Final Log
16:30   End of Week 5 / Phase 13 완료
```

**Day 14 산출물**:
- ✅ Phase 13 전체 완료 검증
- ✅ 모든 자동화 시스템 검증
- ✅ 성능 SLA 달성 확인
- ✅ 운영 이관 완료

---

## 3. 작업 의존성

```
Parallel Streams:

Stream 1: Automation Foundation (Days 1-5)
├─ 1.1-1.4 Cron setup (5 days)
└─ 2.1-2.5 Monitoring (parallel, 3-5 days)

Stream 2: Infrastructure (Days 4-7)
├─ 3.1-3.4 A/B Testing (2 days)
└─ 4.1-4.4 Rollback (2 days)

Stream 3: Operations (Days 8-14)
├─ First retraining (1 day, auto-scheduled)
├─ Monitoring operations (7 days, continuous)
└─ Documentation (2 days)

Synchronization Points:
- Day 7: All infrastructure ready
- Day 8: First retraining scheduled
- Day 14: Phase 13 handover
```

**크리티컬 패스**: 1.1 → 1.2 → 1.3 → 1.4 → (parallel: 2.1-2.5, 3.1-3.4, 4.1-4.4) → 5.1 → 6.1 → 6.5 → 7.1 → 8.1 → 9.1 → 9.4

**병렬화**: Week 4는 최대 병렬화 가능 (3 독립 stream)

---

## 4. 리소스 할당

### 4.1 총 투입 시간

| 작업군 | 예상 | 실제* | 효율 |
|--------|------|------|------|
| **1. Cron 자동화** | 8h | - | - |
| **2. 모니터링** | 12h | - | - |
| **3. A/B 테스팅** | 6h | - | - |
| **4. 롤백** | 6h | - | - |
| **5. 드리프트 감지** | 4h | - | - |
| **6. 재학습 실행** | 10h | - | - |
| **7. 모니터링 운영** | 12h | - | - |
| **8. 문서화** | 10h | - | - |
| **9. QA** | 8h | - | - |
| **TOTAL** | **76h** | **TBD** | **병렬 시 40h** |

### 4.2 병렬화 전략

```
Week 4: 3개 독립 stream 병렬
├─ Stream 1: Cron + Monitoring (5 days)
├─ Stream 2: A/B Testing (2 days)
└─ Stream 3: Rollback (2 days)

Parallel efficiency: 76h → 40h (47% time reduction)

Synchronization: Day 7 checkpoint (모든 시스템 ready)
```

---

## 5. 마일스톤

| 마일스톤 | 날짜 | 목표 | 성공기준 |
|---------|------|------|--------|
| **M1: Cron 설정** | Jul 24 15:30 | 자동화 기초 | 스크립트 등록 ✓ |
| **M2: 모니터링** | Jul 26 15:30 | 실시간 모니터링 | Grafana 대시보드 ✓ |
| **M3: 첫 재학습** | Jul 29-30 | 자동 재학습 실행 | R² 검증 완료 ✓ |
| **M4: 모델 배포** | Jul 30 14:00 | 배포/Hold 결정 | A/B 테스팅 데이터 ✓ |
| **M5: 운영 모드** | Aug 02 | 24/7 모니터링 | 자동 알림 작동 ✓ |
| **M6: 문서화 완료** | Aug 03 16:00 | 모든 가이드 작성 | 4개 문서 완성 ✓ |
| **M7: Phase 13 완료** | Aug 04 16:00 | 전체 시스템 검증 | 운영 이관 ✓ |

---

## 6. 성공 기준 (Completion Checklist)

```
✅ Phase 13.5 완료 조건:

자동화 시스템:
├─ Cron 주간 재학습 작동
├─ 스크립트 성공률 >95%
├─ 자동화 총 소요시간 <120분
└─ 첫 재학습 성공 (R² 검증 완료)

모니터링:
├─ Prometheus 메트릭 수집 중
├─ Grafana 대시보드 운영 중
├─ 알림 시스템 작동 (<5분 지연)
└─ 일일 자동 성능 리포트 생성

A/B 테스팅 & 롤백:
├─ 새 모델 5% 트래픽 라우팅
├─ 통계 검정 구현 (t-test)
├─ 자동 롤백 메커니즘 검증
└─ 장애 조치 테스트 완료

운영:
├─ 2주 연속 성공한 재학습
├─ 모델 성능 유지 (R² > 0.84)
├─ 0회 긴급 롤백
└─ 알림 오탐 <5%

문서화:
├─ 운영 매뉴얼 작성 완료
├─ Runbook 작성 완료
├─ 트러블슈팅 가이드 완료
└─ 자동화 가이드 완료

└─→ Phase 13 전체 완료 → 운영 체제 전환 가능
```

---

**WBS 완성**  
**총 프로젝트 기간**: 14일 (40-76시간)  
**병렬화**: Week 4 최대 3 stream 병렬  
**예상 완료**: 2026-08-04 16:30  
**다음 Phase**: Phase 14 (8-국가 글로벌 확장, 2026-08-05 시작)
