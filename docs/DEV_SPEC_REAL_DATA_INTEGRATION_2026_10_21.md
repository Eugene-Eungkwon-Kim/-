# 다음 개발 명세서 (2026-10-21)

**관계**: `docs/NEXT_WORK_SPEC_2026_10_21.md`(작업 단위 WP-1~3)가 "무엇을 할지"라면, 이 문서는 그중 **코드로 만들 부분**의 설계입니다.
**근거**: `avm_project/AVM_MODEL_EXPERIMENT_STATUS_2026_06_24.md`의 "실제 운영 통합 필요 작업" 체크리스트, 현재 코드(`avm_project/scripts/`, `app/integrations/`), `CLAUDE.md` 규칙
**코드 규칙(전 항목 공통)**: 함수 50줄 이하(복잡한 로직만 100줄), 타입 힌트 100%, 단일 책임, 3줄 이상 반복은 추출, 주석은 WHY만, 1작업 1커밋(`[Phase X.Y]` 형식)

---

## 0. 먼저 알아둘 것: 이미 있는 코드

코드를 확인해 보니 상당수가 이미 구현되어 있습니다. 아래는 **새로 만들지 않고 재사용**합니다.

| 필요한 기능 | 이미 있는 것 | 위치 | 이번 개발에서의 처리 |
|---|---|---|---|
| 드라이브 문자 순회 탐색 | `_candidate_roots`, `find_file` | `scripts/sync_from_external_drive.py` | 공용 모듈로 승격 (DEV-1) |
| 외장하드 감지 | `detect_external_drives` | `scripts/phase_c_step0_read_external_drive.py` | 공용 모듈 호출로 교체 |
| 데이터 루트 경로 | `DATA_ROOT` (기본값 `D:\loan4u_avm_data\...` 하드코딩) | `scripts/avm_paths.py` | 공용 모듈로 해석 (DEV-1) |
| 시간순 분할 | `temporal_split` | `scripts/temporal_split.py` | **재사용.** 같은 함수가 `phase_c_step3_retrain_models.py:32`에 중복 정의되어 있어 제거 (DEV-3) |
| 누수 감사 3종 | 상관 / 단일특성 제거 / 분할 격차 | `scripts/leakage_audit.py` | 재사용 + 그룹 중복 검사 1종 추가 (DEV-3) |
| 재시도·오류 분류 HTTP | `get_with_retry`, `TransientFetchError`, `AuthFetchError`, `SchemaFetchError` | `app/integrations/http_client.py` | 신규 수집기(DEV-4)가 그대로 사용 |
| 컬럼 표준화·누수 컬럼 검사 | `standardize_columns`, `check_leakage_columns` | `scripts/phase_c_step2_validate_and_preprocess.py` | 재사용, 검증 규칙만 확장 (DEV-2) |
| 예외 계층 | `DataValidationError`, `DataProcessingError` 등 | `scripts/exceptions.py` | 재사용, 필요 시 하위 클래스 1개 추가 |
| 보고서 텍스트 추출·섹션 분리 | `extract_text`, `split_sections` | `evaluation-report-analysis/report_analyzer.py` | DEV-4 보고서형 분기에서 재사용 검토 |

**정정**: 이전 명세서(`docs/NEXT_WORK_SPEC_2026_10_21.md`)에서 `data_path_config.py`도 하드코딩 경로라고 썼는데, 확인 결과 그 파일은 저장소 상대경로를 쓰고 있어 **하드코딩은 `avm_paths.py` 한 곳**입니다.

---

## DEV-1. 데이터 루트 경로 단일화 — `scripts/data_locator.py` (신규)

**[목표]** 외장하드 드라이브 문자가 바뀌어도(D: → E: 등) 코드 수정 없이 실데이터 위치를 찾고, 어느 경로가 어떤 근거로 선택됐는지 로그에 남긴다.

**[현황 문제]** 같은 목적의 탐색 로직이 3곳에 흩어져 있고(`avm_paths.py`, `sync_from_external_drive.py`, `phase_c_step0_read_external_drive.py`), 경로 하드코딩은 두 종류입니다.
- `avm_paths.py`가 `D:\loan4u_avm_data\...`를 기본값으로 가지며, 이를 임포트하는 파일이 7개입니다: `vworld_layer1/2_3/8_10/11_14_collector.py`(4), `address_to_pnu_converter.py`, `tier2_monitoring.py`, `vworld_api_key_validator.py`
- `avm_paths`를 거치지 않고 **`F:/loan4u_avm_data/loan4u_working_db/db/loan4u_rtms_comparable_mart.duckdb`를 직접 박은 파일 3개**: `phase7_grounded_avm.py:26`, `phase7_match_engine.py:27`, `phase7_c_address_parser_v2.py:21`. 같은 데이터가 D:와 F:로 서로 다르게 적혀 있어 드라이브 문자 혼선이 이미 코드에 드러나 있습니다

**[공개 인터페이스]**
```python
MARKER_DIRNAME = "loan4u_avm_data"
ENV_VAR = "AVM_DATA_PATH"

@dataclass(frozen=True)
class Resolution:
    root: Path
    source: str          # "arg" | "env" | "scan"
    drive: str | None    # 스캔으로 찾은 경우의 드라이브 문자

class DataRootNotFoundError(DataProcessingError): ...

def candidate_roots(explicit: str | None = None) -> list[Path]: ...
def is_data_root(path: Path) -> bool: ...
def resolve_data_root(explicit: str | None = None,
                      roots: Iterable[Path] | None = None) -> Resolution: ...
```

**[동작 규칙]**
1. 우선순위: 명시 인자 → 환경변수 `AVM_DATA_PATH` → 드라이브 스캔 (명시/환경변수 값이 존재하지 않으면 **조용히 넘어가지 않고** 예외, 오타를 스캔이 가려 버리는 것을 막음)
2. `is_data_root`: 폴더 이름이 `MARKER_DIRNAME`이고 비어 있지 않을 것. 매니페스트 파일명이 확인되면 그 파일 존재 조건을 추가 (§6 질문 1)
3. 스캔은 기존 `_candidate_roots`와 같은 범위(Windows: D~Z, 그 외: /Volumes, /mnt, /media). 후보가 둘 이상이면 **마지막 수정 시각이 최신인 것**을 선택하고 나머지를 경고 로그로 남김 (WP-1에서 사본이 여럿일 때를 대비)
4. 스캔 대상 `roots`를 인자로 주입할 수 있게 해 테스트에서 실제 드라이브에 의존하지 않음

**[변경 대상]**
- `avm_paths.py`: `DATA_ROOT`/`DB_PATH`/`LEDGER_PATH` 이름은 **그대로 유지**(수집기 4종 임포트 호환). 값은 `resolve_data_root()`로 얻되, 못 찾으면 기존 기본값으로 대체해 임포트가 실패하지 않게 함
- `sync_from_external_drive.py`, `phase_c_step0_read_external_drive.py`: 자체 탐색을 `candidate_roots`/`resolve_data_root` 호출로 교체 (동작 동일, 코드 감소)
- `phase7_grounded_avm.py`, `phase7_match_engine.py`, `phase7_c_address_parser_v2.py`: `RTMS_DUCKDB`를 `resolve_data_root().root / "loan4u_working_db/db/loan4u_rtms_comparable_mart.duckdb"`로 교체. 이 3개는 현재 운영 경로와 무관한 Phase 7 코드일 수 있어, 교체 전에 **아직 쓰는 파일인지** 확인하고 안 쓰면 제외 (§6 질문 7)

**[테스트]** `tests/test_data_locator.py`
- 환경변수가 스캔보다 우선 / 존재하지 않는 환경변수는 예외
- 가짜 드라이브 둘(`E`, `F`)에 마커 폴더 → 최신 수정 시각 쪽 선택 + 경고
- 마커 없음 → `DataRootNotFoundError`
- `avm_paths` 임포트 시 못 찾아도 예외 없음

**[완료 기준]** 신규 테스트 통과, 기존 테스트 무회귀, `grep -rnE "[A-Z]:[/\\\\]loan4u_avm_data" --include=*.py avm_project`가 `data_locator.py`(기본 후보 설명)와 테스트 외 0건
**[추정]** 0.5일
**[위험]** Windows에서 연결 끊긴 네트워크 드라이브를 `exists()`로 확인할 때 지연될 수 있음 → 후보 확인에 짧은 타임아웃(스레드) 적용 여부를 구현 시 측정해 결정

---

## DEV-2. 실데이터 계약과 검증 규칙 — `scripts/real_data_contract.py` (신규)

**[목표]** LG 외장하드 원본(Manifest·Runbook이 정의)을 모델 입력 스키마로 변환하고, 검증 규칙을 코드로 강제한다. 상태 보고서의 미완료 항목 "DB 스키마 매핑", "데이터 검증 규칙"에 해당합니다.

**[차단 요인]** Manifest와 Runbook의 **실제 형식을 아직 본 적이 없습니다.** 아래는 형식에 의존하지 않는 부분만 확정하고, 의존하는 부분은 인터페이스만 정의합니다.

**[확정 부분 — 검증 규칙 엔진]**
```python
@dataclass(frozen=True)
class Violation:
    rule: str
    column: str
    count: int
    sample_index: list[int]      # 최대 5개

@dataclass(frozen=True)
class ValidationReport:
    rows: int
    violations: list[Violation]
    @property
    def error_rate(self) -> float: ...     # 위반 행 비율 (중복 집계 안 함)

def validate_transactions(df: pd.DataFrame, rules: Sequence[Rule]) -> ValidationReport: ...
def enforce(report: ValidationReport, max_error_rate: float = 0.05) -> None: ...  # 초과 시 DataValidationError
```
기본 규칙(Runbook이 오면 이 목록을 Runbook 기준으로 교체): 거래금액 > 0 / 전용면적 5~2000㎡ / 거래일이 유효하고 오늘 이후가 아님 / 건축년도 ≤ 거래년 / 취소거래 표시 필드가 있으면 제외 / 동일 거래 키 중복 제거.
각 규칙은 `Rule = Callable[[pd.DataFrame], pd.Series]`(위반 마스크 반환)로 한 함수당 한 규칙, 10줄 안팎.

**[형식 의존 부분 — 인터페이스만 정의]**
```python
@dataclass(frozen=True)
class TableSpec:
    name: str
    path: Path
    columns: dict[str, str]    # 원본 컬럼 → 표준 컬럼 (feature_schema 기준)

def load_manifest(path: Path) -> list[TableSpec]: ...        # 형식 확인 후 구현
def to_model_frame(spec: TableSpec) -> pd.DataFrame: ...     # 컬럼 매핑 + 타입 변환
```

**[통합]** `phase_c_step2_validate_and_preprocess.validate_and_preprocess`가 `standardize_columns` 뒤에 `validate_transactions` → `enforce`를 호출. 검증 보고서를 JSON으로 저장.

**[테스트]** 규칙별 정상/위반 1건씩, `error_rate` 중복 행 집계, `enforce` 임계값 경계(5.0%), 합성 데이터에 위반을 심어 정확히 그 건수가 보고되는지.
**[완료 기준]** 규칙 엔진 테스트 통과 + 실데이터 1회 실행 결과(위반 건수 표)
**[추정]** 규칙 엔진 0.5일 + 매핑은 Manifest 수령 후 0.5~1일 (형식에 따라 변동)

---

## DEV-3. 실데이터 평가 하네스 — `scripts/real_data_eval.py` (신규) + 정리

**[목표]** 실데이터로 7개 모델을 학습·평가하되, **시간순 분할 + 누수 감사를 통과한 수치만** 성능으로 보고한다. PoC의 R² 0.9983이 누수 영향인지 가려내는 것이 핵심입니다.

**[파이프라인]**
```
load(DEV-1 경로, DEV-2 변환) → validate/enforce → temporal_split(70/15/15)
→ leakage_audit(+그룹 중복) → 7개 모델 학습(train) → 튜닝(val) → 최종 평가(test, 1회)
→ real_data_eval_report.json
```

**[신규/변경 함수]**
```python
# leakage_audit.py에 추가 (기존 3종과 같은 flags 반환 규약)
def audit_group_overlap(train: pd.DataFrame, test: pd.DataFrame,
                        key_cols: Sequence[str], threshold: float = 0.30) -> list[dict]: ...
    # 검증 구간 거래의 단지/필지 키가 학습 구간에 이미 있는 비율을 계산.
    # 시간순 분할이어도 같은 단지가 양쪽에 있으면 "동네를 외운" 결과일 수 있어 비율을 보고

# real_data_eval.py
def evaluate_model(model: Any, X_test: pd.DataFrame, y_test: pd.Series) -> dict[str, float]: ...   # r2, mape, mae
def run(data_root: Path, target: str, time_col: str, key_cols: Sequence[str]) -> dict[str, Any]: ...
def gate(metrics: dict[str, float]) -> list[str]: ...    # 미달 사유 목록, 비면 통과
```

**[보고 지표]** R², MAPE, MAE, **괴리율**은 기존 `discrepancy_rate_validation.py`의 정의를 그대로 재사용(구현 시 정의 확인 후 동일 함수 호출. 정의를 새로 만들지 않음).
**[합격선]** `CLAUDE.md` 기준 R² > 0.84, MAPE < 10.5%. 누수 감사 플래그가 있으면 합격 여부와 별개로 보고서 맨 위에 표시.

**[정리 작업]**
- `phase_c_step3_retrain_models.py`의 중복 `temporal_split`을 삭제하고 `temporal_split.temporal_split`을 임포트 (같은 시그니처)
- 같은 파일의 미사용 `train_test_split` 임포트 제거 (사용처 확인 후)

**[보고서 JSON 스키마]**
```json
{
  "data": {"root": "...", "rows": 0, "date_range": ["...", "..."]},
  "validation": {"error_rate": 0.0, "violations": []},
  "leakage": {"flags": [], "group_overlap_ratio": 0.0},
  "models": {"xgboost": {"r2": 0, "mape": 0, "mae": 0, "discrepancy": 0}},
  "gate": {"passed": false, "reasons": []}
}
```

**[테스트]**
- 합성 데이터: 타겟을 그대로 복사한 컬럼을 넣으면 `audit_correlations`가 플래그, 시간 누수(미래 정보)를 넣은 데이터는 분할 격차 플래그
- `audit_group_overlap`: 겹침 0%/100%/경계값
- `gate` 경계값
- `phase_c_step3` 변경 후 기존 동작 동일 (임포트 교체만)

**[완료 기준]** 실데이터 1회 실행 보고서, PoC 대비 지표 증감 표, 합격선 미달 시 원인 후보
**[추정]** 구현 1일 + 실데이터 실행·분석 1일 (데이터 크기와 GPU 가용성에 따라 변동)
**[실행 위치]** 실데이터가 PC에 있으므로 **로컬 세션**. 클라우드에서는 합성 데이터 테스트까지만 가능

---

## DEV-4. kreri.re.kr 수집기 — `scripts/collect_kreri.py` (신규, 차단됨)

**[상태]** 이 세션에서 사이트가 403으로 막혀 자료 종류를 모릅니다. **§6 질문 2건이 답해지기 전에는 파서를 설계하지 않습니다.** 아래는 자료 종류와 무관하게 확정 가능한 골격입니다.

**[골격]**
```python
EXIT_OK, EXIT_AUTH, EXIT_SCHEMA = 0, 2, 3      # CLAUDE.md 종료 코드 규약

@dataclass(frozen=True)
class ManifestEntry:
    url: str
    local_path: str
    sha256: str
    fetched_at: str
    status: str            # "ok" | "skipped" | "schema_error"

def fetch_listing(session: requests.Session, page_url: str) -> list[str]: ...      # 자료 링크 수집 (파서는 답변 후)
def download(session: requests.Session, url: str, dest: Path) -> ManifestEntry: ...  # http_client.get_with_retry 사용
def run(page_url: str, out_dir: Path, delay_s: float = 1.0) -> int: ...             # 종료 코드 반환
```
- **재개**: 매니페스트(JSONL)에 `ok`로 기록된 URL은 건너뜀 (멱등)
- **오류 분류**: `TransientFetchError` → 재시도 후 건너뜀(0), `AuthFetchError` → 즉시 중단(2), `SchemaFetchError`/파싱 실패 → 해당 건만 기록 후 계속, 종료 시 3
- **예의**: 요청 간 지연, 식별 가능한 User-Agent, 순차 요청
- **정리 단계**(`kreri_to_dataset.py`)는 자료 종류별로 분기: 통계표 → 정규화 CSV(기간·지역코드·지표·값), 보고서 → 메타데이터 + 섹션별 텍스트 JSONL. 보고서형은 `evaluation-report-analysis/report_analyzer.py`의 `extract_text`/`split_sections` 재사용을 검토하되, 그 디렉터리명에 하이픈이 있어 일반 임포트가 안 되므로 **공용 모듈로 옮길지 경로 주입으로 쓸지** 구현 시 결정 (§6 질문 4)

**[테스트]** 네트워크 없이 저장된 샘플 HTML/파일로 파서 테스트, 매니페스트 재개 동작, 종료 코드 3분류(가짜 응답으로 각각 유발)
**[선행 조건]** 이용약관·저작권 확인 기록, 접근 가능한 네트워크에서의 최초 확인(사용자 PC)
**[추정]** 답변 후 설계 0.5일 + 구현·테스트 1~2일

---

## 5. 구현 순서와 커밋 단위

```
DEV-1 (경로)  →  DEV-3 (평가 하네스, 합성 데이터까지)  →  DEV-2 (Manifest 수령 후 매핑 완성)
                                                       →  실데이터 실행 (로컬)
DEV-4 는 §6 답변 후 독립 진행
```
- DEV-1과 DEV-3(합성 데이터 범위)은 **Manifest 없이 지금 바로 클라우드에서 구현·테스트 가능**
- DEV-2의 규칙 엔진도 가능하지만 기본 규칙은 임시값이라, Runbook 수령 후 교체
- 커밋은 1작업 1커밋: DEV-1 신규 모듈 → DEV-1 호출부 교체 → DEV-3 `audit_group_overlap` → DEV-3 중복 제거 → DEV-3 하네스 …

## 6. 결정·자료가 필요한 사항

1. **Manifest 파일의 이름과 형식**(JSON/CSV/SQLite?) 샘플 1개, **Runbook의 검증 규칙** 부분 — DEV-1의 마커 조건과 DEV-2 매핑·규칙에 필요
2. **kreri.re.kr/32의 자료 종류**와 **학습 데이터 용도** — DEV-4 설계의 전제
3. **실데이터의 타깃 컬럼, 시간 컬럼, 단지/필지 키 컬럼** 이름 — DEV-3의 `run()` 인자
4. 보고서형 자료를 다룰 경우 `evaluation-report-analysis`의 추출 코드를 **공용 모듈로 이동**해도 됩니까?
5. **Phase 번호** — 커밋 메시지 `[Phase X.Y]`에 쓸 번호
6. 이 개발을 **클라우드 세션에서 DEV-1·DEV-3 합성 범위부터 시작**해도 됩니까?
7. `phase7_*.py` 3개 파일(F: 하드코딩)은 **지금도 쓰는 코드**입니까, 아니면 과거 단계 잔재입니까?

## 7. 위험

| 위험 | 대응 |
|---|---|
| 스캔이 오래된 사본을 선택 | 마지막 수정 시각이 최신인 후보 선택 + 다중 후보 경고 + `AVM_DATA_PATH`로 명시 지정 가능 |
| 드라이브 스캔 지연(끊긴 네트워크 드라이브) | 구현 시 실측 후 타임아웃 적용 |
| 기본 검증 규칙이 실데이터와 맞지 않음 | 임시 규칙임을 보고서에 표시, Runbook 수령 후 교체, 위반 건수만 보고하고 자동 삭제는 하지 않음 |
| 실데이터 성능이 PoC보다 크게 낮음 | 정상적인 결과일 수 있음. 누수 감사 결과와 함께 보고하고 PoC 수치는 계속 "참고용"으로 표기 |
| 임포트 시 부작용(경로 해석 실패로 수집기 중단) | `avm_paths`는 실패 시 기존 기본값으로 대체해 하위 호환 유지 (임포트하는 7개 파일 모두 영향) |

## 8. PC 구현 결과와 최신 정책 정정 (2026-10-23)

현재 결과 이후의 실제 계약·중앙 실행기 연결·하네스 보완·KRERI 지표 보강은 [후속 실행 명세](NEXT_EXECUTION_SPEC_2026_10_23.md)에 상세화했다.

| 항목 | 실제 구현/검증 | 잔여 |
|---|---|---|
| DEV-1 | `data_locator.py`, `AVM_DATA_ROOT` 우선·기존 `AVM_DATA_PATH` VWorld 하위폴더 의미 유지, E: 정본 외 Windows 경로 거절, import 시 장치 접근 없음, sync/Step0 경로 연결 | 실제 E: mount/권한과 공용 운영 진입점 인수는 미실행 |
| DEV-2 | 명시적 `avm.real-data.manifest.v1` JSON→CSV 매핑·타입 변환·행 기준 위반 합집합·5% 경계·빈 입력 차단 | 실제 Manifest 형식/Runbook 및 source DTO 매핑 미인수, 기존 전처리의 운영 교체 없음 |
| DEV-3 | 기존 시간분할 재사용·중복 정의 제거, 네 가지 누수 감사, 명시적 feature 목록, 그룹/시각/타깃 피처 제외, 같은 시각의 분할 경계 거절, train 중앙값, 7모델·기존 상대괴리율 정의 공유 | 실데이터 성능/PoC 대비 수치 미측정, 실데이터 CLI 중앙 admission 연결 필요 |
| DEV-4 | 목적=AVM 피처 보강, 공식 게시판 종류 확인 | 본문·robots GET403, 이용조건/실제 첨부 미확인. 파서·수집 미실행 |

관련 시험은 **40 PASS**다. 합성 400행을 CSV→명시적 매핑→누수 감사→7개 모델→JSON 저장→재조회했다. 무작위 정답 합성 입력의 지표 게이트는 정상적으로 불합격이며, 운영 성능이나 학습 완료로 인정하지 않는다. 타깃 복제·그룹 겹침은 최종 테스트를 열기 전에 차단한다. 원문 타깃/그룹 값은 보고서에 싣지 않는다.

본문 DEV-1의 과거 제안인 최신 수정시간 자동 선택·D: 기본값 fallback은 적용하지 않는다. Windows는 E: 정본만 허용하며 휴대 환경의 다중 후보도 명시 선택을 요구한다. `avm_paths.DATA_ROOT`는 계속 VWorld 하위폴더를 가리키고, 새 `AVM_DATA_ROOT`는 전체 데이터 루트다. Step0/sync의 repo-local 복제 CLI는 Windows에서 운영 admission 미연결 오류로 종료한다.

F: 하드코딩의 Phase7 세 파일은 현재 운영 사용 여부가 확인되지 않아 변경 대상에서 보류했다. 저장소 전체 하드코딩 0건을 주장하지 않는다. 새로운 매핑 형식은 개발 계약이며 기존 원천 Manifest와 같은 형식이라고 주장하지 않는다. 실제 Runbook 없이 정한 개발 검증 규칙은 보고서의 `DEVELOPMENT_DEFAULTS_NOT_RUNBOOK`으로 표시한다.

최신 E: 기준 루트·원천 보존·단일 I/O·중앙 검증·receipt 정책은 본문 과거 경로 제안보다 우선한다. 운영 입력 연결은 해당 공용 실행기에서 허가·잠금·원천·범위를 결속한 뒤 수행한다. 실제 전체 드라이브 감사, 실데이터 평가, 수집기 다운로드, 운영 배포는 미완료다.
