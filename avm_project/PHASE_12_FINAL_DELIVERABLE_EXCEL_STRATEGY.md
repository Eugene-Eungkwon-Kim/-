# Phase 12 최종 산출물 생성 전략
## 기초 데이터 양식 기반 완성 계획

**작성일**: 2026-06-25  
**분석 대상**: d83dc204-Loan4U____QC_v1.1before_fill.xlsx (기초 데이터 양식)

---

## 📊 기초 데이터 구조 분석

### 5개 시트의 역할

```
┌─────────────────────────────────────────────────────────────┐
│ Report (리포트)                                             │
│ • 40행 × 18열                                              │
│ • 최종 리포트 템플릿                                        │
│ • LOAN4U QC REPORT 제목                                    │
│ • KPI, 요약, 분석 결과 표시                                │
│ ⟹ Phase 12의 최종 요약 리포트                             │
├─────────────────────────────────────────────────────────────┤
│ 아파트 시트                                                 │
│ • 997행 × 32열                                              │
│ • 헤더: 연번, 시, 군, 구, 동, 지번, 단지명, 동, 호,      │
│        주택종류(ACT/WEB), 전용면적(ACT/WEB), 준공연도 ... │
│ • 아파트 유형 부동산 데이터                                │
│ ⟹ Phase 12 각 국가의 아파트 기초 데이터                   │
├─────────────────────────────────────────────────────────────┤
│ 빌라 시트                                                   │
│ • 1000행 × 31열                                             │
│ • 아파트와 유사 구조                                        │
│ • 빌라 유형 부동산 데이터                                   │
│ ⟹ Phase 12 각 국가의 빌라/주택 기초 데이터                │
├─────────────────────────────────────────────────────────────┤
│ RAW 시트 (원본 데이터)                                      │
│ • 1000행 × 29열                                             │
│ • 컬럼: 연번, 시, 군, 구, 동, 지번, 단지명, index,       │
│        동, 호, 전유면적, 준공연도,                          │
│        AI예측가 v1.0, AI예측가 v1.1 ...                   │
│ • AI 모델 예측값 포함 (다중 버전)                          │
│ ⟹ Phase 12의 모델 버전별 예측값                           │
├─────────────────────────────────────────────────────────────┤
│ AIpredict 시트 (최종 예측)                                  │
│ • 462행 × 16열                                              │
│ • 컬럼: 번호, 주소, 단지명, pnu, Build_year, ex_Area,    │
│        INDEX, Floor, Official_P, 2025공동주택가격,        │
│        House_count, City_grade, COFIX, predict             │
│ • 최종 예측 결과 (predict 컬럼)                            │
│ ⟹ Phase 12의 최종 모델 예측값                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 기초 데이터 양식 → Phase 12 데이터 맵핑

### 데이터 변환 전략

```
기초 데이터 (Loan4U QC 국내)
  ↓
  ├─ Report: 국내 최종 리포트
  ├─ 아파트: 국내 아파트 (997건)
  ├─ 빌라: 국내 빌라 (1000건)
  ├─ RAW: 국내 모델 버전별 예측
  └─ AIpredict: 국내 최종 예측 (462건)

Phase 12 (8개국 글로벌 확장)
  ↓
  ├─ Report: 글로벌 최종 리포트
  ├─ UK: 영국 부동산 데이터
  ├─ Singapore: 싱가포르 부동산 데이터
  ├─ Japan: 일본 부동산 데이터
  ├─ Germany: 독일 부동산 데이터
  ├─ Australia: 호주 부동산 데이터
  ├─ Canada: 캐나다 부동산 데이터
  ├─ Thailand: 태국 부동산 데이터
  ├─ Hong Kong: 홍콩 부동산 데이터
  ├─ RAW: 국가별 모델 버전별 예측
  └─ GlobalAIpredict: 글로벌 최종 예측
```

---

## 🏗️ Phase 12 최종 산출물 구조 설계

### 신규 Excel 파일: Loan4U_QC_v1.1_Phase12_Global.xlsx

#### Sheet 1: Report (글로벌 최종 리포트)
```
구조: 40행 × 20열 (기초 데이터 Report 확장)

Section 1: 헤더 (Row 1-5)
  • LOAN4U QC GLOBAL REPORT
  • Phase 12: International Market Entry
  • 작성일: 2026-06-25, 실행일: 2026-07-01

Section 2: 글로벌 KPI (Row 7-15)
  • 총 투자: $1,035,000
  • 예상 월 수익: 26.5-40.0억 원
  • 목표 사용자: 790-940명
  • B2B 파트너: 20-28개
  • 평균 R² 점수: 0.87
  • ROI: 236배
  • 진출 국가: 8개
  • 운영 기간: 2026-07-01 ~ 2026-12-31

Section 3: 국가별 요약 (Row 17-30)
  • 테이블: 국가명 | 우선순위 | 월수익 | 사용자 | 파트너 | 진출기간

Section 4: 마일스톤 (Row 32-40)
  • Month 1-3: 11.5-16.0억 원
  • Month 6: 24.5-36.0억 원
  • Month 12: 26.5-40.0억 원
```

#### Sheet 2~9: 국가별 기초 데이터

```
각 국가마다 2개의 시트:

🇬🇧 UK
  ├─ UK_Residential: 부동산 데이터 (아파트/주택)
  │  • 컬럼: 연번, 지역, 우편번호, 주소, 부동산유형, 
  │          거래가, MAARS예측가, 신뢰도, R² ...
  │
  └─ UK_Prediction: 예측 결과
     • 컬럼: 번호, 주소, 부동산유형, UPRN, 
             면적, 건축년도, 거래가, 예측가, predict

🇸🇬 Singapore
  ├─ SG_Residential: HDB/민간 부동산
  │  • 컬럼: 연번, 지역, 주소, 부동산유형(HDB/Private),
  │          면적, 임차기간, 거래가, 예측가 ...
  │
  └─ SG_Prediction: 이원 모델 예측

🇯🇵 Japan
  ├─ JP_Residential: 지역별 부동산 (도시/중도시/지방)
  │
  └─ JP_Prediction: 지역별 예측 결과

... (Germany, Australia, Canada, Thailand, Hong Kong)
```

#### Sheet N: RAW (통합 원본 데이터)
```
• 8개국 × ~1000건 = ~8000행
• 컬럼: 국가코드, 연번, 주소, 부동산유형, 면적, 
        거래가, AI예측가_v1.0, AI예측가_v1.1, 
        AI예측가_v1.2(Phase12), ...
```

#### Sheet N+1: GlobalAIpredict (최종 글로벌 예측)
```
• 8개국 모든 예측 결과 통합
• 462행 → 3000+행 (8개국 × 462/국가)
• 컬럼: 번호, 국가, 주소, 단지명, 
        Build_year, ex_Area, 거래가, 
        Official_Price, predict, Model_Version, R²_Score
```

---

## 📈 기초 데이터의 핵심 필드

### 1. 위치 정보
```
기초: 시, 군, 구, 동, 지번, 단지명
확장: 
  • 국가 코드 (GB, SG, JP, DE, AU, CA, TH, HK)
  • 지역 계층 (도/주/구/동/읍면)
  • 우편번호/Postcode
  • 좌표 (위도, 경도)
```

### 2. 부동산 정보
```
기초: 주택종류, 전용면적, 준공연도, 동, 호
확장:
  • 부동산 유형 (Apartment/House/Villa/Condo/HDB/Land)
  • 면적 (전용/전체)
  • 임차기간 (특히 홍콩, 싱가포르)
  • 층수 (Floor)
  • 방개수 (Rooms)
```

### 3. 가격 정보
```
기초: (비어있음)
필수 추가:
  • 최근 거래가 (Recent Transaction Price)
  • 공식 감정가 (Official_P)
  • 2025 공동주택가격 → 지역별 평균가 확장
  • 예측가 (predict)
```

### 4. 모델 예측
```
기초: 
  • AI예측가 v1.0 (A1)
  • AI예측가 v1.1 (A2)
  
확장 (Phase 12):
  • AI예측가 v1.2 (Phase12)
  • 국가별 모델 (UK, SG, JP, ...)
  • 신뢰도 (Confidence)
  • R² 점수 (Model_R2)
  • RMSE
```

### 5. 추가 지표
```
기초:
  • House_count (단지 내 호수)
  • City_grade (도시 등급)
  • COFIX (금융 지수)

확장:
  • 시장 트렌드 (Market_Trend)
  • 거래량 (Transaction_Volume)
  • 유사 부동산 개수 (Comparable_Count)
  • API 거래 여부 (API_Enabled)
```

---

## 🛠️ 구현 전략 (단계별)

### Phase 1: Report 시트 생성 (30분)
```python
# 1. 글로벌 KPI 데이터 입력
report_data = {
    "제목": "LOAN4U QC GLOBAL REPORT",
    "부제": "Phase 12: International Market Entry & Expansion",
    "총_투자": "$1,035,000",
    "예상_월_수익": "26.5-40.0억 원",
    ...
}

# 2. 국가별 요약 테이블
countries = [
    {"국가": "UK", "우선순위": 1, "월수익": "4-6천만", ...},
    {"국가": "Singapore", "우선순위": 2, ...},
    ...
]

# 3. openpyxl로 Report 시트 생성
```

### Phase 2: 국가별 데이터 시트 생성 (1-2시간)
```python
# 1. Phase 12 데이터 로드
phase12_data = {
    "uk": [...514개 부동산...],
    "sg": [...462개 부동산...],
    "jp": [...550개 부동산...],
    ...
}

# 2. 국가별로 2개 시트 생성
for country, data in phase12_data.items():
    create_residential_sheet(country, data)      # 부동산 기초
    create_prediction_sheet(country, data)        # 예측 결과
```

### Phase 3: RAW 시트 생성 (30분)
```python
# 1. 모든 국가의 데이터 통합
raw_data = []
for country, data in phase12_data.items():
    for item in data:
        raw_data.append({
            "국가": country,
            "주소": item.address,
            "거래가": item.transaction_price,
            "예측가_v1_0": item.prediction_v1_0,
            "예측가_v1_1": item.prediction_v1_1,
            "예측가_v1_2_Phase12": item.prediction_phase12,
        })

# 2. RAW 시트에 입력
```

### Phase 4: GlobalAIpredict 시트 생성 (30분)
```python
# 1. 최종 예측 결과 통합
predictions = []
for country, results in phase12_predictions.items():
    for result in results:
        predictions.append({
            "번호": ...,
            "국가": country,
            "주소": result.address,
            "predict": result.final_prediction,
            "R²": result.r2_score,
        })

# 2. GlobalAIpredict 시트에 입력
```

### Phase 5: 스타일링 & 검증 (1시간)
```
✅ 헤더 서식 (배경색, 굵게)
✅ 데이터 타입 지정 (숫자는 통화, 백분율 등)
✅ 조건부 포맷 (R² > 0.90은 녹색)
✅ 동결창 설정 (첫 행 고정)
✅ 컬럼 너비 자동 조정
✅ 합계 및 통계 추가
```

---

## 📋 데이터 맵핑 테이블

### 기초 데이터 vs Phase 12 확장

| 기초 필드 | 타입 | Phase 12 확장 | 예시 |
|----------|------|-------------|------|
| 연번 | ID | 국가별 순번 | 1-997 (UK), 1-462 (SG) |
| 시, 군, 구, 동 | Location | 국가별 지역 계층 | 경기도 → England/London |
| 지번 | Land Number | Postcode/Postal Code | 129 → SW1A 1AA |
| 단지명 | Complex Name | Property Name | PH129 → Westminster Plaza |
| 동, 호 | Unit | Unit/Apartment | 108-1005 → 203-1203 |
| 주택종류 | Type | 부동산 유형 | 아파트 → Apartment/Condo |
| 전용면적 | Area | 전용/전체 면적 | 84㎡ → 850 sqft |
| 준공연도 | Build Year | 건축년도 | 2015 → 1998 |
| AI예측가 v1.0 | Model v1.0 | 기초 모델 | 예측가 |
| AI예측가 v1.1 | Model v1.1 | 개선 모델 | 예측가 |
| (새로 추가) | Model v1.2 | Phase 12 모델 | 국가별 예측 |

---

## ⚙️ 최종 산출물 규모

```
Loan4U_QC_v1.1_Phase12_Global.xlsx
├─ Report: 40행 × 20열
├─ UK_Residential: 200행 × 15열 (샘플)
├─ UK_Prediction: 200행 × 12열
├─ SG_Residential: 150행 × 16열
├─ SG_Prediction: 150행 × 12열
├─ JP_Residential: 180행 × 16열
├─ JP_Prediction: 180행 × 12열
├─ DE_Residential: 140행 × 15열
├─ DE_Prediction: 140행 × 12열
├─ AU_Residential: 160행 × 15열
├─ AU_Prediction: 160행 × 12열
├─ CA_Residential: 150행 × 15열
├─ CA_Prediction: 150행 × 12열
├─ TH_Residential: 100행 × 15열
├─ TH_Prediction: 100행 × 12열
├─ HK_Residential: 120행 × 16열
├─ HK_Prediction: 120행 × 12열
├─ RAW: 1500행 × 12열 (모든 국가 통합)
└─ GlobalAIpredict: 1500행 × 14열 (최종 예측)

총: 19개 시트, ~10,000행, 평균 250-300MB
```

---

## 🎯 이점

### 기초 데이터 양식 재사용의 이점

```
✅ 일관성
   • Loan4U QC의 표준 구조 유지
   • 국내 + 국제 데이터 통합 가능
   • 시스템 호환성 보장

✅ 확장성
   • 새로운 국가 추가 용이
   • 모델 버전 관리 명확
   • 히스토리 추적 가능

✅ 전문성
   • 기존 검증된 구조
   • 이해관계자 친숙
   • 운영 인수인계 용이

✅ 분석성
   • 국가별 비교 분석 가능
   • 모델 성능 비교 명확
   • 트렌드 분석 가능
```

---

## 📌 다음 단계

```
1️⃣ 기본 데이터 구조 확정
   ☐ 추가할 필드 검토
   ☐ 국가별 특수 필드 정의
   ☐ 포맷/단위 통일

2️⃣ Phase 12 데이터 준비
   ☐ 각 국가별 샘플 데이터 수집
   ☐ 모델 예측값 생성
   ☐ R² 점수 계산

3️⃣ Excel 파일 생성
   ☐ Python 스크립트 작성
   ☐ openpyxl로 19개 시트 생성
   ☐ 스타일링 및 포맷팅

4️⃣ 검증 및 배포
   ☐ 데이터 검증
   ☐ 수식 확인
   ☐ 최종 파일 생성
```

---

**준비 완료!**

기초 데이터 양식을 기반으로 한 Phase 12 최종 산출물(Excel) 생성이 가능합니다.

"**시작**" 명령으로 실행을 시작하시면 됩니다.
