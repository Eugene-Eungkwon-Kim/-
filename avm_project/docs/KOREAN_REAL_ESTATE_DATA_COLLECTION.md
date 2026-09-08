# AVM 프로젝트 - 한국 부동산 데이터 수집 완전 가이드

**최종 업데이트:** 2026-06-09  
**상태:** 📋 데이터 수집 계획 및 가이드 문서  

---

## 📑 목차

1. [개요](#개요)
2. [Data.go.kr 데이터](#datagonkr-데이터)
3. [한국부동산원 데이터](#한국부동산원-데이터)
4. [API 설정 및 인증](#api-설정-및-인증)
5. [데이터 수집 방법](#데이터-수집-방법)
6. [데이터 정제 및 통합](#데이터-정제-및-통합)
7. [자동화 및 스케줄링](#자동화-및-스케줄링)
8. [실행 예제](#실행-예제)

---

## 개요

### 목표
- Data.go.kr에서 제공하는 국토교통부 공식 부동산 데이터 수집
- 한국부동산원의 시장 동향 데이터 수집
- 수집된 데이터를 AVM 모델 학습에 활용

### 주요 데이터 소스

| 소스 | 제공자 | 주요 데이터 | 업데이트 주기 |
|------|--------|-----------|-----------|
| **Data.go.kr** | 국토교통부 | 실거래 정보, 공시지가, 건축물 정보 | 월 1회 |
| **한국부동산원** | 한국부동산원 | 시장 동향, 가격 지수, 심리 지수 | 주/월/분기 |
| **한국감정원** | 한국감정원 | 감정평가 통계 | 월 1회 |
| **통계청** | 통계청 | 주택통계, 건설통계 | 월 1회 |

---

## Data.go.kr 데이터

### 주요 데이터셋 (10개)

#### 1. 부동산 실거래 정보 ⭐⭐⭐ (필수)

**개요:**
- 전국의 부동산 거래 기록
- 월별로 최신 데이터 제공
- API 및 파일 다운로드 방식 지원

**API 정보:**
```
엔드포인트: https://apis.data.go.kr/6440000/budongsanservice/searchAPT
데이터셋ID: 16048670
제공처: 국토교통부
```

**수집 가능한 데이터:**
```
• 거래일자
• 지역 (시도, 시군구, 동)
• 거래가격
• 주소 (도로명, 지번)
• 건물명 (아파트명)
• 층수
• 건물면적
• 토지면적
• 건축년도
• 거래 유형
```

**활용 팁:**
- 월별로 데이터 요청 (과도한 부하 방지)
- 지역코드로 특정 지역만 필터링 가능
- 100건 단위로 페이징 처리 필요

**예상 데이터 규모:**
```
월당 거래량: 약 40,000~60,000건
연간 거래량: 약 500,000~700,000건
예상 파일 크기: 월당 20~30MB
```

#### 2. 아파트 매매 현황

**개요:**
- 아파트 매매 가격 및 거래량 통계
- 지역별, 평수별 분류

**API 정보:**
```
엔드포인트: https://apis.data.go.kr/1613000/AptBizTrend/status
데이터셋ID: 15094143
```

**주요 필드:**
```
• 연월
• 지역
• 아파트명
• 평균가격
• 거래량
• 전월대비 변화율
• 전년대비 변화율
```

#### 3. 전월세 실거래 정보

**개요:**
- 전월세 거래 기록
- 주택 유형별 구분

**API 정보:**
```
엔드포인트: https://apis.data.go.kr/6440000/budongsanservice/searchJeonse
데이터셋ID: 16049552
```

**주요 필드:**
```
• 계약일자
• 법정동
• 주택유형 (단독, 다가구, 아파트 등)
• 보증금
• 월세
• 건물면적
• 건축년도
• 계약기간
```

#### 4. 공시지가 정보 ⭐⭐

**개요:**
- 전국 토지의 공시지가
- 연 1회 공시 (7월경)

**API 정보:**
```
엔드포인트: https://apis.data.go.kr/1611000/nsdi/IndvdLandPriceService/getLandPriceInfo
데이터셋ID: 15012018
```

**주요 필드:**
```
• 공시년도
• 시도/시군구
• 지번
• 지목 (대지, 임야 등)
• 공시지가
• 지가변동률
• 면적
• 용도지역
```

**특징:**
- 매우 큰 데이터셋 (100만 건 이상)
- 페이징 필수
- 메모리 효율 중요

#### 5. 표준지 공시지가

**개요:**
- 대표 토지의 공시지가

**데이터셋ID:** 15012017

#### 6. 건축물 정보

**개요:**
- 전국 건축물의 기본 정보

**데이터셋ID:** 15100575

**주요 필드:**
```
• 건축물번호
• 건물용도
• 건축면적, 연면적
• 건축년도
• 주소
• 주용도, 부용도
```

#### 7. 주택가격동향조사

**개요:**
- 월별 조사된 주택가격 동향

**데이터셋ID:** 15100569

**특징:**
- 통계청의 공식 조사
- 신뢰도 높음

#### 8~10. 기타 데이터셋

```
• 지가변동률
• 토지이용규제정보
• 건설기성 통계
```

---

## 한국부동산원 데이터

### 주요 통계 리포트

#### 1. 주간 아파트 동향 (Weekly)

**URL:** https://www.kab.co.kr/stat/statView.do?menukey=60&statkey=60131

**특징:**
- 매주 목요일 업데이트
- 전국 아파트 시장 종합 분석
- PDF 형식 제공

**주요 내용:**
```
• 전국 아파트 평균가격
• 지역별 가격 현황
• 거래량 분석
• 주간 변화율
• 시장 전망
```

#### 2. 아파트 가격지수 (Monthly)

**URL:** https://www.kab.co.kr/stat/statView.do?menukey=60&statkey=60109

**특징:**
- 월 1회 업데이트
- Excel 다운로드 가능
- 기준시점(2021년 1월=100) 대비 변화

**수집 가능 지역:**
```
• 전국
• 서울
• 경기/인천
• 지방 (6대 광역시 등)
```

#### 3. 오피스 시장 통계 (Quarterly)

**URL:** https://www.kab.co.kr/stat/statView.do?menukey=60&statkey=60202

**주요 지역:**
```
• 서울 강남, 여의도, 강북
• 지방 주요 도시
```

**측정 항목:**
```
• 공급면적
• 임차면적
• 공실면적/률
• 평균임차료
```

#### 4. 물류시설 시장

**URL:** https://www.kab.co.kr/stat/statView.do?menukey=60&statkey=60301

**특징:**
- 분기별 통계
- 대형 물류시설 중심

#### 5. 상가(소매용) 시장

**URL:** https://www.kab.co.kr/stat/statView.do?menukey=60&statkey=60602

**특징:**
- 분기별 업데이트
- 주요 상권 중심

#### 6. 주택시장 심리지수

**URL:** https://www.kab.co.kr/stat/statView.do?menukey=60&statkey=60401

**특징:**
- 월 1회 조사
- 소비자 심리 5점 척도

---

## API 설정 및 인증

### Step 1: Data.go.kr 회원가입

**1.1 웹사이트 접속**
```
URL: https://www.data.go.kr/
```

**1.2 회원가입**
```
1. 상단 "회원가입" 클릭
2. 일반회원 또는 기관회원 선택
3. 이메일 입력
4. 비밀번호 설정
5. 기본정보 입력 (이름, 전화번호 등)
6. 이메일 인증 완료
```

### Step 2: API 활용신청

**2.1 데이터셋 검색**
```
1. 상단 검색창에서 "부동산" 검색
2. "부동산 실거래 정보" 클릭
3. 데이터셋 상세 페이지 확인
```

**2.2 활용신청**
```
1. "활용신청" 버튼 클릭
2. 활용 목적 입력 (AVM 모델 개발)
3. 활용 예상일 설정 (3~6개월)
4. 신청 완료
5. 승인 대기 (보통 1~2시간)
```

**2.3 API 키 확인**
```
1. 마이페이지 접속
2. "나의 API 이용 현황" 클릭
3. 승인된 데이터셋 확인
4. API 키 버튼 클릭 → 복사
```

### Step 3: 개발계정 등록

**3.1 개발계정 생성**
```
1. 마이페이지 > "개발계정 관리"
2. "개발계정 추가" 클릭
3. 계정명 입력 (예: AVM_Development)
4. 설명 입력
5. 저장
```

**3.2 API 키 등록**
```
1. 생성된 개발계정 선택
2. "인증키" 섹션
3. API 키 입력
4. 저장
```

### Step 4: API 테스트

**4.1 Python에서 테스트**

```python
import requests
import json

# API 설정
api_key = 'YOUR_API_KEY_HERE'
url = 'https://apis.data.go.kr/6440000/budongsanservice/searchAPT'

# 요청 파라미터
params = {
    'serviceKey': api_key,
    'DEAL_YMD': '202406',
    'numOfRows': 10,
    '_returnType': 'json'
}

# API 호출
try:
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()

    data = response.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))

    if data['response']['header']['resultCode'] == '00':
        print(f"✅ 성공! {len(data['response']['body']['items'])}개 데이터 수신")
    else:
        print(f"❌ 오류: {data['response']['header']['resultMsg']}")

except Exception as e:
    print(f"❌ 요청 실패: {e}")
```

**4.2 cURL로 테스트**

```bash
curl -X GET "https://apis.data.go.kr/6440000/budongsanservice/searchAPT?serviceKey=YOUR_API_KEY&DEAL_YMD=202406&numOfRows=10&_returnType=json"
```

---

## 데이터 수집 방법

### 방법 1: Python API 수집 (자동화)

**준비 사항:**
```bash
pip install requests pandas
```

**기본 예제:**

```python
import requests
import pandas as pd
from datetime import datetime, timedelta

def collect_real_estate_data(api_key, start_month, end_month):
    """
    부동산 실거래 데이터 수집
    """
    all_data = []
    base_url = 'https://apis.data.go.kr/6440000/budongsanservice/searchAPT'

    current = datetime.strptime(start_month, '%Y%m')
    end = datetime.strptime(end_month, '%Y%m')

    while current <= end:
        month = current.strftime('%Y%m')
        print(f"수집 중: {month}")

        params = {
            'serviceKey': api_key,
            'DEAL_YMD': month,
            'numOfRows': 100,
            'pageNo': 1,
            '_returnType': 'json'
        }

        try:
            response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            if data['response']['header']['resultCode'] == '00':
                items = data['response']['body'].get('items', [])
                all_data.extend(items)
                print(f"  ✅ {len(items)}개 수집")

        except Exception as e:
            print(f"  ❌ 오류: {e}")

        # 다음 달
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)

        time.sleep(0.5)  # API 호출 제한 준수

    # DataFrame으로 변환 및 저장
    df = pd.DataFrame(all_data)
    df.to_csv(f'real_estate_data_{start_month}_{end_month}.csv',
              index=False, encoding='utf-8')

    print(f"\n✅ 총 {len(df)}개 데이터 저장 완료")
    return df

# 사용
api_key = 'YOUR_API_KEY'
data = collect_real_estate_data(api_key, '202401', '202406')
```

### 방법 2: Web Scraping (한국부동산원)

```python
import requests
from bs4 import BeautifulSoup
import pandas as pd

def scrape_apartment_price_index():
    """
    아파트 가격지수 스크래핑
    """
    url = 'https://www.kab.co.kr/stat/statView.do?menukey=60&statkey=60109'

    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    # 테이블 찾기
    table = soup.find('table', {'class': 'tbl_basic'})

    if table:
        # Pandas로 테이블 파싱
        df = pd.read_html(str(table))[0]
        df.to_csv('apartment_price_index.csv', index=False, encoding='utf-8')
        print(f"✅ {len(df)}개 행 수집 완료")
        return df
    else:
        print("❌ 테이블을 찾을 수 없습니다")
        return None

# 사용
data = scrape_apartment_price_index()
```

### 방법 3: 파일 다운로드 (수동)

**한국부동산원 데이터:**

```
1. 원하는 통계 페이지 접속
2. "다운로드" 또는 "엑셀" 버튼 클릭
3. 파일 저장
4. Python으로 읽기
```

**Python 읽기:**

```python
import pandas as pd

# Excel 파일 읽기
df = pd.read_excel('apartment_price_index.xlsx')

# CSV로 변환
df.to_csv('apartment_price_index.csv', index=False, encoding='utf-8')

print(f"✅ {len(df)}개 행 로드 완료")
```

---

## 데이터 정제 및 통합

### Step 1: 데이터 로드

```python
import pandas as pd
import numpy as np
from glob import glob

# 모든 CSV 파일 로드
csv_files = glob('data/raw/*.csv')
dfs = [pd.read_csv(f) for f in csv_files]

print(f"로드된 파일 수: {len(dfs)}")
for i, df in enumerate(dfs):
    print(f"  {i+1}. {df.shape} - {csv_files[i]}")
```

### Step 2: 데이터 병합

```python
# 모든 데이터 통합
combined_df = pd.concat(dfs, ignore_index=True)
print(f"통합 데이터: {combined_df.shape}")

# 저장
combined_df.to_csv('data/raw/combined_real_estate_data.csv',
                    index=False, encoding='utf-8')
```

### Step 3: 데이터 정제

```python
# 결측값 처리
print(f"결측값:\n{combined_df.isnull().sum()}")
combined_df.fillna(combined_df.mean(), inplace=True)

# 중복값 제거
print(f"중복 전: {len(combined_df)}")
combined_df.drop_duplicates(inplace=True)
print(f"중복 후: {len(combined_df)}")

# 데이터 타입 변환
combined_df['거래가격'] = pd.to_numeric(combined_df['거래가격'],
                                         errors='coerce')
combined_df['거래일자'] = pd.to_datetime(combined_df['거래일자'],
                                          format='%Y%m%d')

# 이상값 제거 (거래가격이 음수인 경우)
combined_df = combined_df[combined_df['거래가격'] > 0]

print(f"정제 완료: {combined_df.shape}")
```

### Step 4: 파생 특성 생성

```python
# 건물 나이
combined_df['건물_나이'] = 2026 - combined_df['건축년도']

# 거래가격 범주화
combined_df['가격_범주'] = pd.cut(combined_df['거래가격'],
                                   bins=[0, 500000000, 1000000000, np.inf],
                                   labels=['저가', '중가', '고가'])

# 저장
combined_df.to_csv('data/processed/processed_real_estate_data.csv',
                    index=False, encoding='utf-8')
```

---

## 자동화 및 스케줄링

### Cron Job (Linux/Mac)

```bash
# crontab 편집
crontab -e

# 매월 첫 주 목요일 10시에 데이터 수집 실행
0 10 * * 4 cd /path/to/avm_project && python scripts/data_collection_handler.py
```

### Windows Task Scheduler

```
1. 작업 스케줄러 열기
2. "기본 작업 만들기"
3. 이름: "AVM 데이터 수집"
4. 트리거: 월 1회 (매월 7일 10:00)
5. 작업: python scripts/data_collection_handler.py
6. 저장
```

---

## 실행 예제

### 예제 1: 기본 데이터 수집

```bash
# 스크립트 실행
cd avm_project
python scripts/data_collection_handler.py
```

**출력:**
```
========================================
AVM 프로젝트 - 한국 부동산 데이터 수집
========================================

📊 데이터 소스 요약:
✅ Data.go.kr: 10개 데이터셋
✅ 한국부동산원: 8개 리포트
✅ 추가 공공 데이터

📋 다음 단계:
1. API 키 발급
2. 데이터 수집
3. 데이터 통합
4. 모델 학습에 활용
```

### 예제 2: API 키를 사용한 수집

```python
from avm_project.scripts.data_collection_handler import KoreanRealEstateDataCollector

# 수집기 초기화
collector = KoreanRealEstateDataCollector(api_key='YOUR_API_KEY')

# 부동산 실거래 데이터 수집
df_transaction = collector.collect_real_estate_transaction_data(
    start_date='202401',
    end_date='202406'
)

# 전월세 데이터 수집
df_jeonse = collector.collect_jeonse_data(
    start_date='202401',
    end_date='202406'
)

# 공시지가 수집
df_land_price = collector.collect_land_price_data(target_year='2024')

print(f"수집된 거래 데이터: {len(df_transaction)}개")
print(f"수집된 전월세: {len(df_jeonse)}개")
print(f"수집된 지가: {len(df_land_price)}개")
```

### 예제 3: 데이터 통합 및 정제

```python
# 데이터 병합
import pandas as pd

df_combined = pd.concat([df_transaction, df_jeonse], ignore_index=True)

# 정제
df_combined.dropna(inplace=True)
df_combined.drop_duplicates(inplace=True)

# 저장
df_combined.to_csv('avm_project/data/processed/final_real_estate_data.csv',
                    index=False, encoding='utf-8')

print(f"최종 데이터: {df_combined.shape}")
```

---

## 예상 데이터 규모

### 저장 공간 요구사항

| 데이터셋 | 월간 규모 | 연간 규모 | 누적 (3년) |
|---------|---------|---------|-----------|
| 실거래 정보 | 20-30MB | 240-360MB | 720-1,080MB |
| 전월세 정보 | 5-10MB | 60-120MB | 180-360MB |
| 공시지가 | 50-100MB | 50-100MB | 150-300MB |
| 기타 통계 | 10-20MB | 120-240MB | 360-720MB |
| **합계** | **85-160MB** | **470-820MB** | **1.4-2.5GB** |

### 수집 소요 시간

```
API 기반 수집 (자동): 1주일 (월별 처리)
스크래핑 기반: 2-3시간 (수동 다운로드)
정제 및 통합: 1-2시간
총 소요 시간: 약 1-2주
```

---

## 주의사항

### 1. 데이터 이용 약관

```
✅ 공공데이터이므로 자유롭게 활용 가능
✅ 상업 목적 사용 가능
⚠️ 출처 표시 필수
⚠️ API 이용약관 준수
```

### 2. API 호출 제한

```
• Data.go.kr:
  - 초당 10 요청
  - 일 10,000 요청
  - 월 무제한

• 한국부동산원:
  - 과도한 크롤링 금지
  - robots.txt 준수 필수
  - 웹서버 부하 고려
```

### 3. 데이터 업데이트 주기

```
• 실거래 정보: 월 1회 (해당월 거래 정보)
• 공시지가: 연 1회 (7월)
• 통계 리포트: 주/월/분기별
```

---

## 다음 단계

1. **데이터 수집 (즉시)**
   - API 키 발급
   - 초기 데이터 수집
   - 데이터 검증

2. **데이터 저장 (1주)**
   - 데이터베이스 구축
   - 효율적인 저장 구조 설계

3. **데이터 분석 (2주)**
   - EDA 수행
   - 패턴 발견
   - 피처 엔지니어링

4. **모델 학습 (3주)**
   - 머신러닝 모델 개발
   - 성능 평가
   - 최적화

---

**문서 작성자:** AI Development Team  
**최종 업데이트:** 2026-06-09  
**버전:** 1.0  

관련 파일:
- `scripts/korean_real_estate_data_sources.py` - 데이터 소스 정보
- `scripts/data_collection_handler.py` - 수집 핸들러

---

## 부록: 실거래 통합 수집 CLI (2026-09-08 추가, 권장)

주거용(아파트·다세대·오피스텔)·공장/창고·상업업무용·토지 실거래를 한 번에
수집해 `comparable_sales` 테이블에 적재하고, 바로 Loan4U 스타일 엑셀로
내보내는 오케스트레이터다.

```bash
# .env 에 DATAGOVKR_DECODING_KEY (또는 KOREA_API_KEY 등) 설정 후
python scripts/collect_all_transactions.py --sgg 11680 11650 --year 2025 --month 12 --debug
python scripts/collect_all_transactions.py --sgg 11680 --year 2025 --month 12 \
    --types land commercial --export loan4u_upload.xlsx
```

| 옵션 | 의미 |
|---|---|
| `--sgg` | 법정동코드 5자리, 여러 개 가능 (`app/integrations/sgg_codes.py`) |
| `--types` | `residential industrial commercial land` 중 선택 (기본 전부) |
| `--export PATH` | 수집 후 DB 전체를 자산 유형별 시트의 엑셀로 내보냄 |
| `--debug` | 원본 XML 응답을 로그로 남김 — **첫 실행 시 필수** |

동작 원칙:
- 한 유형의 API 실패는 그 유형만 `호출실패`로 집계되고 나머지는 계속 수집된다.
- 재실행해도 같은 거래는 `transaction_key` 로 걸러져 두 번 쌓이지 않는다.
- 토지 서비스 코드(`RTMSDataSvcLandTrade`)와 4개 유형의 응답 필드 태그명은
  라이브 미검증이다 — `docs/LIMITATIONS.md` §8, §12 참고. 오류 응답이 나면
  data.go.kr 마이페이지의 활용신청 내역에서 서비스명을 확인해
  `app/integrations/korea_api_land.py` 의 `SERVICE` 상수를 맞춘다.

유형별 단독 실행 스크립트: `fetch_transactions_parallel.py`(주거용, 병렬·체크포인트),
`fetch_industrial_transactions.py`, `fetch_commercial_transactions.py`,
`fetch_land_transactions.py`. 엑셀만 다시 내보내려면
`export_comparable_sales_excel.py --out 파일명.xlsx`.
