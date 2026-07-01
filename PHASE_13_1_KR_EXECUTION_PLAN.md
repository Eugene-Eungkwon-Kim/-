# Phase 13.1-KR 상세 실행 계획서
## 한국 부동산 데이터 수집 파이프라인 (Week 1 실행)

**작성일**: 2026-07-01  
**상태**: 🚀 즉시 실행 모드  
**기간**: 2026-07-01 ~ 2026-07-07 (Week 1, 7일)  
**목표**: 50K 통합 거래 데이터셋 준비 → Phase 13.2 GPU 학습 입력 데이터 확보

---

## Executive Summary

**목표**: data.go.kr + MOLIT 시스템으로부터 한국 부동산 실거래 정보 50K+ 레코드 수집 → 통합 검증 → Phase 13.2 모델 학습 데이터 준비

**기간**: 7일 (7월 1일 월요일 ~ 7월 7일 일요일)

**성공 기준**:
- ✅ 50K+ 통합 거래 데이터 확보
- ✅ Null rate <2%, Outlier rate <3%
- ✅ kr_validated.parquet (50K rows, 26 컬럼) 생성
- ✅ Phase 13.2 진행 가능 상태

**필수 입력**:
1. **data.go.kr API Key** (부동산 실거래 정보 API)
2. **MOLIT 시스템 접근 권한** (CSV 다운로드)

---

## 1. 사전 준비 (Day 0 - 6월 30일)

### 1.1 API Key 확보

**data.go.kr**:
```
1. https://www.data.go.kr 방문
2. 회원가입 또는 로그인
3. 마이페이지 → API 신청
4. "부동산 실거래 정보 조회" API 선택
5. 신청 → 승인 대기 (즉시 or 1-2시간)
6. API Key 발급 (62자 문자열)

예: 9S2K4L6m9pQ8rT7uV2wX5yZ3aB1cD4eF6gH9jK2lM5nO8pQ1r
```

**MOLIT 시스템**:
```
1. https://rtdown.molit.go.kr 방문
2. 회원가입 (휴대폰 인증)
3. 부동산거래공개시스템 접근 권한 요청
4. 서울/경기/인천 3개 지역 선택
5. CSV 다운로드 권한 획득 (평일 09:00-18:00)
```

### 1.2 Python 환경 준비

```bash
cd /home/user/-/avm_project

# 의존성 설치
pip install -r requirements.txt

# 특히 필요한 라이브러리 확인
python3 -c "
import pandas as pd
import numpy as np
import requests
print('✓ Dependencies OK')
"
```

### 1.3 디렉토리 준비

```bash
mkdir -p data/raw data/processed output logs

# 구조 확인
ls -la data/
# raw/     → 원본 데이터
# processed/ → 정제된 데이터
```

---

## 2. 일일 실행 계획

### Day 1 (Jul 1, Mon): API 연동 & data.go.kr 수집

**목표**: data.go.kr에서 10K+ 레코드 수집

**Time Schedule**:
```
09:00-10:00  사전 준비
  ├─ API Key 최종 확인
  ├─ phase13_data_collector.py 수정 (KR 추가)
  └─ 스크립트 드라이런

10:00-12:00  data.go.kr 수집 (2시간)
  ├─ API 호출 (rate limit 1000 req/day)
  ├─ 2024-04월~06월 거래정보 수집
  ├─ 10K+ 레코드 목표
  └─ CSV 저장: avm_project/data/raw/datagokr_transactions.csv

12:00-13:00  점심

13:00-14:00  검증 & 로깅
  ├─ 수집 완료 확인 (10K+ records)
  ├─ 스키마 검증
  ├─ 출력: avm_project/output/collection_day1.log
  └─ 다음날 MOLIT 준비
```

**실행 스크립트**:
```python
# scripts/day1_collect_datagokr.py
from phase13_data_collector import Phase13DataCollector

collector = Phase13DataCollector(output_dir='data/raw')
success, counts = collector.collect_kr_datagokr(
    api_key='YOUR_API_KEY_HERE',
    start_month='202404',
    end_month='202406'
)

print(f"✓ Collected {counts['total_records']:,} records")
# Expected: ~10,000 records
```

**성공 지표**:
- 10,000+ 레코드 수집
- 26개 컬럼 (거래가, 면적, 위도, 경도, 건축년도 등)
- Null rate <5%

---

### Day 2-3 (Jul 2-3, Tue-Wed): MOLIT CSV 수집 & 통합

**목표**: MOLIT 20K+ 레코드 수집, data.go.kr과 병합

**Time Schedule (각 2시간)**:

**Day 2**:
```
09:00-11:00  MOLIT CSV 다운로드
  ├─ 서울 (2024-04~06): 5K~7K
  ├─ 경기 (2024-04~06): 7K~10K
  └─ 인천 (2024-04~06): 3K~5K
     → 15K~22K 예상

11:00-12:00  데이터 정제
  ├─ EUC-KR → UTF-8 인코딩 변환
  ├─ 컬럼 이름 표준화
  └─ 타입 검증

12:00-13:00  점심

13:00-14:30  병합 작업
  ├─ data.go.kr (10K) + MOLIT (20K) → 통합
  ├─ 스키마 매핑 (컬럼명 통일)
  ├─ 중복 확인 & 제거
  └─ 임시 저장: data/raw/kr_raw_merged.csv (30K)
```

**Day 3**:
```
09:00-12:00  통합 데이터 최종 검증
  ├─ Null rate 확인
  ├─ 범위 검증 (거래가, 면적, 위치)
  ├─ 이상치 탐지
  └─ 30K 데이터 → 50K로 증강 준비

12:00-13:00  점심

13:00-14:30  데이터 증강 (선택사항)
  ├─ 공개 샘플 데이터 추가 (10K)
  ├─ 또는 MOLIT 추가 수집
  └─ 목표: 50K 통합 데이터
```

**실행 스크립트**:
```python
# scripts/day2_collect_molit.py
import pandas as pd

# MOLIT CSV 로드 (사용자 다운로드)
seoul = pd.read_csv('molit_seoul_202404-06.csv', encoding='euc-kr')
gyeonggi = pd.read_csv('molit_gyeonggi_202404-06.csv', encoding='euc-kr')
incheon = pd.read_csv('molit_incheon_202404-06.csv', encoding='euc-kr')

# 인코딩 변환
for df in [seoul, gyeonggi, incheon]:
    df.columns = df.columns.str.encode('utf-8').decode('utf-8')

# 병합
merged = pd.concat([seoul, gyeonggi, incheon], ignore_index=True)
merged.to_csv('data/raw/kr_raw_merged.csv', index=False, encoding='utf-8')

print(f"✓ Merged: {len(merged):,} records")
# Expected: 20K~25K records
```

**성공 지표**:
- 20K+ MOLIT 레코드 수집
- data.go.kr + MOLIT 통합: 30K~35K 레코드
- 스키마 통일 완료

---

### Day 4 (Jul 4, Thu): 데이터 정제 & 전처리

**목표**: 50K 통합 데이터셋 준비 (정제 + 특성 엔지니어링 기초)

**Time Schedule**:
```
09:00-10:30  데이터 정제
  ├─ Null 값 처리 (KNN imputation)
  ├─ 이상치 제거 (3-시그마)
  ├─ 범위 검증
  └─ 중복 제거 (거래일, 주소, 거래가 기준)

10:30-12:00  특성 엔지니어링 기초
  ├─ 기본 10개 특성 추출
  ├─ 파생 특성 생성 (빌딩 연령, 거리 등)
  └─ StandardScaler 정규화

12:00-13:00  점심

13:00-15:00  Parquet 저장 & 검증
  ├─ Compression: snappy
  ├─ 품질 통계 기록
  └─ 출력: data/processed/kr_validated.parquet
```

**실행 스크립트**:
```python
# scripts/day4_data_preprocessing.py
from scripts.data_preprocessing import DataPreprocessor

preprocessor = DataPreprocessor()
df = preprocessor.load_data('data/raw/kr_raw_merged.csv')

# 정제
df = preprocessor.handle_missing_values(df)
df = preprocessor.detect_outliers(df, threshold=3)
df = preprocessor.normalize_data(df)

# 특성 엔지니어링
df = preprocessor.feature_engineering(df)

# 저장
preprocessor.save_processed_data(
    df,
    output_path='data/processed/kr_validated.parquet'
)

print(f"✓ Processed: {len(df):,} records, {len(df.columns)} features")
# Expected: 50K records, 26 columns
```

**성공 지표**:
- Null rate <2%
- Outlier rate <3%
- 50K 레코드 확보
- Parquet 저장 완료

---

### Day 5 (Jul 5, Fri): 데이터 프로파일링 & QA

**목표**: 데이터 품질 확인, Phase 13.2 준비 상태 확인

**Time Schedule**:
```
09:00-11:00  데이터 프로파일링
  ├─ 기본 통계 (min, max, mean, std)
  ├─ 분포 시각화
  ├─ 상관계수 분석
  └─ 출력: output/data_profiling.png

11:00-12:00  지오코딩 검증
  ├─ 위도/경도 범위 확인 (서울 기준)
  ├─ 유효성 검사
  ├─ 지오코딩 맵 시각화
  └─ 출력: output/geocoding_validation.png

12:00-13:00  점심

13:00-15:00  최종 품질 보고서
  ├─ 모든 통계 수집
  ├─ 이상치 분석
  ├─ Phase 13.2 사전 확인
  └─ 출력: output/phase13_kr_data_quality_report.md
```

**실행 스크립트**:
```python
# scripts/day5_data_profiling.py
import pandas as pd
from scripts.data_preprocessing import DataPreprocessor

df = pd.read_parquet('data/processed/kr_validated.parquet')

# 프로파일링
profiling = {
    'total_records': len(df),
    'features': len(df.columns),
    'null_rate': df.isnull().sum().sum() / (len(df) * len(df.columns)),
    'stats': df.describe().to_dict(),
}

# 지오코딩 검증
lat_valid = (df['latitude'] >= 37.0) & (df['latitude'] <= 38.0)
lon_valid = (df['longitude'] >= 126.5) & (df['longitude'] <= 127.5)
geo_valid = (lat_valid & lon_valid).sum() / len(df)

print(f"✓ Data Profile: {len(df):,} records, {len(df.columns)} features")
print(f"✓ Null Rate: {null_rate*100:.2f}%")
print(f"✓ Geocoding Valid: {geo_valid*100:.2f}%")
```

**성공 지표**:
- Completeness: >95%
- Accuracy: >98% (범위 검증)
- Consistency: 컬럼 타입 일치
- 품질 보고서 완성

---

### Day 6-7 (Jul 6-7, Sat-Sun): 최종 검증 & Phase 13.2 준비

**목표**: Phase 13.2 모델 학습 준비 완료

**Time Schedule**:

**Day 6**:
```
09:00-11:00  Train/Test Split 준비
  ├─ 시간순 분할 (80/20)
  │  ├─ Train: 2026-01-01 ~ 2026-03-15 (40K)
  │  └─ Test: 2026-03-16 ~ 2026-04-30 (10K)
  ├─ 레이블 분리 (y_train, y_test)
  └─ 저장: data/processed/X_train.pkl, X_test.pkl

11:00-12:00  StandardScaler 준비
  ├─ fit on train set
  ├─ transform test set
  ├─ 평균/표준편차 저장
  └─ 모니터링용 metadata

12:00-13:00  점심

13:00-15:00  최종 QA
  ├─ 모든 데이터 파일 검증
  ├─ 메타데이터 검증
  ├─ Phase 13.2 체크리스트
  └─ 결과 저장: output/phase13_kr_qa_report.md
```

**Day 7**:
```
09:00-11:00  최종 검증 & 승인
  ├─ 사용자 검토 (optional)
  ├─ 데이터 샘플 확인
  ├─ 통계 재검증
  └─ 승인 기록

11:00-12:00  Phase 13.2 준비 상태 확인
  ├─ GPU 환경 확인
  ├─ phase13_model_trainer.py 검증
  ├─ 하이퍼파라미터 설정
  └─ 학습 시작 준비

12:00-13:00  점심

13:00-14:00  모니터링 & 최종 정리
  ├─ 로그 아카이빙
  ├─ 최종 리포트 생성
  └─ Phase 13.2 시작 승인
```

**성공 지표**:
- Train/Test 분할 완료 (40K/10K)
- 정규화 설정 완료
- 모든 메타데이터 준비
- Phase 13.2 시작 준비 완료

---

## 3. 필수 파일 및 산출물

### 3.1 입력 파일

```
avm_project/
├─ data/raw/
│  ├─ datagokr_transactions.csv (10K from data.go.kr API)
│  ├─ molit_seoul_*.csv (MOLIT 다운로드)
│  ├─ molit_gyeonggi_*.csv
│  └─ molit_incheon_*.csv
```

### 3.2 출력 파일 (최종 산출물)

```
avm_project/
├─ data/processed/
│  ├─ kr_validated.parquet (50K rows, 26 columns) ⭐
│  ├─ X_train.pkl (40K × 45 features)
│  ├─ X_test.pkl (10K × 45 features)
│  ├─ y_train.pkl (40K targets)
│  ├─ y_test.pkl (10K targets)
│  └─ scaler.pkl (StandardScaler metadata)
│
├─ output/
│  ├─ collection_day1.log
│  ├─ data_profiling.png
│  ├─ geocoding_validation.png
│  ├─ phase13_kr_data_quality_report.md
│  ├─ phase13_kr_qa_report.md
│  └─ collection_metrics.json
```

---

## 4. 기술 주요사항

### 4.1 API Rate Limiting

**data.go.kr**:
- Rate Limit: 1,000 req/day (Free tier)
- 해결: 배치 요청 (월별, 3개월 × 400 req = 1200 req)
- 방법: 요청 간격 0.5초 설정

```python
import time
for page in range(1, num_pages):
    api_result = requests.get(url, params={...})
    time.sleep(0.5)  # 0.5초 간격
```

### 4.2 인코딩 처리

**MOLIT CSV**:
- 원본: EUC-KR 인코딩
- 변환: UTF-8

```python
import pandas as pd
df = pd.read_csv('file.csv', encoding='euc-kr')
df.to_csv('file_utf8.csv', encoding='utf-8', index=False)
```

### 4.3 Feature Engineering

**기본 10개 + 파생 특성**:
```
Base-10:
  area_sqm, old_price, latitude, longitude, property_type
  building_age, floor, distance_subway, distance_school, distance_park

Derived-35 (Phase 13.2에서):
  temporal (4): year, month, quarter, age²
  location (6): lat/lon cluster, distances
  market (3): avg price, trend, volume
  categorical (12): one-hot encoding
  interaction (10): polynomial, cross-terms
  
Total: 45 features
```

---

## 5. 실행 체크리스트

### Pre-execution (Day 0)
- [ ] data.go.kr API Key 발급받음
- [ ] MOLIT 회원가입 + 접근권한 획득
- [ ] Python 환경 설정 완료
- [ ] 디렉토리 구조 생성
- [ ] phase13_data_collector.py KR 추가 완료

### Week 1 Execution
- [ ] Day 1: data.go.kr 10K 레코드 수집
- [ ] Day 2-3: MOLIT 20K 레코드 수집 & 병합
- [ ] Day 4: 데이터 정제 & 특성 엔지니어링
- [ ] Day 5: 데이터 프로파일링 & QA
- [ ] Day 6-7: 최종 검증 & Phase 13.2 준비

### Post-execution
- [ ] kr_validated.parquet 생성 (50K rows)
- [ ] Train/Test 분할 완료 (40K/10K)
- [ ] 품질 보고서 작성 완료
- [ ] Phase 13.2 시작 승인

---

## 6. 위험 및 대응

| 위험 | 확률 | 대응책 |
|------|------|--------|
| API 키 미발급 | 20% | MOLIT만 사용 (25K) 또는 공개 데이터 |
| MOLIT 접근 거부 | 15% | data.go.kr만 사용 (10K) → 샘플 증강 |
| 데이터 품질 저하 | 10% | EDA 재실행 + 추가 수집 |
| 수집 시간 초과 | 15% | Rate limiting 완화 또는 병렬 수집 |

---

## 7. 성공 기준 (최종 확인)

**Phase 13.1-KR 완료 조건**:
```
✅ 데이터 수집
  ├─ 50K+ 통합 레코드 확보
  ├─ data.go.kr + MOLIT 병합 완료
  └─ 26개 표준 컬럼

✅ 데이터 품질
  ├─ Null rate <2%
  ├─ Outlier rate <3%
  ├─ 범위 검증 완료 (지오코딩 포함)
  └─ 인코딩 통일 (UTF-8)

✅ 산출물
  ├─ kr_validated.parquet (50K rows)
  ├─ X_train/X_test 분할 (40K/10K)
  ├─ 품질 보고서 + 프로파일링
  └─ 메타데이터 저장

✅ Phase 13.2 준비
  ├─ GPU 환경 확인
  ├─ 하이퍼파라미터 준비
  └─ phase13_model_trainer.py 검증

└─→ Phase 13.2 GPU 모델 학습 시작 가능
```

---

**Phase 13.1-KR 실행 준비 완료**  
**시작일**: 2026-07-01 (월요일) 09:00  
**완료일**: 2026-07-07 (일요일) 14:00 예상  
**다음 Phase**: Phase 13.2 GPU 모델 학습 (2026-07-08)
