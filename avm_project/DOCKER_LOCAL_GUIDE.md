# AVM Dashboard — 로컬 Docker 실행 가이드 (Phase 3 Week 2)

> **원칙:** 충분한 성능 검증 전까지 **클라우드 배포 금지**. 모든 작업은 로컬 우선.
> 이 문서는 백엔드 + 프론트엔드를 **로컬 컨테이너**로 띄우는 방법만 다룬다.

---

## 1. 구성 개요

```
avm_project/
├── Dockerfile               # 백엔드 이미지 (FastAPI + ML 모델 서빙)
├── .dockerignore            # 백엔드 빌드 컨텍스트 제외 목록
├── docker-compose.yml       # 백엔드 + 프론트엔드 통합 오케스트레이션
├── backend/
│   ├── __init__.py          # backend 를 정식 패키지로 만듦 (backend.main:app)
│   ├── requirements.txt     # 웹 + ML 런타임 의존성 (검증된 버전 고정)
│   └── main.py              # FastAPI 앱 (REST + WebSocket)
└── frontend/
    ├── Dockerfile           # Next.js 14 이미지
    ├── .dockerignore
    └── package.json         # 프론트엔드 의존성/스크립트
```

| 서비스 | 포트 | 설명 |
|--------|------|------|
| backend  | 8000 | FastAPI REST API + WebSocket (`/ws/dashboard`, `/ws/monitoring`) |
| frontend | 3000 | Next.js 대시보드 UI |

---

## 2. 빠른 시작 (통합 실행)

```bash
cd avm_project

# 이미지 빌드 + 실행 (백엔드, 프론트엔드 동시)
docker compose up --build

# 백그라운드 실행
docker compose up --build -d

# 종료
docker compose down
```

접속:
- 대시보드: http://localhost:3000
- API 문서(Swagger): http://localhost:8000/docs
- 헬스 체크: http://localhost:8000/health

---

## 3. 개별 빌드/실행

### 백엔드만

```bash
cd avm_project
docker build -f Dockerfile -t avm-backend:local .
docker run --rm -p 8000:8000 \
  -v "$(pwd)/models:/app/models:ro" \
  -v "$(pwd)/data:/app/data:ro" \
  -v "$(pwd)/config:/app/config:ro" \
  -v "$(pwd)/logs:/app/logs" \
  avm-backend:local
```

### 프론트엔드만

```bash
cd avm_project/frontend
docker build -t avm-frontend:local .
docker run --rm -p 3000:3000 \
  -e NEXT_PUBLIC_API_URL=http://localhost:8000 \
  avm-frontend:local
```

---

## 4. Docker 없이 직접 실행 (개발용)

### 백엔드

```bash
cd avm_project
pip install -r backend/requirements.txt
# 방법 1: 프로젝트 루트에서 (권장, 컨테이너 CMD 와 동일)
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
# 방법 2: backend 디렉토리에서 (문서 호환)
cd backend && uvicorn main:app --reload --port 8000
```

> `main.py` 는 두 실행 방식을 모두 지원하도록 임포트를 try/except 로 처리한다.

### 프론트엔드

```bash
cd avm_project/frontend
npm install
npm run dev      # http://localhost:3000
```

---

## 5. 중요 사항 / 주의

### 5.1 ML 런타임 버전 고정
`backend/requirements.txt` 의 `scikit-learn`, `xgboost`, `lightgbm` 버전은
**모델(.joblib)을 학습한 환경과 호환**되어야 한다. 버전 불일치 시 역직렬화
경고/오류가 발생할 수 있다. 현재 고정 버전으로 7개 실모델 로드가 검증됨:

| 패키지 | 버전 |
|--------|------|
| scikit-learn | 1.9.0 |
| xgboost | 3.2.0 |
| lightgbm | 4.6.0 |
| pandas | 3.0.3 |
| numpy | 2.4.6 |

### 5.2 WebSocket 지원
백엔드는 `uvicorn[standard]` 가 포함하는 `websockets` 구현이 **반드시** 필요하다.
일반 `uvicorn` 만 설치하면 WebSocket 업그레이드가 실패하고 `/ws/*` 가 404 를 반환한다.
(이 가이드의 requirements 는 `uvicorn[standard]` 로 고정되어 있음.)

### 5.3 모델/데이터는 이미지에 포함 + 볼륨 마운트
- 빌드 시 `COPY . .` 로 `models/`, `data/`, `config/` 가 이미지에 포함된다.
- compose 는 같은 경로를 읽기전용 볼륨으로도 마운트하여 **재빌드 없이** 최신
  모델/데이터를 반영한다. (주간 재학습으로 갱신된 모델 즉시 사용 가능)
- `logs/` 는 쓰기 가능 볼륨으로 호스트에 영속된다 (재학습 이력 보존).

### 5.4 경로 규칙
백엔드 모듈은 `backend/` 가 `avm_project/` 내부에 있다는 전제로 경로를 계산한다
(`Path(__file__).parent.parent == avm_project`). 따라서 데이터/모델/로그/설정은
모두 `avm_project/{data,models,logs,config}` 에서 로드된다.

---

## 6. 동작 검증 체크리스트

```bash
# 1) 헬스 체크
curl http://localhost:8000/health
# → {"status":"healthy",...}

# 2) API 문서 200 확인
curl -o /dev/null -w "%{http_code}\n" http://localhost:8000/docs

# 3) WebSocket ping/pong (Python)
python - <<'PY'
import asyncio, json, websockets
async def t(p):
    async with websockets.connect(f"ws://localhost:8000{p}") as ws:
        await ws.send("ping")
        print(p, "->", json.loads(await ws.recv())["type"])
asyncio.run(asyncio.wait_for(t("/ws/dashboard"), 5))
PY
```

---

**상태:** Phase 3 Week 2 (로컬 컨테이너화) 완료 — 클라우드 배포는 보류(성능 검증 후).
