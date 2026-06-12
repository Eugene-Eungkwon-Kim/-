# NPL AVM 운영 가이드

**버전**: 1.0.0  
**최종 업데이트**: 2026-06-09  
**대상**: 운영팀, DevOps 엔지니어

---

## 📖 목차

1. [배포 절차](#배포-절차)
2. [모니터링](#모니터링)
3. [장애 대응](#장애-대응)
4. [성능 튜닝](#성능-튜닝)
5. [정기 점검](#정기-점검)
6. [백업 & 복구](#백업--복구)

---

## 배포 절차

### 표준 배포 프로세스

#### Step 1: 배포 전 확인

```bash
# 1.1 현재 상태 확인
kubectl get deployment -n npl-avm
kubectl get svc -n npl-avm
kubectl get pods -n npl-avm

# 1.2 모델 성능 확인
curl -s http://localhost:8000/api/v1/metrics | jq '.r2_score'
# 출력: 0.8721 (✅ >= 0.85 확인)

# 1.3 API 헬스 체크
curl http://localhost:8000/api/v1/health
# 출력: {"status": "healthy", ...}
```

#### Step 2: Blue/Green 배포 시작

```bash
# 2.1 Green 환경 스케일 업
kubectl scale deployment npl-avm-green -n npl-avm --replicas=3

# 2.2 Green 준비 상태 대기
kubectl rollout status deployment/npl-avm-green -n npl-avm --timeout=5m

# 2.3 Green 헬스 체크
GREEN_POD=$(kubectl get pod -n npl-avm -l app=npl-avm,version=v2 -o jsonpath='{.items[0].metadata.name}')
kubectl exec $GREEN_POD -n npl-avm -- curl -s http://localhost:8000/api/v1/ready
```

#### Step 3: 성능 검증

```bash
# 3.1 스모크 테스트 실행
kubectl exec $GREEN_POD -n npl-avm -- python -m pytest tests/test_smoke.py -v

# 3.2 응답시간 확인
# (p95 < 500ms 확인)
kubectl exec $GREEN_POD -n npl-avm -- curl -s http://localhost:8000/api/v1/metrics

# 3.3 에러율 확인
# (에러율 < 1% 확인)
```

#### Step 4: 트래픽 전환 (Blue → Green)

```bash
# 4.1 Service selector 변경
kubectl patch svc npl-avm -n npl-avm -p '{"spec":{"selector":{"version":"v2"}}}'

echo "✅ 트래픽 전환 완료 (Blue v1 → Green v2)"

# 4.2 검증
kubectl get svc npl-avm -n npl-avm -o jsonpath='{.spec.selector}'
# 출력: {"app":"npl-avm","version":"v2"}
```

#### Step 5: 배포 후 모니터링

```bash
# 5.1 5분간 모니터링
for i in {1..30}; do
  ERROR_RATE=$(kubectl exec -c prometheus -n monitoring \
    $(kubectl get pod -n monitoring -l app=prometheus -o jsonpath='{.items[0].metadata.name}') \
    -- promtool query instant 'npl_avm_error_rate')
  
  echo "[$i/30] 에러율: $ERROR_RATE"
  
  if (( $(echo "$ERROR_RATE < 0.01" | bc -l) )); then
    echo "✅ 에러율 정상"
    break
  fi
  
  sleep 10
done

# 5.2 응답시간 확인
kubectl logs -n npl-avm deployment/npl-avm-blue --tail=20 | grep 'latency'

# 5.3 최종 검증
curl -s http://api.npl-avm.example.com/api/v1/health
```

#### Step 6: 이전 환경(Blue) 정리

```bash
# 6.1 Blue 스케일 다운
kubectl scale deployment npl-avm-blue -n npl-avm --replicas=0

# 6.2 확인
kubectl get deployment -n npl-avm

echo "✅ 배포 완료"
```

### 배포 자동화 (GitHub Actions)

1. **코드 푸시**:
```bash
git push origin main
```

2. **GitHub Actions 실행**:
   - Test: Python 3.11, 3.12 병렬 실행
   - Validate Model: R² >= 0.85 확인
   - Code Quality: Black, Pylint, isort
   - Build: Docker 이미지 빌드 & 푸시
   - Deploy: Kubernetes 배포

3. **진행 상황 확인**:
```bash
# GitHub CLI
gh run list --workflow=ci-cd-pipeline.yml

# 또는 GitHub 웹사이트
https://github.com/your-org/npl-avm/actions
```

### 배포 체크리스트

- [ ] 모델 성능 확인 (R² >= 0.85)
- [ ] API 헬스 체크 완료
- [ ] 코드 품질 통과
- [ ] 테스트 18/18 통과
- [ ] Docker 이미지 빌드 완료
- [ ] Green 환경 준비 완료
- [ ] 스모크 테스트 통과
- [ ] 응답시간 < 500ms 확인
- [ ] 에러율 < 1% 확인
- [ ] 트래픽 전환 완료
- [ ] 5분 모니터링 완료
- [ ] Blue 환경 정리 완료

---

## 모니터링

### 대시보드 접근

```
Grafana: https://grafana.example.com
계정: admin / (패스워드는 보안 볼트에서 확인)

대시보드 목록:
├─ NPL AVM Production Monitoring (메인)
├─ Model Performance
├─ API Performance
├─ Infrastructure
└─ Business Metrics
```

### 핵심 지표 (SLA)

```
지표                | 목표    | 현재    | 상태
────────────────────┼────────┼────────┼──────────
가용성              | 99.9%  | 99.95% | ✅
p95 응답시간        | < 500ms| 45ms   | ✅
에러율              | < 1%   | 0.05%  | ✅
모델 R² 점수        | >= 0.85| 0.8721 | ✅
```

### 알림 규칙

#### Critical (즉시 온콜 호출)

```
1. HighErrorRate (에러율 > 5% for 1분)
   → PagerDuty 즉시 알림
   → 대응: 최근 배포 확인 → 필요시 롤백

2. SLAViolation (p95 > 1초 for 5분)
   → PagerDuty 즉시 알림
   → 대응: 리소스 스케일 업

3. ModelPerformanceDegradation (R² < 0.80)
   → PagerDuty 즉시 알림
   → 대응: 모델 재훈련 시작
```

#### Warning (팀 알림)

```
1. HighResponseLatency (p95 > 500ms for 3분)
   → Slack #npl-avm-ops 채널

2. HighMemoryUsage (> 85% for 5분)
   → Slack #npl-avm-ops 채널

3. HighCPUUsage (> 80% for 5분)
   → Slack #npl-avm-ops 채널
```

### 커스텀 쿼리

```promql
# 시간대별 요청 수
rate(npl_avm_request_total[5m])

# 에러율 추이
rate(npl_avm_error_total[5m]) / rate(npl_avm_request_total[5m])

# 예측 시간 분포
histogram_quantile(0.95, npl_avm_prediction_latency_seconds_bucket)

# 모델 성능 추이
npl_avm_model_r2_score
```

---

## 장애 대응

### 장애 판단 기준

```
심각도별 분류:

Critical (즉시 대응):
├─ 가용성 < 95% (연속 2분)
├─ 에러율 > 10% (연속 1분)
└─ 응답시간 p95 > 2초 (연속 3분)

Major (1시간 내 해결):
├─ 가용성 95-99% (연속 5분)
├─ 에러율 1-10% (연속 2분)
└─ 응답시간 500ms-2s

Minor (업무 시간 내 해결):
├─ 경고 알림 (Warning 수준)
├─ 문서화되지 않은 동작
└─ 성능 저하 (SLA 미충족 아님)
```

### 대응 절차

#### 1단계: 장애 인지 & 초기 대응

```bash
# 1.1 문제 확인
curl -s http://api.npl-avm.example.com/api/v1/health

# 1.2 Slack 알림 확인
# #npl-avm-alert 채널에서 알림 내용 확인

# 1.3 팀 통지
# 1. Slack에서 @on-call 태그
# 2. 필요시 전화 연락
```

#### 2단계: 원인 진단

```bash
# 2.1 Pod 상태 확인
kubectl get pods -n npl-avm -o wide
kubectl describe pod <pod-name> -n npl-avm

# 2.2 로그 확인
kubectl logs -n npl-avm deployment/npl-avm-blue --tail=100 | grep -i error

# 2.3 메트릭 확인
# Grafana 대시보드에서 그래프 확인
# - CPU/메모리 사용률
# - 요청 수
# - 에러율
# - 응답시간

# 2.4 최근 배포 확인
kubectl rollout history deployment/npl-avm-blue -n npl-avm

# 2.5 모델 성능 확인
curl -s http://api.npl-avm.example.com/api/v1/metrics | jq '.r2_score'
```

#### 3단계: 일시적 대응

```bash
# 리소스 부족인 경우
kubectl scale deployment npl-avm-blue -n npl-avm --replicas=5

# 메모리 누수인 경우
kubectl rollout restart deployment/npl-avm-blue -n npl-avm

# 캐시 문제인 경우
kubectl rollout restart deployment/npl-avm-blue -n npl-avm --history=2
```

#### 4단계: 롤백 (필요시)

```bash
# 4.1 이전 버전 확인
kubectl rollout history deployment/npl-avm-blue -n npl-avm

# 4.2 롤백 실행
kubectl rollout undo deployment/npl-avm-blue -n npl-avm

# 4.3 상태 확인
kubectl rollout status deployment/npl-avm-blue -n npl-avm --timeout=5m

# 4.4 검증
curl -s http://api.npl-avm.example.com/api/v1/health
```

### 일반적인 문제 및 해결

#### 문제 1: 높은 응답시간 (p95 > 2초)

**원인 진단**:
```bash
# CPU/메모리 확인
kubectl top pod -n npl-avm

# 느린 쿼리 확인
kubectl logs -n npl-avm deployment/npl-avm-blue | grep 'duration'

# 외부 API 응답시간 확인
curl -s http://api.npl-avm.example.com/api/v1/metrics | jq '.external_api_latency'
```

**해결**:
```bash
# 1. 자동 스케일 아웃 (일반적으로 자동)
kubectl scale deployment npl-avm-blue -n npl-avm --replicas=5

# 2. 캐시 확인
# (Redis/Memcached 상태 확인)
redis-cli info stats

# 3. 쿼리 최적화
# (DB 인덱스 확인)
```

#### 문제 2: 높은 에러율 (> 5%)

**원인 진단**:
```bash
# 에러 로그 확인
kubectl logs -n npl-avm deployment/npl-avm-blue | grep ERROR

# 에러 종류별 집계
kubectl logs -n npl-avm deployment/npl-avm-blue | grep ERROR | awk '{print $NF}' | sort | uniq -c
```

**해결**:
```bash
# 1. 최근 배포 롤백
kubectl rollout undo deployment/npl-avm-blue -n npl-avm

# 2. 의존성 확인
# - 외부 API 상태
# - DB 연결
# - 메시지 큐

# 3. 필요시 재시작
kubectl rollout restart deployment/npl-avm-blue -n npl-avm
```

#### 문제 3: 모델 성능 저하 (R² < 0.85)

**원인 진단**:
```bash
# 모델 메타데이터 확인
curl -s http://api.npl-avm.example.com/api/v1/metrics

# 예측 오차 분석
# (분석가 팀과 협력)
```

**해결**:
```bash
# 1. 백그라운드에서 모델 재훈련
python scripts/phase2_advanced_models.py &

# 2. 임시로 이전 모델 사용
kubectl patch deployment npl-avm-blue -n npl-avm \
  -p '{"spec":{"template":{"spec":{"containers":[{"name":"npl-avm","env":[{"name":"MODEL_VERSION","value":"baseline"}]}]}}}}'

# 3. 재훈련 완료 후 배포
# (Step 1-5의 표준 배포 절차 따름)
```

---

## 성능 튜닝

### 캐싱 최적화

```yaml
# Redis 캐시 정책
1. 비교사례 캐시 (TTL: 24h)
   - 지역별, 물건 유형별로 캐시 키 분류

2. 모델 메타데이터 캐시 (TTL: 1h)
   - 성능 지표는 매시간 갱신

3. 지역 데이터 캐시 (TTL: 7d)
   - 시장 데이터는 주간 갱신
```

**캐시 히트율 모니터링**:
```bash
# Redis 통계
redis-cli info stats | grep hit_rate

# 목표: > 90%
```

### 데이터베이스 최적화

```sql
-- 자주 사용되는 쿼리 인덱싱
CREATE INDEX idx_property_location 
ON properties(location_sido, location_sigungu);

CREATE INDEX idx_comparable_type_date 
ON comparable_sales(property_type, transaction_date);

-- 인덱스 사용 확인
EXPLAIN ANALYZE SELECT ... ;
```

### Kubernetes 리소스 최적화

```yaml
# 리소스 요청/제한 조정
resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "2Gi"
    cpu: "1000m"

# HPA 스케일링 정책
minReplicas: 2
maxReplicas: 10
targetCPU: 70%
targetMemory: 80%
```

---

## 정기 점검

### 일일 점검 (매일 09:00)

```bash
#!/bin/bash
# daily_check.sh

echo "🔍 Daily Health Check"

# 1. 가용성
UPTIME=$(kubectl uptime npl-avm)
echo "✅ Uptime: $UPTIME"

# 2. 에러율
ERROR_RATE=$(curl -s http://api.npl-avm.example.com/api/v1/metrics | jq '.error_rate')
echo "✅ Error Rate: ${ERROR_RATE}%"

# 3. 응답시간
P95=$(curl -s http://api.npl-avm.example.com/api/v1/metrics | jq '.p95_latency')
echo "✅ p95 Latency: ${P95}ms"

# 4. 모델 성능
R2=$(curl -s http://api.npl-avm.example.com/api/v1/metrics | jq '.r2_score')
echo "✅ Model R²: $R2"

# 결과 정리
echo "Daily check completed at $(date)"
```

### 주간 점검 (매주 금요일 17:00)

- [ ] 배포 내역 검토 (몇 건?)
- [ ] 인시던트 검토 (몇 건? 원인?)
- [ ] 성능 트렌드 분석
- [ ] 용량 계획 검토
- [ ] 보안 업데이트 확인

### 월간 점검 (매월 1일 09:00)

- [ ] 재해복구 훈련 실행
- [ ] 성능 벤치마크 실행
- [ ] 로그 아카이빙
- [ ] 백업 검증
- [ ] 비용 분석

---

## 백업 & 복구

### 자동 백업

```bash
# PostgreSQL 백업 (매일 02:00)
pg_dump npl_avm > /backups/npl_avm_$(date +%Y%m%d).sql
gzip /backups/npl_avm_*.sql

# 모델 백업 (배포 시)
cp models/advanced_best.pkl /backups/models/advanced_best_$(date +%Y%m%d_%H%M%S).pkl
```

### 복구 절차

```bash
# 1. 백업 파일 확인
ls -lh /backups/npl_avm_*.sql.gz

# 2. 복구 실행
gunzip /backups/npl_avm_20260609.sql.gz
psql npl_avm < /backups/npl_avm_20260609.sql

# 3. 검증
psql -c "SELECT COUNT(*) FROM comparable_sales;"
```

---

## 연락처

**장애 신고**:
- 📞 온콜 전화: 010-****-****
- 📧 이메일: ops-team@npl-avm.example.com
- 💬 Slack: #npl-avm-alert (자동 알림)

**에스컬레이션**:
```
레벨 1: 온콜 (15분 내)
  ↓
레벨 2: 시니어 엔지니어 (30분 내)
  ↓
레벨 3: 팀 리드 (1시간 내)
```

---

**최종 업데이트**: 2026-06-09  
**버전**: 1.0.0
