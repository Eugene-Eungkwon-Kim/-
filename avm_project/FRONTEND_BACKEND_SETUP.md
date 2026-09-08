# 🚀 AVM Dashboard - 전체 시스템 설정 가이드

**상태:** ✅ 개발 준비 완료  
**업데이트:** 2026-06-19

---

## 📋 목차

1. [시스템 구조](#시스템-구조)
2. [사전 요구사항](#사전-요구사항)
3. [FastAPI 백엔드 설정](#fastapi-백엔드-설정)
4. [Next.js 프론트엔드 설정](#nextjs-프론트엔드-설정)
5. [실행 방법](#실행-방법)
6. [API 엔드포인트](#api-엔드포인트)
7. [문제 해결](#문제-해결)

---

## 시스템 구조

```
AVM Dashboard System
├── Backend (FastAPI)
│   ├── PORT: 8000
│   ├── Base URL: http://localhost:8000
│   └── API Documentation: http://localhost:8000/docs
│
└── Frontend (Next.js)
    ├── PORT: 3000
    ├── Base URL: http://localhost:3000
    └── API Client: axios + TypeScript
```

### 데이터 흐름

```
Browser (http://localhost:3000)
    ↓
React Components
    ↓
API Service Layer (lib/api.ts)
    ↓
Axios HTTP Client
    ↓
FastAPI Backend (http://localhost:8000)
    ↓
Data Processing & Storage
    ↓
Response JSON
```

---

## 사전 요구사항

### 1. Node.js & npm
```bash
# 확인
node --version  # v18.0.0 이상
npm --version   # v9.0.0 이상

# 설치 (필요시)
# macOS
brew install node

# Linux
sudo apt-get install nodejs npm

# Windows
# https://nodejs.org/en/ 에서 다운로드
```

### 2. Python 3.8+
```bash
# 확인
python3 --version  # 3.8 이상

# 설치 (필요시)
# macOS
brew install python3

# Linux
sudo apt-get install python3 python3-pip

# Windows
# https://www.python.org/ 에서 다운로드
```

### 3. Git
```bash
git --version  # 2.0 이상
```

---

## FastAPI 백엔드 설정

### Step 1: 백엔드 디렉토리 생성

```bash
cd /home/user/-/avm_project
mkdir -p backend
cd backend
```

### Step 2: Python 가상환경 생성

```bash
# 가상환경 생성
python3 -m venv venv

# 활성화 (Linux/macOS)
source venv/bin/activate

# 활성화 (Windows)
venv\Scripts\activate

# 확인 (프롬프트에 (venv) 표시)
(venv) $
```

### Step 3: 패키지 설치

```bash
# backend/requirements.txt 에서 설치
pip install -r requirements.txt

# 설치 확인
pip list | grep fastapi
```

### Step 4: 환경 설정 (.env)

```bash
# backend/.env 생성
touch .env
```

```env
# .env 내용
ENVIRONMENT=development
DEBUG=true
DATABASE_URL=sqlite:///./avm.db
SECRET_KEY=your-secret-key-here-change-in-production
```

### Step 5: 백엔드 실행

```bash
# 방법 1: python으로 직접 실행
python3 main.py

# 방법 2: uvicorn으로 실행 (권장)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 출력:
# INFO:     Uvicorn running on http://0.0.0.0:8000
# INFO:     Application startup complete
```

### Step 6: API 문서 확인

```
브라우저에서 열기:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
```

---

## Next.js 프론트엔드 설정

### Step 1: 프론트엔드 디렉토리 이동

```bash
cd /home/user/-/avm_project/frontend
```

### Step 2: 패키지 설치

```bash
npm install

# 또는 yarn 사용
yarn install

# 설치 확인
npm list react react-dom next
```

### Step 3: 환경 설정

```bash
# .env.local 생성
cp .env.example .env.local
```

```bash
# .env.local 내용 (기본값)
NEXT_PUBLIC_API_URL=http://localhost:8000
NODE_ENV=development
DEBUG=false
```

### Step 4: 프론트엔드 개발 서버 실행

```bash
npm run dev

# 출력:
# > avm-dashboard@1.0.0 dev
# > next dev
# - ready - started server on 0.0.0.0:3000
# - event - compiled client and server successfully
```

### Step 5: 브라우저 접속

```
http://localhost:3000
```

---

## 실행 방법

### 한 번에 모두 실행

#### 터미널 1: FastAPI 백엔드

```bash
cd /home/user/-/avm_project/backend
source venv/bin/activate  # or venv\Scripts\activate (Windows)
uvicorn main:app --reload --port 8000
```

#### 터미널 2: Next.js 프론트엔드

```bash
cd /home/user/-/avm_project/frontend
npm run dev
```

#### 터미널 3: 선택 사항 - 로그 보기

```bash
# 백엔드 로그
tail -f /home/user/-/avm_project/avm_project/logs/weekly_retrain.log

# 또는 프론트엔드 빌드 로그
npm run build
```

### 테스트 계정

```
이메일: admin@avm.com
비밀번호: demo123
```

---

## API 엔드포인트

### 인증 (Auth)

```
POST   /auth/login           - 로그인
POST   /auth/logout          - 로그아웃
GET    /auth/me              - 현재 사용자 정보
```

### 대시보드 (Dashboard)

```
GET    /dashboard/summary    - 요약 정보 (R², RMSE, MAE)
GET    /dashboard/trend      - R² 추세 데이터
GET    /dashboard/recent-trainings - 최근 재학습
GET    /dashboard/statistics - 통계 정보
```

### 모델 (Models)

```
GET    /models               - 모델 목록
GET    /models/{id}          - 모델 상세 정보
GET    /models/{id}/feature-importance - 특성 중요도
POST   /models/{id}/deploy   - 모델 배포
DELETE /models/{id}          - 모델 삭제
```

### 데이터 (Data)

수집 파이프라인(`scripts/collect_all_transactions.py` 등)이 `comparable_sales`
테이블에 적재한 **실측값**을 돌려준다. 프론트(`frontend/lib/api.ts` `dataAPI`)는
이 경로를 쓴다.

```
GET    /data/comparable-sales/summary             - 총 건수, 자산유형별·시도별 건수
GET    /data/comparable-sales/price-distribution  - 거래금액 구간별 건수
GET    /data/comparable-sales/region-distribution - 시군구별 건수
GET    /data/comparable-sales/quality             - 결측·이상치 기반 품질 점수 (0건이면 status=no_data)
```

아래 3개는 고정 예시값을 돌려주는 **deprecated** 엔드포인트다(OpenAPI 문서에
deprecated 로 표시됨). 새 코드에서 쓰지 말 것.

```
GET    /data/quality             - (deprecated) 고정값
GET    /data/price-distribution  - (deprecated) 고정값
GET    /data/region-distribution - (deprecated) 고정값
```

### 설정 (Settings)

```
GET    /settings             - 설정 조회
PUT    /settings             - 설정 업데이트
POST   /settings/test-email  - 이메일 테스트
POST   /settings/test-slack  - Slack 테스트
```

### 재학습 (Retraining)

```
POST   /retraining/start     - 재학습 시작
GET    /retraining/status    - 재학습 상태
GET    /retraining/history   - 재학습 이력
POST   /retraining/cancel    - 재학습 취소
```

### 헬스 체크

```
GET    /health               - 서버 상태 확인
```

---

## 문제 해결

### 1. "port 8000 already in use" 오류

```bash
# 포트 확인
lsof -i :8000  # Linux/macOS
netstat -ano | findstr :8000  # Windows

# 프로세스 종료
kill -9 <PID>  # Linux/macOS
taskkill /PID <PID> /F  # Windows

# 또는 다른 포트 사용
uvicorn main:app --reload --port 8001
```

### 2. "CORS 오류" 또는 "Access-Control-Allow-Origin"

백엔드의 CORS 설정 확인:

```python
# backend/main.py 에서
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 프론트엔드 주소
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 3. "Cannot GET /" (프론트엔드)

```bash
# 다시 설치
rm -rf node_modules package-lock.json
npm install

# 캐시 청소
npm run clean  # 또는
rm -rf .next

# 다시 실행
npm run dev
```

### 4. "API connection refused"

프론트엔드가 백엔드를 찾지 못할 때:

```bash
# 1. 백엔드가 실행 중인지 확인
curl http://localhost:8000/health

# 2. .env.local 확인
cat frontend/.env.local  # NEXT_PUBLIC_API_URL 확인

# 3. 방화벽 설정 확인
# 포트 8000이 열려있는지 확인
```

### 5. Python 모듈 import 오류

```bash
# venv 활성화 확인
which python3  # /path/to/venv/bin/python3 이어야 함

# 패키지 재설치
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt --force-reinstall
```

---

## 개발 팁

### 1. 백엔드 자동 재로드

```bash
# uvicorn --reload 플래그 사용 (기본값)
uvicorn main:app --reload
```

### 2. 프론트엔드 Hot Reload

```bash
# npm run dev 는 자동으로 hot reload 지원
npm run dev
```

### 3. API 테스트 (curl)

```bash
# 헬스 체크
curl http://localhost:8000/health

# 로그인
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@avm.com","password":"demo123"}'

# 대시보드 요약
curl -X GET http://localhost:8000/dashboard/summary \
  -H "Authorization: Bearer demo_token_12345"
```

### 4. 브라우저 개발자 도구

```javascript
// 콘솔에서 테스트
const response = await fetch('http://localhost:8000/health');
const data = await response.json();
console.log(data);
```

---

## 빌드 및 배포

### 프로덕션 빌드 (프론트엔드)

```bash
cd frontend
npm run build
npm run start
```

### 프로덕션 실행 (백엔드)

```bash
cd backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## 다음 단계

1. ✅ 백엔드 API 서버 실행
2. ✅ 프론트엔드 개발 서버 실행
3. ⏳ API 통합 테스트
4. ⏳ 데이터베이스 연동
5. ⏳ 인증 시스템 완성
6. ⏳ Google Cloud Run 배포

---

**마지막 업데이트:** 2026-06-19  
**상태:** 개발 진행 중
