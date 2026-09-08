# CLAUDE.md

이 저장소에는 세 개의 서로 다른 프로젝트가 함께 있습니다: 휴대폰 파일 정리
스크립트(루트), MAARS 플랫폼(`src/` 등, Node/TypeScript), AVM
프로젝트(`avm_project/`, Python). 아래 "저장소 전역 원칙"은 어디서 작업하든
적용되고, "AVM 프로젝트 전용" 이하는 `avm_project/` 안에서 작업할 때만
적용됩니다.

## 저장소 전역 원칙

### 파이썬 퍼스트 원칙 (데이터 수집 · 스크래핑)

데이터 수집/스크래핑 작업은 기본적으로 독립 실행 가능한 파이썬 스크립트로 만들고,
그 스크립트를 반복 실행하는 방식으로 처리한다. AI(Claude)가 매 실행마다 개입해서
데이터를 받아오는 방식은 쓰지 않는다.

AI 개입은 다음 경우로 한정한다:

- 신규 데이터소스의 최초 설계 (인증 방식, 응답 스키마 파악, 레이트리밋 확인)
- 오류를 진단한 결과 원인이 코드/스키마 변경인 경우의 스크립트 수정
- 사이트 구조 변경 등으로 파서·셀렉터를 다시 짜야 하는 경우

오류 원인이 판단이 필요 없는 일시적 문제(네트워크 타임아웃, 429, 5xx)라면
스크립트가 자체 재시도로 처리해야 하며, 그때마다 AI가 개입할 필요는 없다.

### 오류 분류와 종료 코드 규약

새 수집 스크립트를 작성하거나 기존 스크립트를 손볼 때는 오류를 아래 세 가지로
구분해서 처리한다 (`fetch_realestate.py`와
`avm_project/app/integrations/http_client.py`가 참고 구현).

| 분류 | 예시 | 처리 | 종료 코드 |
|---|---|---|---|
| 일시적 (transient) | 타임아웃, HTTP 429, 5xx, 네트워크 오류 | 지수 백오프로 자동 재시도, 소진되면 해당 단위만 건너뜀 | 0 (부분 실패는 정상 종료) |
| 인증 (auth) | HTTP 401/403, 서비스키 오류 응답 | 재시도해도 해결되지 않으므로 즉시 중단 | 2 |
| 스키마/예기치 않음 (schema) | XML/JSON 파싱 실패, 알 수 없는 API 오류 코드, 필드 구조 변경 | 해당 단위는 건너뛰고 목록에 기록, 실행 끝에 검토 필요 표시 | 3 |

이 구분이 있어야 "오류가 나면 무조건 AI를 부른다"를 피할 수 있다 — 일시적
오류는 스크립트가 스스로 해결하고, 실제로 판단이 필요한 인증·스키마 오류만
사람 또는 AI에게 넘어간다.

---

## AVM 프로젝트 전용 (`avm_project/` 하위)

### Quick Reference

**Project**: Loan4U Automatic Valuation Model (AVM) - Phase 12-14
**Policy File**: `.claude/EXECUTION_POLICY.md` (required reading for all agents)

### ⚠️ 환경 설정 (모든 에이전트 필수)

**Windows 사용자**: 드라이브 문자 변경 문제 확인
```powershell
# 자동 수정 스크립트 실행 (권장)
.\.claude\fix_external_drive.ps1 -AutoFix

# 또는 수동 확인
cd E:\avm_project  # E드라이브 확인 (D드라이브가 아님!)
git status
```

**모든 에이전트**:
1. **읽기**: `.claude/ENVIRONMENT_SETUP_GUIDE.md` - 환경 설정 가이드 (필수)
2. **읽기**: `.claude/EXECUTION_POLICY.md` - 개발 정책 (필수)
3. **검토**: `avm_project/README.md` - 프로젝트 개요
4. **확인**: `avm_project/scripts/loan4u_phase12_pipeline.py` - 참조 구현

### Code Quality Standards

These apply to ALL code written under `avm_project/`:

#### Mandatory
- **Max 50 lines per function** (100 max for complex logic only)
- **100% type hints** on all function signatures
- **Single Responsibility Principle**: One function = one reason to change
- **DRY Principle**: Extract any 3+ repeated lines into helper function/loop
- **Minimal comments**: Only for WHY (non-obvious intent), never WHAT (code explains itself)

#### Review Checklist Before Every Commit
```
- [ ] No function exceeds 50 lines (or justified 100)
- [ ] All functions have complete type hints
- [ ] Each function has single responsibility
- [ ] No code repetition (3+ identical lines extracted)
- [ ] No debug prints, commented code, verbose docstrings
- [ ] Comments explain WHY, not WHAT
```

### Work Reporting Template

After completing any phase, use this template:

```
### [Phase X.Y] [작업명 - Work Title]

**[목표]** Objectives
Brief goal (1-2 sentences)

**[대상]** Target Scope
Affected files/modules

**[범위 포함]** Included
- Specific deliverable 1
- Specific deliverable 2

**[범위 제외]** Excluded
- Known limitations

**[완료 기준]** Completion Criteria
- Tests passing ✓
- Code review done ✓

**[일정]** Schedule
- Actual: X hours vs Y estimate
- Blockers: (if any)

**[참고자료]** References
- Key documentation files

**[추가 정보]** Notes
- Performance metrics
- Recommendations
```

### Git Commit Standards

#### Message Format
```
[Phase X.Y] Brief description (under 70 chars)

Detailed explanation (wrapped at 72 chars):
- What changed
- Why it changed
- Impact on next phase

Completion checklist:
- Code quality standards met ✓
- Type hints complete ✓
- Tests passing ✓
```

#### Commit Policy
- **Atomic**: One task = one commit (not bundled)
- **Incremental**: Small, logical changes
- **Reversible**: Each commit stands alone
- **Tested**: No breaking changes

### GPU/NPU Optimization (RTX 5050 + Onboard NPU)

**Three-Stage Pipeline:**
1. **GPU Training** (RTX 5050): 7-8x speedup vs CPU (35min→5min for XGBoost)
2. **Model Conversion** (ONNX→OpenVINO IR): 1 day preparation for NPU
3. **NPU Inference**: 10x speedup (5-10ms→1ms latency), 70% power reduction

**Current Performance Targets:**
- Training: Gradient Boosting, XGBoost (gpu_hist), LightGBM (gpu)
- Inference: OpenVINO on onboard NPU
- Accuracy: R² >0.84, MAPE <10.5%

### Key Project Structure

```
avm_project/
├── scripts/                            # 파이프라인 · 데이터 수집 스크립트
├── app/integrations/http_client.py     # 공용 재시도/오류분류 HTTP 클라이언트
├── config/
│   └── avm_config.json
├── data/
│   ├── raw/
│   └── processed/
├── docs/
├── README.md
├── requirements.txt
└── requirements-minimal.txt

.claude/
├── EXECUTION_POLICY.md
├── settings.json
└── settings.local.json
```

### Critical Constants

```python
# 9 target countries for expansion (BR priority for Phase 13)
COUNTRIES = ['BR', 'UK', 'SG', 'JP', 'DE', 'AU', 'CA', 'TH', 'HK']

# Country-specific tolerance ranges
TOLERANCE_MAP = {
    'UK': 0.05, 'JP': 0.05,      # ±5% (strict)
    'SG': 0.08, 'DE': 0.08, 'HK': 0.08,  # ±8% (moderate)
    'AU': 0.10, 'CA': 0.10,      # ±10% (relaxed)
    'TH': 0.15                   # ±15% (most relaxed)
}

# Model confidence adjustment factors
CONFIDENCE_MAP = {
    'v1.0': 1.0,   # Full confidence
    'v1.1': 0.98,  # 2% reduction
    'v1.2': 0.95   # 5% reduction
}

# Price validation result grades
GRADE_COLORS = {
    '적정': 'C6EFCE',        # Green - acceptable
    '확인필요': 'FFEB9C',    # Yellow - needs review
    '편차주의': 'FFC7CE',    # Light red - high variance
    '추가확인': 'FF0000'     # Red - requires action
}
```

### For New Agents (AVM 작업 시)

1. **Read** `.claude/EXECUTION_POLICY.md` first (required)
2. **Read** this file's AVM 섹션 for context
3. **Review** `avm_project/README.md` for project overview
4. **Check** `avm_project/scripts/loan4u_phase12_pipeline.py` for code standards example
5. **Follow** all standards in "Code Quality Standards" above
6. **Report** work using the template above
7. **Commit** using the format above

### Escalation & Questions

- **Code standards questions**: Refer to `.claude/EXECUTION_POLICY.md` Section 1
- **Policy conflicts**: Raise with team lead (user)
- **Technical blockers**: Document and commit as debugging step
