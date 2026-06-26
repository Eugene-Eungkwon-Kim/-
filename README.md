# Loan4U Automatic Valuation Model (AVM) - Phase 12-13 Development

**Status**: Phase 12 (70% complete) → Phase 13 (10% complete)  
**Current Branch**: `claude/eloquent-meitner-lqxu9r`  
**Next Milestone**: 2026-07-14 (Phase 13 completion with GPU/NPU optimization)

## 📋 Quick Start

### For Development
```bash
# Clone and navigate
cd /home/user/-/avm_project

# Install dependencies
pip install -r requirements.txt  # Full stack
# OR
pip install -r requirements-minimal.txt  # Quick start

# Run Phase 12 pipeline
python scripts/loan4u_phase12_pipeline.py

# Check compliance
python -m py_compile scripts/loan4u_phase12_pipeline.py
```

### For Agents Joining This Project
1. **Read** [CLAUDE.md](./CLAUDE.md) - Environment & standards (START HERE)
2. **Read** [.claude/EXECUTION_POLICY.md](./.claude/EXECUTION_POLICY.md) - Complete policy (MANDATORY)
3. **Review** [avm_project/scripts/loan4u_phase12_pipeline.py](./avm_project/scripts/loan4u_phase12_pipeline.py) - Reference implementation
4. **Follow** Code Quality Standards (Section 3 below)

## 🎯 Project Overview

**Loan4U AVM** is an automated valuation model expansion project targeting 8 international markets (UK, SG, JP, DE, AU, CA, TH, HK) with GPU/NPU optimization for production deployment.

### Phase 12: Data Validation & Integration (70% complete)
- ✅ Core pipeline: 417-line unified Excel/PDF generator
- ✅ Price validation: 4-grade conformity classifier (적정/확인필요/편차주의/추가확인)
- ✅ Country expansion: 8 countries × 2 sheets each
- ⏳ PDF generation: In progress (Phase 12.G)
- ⏳ Validation module: In progress (Phase 12.H)

**Deliverable**: 21-sheet workbook + PDF report (1000+ records)

### Phase 13: Model Development & Deployment (10% complete)
- ⏳ Data collection: 1M+ records across 8 countries
- ⏳ Feature engineering: 30-35 features per country
- ⏳ GPU training: XGBoost, LightGBM, Gradient Boosting (RTX 5050)
- ⏳ NPU optimization: ONNX → OpenVINO IR conversion
- ⏳ API deployment: FastAPI + NPU inference engine

**Target**: Production ML pipeline with 7-8x training acceleration (GPU) + 10x inference acceleration (NPU)

## 🏗️ Project Structure

```
/home/user/-/
├── avm_project/                          # Main project directory
│   ├── scripts/
│   │   ├── loan4u_phase12_pipeline.py    # ✅ 417 lines, reference implementation
│   │   ├── phase12_pdf_generator.py      # 🚧 Phase 12.G
│   │   ├── phase12_validator.py          # 🚧 Phase 12.H
│   │   ├── phase13_data_collector.py     # 🚧 Phase 13.1
│   │   ├── phase13_model_trainer.py      # 🚧 Phase 13.2
│   │   └── phase13_model_converter.py    # 🚧 Phase 13.2.5 (NEW)
│   ├── config/
│   │   └── avm_config.json               # 26 configuration items
│   ├── data/
│   │   ├── raw/                          # Input data
│   │   └── processed/                    # Processed data
│   ├── output/                           # Generated deliverables
│   ├── docs/
│   │   ├── PHASE_12_IMPLEMENTATION_SPEC.md
│   │   ├── PHASE_12_CODE_INDEX.md
│   │   ├── GPU_NPU_OPTIMIZATION_STRATEGY.md
│   │   └── NEXT_DEVELOPMENT_DETAILED_REPORT.md
│   ├── README.md                         # Project-specific README
│   ├── requirements.txt                  # Full dependencies
│   └── requirements-minimal.txt          # Quick start dependencies
│
├── CLAUDE.md                             # ✅ Agent configuration guide
├── README.md                             # This file
├── .gitignore                            # Git ignore rules
│
└── .claude/
    ├── EXECUTION_POLICY.md               # ✅ Development policy (MANDATORY)
    ├── settings.json                     # Agent settings
    └── settings.local.json               # Local overrides
```

## 🔧 Code Quality Standards

**These apply to ALL code in this repository** (see `.claude/EXECUTION_POLICY.md` Section 1 for details):

### Mandatory Requirements
| Requirement | Standard | Verification |
|-------------|----------|--------------|
| Function size | Max 50 lines (100 for complex logic only) | Manual review |
| Type hints | 100% on all function signatures | `mypy` check |
| Principles | SRP + DRY (no 3+ repeated lines) | Code review |
| Comments | Only for WHY (non-obvious logic), never WHAT | Visual check |
| Dead code | Delete completely (no stubs) | Git review |

### Pre-Commit Checklist
```
- [ ] No function > 50 lines (or justified 100)
- [ ] All functions have complete type hints
- [ ] Single Responsibility Principle met
- [ ] No code repetition (3+ identical lines extracted)
- [ ] No debug prints or commented code
- [ ] Comments explain WHY, not WHAT
```

### Reference Implementation
See [loan4u_phase12_pipeline.py](./avm_project/scripts/loan4u_phase12_pipeline.py) (417 lines) for compliant code example:
- Type hints: ✅ All functions annotated
- SRP: ✅ Each function has single responsibility
- DRY: ✅ Reusable utilities (normalize_*, style_*, autofit_*)
- Comments: ✅ Only on complex logic (e.g., column index handling)

## 📊 Development Schedule

### Phase 12: Data Validation (Target: 2026-07-03)
| Phase | Task | Status | Time |
|-------|------|--------|------|
| 12.A-F | Core pipeline | ✅ Done | 5 days |
| 12.G | PDF generation | ⏳ In progress | 2 days |
| 12.H | Validation & finalization | ⏳ In progress | 2 days |
| **Total** | | **70% complete** | **9 days** |

### Phase 13: Model Development (Target: 2026-07-14)
| Phase | Task | Status | Time |
|-------|------|--------|------|
| 13.1 | Data collection + feature engineering | ⏳ Queue | 5 days |
| 13.2 | GPU model training (XGBoost, LightGBM, GB) | ⏳ Queue | 4 days |
| 13.2.5 | **NEW** Model conversion (ONNX→OpenVINO IR) | ⏳ Queue | 1 day |
| 13.3 | Model validation (R²>0.84, MAPE<10.5%) | ⏳ Queue | 2 days |
| 13.4 | NPU deployment + API | ⏳ Queue | 3 days |
| **Total** | | **10% complete** | **15 days** |

### GPU/NPU Optimization (RTX 5050 + Onboard NPU)
- **Training**: 7-8x faster with GPU (XGBoost 35min→5min)
- **Inference**: 10x faster with NPU (5-10ms→1ms latency)
- **Power**: 70% reduction with NPU
- **Accuracy**: R² >0.84, MAPE <10.5%

## 🌍 International Markets

**8 Target Countries with High Data Maturity:**

| Country | Code | Tolerance | Data Source | Status |
|---------|------|-----------|-------------|--------|
| United Kingdom | UK | ±5% | HM Land Registry, Rightmove | ✅ Ready |
| Singapore | SG | ±8% | URA, PropertyGuru | ✅ Ready |
| Japan | JP | ±5% | REIT-DB, MLIT | ✅ Ready |
| Germany | DE | ±8% | Zillium, Berlin Property Register | ✅ Ready |
| Australia | AU | ±10% | ABS, RP Data | ✅ Ready |
| Canada | CA | ±10% | StatsCan, RE/MAX | ✅ Ready |
| Thailand | TH | ±15% | TREB, Proppy | ✅ Ready |
| Hong Kong | HK | ±8% | Centaline, RICS | ✅ Ready |

## 📈 Key Metrics

### Phase 12 Output (Workbook)
| Metric | Value |
|--------|-------|
| Total sheets | 21 (5 domestic + 8×2 country + 1 report) |
| Total records | 1,000+ properties |
| Validation grades | 4-tier: 적정/확인필요/편차주의/추가확인 |
| File size | ~2.3 MB |

### Phase 13 Target (Model)
| Metric | Target |
|--------|--------|
| R² Score | >0.84 |
| MAPE | <10.5% |
| Training time | 35→5 min (GPU, 7x speedup) |
| Inference time | 5-10ms→1ms (NPU, 10x speedup) |
| Power consumption | 70% reduction (NPU) |

## 🚀 Work Reporting Policy

After completing any phase, use this template (see `.claude/EXECUTION_POLICY.md` Section 2):

```markdown
### [Phase X.Y] [작업명 - Work Title]

**[목표]** Objectives  
Brief goal (1-2 sentences)

**[대상]** Target Scope  
Affected files/modules

**[범위 포함]** Included  
- Deliverable 1 ✓
- Deliverable 2 ✓

**[범위 제외]** Excluded  
- Known limitations

**[완료 기준]** Completion Criteria  
- Tests passing ✓
- Code review done ✓

**[일정]** Schedule  
- Actual: X hours vs Y estimate

**[참고자료]** References  
- Documentation files

**[추가 정보]** Notes  
- Performance metrics
- Next phase recommendations
```

## 🔐 Git Commit Policy

All commits must follow atomic, policy-compliant format:

```bash
git commit -m "[Phase X.Y] Brief description (under 70 chars)

Detailed explanation (wrapped at 72 chars):
- What changed and why
- Impact on next phase

Completion checklist:
- Code quality standards met ✓
- Type hints complete ✓
- Tests passing ✓

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_..."
```

See `.claude/EXECUTION_POLICY.md` Section 3 for complete git standards.

## 📚 Documentation

| Document | Purpose | Lines |
|----------|---------|-------|
| [CLAUDE.md](./CLAUDE.md) | Agent config & quick reference | 242 |
| [.claude/EXECUTION_POLICY.md](./.claude/EXECUTION_POLICY.md) | Complete development policy | 234 |
| [PHASE_12_IMPLEMENTATION_SPEC.md](./avm_project/docs/PHASE_12_IMPLEMENTATION_SPEC.md) | Technical specification | 156 |
| [PHASE_12_CODE_INDEX.md](./avm_project/docs/PHASE_12_CODE_INDEX.md) | Architecture reference | 204 |
| [GPU_NPU_OPTIMIZATION_STRATEGY.md](./avm_project/docs/GPU_NPU_OPTIMIZATION_STRATEGY.md) | Hardware optimization plan | 736 |
| [NEXT_DEVELOPMENT_DETAILED_REPORT.md](./avm_project/docs/NEXT_DEVELOPMENT_DETAILED_REPORT.md) | Phase 13 roadmap | 385 |

## 🛠️ Development Commands

```bash
# Check syntax compliance
python -m py_compile avm_project/scripts/loan4u_phase12_pipeline.py

# Run pipeline
python avm_project/scripts/loan4u_phase12_pipeline.py --base data/raw/before_fill.xlsx --config config/phase12 --output output/corrected.xlsx

# View git history
git log --oneline -10

# Check branch status
git status

# Verify policy compliance
cat CLAUDE.md              # Quick reference
cat .claude/EXECUTION_POLICY.md  # Complete policy
```

## ❓ FAQ & Escalation

### Code Quality Questions
→ See `.claude/EXECUTION_POLICY.md` Section 1

### Schedule Changes
→ Document in work report Section [추가 정보]

### Technical Blockers
→ Commit as debugging step with issue notes

### Policy Conflicts
→ Raise with team lead (send report using work reporting template)

## 📞 Support & Contact

- **Project Lead**: Loan4U AVM Development Team
- **Current Session**: Claude Code with Sonnet 4.6 model
- **Policy File**: `.claude/EXECUTION_POLICY.md` (complete reference)
- **Configuration**: [CLAUDE.md](./CLAUDE.md) (agent setup)

---

**Last Updated**: 2026-06-26  
**Policy Version**: 1.0  
**All agents must read** [.claude/EXECUTION_POLICY.md](./.claude/EXECUTION_POLICY.md) **before starting work**
