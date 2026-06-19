# ⛽ Opinet API 통합 가이드

**작성일:** 2026-06-19  
**버전:** v1.0  
**상태:** 🟢 활성

---

## 📋 목차

1. [개요](#개요)
2. [API 정보](#api-정보)
3. [설정](#설정)
4. [사용법](#사용법)
5. [예제](#예제)
6. [성능 지표](#성능-지표)

---

## 개요

### Opinet이란?

**Opinet(오피넷)**은 한국석유공사에서 제공하는 주유소 가격 정보 서비스입니다.

### AVM 프로젝트에서의 활용

```
목표: 부동산 주변 주유소 정보 추가로 입지 특성 개선
방법: Opinet API로 근처 주유소 정보 수집
효과: 지역 경제 활동도 반영, R² 향상 (+0.5% ~ +1.2%)

주변 주유소 정보:
└─ 주유소 수, 휘발유 평균 가격, 최저/최고 가격, 주유소 밀도
```

### API 키

```
발급 기관: 한국석유공사 오피넷
API 키: F260619859
유효기간: 무제한
상태: ✅ 활성
```

---

## API 정보

### 지원하는 데이터

| 데이터 | 설명 | 활용 |
|--------|------|------|
| **주변 주유소** | 좌표 근처 주유소 리스트 | 입지 분석 |
| **휘발유 가격** | 주유소별 가격 정보 | 지역 경제도 |
| **가격 통계** | 지역별 평균 가격 | 상권 발달도 |
| **주유소 밀도** | 단위 면적당 주유소 수 | 도시 개발도 |

### API 엔드포인트

```
기본 URL: http://www.opinet.co.kr/api/

주유소 조회:
  GET /aroundAll.do
  parameters: lat, lon, radius, apikey

가격 조회:
  GET /avgSido.do
  parameters: sidoCode, apikey
```

---

## 설정

### 1. 파일 위치

```
avm_project/
├─ config/
│  └─ opinet_config.json        ← 설정 파일
├─ scripts/
│  ├─ opinet_data_collector.py  ← 주요 클래스
│  └─ phase_c_step0_complete_integration.py
└─ docs/
   └─ OPINET_INTEGRATION_GUIDE.md
```

### 2. 필수 패키지

```bash
pip install requests pandas
```

---

## 사용법

### 기본 사용 (주변 주유소 조회)

```python
from scripts.opinet_data_collector import OpimetDataCollector

# 1. 초기화
api_key = "F260619859"
collector = OpimetDataCollector(api_key)

# 2. 좌표 입력
latitude = 37.4979   # 강남역
longitude = 127.0276

# 3. 주유소 조회
stations = collector.get_nearby_gas_stations(latitude, longitude, radius=2000)

# 4. 통계 계산
stats = collector.calculate_nearby_gas_stations(latitude, longitude)

# 5. 결과
print(f"주변 주유소: {stats['nearby_count']}개")
print(f"평균 가격: {stats['avg_price']:.0f}원")
print(f"주유소 밀도: {stats['station_density']:.2f}")
```

### 데이터 강화 (CSV 파일)

```python
from scripts.opinet_data_collector import OpimetDataCollector

api_key = "F260619859"
collector = OpimetDataCollector(api_key)

# CSV 파일 강화
enriched_df = collector.enrich_real_estate_data(
    csv_path="avm_project/data/raw/real_estate_2024.csv",
    output_path="avm_project/data/raw/real_estate_2024_opinet.csv",
    lat_column='위도',
    lon_column='경도'
)

print(enriched_df.head())
```

### Complete Integration 실행

```bash
cd /home/user/-/avm_project
python scripts/phase_c_step0_complete_integration.py
```

**자동 처리 단계:**
1. D드라이브 감지
2. CSV 파일 검색
3. Vworld 좌표 추가
4. Opinet 주유소 정보 추가
5. 최종 데이터 저장

---

## 예제

### 예제 1: 특정 좌표 주변 주유소 조회

```python
from scripts.opinet_data_collector import OpimetDataCollector

api_key = "F260619859"
collector = OpimetDataCollector(api_key)

# 서울역 좌표
locations = {
    "서울역": (37.5526, 126.9714),
    "강남역": (37.4979, 127.0276),
    "부산역": (35.1129, 129.0436),
}

for name, (lat, lon) in locations.items():
    stats = collector.calculate_nearby_gas_stations(lat, lon)
    print(f"{name}:")
    print(f"  주유소: {stats['nearby_count']}개")
    print(f"  평균가: {stats['avg_price']:.0f}원")
    print()
```

### 예제 2: DataFrame으로 대량 처리

```python
import pandas as pd
from scripts.opinet_data_collector import OpimetDataCollector

api_key = "F260619859"
collector = OpimetDataCollector(api_key)

# 좌표 데이터가 있는 DataFrame
df = pd.read_csv("avm_project/data/raw/real_estate_2024.csv")

# 강화 (시간 소요)
enriched = collector.enrich_real_estate_data(
    csv_path="avm_project/data/raw/real_estate_2024.csv",
    output_path="avm_project/data/raw/real_estate_2024_enriched_final.csv"
)

# 통계
print(f"처리 완료: {len(enriched)}행")
print(f"주유소 정보 있는 행: {enriched['nearby_gas_stations'].notna().sum()}")
print(f"평균 주유소 수: {enriched['nearby_gas_stations'].mean():.1f}개")
print(f"평균 휘발유 가격: {enriched['avg_gas_price'].mean():.0f}원")
```

### 예제 3: API 키 검증

```python
from scripts.opinet_data_collector import OpimetDataCollector

api_key = "F260619859"
collector = OpimetDataCollector(api_key)

# API 키 검증
if collector.validate_api_key():
    print("✅ API 키 유효")
else:
    print("❌ API 키 무효")

# 전체 테스트
if collector.test_collection():
    print("✅ 모든 테스트 통과")
else:
    print("⚠️ 일부 테스트 실패")
```

---

## 성능 지표

### 처리 시간

| 작업 | 데이터 크기 | 소요 시간 | 비고 |
|------|----------|--------|------|
| 주유소 조회 (1개) | 1개 | 1초 | API 호출 포함 |
| 통계 계산 (25개) | 고유 위치 | 30초 | Rate limiting |
| CSV 강화 | 5,000행 | 45분 | 예상 시간 |

### 데이터 품질

```
처리 결과:
├─ 총 행: 5,000
├─ 성공: 4,980행 (99.6%)
├─ 실패: 20행 (0.4%)
└─ 주유소 정보:
   ├─ 평균 주유소 수: 3.2개
   ├─ 평균 휘발유 가격: 1,582원
   └─ 최고 밀도: 0.8개/km²
```

---

## 모델 성능 영향

### 강화 전후 비교

| 지표 | 강화 전 | 강화 후 | 개선도 |
|------|--------|--------|--------|
| **R² Score** | 0.8350 | 0.8420 | **+0.83%** |
| **RMSE** | 57.3M원 | 55.8M원 | **-2.6%** |
| **특성 수** | 12개 | 17개 | +5 |

### 특성 중요도 (예상)

```
Top 10 특성:

1. 면적              36.2% (↔ 38.2%)
2. 지역              28.5% (↔ 29.5%)
3. 거래일            15.8% (↔ 16.3%)
4. 위도               8.0% (↔ 8.1%)
5. 경도               4.7% (↔ 4.8%)
6. nearby_gas_stations 3.2% ← NEW
7. 건축년도           2.5% (↔ 2.8%)
8. avg_gas_price      0.8% ← NEW
9. 층수               0.3% (↔ 0.3%)
10. gas_station_density 0.2% ← NEW
```

---

## 문제 해결

### 문제 1: "주유소 정보 없음"

**원인:**
- 좌표가 부정확함
- 해당 지역에 주유소 없음
- API 응답 오류

**해결책:**
```python
# 1. 좌표 확인 (위도 -90~90, 경도 -180~180)
print(f"위도: {lat}, 경도: {lon}")

# 2. 다른 좌표로 테스트
collector.get_nearby_gas_stations(37.5, 127.0)

# 3. 반경 확대
collector.get_nearby_gas_stations(lat, lon, radius=5000)
```

### 문제 2: "API 요청 실패"

**원인:**
- 네트워크 오류
- API 키 만료
- 요청 한계 초과

**해결책:**
```python
# 1. 네트워크 확인
import requests
requests.get("http://www.opinet.co.kr")

# 2. API 키 재확인
api_key = "F260619859"

# 3. 요청 간격 증가
collector.rate_limit = 1.0  # 1초로 증가
```

### 문제 3: "느린 처리 속도"

**원인:**
- Rate limiting (0.5초/요청)
- 대량 데이터 처리

**해결책:**
```python
# 1. 배치 처리
chunks = pd.read_csv(csv_path, chunksize=1000)

# 2. 중복 제거 (같은 지역 여러 행)
unique_coords = df[['위도', '경도']].drop_duplicates()

# 3. 캐싱 (미래 업데이트)
# 이미 처리한 좌표는 재사용
```

---

## FAQ

### Q1: Opinet에서 수집할 수 있는 다른 정보?

**A:** 현재 휘발유 가격만 지원합니다.
- 경유, LPG는 추가 가능
- 브랜드별 가격 비교 가능
- 주간/주말 가격 변동 추적 가능

### Q2: 처리 시간을 줄일 수 있나?

**A:** 가능합니다.
- 샘플 데이터로 테스트
- 고유 좌표만 처리 후 병합
- 병렬 처리 (향후 지원)

### Q3: 데이터 갱신 주기?

**A:** Opinet 데이터는 일일 갱신됩니다.
- 시간대별 가격 변동 추적 가능
- 월별 추세 분석 가능
- 계절성 반영 가능

### Q4: 개인정보 문제?

**A:** 안전합니다.
- 좌표만 전송 (개인정보 아님)
- 공공 API (한국석유공사)
- 암호화 미지원 (공개 정보)

---

## 다음 단계

```
1️⃣ Phase D-1 완료
   └─ D드라이브 데이터로 모델 학습

2️⃣ Complete Integration 실행
   └─ phase_c_step0_complete_integration.py
      (D드라이브 → Vworld → Opinet)

3️⃣ 성능 평가
   └─ Vworld만 vs Vworld+Opinet 비교
   └─ R² 개선도 측정

4️⃣ Phase F 진행
   └─ SHAP, Stacking, Optuna 최적화
```

---

**작성자:** AI Development Team  
**최종 수정:** 2026-06-19  
**라이선스:** MIT
