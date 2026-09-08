# 기술적 부채 해결 계획

## 1단계: 코드 품질 리팩토링 (우선순위 높음)

### A. 함수 크기 감소 (357→50줄 목표)
**대상**: `scripts/data_collection_handler.py::generate_data_collection_guide`
- 현재: 357줄 (매우 위험)
- 목표: 50줄 이하의 헬퍼 함수 분리
- 영향: 중핵심 데이터 수집 로직

**대상들 (우선순위)**:
1. `data_collection_handler.py::generate_data_collection_guide` (357줄)
2. `phase_c_step2_validate_and_preprocess.py::validate_and_preprocess` (183줄)
3. `phase_c_step3_retrain_models.py::retrain_models` (175줄)
4. `phase_c_step0_complete_integration.py::phase_c_step0_complete` (192줄)

### B. Type Hints 추가 (38%→100% 목표)
**대상**: `scripts/api_server.py` (현재 38% 커버리지)
- 수정 방침: 모든 함수에 반환타입 명시
- 변수 타입도 함수 인자에 완전 명시

## 2단계: 테스트 커버리지 개선

### A. Unit Test 추가
- 기존: 45개 (Phase 13.1-GBL만)
- 목표: 각 주요 모듈별 최소 5개 테스트
- 순서: 
  1. `api_server.py` 
  2. `data_collection_handler.py`
  3. `validate_real_estate_data.py`

### B. Integration Test 추가
- API 엔드포인트 통합 테스트
- 데이터 파이프라인 E2E 테스트

## 3단계: 의존성 정리

### A. requirements.txt 정리
- 사용하지 않는 패키지 제거
- 버전 핀닝 (모든 패키지 == 지정)
- 순환 의존성 확인

### B. 보안 업데이트
- CVE 스캔 (bandit, safety)
- 최신 버전 확인

## 4단계: 문서화 개선

### A. API 문서
- OpenAPI/Swagger 스펙 생성
- 엔드포인트별 예제 추가

### B. 개발자 가이드
- 새로운 모듈 추가 가이드
- 테스트 작성 템플릿

## 예상 효과

| 메트릭 | 현재 | 목표 | 개선도 |
|--------|------|------|--------|
| 함수 평균 크기 | ~100줄 | ~30줄 | 70% |
| Type Hints | 60% | 100% | +40% |
| 테스트 커버리지 | 45개 | 150+ | +233% |
| 순환 복잡도 | 높음 | 낮음 | 감소 |

## 일정
- 1단계 (리팩토링): 2-3시간
- 2단계 (테스트): 2시간
- 3단계 (의존성): 30분
- 4단계 (문서): 1시간
- **총**: ~6-7시간

---
**상태**: 계획 수립 완료, 실행 대기
**우선순위**: 1단계부터 순차 실행
