# 데이터 통합 전략 및 실행 계획
**작성일:** 2026-06-24  
**상태:** 🚧 LG 외장하드 데이터 대기 중 | API 통합 준비 완료  
**목표:** 실제 부동산 데이터로 R² ≥ 0.85 달성

---

## 📊 현재 상황 분석

### 1. 데이터 소스 현황

| 소스 | 상태 | 데이터 형태 | 행수 | 신호 |
|------|------|-----------|------|------|
| **LG 외장하드** | ⏳ 대기 | CSV (예정) | ? | ? |
| **VWorld API** | ⚠️ Key 필요 | API 응답 JSON | - | 정상 예상 |
| **건축물관리대장 API** | ⚠️ Key 필요 | API 응답 JSON | - | 정상 예상 |
| **실거래가 정보 API** | ⚠️ Key 필요 | API 응답 JSON | - | 정상 예상 |
| **현재 Synthetic 데이터** | ✅ 사용 중 | CSV | 3,000 | ❌ 매우약함 (max corr 0.039) |

### 2. 각 데이터 소스의 특성

#### LG 외장하드 데이터 (최우선)
- **경로:** `/mnt/avm_data/Raw_Data/` 또는 `/Processed_Data/`
- **현재:** 디렉토리 구조만 존재 (파일 없음)
- **예상 내용:**
  - 건축물관리대장 원본 또는 전처리 데이터
  - VWorld 지번도 및 건물정보
  - 실제 거래 이력 데이터
- **강점:** 물리적 접근 가능, 네트워크 지연 없음, 대용량 처리 가능
- **예상 신호:** ✅ 강함 (정상 부동산 데이터)

#### API 기반 데이터 (LG 외장하드 부족 시 보강)
- **VWorld:** 지번도, 건물 용도, 면적, 연식
- **건축물관리대장:** 건물 기본정보, 층수, 방수, 주용도
- **실거래가:** 실제 거래가, 거래일자, 거래건수
- **강점:** 실시간 데이터, 공식 소스, 정확도 높음
- **약점:** API 인증 필요, 요청 속도 제한, 할당량 제한
- **예상 신호:** ✅ 강함 (공식 통계 데이터)

#### 현재 Synthetic 데이터 (폴백)
- **경로:** `data/processed/cleaned_real_estate_combined_20260617.csv`
- **상태:** ✅ 즉시 사용 가능
- **신호:** ❌ 매우약함 (최대 상관 0.0388)
- **용도:** 인프라 테스트 (모델 정확도 검증 불가)

---

## 🎯 3-Track 병렬 실행 전략

### Track A: 데이터베이스 로드 (병렬 진행)
**목표:** 실제 데이터를 검증된 스키마로 DB에 적재  
**소요 시간:** 1-2일 (데이터 준비 후)

#### A1. 데이터 검증 (즉시)
```bash
# 현재: LG 외장하드 데이터 구조 파악
python3 scripts/real_estate_data_loader.py
# 결과: LG 외장하드 데이터 없음 → synthetic 폴백

# 필요: LG 외장하드 데이터 업로드
# 위치: /mnt/avm_data/Raw_Data/ 또는 /Processed_Data/
# 파일: CSV 형식 (건축물관리대장, VWorld, 실거래가)
```

#### A2. 데이터 스키마 매핑 (LG 데이터 도착 후)
```
필수 컬럼 매핑:
- area_sqm ← 전용면적 / 건축면적
- year_built ← 건축년도
- floor ← 층수
- market_price ← 실거래가 / 거래금액
- ... (나머지 19개 feature)
```

#### A3. DB 테이블 생성 및 적재
- PostgreSQL/MySQL 스키마 설계
- 데이터 정제 파이프라인 실행
- 품질 검증 (결측치, 이상치 제거)

### Track B: 모델 재학습 (데이터 대기)
**목표:** 실제 데이터로 R² ≥ 0.85 달성  
**소요 시간:** 2-3시간 (데이터 준비 후)

#### B1. 데이터 준비 (LG 외장하드 도착 후)
```bash
# 실제 데이터 로드 및 정제
python3 scripts/real_estate_data_loader.py

# 신호 분석 (feature-target 상관)
# 결과: correlation_analysis.json
```

#### B2. 모델 재학습 (신호 확인 후)
```bash
# 7개 모델 재학습 (Linear, DT, RF, GB, XGBoost, LightGBM, Ensemble)
python3 scripts/retrain_models_with_real_data.py

# 예상 결과 (실제 신호 있을 때):
# - Linear Regression: R² ≥ 0.70
# - Random Forest: R² ≥ 0.80
# - Gradient Boosting: R² ≥ 0.82
# - XGBoost: R² ≥ 0.85 ✅
# - LightGBM: R² ≥ 0.86 ✅
```

#### B3. 성능 검증
- R² 점수 ≥ 0.85 확인
- Cross-validation 점수 비교
- Feature importance 분석

### Track C: 클라우드 배포 (병렬 진행)
**목표:** 프로덕션 준비 완료  
**소요 시간:** 2-3일 (인프라 기반)

#### C1. 클라우드 인프라 설계 (즉시)
- AWS / GCP / Azure 선택
- VPC, 보안그룹, IAM 설정
- RDS (DB), Lambda (API), S3 (모델 저장소)

#### C2. 배포 파이프라인 구축 (즉시)
- Docker 이미지 빌드
- CI/CD (GitHub Actions / GitLab CI)
- 자동 테스트 & 배포

#### C3. 모델 서빙 설정 (B 완료 후)
- 학습된 모델 업로드
- API 엔드포인트 배포
- 성능 모니터링

---

## 🔄 즉시 실행 항목 (LG 데이터 대기 중)

### Step 1. LG 외장하드 데이터 준비 ⏳
**담당자 작업:**
```
1. LG 외장하드 D: 드라이브에서 다음 파일 복사
   - 건축물관리대장_YYYYMM.csv
   - VWorld_부동산정보_YYYYMM.csv
   - 실거래가_YYYYMM.csv

2. 복사 경로:
   /mnt/avm_data/Raw_Data/
   또는
   /mnt/avm_data/Processed_Data/

3. 파일 형식 확인:
   - 인코딩: UTF-8-sig (Excel 한글 호환)
   - 구분자: , (쉼표)
   - 헤더 행 포함
```

### Step 2. API Key 준비 (LG 데이터 부족 시 보강)
**설정 파일:** `config/avm_config.json`
```json
{
  "api_keys": {
    "vworld_key": "YOUR_VWORLD_API_KEY",
    "building_registry_key": "YOUR_BUILDING_REGISTRY_KEY",
    "transaction_price_key": "YOUR_TRANSACTION_PRICE_KEY"
  }
}
```

**API 발급 절차:**
1. VWorld: https://www.vworld.kr/ → API 신청
2. 건축물관리대장: https://www.data.go.kr/ → 부동산 관련 API 검색 & 신청
3. 실거래가: https://www.data.go.kr/ → "부동산 실거래가" API 신청

**예상 승인 시간:** 24-48시간

### Step 3. 데이터 로드 및 검증 (Step 1 완료 후)
```bash
cd /home/user/-/avm_project

# LG 외장하드 데이터 로드
python3 scripts/real_estate_data_loader.py
# 예상 결과: correlation_analysis.json 생성, 신호 확인

# API 기반 데이터 수집 (Key 준비 후)
python3 scripts/api_real_estate_fetcher.py
```

### Step 4. 모델 재학습 (Step 3 완료 후)
```bash
# 실제 데이터로 모델 재학습
python3 scripts/retrain_models_with_real_data.py
# 예상 결과: R² ≥ 0.85 달성 (정상 신호 시)
```

---

## 📋 파일 정리

### 새로 생성된 파일
| 파일 | 목적 | 상태 |
|------|------|------|
| `scripts/real_estate_data_loader.py` | LG 외장하드 + 폴백 데이터 로드 | ✅ 완성 |
| `scripts/api_real_estate_fetcher.py` | VWorld + 건축물관리대장 API 수집 | ✅ 완성 |
| `data/real/real_estate_data_20260624.csv` | 현재 데이터 (synthetic 폴백) | ✅ 생성됨 |
| `data/real/correlation_analysis.json` | 신호 분석 결과 | ✅ 생성됨 |

### 예정 파일 (LG 데이터 도착 후)
| 파일 | 목적 |
|------|------|
| `data/real/real_estate_data_actual_YYYYMMDD.csv` | LG 외장하드 통합 데이터 |
| `models/retrained_YYYYMMDD/` | 실제 데이터로 재학습한 모델 |
| `DATA_RETRAINING_RESULTS_REAL_DATA.md` | 최종 모델 성능 보고서 |

---

## 🎯 성공 기준

| 항목 | 기준 | 현재 | 목표 |
|------|------|------|------|
| **Data Signal** | Max Correlation | 0.0388 | ≥ 0.50 |
| **Model R²** | 7개 모델 평균 | -0.0709 | ≥ 0.85 |
| **DB Integration** | 데이터 적재 | ⏳ 대기 | ✅ 완료 |
| **Cloud Deployment** | API 운영 | 🚧 진행 중 | ✅ 완료 |

---

## ⏱️ 예상 일정

```
2026-06-24 (지금)
├─ Step 1: LG 외장하드 데이터 준비 ⏳ (담당자)
├─ Step 2: API Key 발급 신청 ⏳ (담당자, 24-48시간)
│
2026-06-25
├─ Step 3a: LG 데이터 도착 시 → 로드 및 검증 (2시간)
├─ Step 3b: API Key 승인 시 → API 수집 (2시간)
│
2026-06-26
├─ Step 4: 모델 재학습 (3시간)
├─ Track A: DB 적재 (병렬, 2시간)
├─ Track C: 클라우드 배포 (병렬, 2-3시간)
│
2026-06-27
└─ 🎯 최종 검증 및 보고서 작성
```

---

## 🔑 핵심 의사결정 포인트

### Q1: LG 외장하드 데이터는 언제 준비 가능한가?
- **영향:** Track A 시작 시점, 모델 재학습 가능 여부
- **필요한 응답:** 예상 날짜 및 파일 형식

### Q2: API Key를 발급할 것인가, 아니면 LG 데이터만 사용할 것인가?
- **Option A:** LG 데이터만 사용 → 빠름, 네트워크 지연 없음
- **Option B:** LG + API → 보강, 더 완전한 데이터셋
- **권장:** Option B (보강)

### Q3: 합성 데이터로 먼저 Track A/C를 진행할 것인가?
- **현재 계획:** Track C는 즉시, Track A는 LG 데이터 대기
- **이유:** Track A는 실제 데이터 기반이어야 의미 있음

---

## 📞 다음 액션

1. **LG 외장하드 데이터 준비** ← 🚨 **CRITICAL** 우선순위
   - 파일 형태와 위치 확인
   - `/mnt/avm_data/` 로 복사
   
2. **API Key 준비** (LG 데이터 부족 시)
   - data.go.kr 에서 신청
   - config/avm_config.json 에 입력
   
3. **Track C 병렬 진행** (LG 데이터 대기 중)
   - 클라우드 인프라 설계
   - 배포 파이프라인 구축

---

**상태:** 🚧 LG 외장하드 데이터 수집 대기 중  
**다음 체크:** 2026-06-25 (1일 후)
