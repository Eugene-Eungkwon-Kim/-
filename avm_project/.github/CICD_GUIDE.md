# CI/CD Pipeline Guide (Phase 3 Week 4 — Local)

> **원칙 (Principle):** All testing and validation is **local-first**. No cloud deployment until performance is verified.
>
> **상태 (Status):** CI/CD pipelines run on push/PR to validate code quality, tests, and Docker builds.

---

## Overview

This project uses **GitHub Actions** to automate code quality checks, testing, and Docker image validation. All pipelines run **locally within the GitHub Actions runner** (Ubuntu Linux) — no deployment to cloud services.

### Active Workflows

| Workflow | Purpose | Trigger |
|----------|---------|---------|
| **ci.yml** | Quick validation + core suite | Every push/PR |
| **backend-test.yml** | Backend pytest + Docker build | Backend code changes |
| **frontend-test.yml** | Frontend build + type check | Frontend code changes |
| **integration-test.yml** | Docker Compose validation + E2E | Every push/PR |
| **code-quality.yml** | Linting, complexity, security | Every push/PR |

---

## Running Tests Locally

### Backend Tests

```bash
cd avm_project

# Install dependencies
pip install -r backend/requirements.txt

# Run all tests
pytest tests/ -v

# Run only E2E WebSocket tests
pytest tests/test_e2e_websocket.py -v

# Run with coverage
pytest tests/ --cov=backend --cov-report=html

# Run single test file
pytest tests/test_api_endpoints.py -v

# Run tests matching pattern
pytest -k "websocket" -v
```

### Frontend Tests

```bash
cd avm_project/frontend

# Install dependencies
npm install

# Run linting
npm run lint

# Run tests (if test scripts exist)
npm test

# Build production
npm run build

# Type check
npx tsc --noEmit
```

### Docker Compose Local Run

```bash
cd avm_project

# Validate compose file
docker compose config

# Build and run services
docker compose up --build

# Background mode
docker compose up --build -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

---

## Workflow Details

### 1. **ci.yml** — Main CI Pipeline

Runs on every push/PR. Quick checks + suite status.

**Jobs:**
- `validate`: Project structure check
- `backend`: Module import verification
- `frontend`: Build verification
- `docker`: Image build + validation
- `status`: Final status summary

**Example output:**
```
✅ All CI checks passed!
```

---

### 2. **backend-test.yml** — Backend Suite

Triggered by changes to `backend/`, `tests/`, or `Dockerfile`.

**Jobs:**
- `test`: Run pytest (Python 3.11)
  - All tests in `tests/`
  - E2E WebSocket tests: `test_e2e_websocket.py`
  - Module import verification
  
- `docker-build`: Build backend Docker image
  - Validates Dockerfile
  - Builds: `avm-backend:test`
  
- `lint`: Code quality checks
  - Black (formatting)
  - isort (import ordering)
  - flake8 (PEP 8)
  - pylint (static analysis)
  
- `health-check`: Verify backend loads
  - Imports `backend.main:app`
  - Checks entrypoint configuration

**Key tests:**
```python
# HTTP endpoints
curl http://localhost:8000/health              # Health check
curl http://localhost:8000/docs                # Swagger UI
curl http://localhost:8000/api/version         # Model info

# WebSocket endpoints
ws://localhost:8000/ws/dashboard               # Dashboard updates
ws://localhost:8000/ws/monitoring              # Retraining status
```

---

### 3. **frontend-test.yml** — Frontend Suite

Triggered by changes to `frontend/` or this workflow.

**Jobs:**
- `test`: Run Node tests (18.x, 20.x)
  - npm lint
  - npm test (Jest with --passWithNoTests fallback)
  - npm test -- --coverage
  
- `build`: Build frontend Docker image
  - Builds: `avm-frontend:test`
  - Verifies build completes
  
- `type-check`: TypeScript validation
  - npx tsc --noEmit
  - npm run build (production build)
  - Checks NEXT_PUBLIC_API_URL is set

---

### 4. **integration-test.yml** — Full Stack E2E

Validates all layers: Docker, networking, configuration.

**Jobs:**
- `docker-compose-validation`: Compose file syntax + services
- `backend-docker-verify`: Image architecture, entrypoint, OS
- `frontend-docker-verify`: Node availability, working directory
- `network-config`: Service connectivity paths
- `healthcheck-config`: Backend health check probe
- `local-execution-test`: Python imports without Docker
- `configuration-audit`: Dockerfile hadolint, env vars, volumes

**Example checks:**
```bash
# Verify architecture
docker image inspect avm-backend:test | jq -r '.[0].Architecture'
# → amd64 ✅

# Verify network
docker compose config | jq '.networks'
# → {"avm-network": {"driver": "bridge"}} ✅
```

---

### 5. **code-quality.yml** — Linting & Security

Continuous quality monitoring (informational).

**Jobs:**
- `python-lint`: Black, isort, flake8, pylint
- `javascript-lint`: ESLint, TypeScript
- `dependency-check`: Safety (Python) + npm audit
- `code-complexity`: Cyclomatic complexity, maintainability index
- `security-headers`: Secret scanning, .gitignore coverage
- `docker-security`: Dockerfile best practices (hadolint)
- `environment-config`: docker-compose.yml audit

**Severity Levels:**
- 🔴 **Critical**: Tests fail (pytest, Docker build)
- 🟡 **Warning**: Linting/formatting (informational, `--exit-zero`)
- 🟢 **Info**: Complexity metrics, audit results

---

## Test Coverage Map

### Backend (pytest)

| Area | File | Tests | Coverage |
|------|------|-------|----------|
| API Endpoints | `test_api_endpoints.py` | 7 | Health, predict, confidence |
| WebSocket | `test_e2e_websocket.py` | 30+ | Connection, ping/pong, broadcasts, errors |
| API Server | `test_api_server.py` | Multiple | Subroute validation |
| Integration | `test_integration.py` | Multiple | Full workflow testing |

### Frontend (Jest)

| Area | File | Status |
|------|------|--------|
| Build | `npm run build` | ✅ Validated in CI |
| Lint | `npm run lint` | ✅ Runs in CI |
| Tests | `npm test` | Uses `--passWithNoTests` (no unit tests yet) |
| Type Check | `npx tsc` | ✅ Strict mode enabled |

### Docker & Compose

| Component | Validation | Status |
|-----------|-----------|--------|
| Backend Dockerfile | hadolint | ✅ Checked |
| Frontend Dockerfile | Image build | ✅ Verified |
| docker-compose.yml | `docker compose config` | ✅ Validated |
| Volume mounts | Config audit | ✅ Checked |
| Networking | Network inspect | ✅ Verified |

---

## Troubleshooting CI Failures

### Backend Tests Failing

```bash
# Run locally to diagnose
cd avm_project
pip install -r backend/requirements.txt
pytest tests/test_e2e_websocket.py -v

# Common issues:
# - Missing ML models: See DOCKER_LOCAL_GUIDE.md section 5.3
# - WebSocket: Verify uvicorn[standard] is installed
# - Imports: Check backend/__init__.py exists
```

### Docker Build Failing

```bash
# Test build locally
cd avm_project
docker build -f Dockerfile -t avm-backend:test .

# Check layers
docker history avm-backend:test

# Common issues:
# - Missing libgomp1 (OpenMP for xgboost/lightgbm)
# - Requirements.txt not found
# - .dockerignore excluding necessary files
```

### Frontend Build Failing

```bash
# Test build locally
cd avm_project/frontend
npm install
npm run build

# Check env var
echo $NEXT_PUBLIC_API_URL  # Should be set to http://localhost:8000

# Common issues:
# - Missing package-lock.json
# - Node version mismatch (test with node 18.x and 20.x)
# - TypeScript errors in strict mode
```

---

## Recommended Local Development Flow

```bash
# 1. After cloning/pulling
cd avm_project
git checkout claude/eloquent-meitner-lqxu9r

# 2. Install dependencies
pip install -r backend/requirements.txt
cd frontend && npm install && cd ..

# 3. Run tests before pushing
pytest tests/ -v
cd frontend && npm test && cd ..

# 4. Build Docker images locally
docker compose up --build

# 5. Verify health
curl http://localhost:8000/health

# 6. Push when tests pass
git push origin claude/eloquent-meitner-lqxu9r
```

---

## Key Configuration Files

| File | Purpose |
|------|---------|
| `.github/workflows/*.yml` | GitHub Actions workflow definitions |
| `backend/requirements.txt` | Python dependencies (pytest, httpx, websockets) |
| `frontend/package.json` | Node dependencies (jest, testing-library) |
| `frontend/jest.config.js` | Jest configuration |
| `frontend/jest.setup.js` | Jest setup |
| `Dockerfile` | Backend image |
| `frontend/Dockerfile` | Frontend image |
| `docker-compose.yml` | Multi-service orchestration |

---

## CI Status Badges

To display workflow status in README.md:

```markdown
![Backend Tests](https://github.com/eugene-eungkwon-kim/-/actions/workflows/backend-test.yml/badge.svg?branch=claude/eloquent-meitner-lqxu9r)
![Frontend Tests](https://github.com/eugene-eungkwon-kim/-/actions/workflows/frontend-test.yml/badge.svg?branch=claude/eloquent-meitner-lqxu9r)
![Integration Tests](https://github.com/eugene-eungkwon-kim/-/actions/workflows/integration-test.yml/badge.svg?branch=claude/eloquent-meitner-lqxu9r)
![Code Quality](https://github.com/eugene-eungkwon-kim/-/actions/workflows/code-quality.yml/badge.svg?branch=claude/eloquent-meitner-lqxu9r)
```

---

## Future Enhancements (Post-Phase 3 Week 4)

- [ ] Performance benchmarking (model inference time)
- [ ] Load testing (concurrent WebSocket connections)
- [ ] Security scanning (OWASP top 10, dependency audit)
- [ ] Coverage thresholds (pytest --cov-fail-under=80)
- [ ] E2E UI tests (Playwright, Cypress)
- [ ] Staging environment validation (once deployed)

---

**Last Updated:** Phase 3 Week 4  
**Branch:** `claude/eloquent-meitner-lqxu9r`  
**Principle:** Local-first validation, zero cloud deployment without performance verification
