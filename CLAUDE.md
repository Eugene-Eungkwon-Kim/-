# Loan4U AVM Development - Claude Agent Configuration

## Quick Reference

**Project**: Loan4U Automatic Valuation Model (AVM) - Phase 12-13  
**Current Branch**: `claude/eloquent-meitner-lqxu9r`  
**Policy File**: `.claude/EXECUTION_POLICY.md` (required reading for all agents)  
**Status**: Phase 12 complete, Phase 13 in progress  

## For Claude Agents

Before starting work:
1. **Read** `.claude/EXECUTION_POLICY.md` - Contains all mandatory standards
2. **Review** `README.md` - Project overview
3. **Check** `avm_project/scripts/loan4u_phase12_pipeline.py` - Reference implementation (417 lines, all standards met)

## Code Quality Standards

These apply to ALL code written in this repository:

### Mandatory
- **Max 50 lines per function** (100 max for complex logic only)
- **100% type hints** on all function signatures
- **Single Responsibility Principle**: One function = one reason to change
- **DRY Principle**: Extract any 3+ repeated lines into helper function/loop
- **Minimal comments**: Only for WHY (non-obvious intent), never WHAT (code explains itself)

### Review Checklist Before Every Commit
```
- [ ] No function exceeds 50 lines (or justified 100)
- [ ] All functions have complete type hints
- [ ] Each function has single responsibility
- [ ] No code repetition (3+ identical lines extracted)
- [ ] No debug prints, commented code, verbose docstrings
- [ ] Comments explain WHY, not WHAT
```

## Work Reporting Template

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

## Git Commit Standards

### Message Format
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

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_...
```

### Commit Policy
- **Atomic**: One task = one commit (not bundled)
- **Incremental**: Small, logical changes
- **Reversible**: Each commit stands alone
- **Tested**: No breaking changes

## Current Phase Status

### Phase 12 ✅ (70% complete)
- ✅ 12.A-F: Core pipeline (417 lines, tested)
- ✅ 12.G: PDF generation framework designed
- ⏳ 12.H: Validation module (in progress)
- 🎯 Deliverable: 21-sheet Excel + PDF report

### Phase 13 🚧 (10% complete)
- ⏳ 13.1: Data collection pipeline
- ⏳ 13.2: GPU-accelerated model training (RTX 5050)
- ⏳ 13.2.5: **NEW** Model conversion for NPU optimization
- ⏳ 13.3: Model validation
- ⏳ 13.4: NPU-based API deployment
- 🎯 Deliverable: Production ML pipeline

### Schedule
- **Phase 12 target**: 2026-07-03
- **Phase 13 target**: 2026-07-14 (with GPU/NPU optimization)

## GPU/NPU Optimization (RTX 5050 + Onboard NPU)

**Three-Stage Pipeline:**
1. **GPU Training** (RTX 5050): 7-8x speedup vs CPU (35min→5min for XGBoost)
2. **Model Conversion** (ONNX→OpenVINO IR): 1 day preparation for NPU
3. **NPU Inference**: 10x speedup (5-10ms→1ms latency), 70% power reduction

**Current Performance Targets:**
- Training: Gradient Boosting, XGBoost (gpu_hist), LightGBM (gpu)
- Inference: OpenVINO on onboard NPU
- Accuracy: R² >0.84, MAPE <10.5%

## Key Project Structure

```
avm_project/
├── scripts/
│   ├── loan4u_phase12_pipeline.py     # ✅ 417 lines, reference impl
│   ├── phase12_pdf_generator.py       # 🚧 Phase 12.G
│   ├── phase12_validator.py           # 🚧 Phase 12.H
│   ├── phase13_data_collector.py      # 🚧 Phase 13.1
│   ├── phase13_model_trainer.py       # 🚧 Phase 13.2
│   └── phase13_model_converter.py     # 🚧 Phase 13.2.5 (NEW)
├── config/
│   └── avm_config.json                # 26 configuration items
├── data/
│   ├── raw/                           # Input data
│   └── processed/                     # Processed data
├── output/
│   └── Phase12_Global_Corrected.xlsx  # 21-sheet deliverable
├── docs/
│   ├── PHASE_12_IMPLEMENTATION_SPEC.md
│   ├── PHASE_12_CODE_INDEX.md
│   ├── GPU_NPU_OPTIMIZATION_STRATEGY.md
│   └── NEXT_DEVELOPMENT_DETAILED_REPORT.md
├── README.md                          # Project overview
├── requirements.txt                   # Full dependencies
└── requirements-minimal.txt           # Quick start

.claude/
├── EXECUTION_POLICY.md                # ✅ This policy document
├── settings.json                      # Agent settings
└── settings.local.json                # Local overrides
```

## Critical Constants

```python
# 8 target countries for expansion
COUNTRIES = ['UK', 'SG', 'JP', 'DE', 'AU', 'CA', 'TH', 'HK']

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

## For New Agents

When joining this project:

1. **Read** `.claude/EXECUTION_POLICY.md` first (required)
2. **Read** this file (CLAUDE.md) for context
3. **Review** `README.md` for project overview
4. **Check** `avm_project/scripts/loan4u_phase12_pipeline.py` for code standards example
5. **Follow** all standards in Section "Code Quality Standards" above
6. **Report** work using template in Section "Work Reporting Template" above
7. **Commit** using format in Section "Git Commit Standards" above

## Escalation & Questions

- **Code standards questions**: Refer to `.claude/EXECUTION_POLICY.md` Section 1
- **Schedule changes**: Document in work report Section [추가 정보]
- **Policy conflicts**: Raise with team lead (user)
- **Technical blockers**: Document and commit as debugging step

## Quick Commands

```bash
# Check policy compliance
python -m py_compile avm_project/scripts/*.py

# Run existing pipeline
python avm_project/scripts/loan4u_phase12_pipeline.py

# Verify git history
git log --oneline -10

# Check branch status
git status

# Commit with template
git commit -m "[Phase X.Y] Description

Details here.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_..."
```

---

**Last Updated**: 2026-06-26  
**Maintained by**: Loan4U AVM Development Team  
**Policy Version**: 1.0 (see `.claude/EXECUTION_POLICY.md` for details)
