# TechDebt 코드 품질 개선 상세 계획

**담당**: 개발자 3 (1명)  
**기간**: 2026-07-24 ~ 2026-08-13 (21일, 실제 작업 7일)  
**목표**: Type hints 추가, 테스트 강화, 배포 전 안정성 확보  

---

## 📋 기본 정보

### 개선 대상 모듈

**Tier 1 (필수, 1일)**: 
- `avm_project/scripts/api_server.py`
- `avm_project/scripts/data_collection_handler.py`

**Tier 2 (권장, 4일)**:
- `avm_project/scripts/` 테스트 강화
- 반복 코드 제거
- Docstring 완성

### 코딩 기준 (CODING_STANDARDS.md)
```
✓ 함수 크기: ≤50줄 (최대 100줄 정당화)
✓ Type hints: 100% 
✓ Docstring: Args/Returns/Raises 완전
✓ 주석: WHY만 (WHAT 제거)
✓ Import: 표준→서드파티→로컬 순서
```

---

## 📅 Tier 1: 즉시 개선 (1일, 2026-07-24)

### Step 1: api_server.py Type Hints (40분)

**목표**: 모든 함수에 type hints 추가

```python
# 현재 상태 (개선 전)
def validate_request(request):
    """Request 검증"""
    if 'data' not in request:
        return False
    return True

# 개선 후
def validate_request(request: Dict[str, Any]) -> bool:
    """Request 검증
    
    Args:
        request: HTTP 요청 딕셔너리
        
    Returns:
        bool: 검증 성공 여부
    """
    if 'data' not in request:
        return False
    return True
```

**작업 체크리스트**:
- [ ] 함수 목록 추출 (MyPy 스캔)
- [ ] 각 함수에 입력/반환 타입 추가
- [ ] 변수 타입 명시 (Union, Optional 등)
- [ ] Import 추가 (typing 모듈)
- [ ] MyPy 검증 (0 error)

**예상 함수 수**: 30~40개  
**예상 시간**: 40분

**산출물**:
- 개선된 `api_server.py`
- `MYPY_VALIDATION_REPORT.txt`

---

### Step 2: data_collection_handler.py 함수 분해 (30분)

**목표**: 큰 함수를 <50줄 단위로 분해

```python
# 현재 상태 (개선 전, ~200줄)
def generate_data_collection_guide(config):
    """데이터 수집 가이드 생성 - 긴 함수"""
    # ... 50줄
    if condition1:
        # ... 50줄
    if condition2:
        # ... 50줄
    if condition3:
        # ... 50줄
    return result

# 개선 후 (함수 분해)
def generate_data_collection_guide(config: Dict) -> str:
    """데이터 수집 가이드 생성"""
    guidance = ""
    guidance += _prepare_header(config)
    guidance += _collect_core_info(config)
    guidance += _collect_optional_info(config)
    guidance += _add_footer()
    return guidance

def _prepare_header(config: Dict) -> str:
    """헤더 준비 (<50줄)"""
    # ...

def _collect_core_info(config: Dict) -> str:
    """핵심 정보 수집 (<50줄)"""
    # ...

def _collect_optional_info(config: Dict) -> str:
    """선택 정보 수집 (<50줄)"""
    # ...

def _add_footer() -> str:
    """푸터 추가 (<50줄)"""
    # ...
```

**작업 체크리스트**:
- [ ] 함수 크기 분석 (>50줄 찾기)
- [ ] 헬퍼 함수 추출
- [ ] 각 함수 type hints 추가
- [ ] 함수 간 의존성 확인
- [ ] 테스트 각 함수별 작성

**예상 함수 분해**: 3~5개  
**예상 시간**: 30분

**산출물**:
- 개선된 `data_collection_handler.py`
- `FUNCTION_REFACTORING_REPORT.md`

---

### Step 3: 기본 단위 테스트 작성 (20분)

**목표**: 각 모듈 기본 단위 테스트 10개

```python
# tests/test_api_server_basic.py
import pytest
from avm_project.scripts.api_server import validate_request, process_data

class TestApiServerBasic:
    """api_server.py 기본 테스트"""
    
    def test_validate_request_valid(self) -> None:
        """유효한 요청 검증"""
        request = {'data': {'key': 'value'}}
        assert validate_request(request) is True
    
    def test_validate_request_invalid(self) -> None:
        """무효한 요청 검증"""
        request = {}
        assert validate_request(request) is False
    
    def test_validate_request_missing_data(self) -> None:
        """data 필드 누락"""
        request = {'other': 'value'}
        assert validate_request(request) is False
    
    def test_process_data_success(self) -> None:
        """데이터 처리 성공"""
        data = {'value': 100}
        result = process_data(data)
        assert result['status'] == 'success'
    
    # ... 5개 더

# tests/test_data_collection_basic.py
class TestDataCollectionBasic:
    """data_collection_handler.py 기본 테스트"""
    
    def test_generate_guide_basic(self) -> None:
        """기본 가이드 생성"""
        config = {'source': 'vworld'}
        guide = generate_data_collection_guide(config)
        assert len(guide) > 0
    
    # ... 4개 더
```

**작업 체크리스트**:
- [ ] 테스트 클래스 생성 (2개)
- [ ] 기본 케이스 테스트 (5개 × 2 = 10개)
- [ ] pytest 실행 및 검증
- [ ] 커버리지 확인 (>50%)

**예상 테스트 수**: 10개  
**예상 시간**: 20분

**산출물**:
- `tests/test_api_server_basic.py`
- `tests/test_data_collection_basic.py`
- `TIER1_TEST_REPORT.txt`

---

## 📅 Tier 2: 테스트 강화 (4일, 2026-07-31 ~ 08-03)

### Day 8-9 (07-31 ~ 08-01): api_server 테스트 45개 작성

**목표**: api_server.py 엔드포인트별 전체 테스트

```python
# tests/test_api_server_comprehensive.py
class TestApiServerEndpoints:
    """API 엔드포인트 전체 테스트"""
    
    class TestHealthCheck:
        """GET /health 엔드포인트"""
        def test_health_check_success(self) -> None: ...
        def test_health_check_response_format(self) -> None: ...
        def test_health_check_status_code(self) -> None: ...
    
    class TestDataValidation:
        """POST /validate 엔드포인트"""
        def test_validate_valid_data(self) -> None: ...
        def test_validate_invalid_data(self) -> None: ...
        def test_validate_empty_data(self) -> None: ...
        def test_validate_missing_fields(self) -> None: ...
        def test_validate_response_format(self) -> None: ...
    
    class TestDataProcessing:
        """POST /process 엔드포인트"""
        def test_process_single_record(self) -> None: ...
        def test_process_multiple_records(self) -> None: ...
        def test_process_batch_limit(self) -> None: ...
        # ... 10개 더
    
    class TestErrorHandling:
        """에러 처리 테스트"""
        def test_400_bad_request(self) -> None: ...
        def test_401_unauthorized(self) -> None: ...
        def test_403_forbidden(self) -> None: ...
        def test_404_not_found(self) -> None: ...
        def test_500_server_error(self) -> None: ...
        def test_503_service_unavailable(self) -> None: ...
    
    class TestPerformance:
        """성능 테스트"""
        def test_response_time_under_500ms(self) -> None: ...
        def test_concurrent_requests(self) -> None: ...
        def test_memory_usage_stable(self) -> None: ...
```

**테스트 분류**:
- 엔드포인트별 (5개 × 5 = 25개)
- 에러 처리 (6개)
- 성능 (3개)
- 통합 테스트 (11개)

**작업**:
- [ ] 테스트 케이스 45개 작성
- [ ] pytest 실행 및 모두 통과
- [ ] 커버리지 보고서 생성 (목표 >80%)

**예상 시간**: 2시간

**산출물**:
- `tests/test_api_server_comprehensive.py` (45개 테스트)
- `API_SERVER_COVERAGE_REPORT.html`

---

### Day 10 (08-02): data_collection 테스트 15개 작성

**목표**: data_collection_handler.py 함수별 테스트

```python
# tests/test_data_collection_comprehensive.py
class TestDataCollection:
    """데이터 수집 핸들러 테스트"""
    
    class TestHeaderCollection:
        """헤더 수집 테스트"""
        def test_prepare_header_basic(self) -> None: ...
        def test_prepare_header_with_config(self) -> None: ...
        def test_prepare_header_response_format(self) -> None: ...
    
    class TestCoreInfoCollection:
        """핵심 정보 수집 테스트"""
        def test_collect_core_info_vworld(self) -> None: ...
        def test_collect_core_info_all_fields(self) -> None: ...
        def test_collect_core_info_error_handling(self) -> None: ...
        def test_collect_core_info_pagination(self) -> None: ...
    
    class TestOptionalInfoCollection:
        """선택 정보 수집 테스트"""
        def test_collect_optional_basic(self) -> None: ...
        def test_collect_optional_with_filters(self) -> None: ...
        def test_collect_optional_empty_result(self) -> None: ...
        def test_collect_optional_performance(self) -> None: ...
    
    class TestFooterGeneration:
        """푸터 생성 테스트"""
        def test_add_footer_format(self) -> None: ...
        def test_add_footer_content(self) -> None: ...
        def test_add_footer_with_metadata(self) -> None: ...
    
    class TestIntegration:
        """통합 테스트"""
        def test_generate_full_guide(self) -> None: ...
        def test_generate_guide_error_recovery(self) -> None: ...
```

**작업**:
- [ ] 테스트 케이스 15개 작성
- [ ] pytest 실행 및 모두 통과
- [ ] 커버리지 보고서 생성 (목표 >70%)

**예상 시간**: 1시간

**산출물**:
- `tests/test_data_collection_comprehensive.py` (15개 테스트)
- `DATA_COLLECTION_COVERAGE_REPORT.html`

---

### Day 11 (08-03): 반복 코드 제거 및 Docstring 완성

**목표**: DRY 원칙 적용, 모든 함수 docstring 완성

```python
# 반복 코드 제거 예시
# 현재 (반복)
if 'name' in request and 'email' in request:
    process_user(request['name'], request['email'])
if 'phone' in request and 'address' in request:
    process_contact(request['phone'], request['address'])
if 'company' in request and 'position' in request:
    process_employment(request['company'], request['position'])

# 개선 (DRY)
def _process_field_group(
    request: Dict,
    field_names: List[str],
    processor: Callable
) -> None:
    """필드 그룹 처리"""
    if all(field in request for field in field_names):
        processor(*[request[f] for f in field_names])

_process_field_group(request, ['name', 'email'], process_user)
_process_field_group(request, ['phone', 'address'], process_contact)
_process_field_group(request, ['company', 'position'], process_employment)
```

**작업**:
- [ ] 반복 패턴 찾기 (3+ 줄 반복)
- [ ] 공통 로직 추출
- [ ] 모든 함수 docstring 추가 (Args/Returns)
- [ ] Black/isort 코드 포맷 정렬

**예상 시간**: 1시간

**산출물**:
- 개선된 `api_server.py` (반복 코드 -20%)
- 개선된 `data_collection_handler.py` (docstring 100%)

---

### Day 12-13 (08-04 ~ 08-05): 코드 리뷰 및 최종 검증

**목표**: 모든 개선사항 최종 검증

```
□ 정적 분석 검증
  - MyPy: 0 errors
  - Pylint: score >9.0
  - Black: format ok
  
□ 테스트 검증
  - api_server 45개 테스트 통과 ✓
  - data_collection 15개 테스트 통과 ✓
  - 기본 테스트 10개 통과 ✓
  - 총 70개 테스트 통과 ✓
  
□ 커버리지 검증
  - api_server.py: >80%
  - data_collection_handler.py: >70%
  - 전체: >75%
  
□ 성능 검증
  - 함수 크기: 모두 <50줄 ✓
  - 메모리 누수: 없음 ✓
  - 응답 시간: <500ms ✓
```

**작업**:
- [ ] 정적 분석 도구 실행
- [ ] 모든 테스트 통과 확인
- [ ] 커버리지 리포트 생성
- [ ] 코드 리뷰 및 승인

**예상 시간**: 2시간

**산출물**:
- `MYPY_VALIDATION_REPORT.txt`
- `PYLINT_VALIDATION_REPORT.txt`
- `TEST_COVERAGE_REPORT.html`
- `CODE_REVIEW_CHECKLIST.md`

---

## 🎯 완료 기준

### Tier 1 (필수)
```
✓ Type hints: 80% 이상 추가
✓ api_server.py: 모든 함수에 타입 추가
✓ data_collection_handler.py: 함수 분해 완료
✓ 기본 테스트: 10개 작성 및 통과
✓ MyPy: 0 errors
```

### Tier 2 (권장)
```
✓ api_server 테스트: 45개 모두 통과
✓ data_collection 테스트: 15개 모두 통과
✓ 테스트 커버리지: >75%
✓ 함수 크기: 모두 <50줄
✓ Docstring: 100% 완성
✓ 반복 코드 제거: DRY 원칙 적용
✓ 정적 분석: MyPy/Pylint 통과
```

---

## 📊 진도 관리

| 날짜 | 내용 | 목표 | 진도 |
|------|------|------|------|
| 07-24 | Tier 1 시작 | 1일 완료 | □ |
| 07-25 | - | - | - |
| 07-31 | api_server 테스트 | 45개 작성 | □□ |
| 08-01 | - | - | - |
| 08-02 | data_collection 테스트 | 15개 작성 | □ |
| 08-03 | DRY 원칙 + Docstring | - | □ |
| 08-04 | 코드 리뷰 시작 | - | □ |
| 08-05 | 최종 검증 | 모두 통과 | □ |
| 08-06 ~ 08-13 | Phase 13.3 병렬 지원 | - | - |

---

## 🔗 참고 자료

- [CODING_STANDARDS.md](D:\avm_work\.claude\CODING_STANDARDS.md)
- [Phase 13.1-GBL 참조](D:\avm_work\avm_project\scripts\country_configs.py)
- MyPy: https://mypy.readthedocs.io/
- Pylint: https://pylint.pycqa.org/
- Pytest: https://pytest.org/

---

**상태**: ✅ 준비 완료, 2026-07-24 시작  
**연락처**: eugene1108@gmail.com
