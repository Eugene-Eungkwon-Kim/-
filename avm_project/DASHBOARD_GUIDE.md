# 🎨 AVM 성능 모니터링 대시보드

**상태**: ✅ 완료 (2026-06-16)  
**기술 스택**: FastAPI + Chart.js + 실시간 업데이트  
**접근 URL**: `http://localhost:8000/dashboard`

---

## 📊 대시보드 기능

### 1️⃣ 실시간 현황 (Summary)
- **현재 R²**: 최신 모델의 정확도 점수
- **변화도**: 이전 대비 R² 변화량
- **모델명**: 현재 최고 성능 모델
- **상태**: 건강/주의 상태 표시
- **추이**: 📈 향상 / 📉 저하 / → 유지

### 2️⃣ 성능 추이 그래프
- **R² 시계열**: 모델 성능 변화 시각화
- **차트 라이브러리**: Chart.js (6만+ npm 다운로드)
- **범위**: 최근 50개 기록 표시
- **상호작용**: 마우스 호버로 상세 정보

### 3️⃣ 성능 통계 (Statistics)
- **최고 R²**: 기록 중 최고 성능
- **평균 R²**: 전체 평균 정확도
- **최저 R²**: 가장 낮은 성능
- **평균 RMSE**: 평균 예측 오차

### 4️⃣ 챔피언 모델 (Champion)
- **모델명**: 현재 프로덕션 모델
- **R² 점수**: 검증 데이터셋 정확도
- **RMSE**: 평균제곱근오차
- **서명**: SHA256 해시 (무결성 검증)

### 5️⃣ 최근 알림 (Alerts)
- **성능 회귀**: > 2% 성능 저하
- **심각도**: HIGH / MEDIUM / INFO
- **타임스탐프**: 발생 시각
- **상세정보**: 이전/현재 R² 비교

---

## 🚀 사용 방법

### 1. API 서버 시작

```bash
# 개발 모드
cd scripts
python3 -c "import api_server; import uvicorn; uvicorn.run(api_server.app, host='0.0.0.0', port=8000)"

# 또는 uvicorn 직접 사용
uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
```

### 2. 브라우저 접속

```
http://localhost:8000/dashboard
```

### 3. 데이터 자동 새로고침

- **간격**: 30초마다 자동 업데이트
- **데이터 소스**: 
  - `/dashboard/api/summary` — 요약 데이터
  - `/dashboard/api/performance` — 성능 이력
  - `/dashboard/api/alerts` — 알림 로그

---

## 🔌 REST API 엔드포인트

### 요약 데이터
```bash
curl http://localhost:8000/dashboard/api/summary
```

**응답 예시**:
```json
{
  "timestamp": "2026-06-16T10:30:00",
  "performance": {
    "total_records": 5,
    "latest": {
      "timestamp": "2026-06-16T10:17:34",
      "model": "LGBMRegressor",
      "r2": 0.748773,
      "rmse": 407693292.83,
      "r2_change": 0,
      "trend": "→ 유지"
    },
    "stats": {
      "best_r2": 0.748773,
      "worst_r2": 0.748773,
      "avg_r2": 0.748773,
      "best_rmse": 407693292.83,
      "worst_rmse": 407693292.83,
      "avg_rmse": 407693292.83
    }
  },
  "champion": {
    "name": "LGBMRegressor",
    "r2": 0.748773,
    "rmse": 407693292.83,
    "promoted_at": "2026-06-16T10:17:34",
    "sha256": "acd7362bd04c9d9b..."
  },
  "recent_alerts": [],
  "status": "healthy"
}
```

### 성능 이력
```bash
curl http://localhost:8000/dashboard/api/performance?limit=10
```

### 최근 알림
```bash
curl http://localhost:8000/dashboard/api/alerts?limit=20
```

---

## 🎨 대시보드 디자인

### 색상 테마
- **주색상**: Purple (#667eea) & Violet (#764ba2)
- **성공**: Green (#10b981)
- **경고**: Amber (#f59e0b)
- **위험**: Red (#ef4444)
- **배경**: Gradient Purple to Violet

### 반응형 레이아웃
- **데스크톱**: 2열 그리드 (400px 최소 너비)
- **태블릿**: 자동 조정
- **모바일**: 단일 열 스택

### UI 컴포넌트
- **카드**: 흰색 배경, 그림자 효과
- **그래프**: Chart.js 반응형 라인 차트
- **상태 배지**: 색상 코딩된 상태 표시
- **로딩 애니메이션**: 스핀 애니메이션

---

## 📈 성능 분석

### 대시보드로 할 수 있는 분석

#### 1. 성능 추이 분석
- 그래프에서 R² 변화 패턴 확인
- 상승 추세 = 모델 개선
- 하강 추세 = 데이터 분포 변화 또는 이슈 신호

#### 2. 이상 감지
- 갑작스런 R² 급락 → 알림 확인
- 회귀 패턴 반복 → 구조적 문제 가능

#### 3. 모델 비교
- 챔피언 모델 추이 추적
- 통계에서 최고/최저 성능 비교
- 평균 성능 기준 이상 여부 판단

#### 4. 신뢰도 평가
- SHA256 서명으로 모델 무결성 검증
- 동일 모델 재학습 시 새 서명 생성
- 서명 변화 추적

---

## 🔄 루핑 자동화와의 통합

### 자동 데이터 수집

```
매주 목요일 10:00
  ↓
auto_retraining.py 실행
  ↓
모델 재학습 + 성능 기록
  ↓
logs/performance_history.jsonl 업데이트
  ↓
대시보드 30초마다 자동 새로고침
  ↓
실시간 시각화
```

### 알림 자동화

성능 회귀 감지 시:
```
1. alerts.log 기록
2. 대시보드에 즉시 표시
3. 30초 이내 UI 업데이트
```

---

## 🚨 문제 해결

### Q: 대시보드가 로드되지 않음
```bash
# API 서버 실행 확인
ps aux | grep api_server

# 포트 확인
lsof -i :8000

# 수동으로 데이터 조회
curl http://localhost:8000/dashboard/api/summary
```

### Q: 데이터가 업데이트되지 않음
```bash
# 성능 이력 확인
tail logs/performance_history.jsonl

# 스케줄러 실행 확인
ps aux | grep looping_scheduler
```

### Q: 그래프가 비어있음
```bash
# 최소 2개 기록 필요
wc -l logs/performance_history.jsonl

# 재학습으로 데이터 생성
python3 scripts/auto_retraining.py
```

---

## 🔐 보안 고려사항

### 접근 제어
- 현재: 인증 없음 (로컬 개발 환경)
- 운영 환경: 다음 추가 권장
  - OAuth/API Key 기반 인증
  - HTTPS 암호화
  - IP 화이트리스트

### 데이터 보호
- 성능 이력: 자동 생성 (민감하지 않음)
- 모델 서명: 공개 정보 (무결성만 검증)
- 알림: 감시 로그 (내부용)

---

## 📊 예상 활용

### 1. 주간 모니터링
```
목요일 10:00
  ↓
auto_retraining 자동 실행
  ↓
금요일 오전
  ↓
대시보드로 성능 리뷰
```

### 2. 성능 이상 감지
```
성능 회귀 발생
  ↓
alerts.log에 기록
  ↓
대시보드에 즉시 표시
  ↓
조사 및 개선
```

### 3. 장기 추이 분석
```
3개월 데이터 누적
  ↓
성능 그래프에서 계절성 패턴 파악
  ↓
데이터 수집 시기별 성능 차이 분석
```

---

## 🎯 향후 개선 사항

- [ ] 대시보드 커스터마이제이션 (드래그앤드롭 레이아웃)
- [ ] 다중 모델 성능 비교 (병렬 그래프)
- [ ] 예측 분포 시각화 (히스토그램)
- [ ] 비용/성능 트레이드오프 분석
- [ ] 내보내기 기능 (PDF/CSV 리포트)
- [ ] 실시간 알림 (WebSocket 푸시)

---

**상태**: ✅ 프로덕션 준비 완료  
**마지막 업데이트**: 2026-06-16 10:30 UTC
