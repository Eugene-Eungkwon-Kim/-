# NPL AVM 사용자 가이드

**버전**: 1.0.0  
**최종 업데이트**: 2026-06-09  
**대상**: 부동산 감정사, NPL 펀드매니저, 데이터 분석가

---

## 📖 목차

1. [빠른 시작](#빠른-시작)
2. [주요 기능](#주요-기능)
3. [시나리오별 사용](#시나리오별-사용)
4. [FAQ](#faq)
5. [트러블슈팅](#트러블슈팅)

---

## 빠른 시작

### 1단계: API 키 발급 (2분)

1. NPL AVM 포털 접속: https://portal.npl-avm.example.com
2. 로그인 (회사 계정)
3. "API 관리" 메뉴 → "새 API 키 발급"
4. 키 복사 (재표시 불가능하므로 안전하게 보관)

### 2단계: 환경 설정 (1분)

```bash
# macOS / Linux
echo 'export NPL_API_KEY="sk_prod_xxx"' >> ~/.bashrc
source ~/.bashrc

# Windows PowerShell
[Environment]::SetEnvironmentVariable("NPL_API_KEY","sk_prod_xxx")
```

### 3단계: 첫 요청 실행 (1분)

```bash
curl -X GET https://api.npl-avm.example.com/api/v1/health \
  -H "X-API-Key: $NPL_API_KEY"

# 응답
# {"status": "healthy", ...}
```

✅ **완료! 이제 물건 감정가를 추정할 수 있습니다.**

---

## 주요 기능

### 1. 단일 물건 감정가 추정

**사용 시나리오**: 하나의 물건을 빠르게 평가해야 할 때

**특징**:
- ⏱️ 응답시간: < 2초
- 🎯 정확도: R² 0.8721 (2021 대비 +40% 개선)
- 📊 신뢰도 구간: 95% 신뢰도로 범위 제공
- 🔍 비교사례: 자동 매칭된 5개 사례

**요청**:
```bash
curl -X POST https://api.npl-avm.example.com/api/v1/estimate \
  -H "X-API-Key: $NPL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "land_area_sqm": 125.5,
    "building_area_sqm": 95.3,
    "building_age": 5,
    "property_type": "아파트",
    "location_sido": "서울",
    "location_sigungu": "강남구"
  }'
```

**응답 해석**:
```json
{
  "estimated_price": 850000000,              ← 추정가 (원화)
  "price_per_sqm": 8921053,                  ← 단위가격 (원/㎡)
  "confidence_score": 0.87,                  ← 신뢰도 (0-1)
  "confidence_interval": {
    "lower_bound": 765000000,                ← 95% 신뢰도 하한
    "upper_bound": 935000000                 ← 95% 신뢰도 상한
  },
  "comparable_properties": [                 ← 비교사례 5건
    {
      "address": "서울 강남구 테헤란로 123",
      "price": 820000000,
      "similarity_score": 0.92,               ← 유사도 (0-1)
      "transaction_date": "2026-03-15"
    },
    ...
  ]
}
```

### 2. 배치 감정 (대량 처리)

**사용 시나리오**: 100건 이상의 물건을 일괄 평가해야 할 때

**특징**:
- 📦 최대 1,000건까지 한 번에 요청
- ⏱️ 처리시간: 100건 약 2분
- 🔄 비동기 처리 (작업 ID로 추적)
- 📥 결과 CSV 다운로드 가능

**요청**:
```bash
curl -X POST https://api.npl-avm.example.com/api/v1/batch-estimate \
  -H "X-API-Key: $NPL_API_KEY" \
  -H "Content-Type: application/json" \
  -d @properties.json
```

`properties.json` 형식:
```json
{
  "properties": [
    {
      "land_area_sqm": 125.5,
      "building_area_sqm": 95.3,
      "building_age": 5,
      "property_type": "아파트",
      "location_sido": "서울"
    },
    {
      "land_area_sqm": 250.0,
      "building_area_sqm": 180.0,
      "building_age": 10,
      "property_type": "주택",
      "location_sido": "경기"
    }
  ]
}
```

**응답 추적**:
```bash
# Job ID로 진행 상황 확인
curl -X GET "https://api.npl-avm.example.com/api/v1/batch-estimate/job_abc123" \
  -H "X-API-Key: $NPL_API_KEY"

# 응답
{
  "status": "processing",   # queued, processing, completed, failed
  "progress": 45,            # 0-100%
  "estimated_completion_time": "2026-06-09T10:32:00Z"
}
```

### 3. 비교사례 자동 매칭

**사용 시나리오**: 특정 물건과 유사한 거래 사례를 찾아야 할 때

**매칭 기준**:
- 물건 유형 (동일)
- 지역 (동일 지역)
- 건물 연령 (±5년)
- 면적 (±10%)

**요청**:
```bash
curl -X POST https://api.npl-avm.example.com/api/v1/compare \
  -H "X-API-Key: $NPL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": "prop_001",
    "count": 5,
    "date_range": {
      "from": "2025-06-09",
      "to": "2026-06-09"
    }
  }'
```

---

## 시나리오별 사용

### 시나리오 1: 감정사 (일일 20건 평가)

**목표**: 하루 20건의 물건을 빠르게 평가

**표준 프로세스**:
```
1. 물건 기본 정보 입력 (30초)
   └─ 면적, 건물연령, 위치 등

2. 감정가 요청 (2초)
   └─ POST /estimate

3. 결과 검토 (1분)
   └─ 추정가, 신뢰도, 비교사례 확인

4. 필요시 조정 (30초)
   └─ 신뢰도 낮으면 비교사례 추가 조회

총 시간: 약 2분/건 (기존 10분 → 80% 단축)
```

**Python 예제**:
```python
import requests
import os

API_KEY = os.getenv('NPL_API_KEY')
BASE_URL = 'https://api.npl-avm.example.com/api/v1'

def estimate_and_report(properties):
    """20건 물건 배치 처리"""
    headers = {'X-API-Key': API_KEY}
    
    results = []
    for prop in properties:
        response = requests.post(
            f'{BASE_URL}/estimate',
            json=prop,
            headers=headers
        )
        result = response.json()
        results.append({
            'address': prop.get('location_sigungu', 'Unknown'),
            'estimated_price': result['estimated_price'],
            'confidence': result['confidence_score'],
            'comparable_count': len(result['comparable_properties'])
        })
        print(f"✅ {prop['location_sigungu']}: ₩{result['estimated_price']:,}")
    
    return results

# 사용
properties = [
    {'land_area_sqm': 125.5, ...},
    {'land_area_sqm': 150.0, ...},
    ...
]

results = estimate_and_report(properties)
```

### 시나리오 2: NPL 펀드매니저 (월간 100건 평가)

**목표**: 월간 100개 물건의 일괄 평가

**표준 프로세스**:
```
1. 데이터 준비 (30분)
   └─ Excel → JSON 변환

2. 배치 요청 (1분)
   └─ POST /batch-estimate (100건)

3. 진행 상황 모니터링 (2분)
   └─ GET /batch-estimate/{job_id} 주기적 확인

4. 결과 분석 (30분)
   └─ 신뢰도별 분류
   └─ 평균가격 계산
   └─ 지역별 분석

총 시간: 약 1시간 (기존 10시간 → 90% 단축)
```

**Excel 연동**:
```excel
=IFERROR(IMPORTDATA(
  "https://api.npl-avm.example.com/api/v1/batch-estimate",
  {"X-API-Key": $A$1}
), "처리 중...")
```

### 시나리오 3: 데이터 분석가 (월간 3개 리포트)

**목표**: 시장 분석 리포트 작성

**표준 프로세스**:
```
1. 데이터 추출 (5분)
   └─ /batch-estimate로 대량 추정가 생성

2. 분석 쿼리 (10분)
   └─ 지역별, 물건유형별 통계

3. 시각화 (20분)
   └─ Grafana 대시보드 생성

4. 리포트 작성 (30분)
   └─ Markdown → PDF 변환

총 시간: 약 1시간 (기존 12시간 → 92% 단축)
```

---

## FAQ

### Q1: 추정가는 정확한가요?

**A:** NPL AVM의 성능:
- **R² 0.8721**: 87.2%의 가격 변동 설명 가능
- **MAPE 19.56%**: 평균 오차 약 20% (±10%)
- **신뢰도 구간**: 95% 신뢰도로 상/하한 제공

**참고**: 
- 신뢰도 < 0.80 → 비교사례 추가 확인 권장
- 특수 목적 물건(병원, 학교 등) → 전문가 판단 권장

---

### Q2: 어떤 물건 유형을 지원하나요?

**A:** 현재 지원하는 유형:
- ✅ 아파트 (가장 정확)
- ✅ 주택
- ✅ 오피스
- ✅ 상업용
- ✅ 공업용
- ✅ 토지

**지원되지 않음**:
- ❌ 병원, 학교 등 특수 건물
- ❌ 문화재
- ❌ 산림

---

### Q3: API 응답이 느립니다. 원인이 무엇인가요?

**A:** 일반적인 응답 시간:
- 단일 요청: < 2초
- 배치 요청: 100건 약 2분

**느린 경우 확인사항**:
1. 네트워크 연결 (ping api.npl-avm.example.com)
2. 서버 상태: `curl /api/v1/health`
3. 모델 로드: `curl /api/v1/ready`
4. 지역 캐시 서버 상태

---

### Q4: 배치 처리 중 일부가 실패했습니다.

**A:** 배치 처리 결과:
```json
{
  "status": "partial_success",
  "successful_count": 95,
  "failed_count": 5,
  "errors": [
    {
      "index": 3,
      "error": "Invalid property_type: 병원"
    }
  ]
}
```

**해결 방법**:
1. 에러 항목 확인
2. 데이터 수정 (property_type, 필수 필드 등)
3. 재요청

---

### Q5: 신뢰도가 낮으면 어떻게 하나요?

**A:** 신뢰도 < 0.80인 경우:

1. **비교사례 확인**:
   ```bash
   curl POST /compare -d '{"property_id": "...", "count": 10}'
   ```

2. **특수 요인 검토**:
   - 위치 (강남역 근처 등)
   - 조망 (한강, 공원 등)
   - 시설 (대형 쇼핑몰 인근 등)

3. **전문가 판단**:
   - 신뢰도 < 0.70 → 전문가 현장 확인 권장

---

### Q6: 이전 거래가와 차이가 많이 납니다.

**A:** 차이의 원인:

1. **시간 경과**: 시장 변동 (± 5-10%/년)
2. **물건 상태**: 리모델링, 노후도 변화
3. **시장 조건**: 금리, 경기 변동
4. **데이터 품질**: 거래가 데이터의 신뢰도

**확인 방법**:
```bash
# 비교사례 조회
curl POST /compare -d '{"property_id": "...", "date_range": {"from": "2025-01-01"}}'
```

---

### Q7: 데이터 개인정보는 안전한가요?

**A:** 보안 조치:
- 🔐 HTTPS 암호화 (TLS 1.3)
- 🔑 API 키 기반 인증
- 🛡️ 데이터 즉시 삭제 (분석 후 24시간)
- ✅ GDPR, CCPA 준수
- 🔍 감시 및 모니터링

**정보 정책**:
- 물건 주소: 분석에만 사용, 저장 안 함
- 거래가: 모델 학습에만 사용
- 개인정보: 수집 안 함

---

### Q8: API 사용 비용은?

**A:** 가격 정책:
```
무료: 월 100건 (테스트용)
Pro: ₩99,000/월 (월 1,000건)
Enterprise: 별도 문의 (무제한)
```

**청구**:
- 실제 사용량 기반
- 월간 청구서 발급
- 신용카드, 계약금 지원

---

### Q9: 문제가 있으면 어디로 연락하나요?

**A:** 지원 채널:

| 채널 | 응답시간 | 대상 |
|------|---------|------|
| 📧 support@npl-avm.example.com | < 4시간 | 일반 문의 |
| 💬 Slack (paid plan) | < 1시간 | Pro/Enterprise |
| 📞 1588-**** | 수시 | 긴급 (가입자만) |

---

### Q10: 더 많은 기능이 필요합니다.

**A:** 향후 계획 (2026-H2):
- [ ] 다중 물건 비교 (A vs B)
- [ ] 시계열 분석 (가격 추이)
- [ ] 포트폴리오 분석
- [ ] 자동 리포트 생성
- [ ] Webhook 지원
- [ ] 사용자 정의 모델

**기능 요청**: [Feature Request Form](https://forms.npl-avm.example.com)

---

## 트러블슈팅

### 문제: "401 Unauthorized"

**원인**: API 키가 잘못되었거나 없음

**해결**:
```bash
# 1. API 키 확인
echo $NPL_API_KEY

# 2. 올바른 형식인지 확인
# sk_prod_... (프로덕션)
# sk_test_... (테스트)

# 3. 환경 변수 재설정
export NPL_API_KEY="sk_prod_xxx"

# 4. 재시도
curl -H "X-API-Key: $NPL_API_KEY" /api/v1/health
```

---

### 문제: "400 Bad Request"

**원인**: 요청 형식이 잘못됨

**확인 사항**:
```bash
# 1. JSON 형식 검증
echo '{"land_area_sqm": 125.5, ...}' | jq .

# 2. 필수 필드 확인
# - land_area_sqm (필수)
# - building_area_sqm (필수)
# - property_type (필수)
# - location_sido (필수)

# 3. 데이터 타입 확인
# - 숫자: "125.5" → 125.5
# - 문자: 앞뒤 따옴표 포함
```

---

### 문제: "429 Too Many Requests"

**원인**: API 요청 제한 초과

**한도**:
- 무료: 100건/월
- Pro: 1,000건/월
- Enterprise: 무제한

**해결**:
```bash
# 1. 요청 간격 조정 (1초 이상)
sleep 1
curl ...

# 2. 배치 처리 사용
# 단일 요청 20개 → 배치 요청 1개

# 3. 플랜 업그레이드
# https://portal.npl-avm.example.com/billing
```

---

### 문제: "500 Internal Server Error"

**원인**: 서버 오류 (드물지만 발생할 수 있음)

**임시 조치**:
```bash
# 1. 몇 초 후 재시도
sleep 5
curl ...

# 2. 지역 캐시 서버로 재시도
# api-kr.npl-avm.example.com
# api-jp.npl-avm.example.com

# 3. 지속되면 지원팀 연락
curl "https://support.npl-avm.example.com/incidents"
```

---

## 다음 단계

**추천 문서**:
- 📖 [API 상세 가이드](./API_GUIDE.md)
- 🔧 [운영 가이드](./OPERATIONS_GUIDE.md)
- 💾 [OpenAPI 스펙](./openapi-spec.yaml)

**학습 자료**:
- 📺 [비디오 튜토리얼](https://youtube.npl-avm.example.com) (5개, 3분씩)
- 📝 [기술 블로그](https://blog.npl-avm.example.com)
- 🎯 [케이스 스터디](https://case-studies.npl-avm.example.com)

---

**버전**: 1.0.0  
**최종 업데이트**: 2026-06-09  
**다음 업데이트**: 2026-09-09
