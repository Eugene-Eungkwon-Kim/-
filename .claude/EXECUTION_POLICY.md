# Execution Policy - Loan4U AVM Phase 12-13 Development

## Policy Effective Date
2026-06-26 onwards

## 1. Code Quality Standards (Fixed)

### Function Size
- **Maximum**: 50 lines per function
- **Stretch limit**: 100 lines for genuinely complex logic only
- **Enforcement**: Every function must be reviewed for SRP compliance before commit

### Type Hints
- **Requirement**: 100% type hints on all function signatures
- **Format**: `def function_name(param: Type, ...) -> ReturnType:`
- **Collections**: Use `List[T]`, `Dict[K, V]`, `Optional[T]`, `Tuple[T, ...]`

### Code Organization
- **Principle**: Single Responsibility Principle (SRP) - one function, one reason to change
- **DRY**: Don't Repeat Yourself - extract any 3+ repeated lines into a function/loop
- **Modularity**: Pure functions preferred; minimal state mutations
- **Comments**: Only for non-obvious logic or hidden constraints
  - No docstrings longer than 1 line
  - No comment blocks explaining WHAT code does (code should be self-explanatory)
  - Comments only for WHY (non-obvious intent) or workarounds

### Code Removal
- **Dead code**: Delete completely (no `# removed` comments or renamed _vars)
- **Debug prints**: Remove before commit
- **Verbose docstrings**: Strip to 1 line or remove
- **Commented-out code**: Delete

## 2. Work Reporting Template

**When to apply**: After every phase completion, before moving to next phase

```markdown
## [Phase X.Y Completion Report]

### [작업명] Work Title
Brief descriptive title

### [목표] Objectives
What was the goal? (1-2 sentences)

### [대상] Target Scope
Files, modules, or systems affected

### [범위 포함] What's Included
- Specific deliverables ✓
- Code changes ✓
- Documentation ✓

### [범위 제외] What's Excluded
- Items deferred to later phases
- Known limitations

### [완료 기준] Completion Criteria
- All tests passing ✓
- Code review completed ✓
- Documentation updated ✓

### [일정] Schedule
- Actual: HH:MM (vs estimate)
- Blockers: (if any)

### [참고자료] Reference Materials
- PHASE_12_IMPLEMENTATION_SPEC.md
- GPU_NPU_OPTIMIZATION_STRATEGY.md
- Relevant commit messages

### [추가 정보] Additional Notes
- Performance metrics
- Known issues
- Recommendations for next phase
```

**Mandatory sections**: All 9 must be present
**Format**: Korean section headers (고정), English content acceptable
**File location**: Commit message or PHASE_COMPLETION_REPORTS.md

## 3. Git Commit Policy

### Commit Message Format
```
[Phase X.Y] Brief description (under 70 chars)

Detailed explanation of changes (wrapped at 72 chars):
- What changed
- Why it changed
- Impact on next phase

Completion checklist:
- Code quality standards met ✓
- Type hints added ✓
- Tests passing ✓
- Documentation updated ✓

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_...
```

### Atomic Commits
- **One task = one commit** (not bundled)
- **Incremental**: Small, logical changes
- **Reversible**: Each commit stands alone
- **Tested**: No breaking changes

### Verification
```bash
git config user.email noreply@anthropic.com
git config user.name Claude
git log --oneline -5  # Verify green checkmarks
```

## 4. Development Schedule

### Phase 12 (Complete by 2026-07-03)
- ✅ 12.A-F: Core pipeline (417-line working implementation)
- ⏳ 12.G: PDF generation (Phase12PDFGenerator, ~250 lines, 2 days)
- ⏳ 12.H: Validation & finalization (Phase12Validator, ~200 lines, 2 days)
- 🎯 Deliverable: 21-sheet workbook + PDF report

### Phase 13 (Complete by 2026-07-14, with GPU/NPU optimization)
- Phase 13.1: Data collection (8 countries, 1M+ records, 3 days)
- Phase 13.1: Feature engineering (30-35 features/country, 2 days)
- Phase 13.2: GPU model training (XGBoost, LightGBM, Gradient Boosting, 4 days)
- Phase 13.2.5: **NEW** Model conversion (ONNX → OpenVINO IR, 1 day) - RTX 5050 GPU optimization
- Phase 13.3: Model validation (R² >0.84, MAPE <10.5%, 2 days)
- Phase 13.4: NPU deployment (FastAPI + OpenVINO inference, 3 days)
- 🎯 Deliverable: Production ML pipeline with GPU/NPU acceleration

### Performance Targets
- Training acceleration: **7-8x faster** with GPU (vs CPU baseline)
- Inference acceleration: **10x faster** with NPU (vs CPU, 5-10ms → 1ms)
- Power reduction: **70% less** energy consumption with NPU
- Model accuracy: **R² >0.84**, MAPE <10.5%

## 5. Multi-Agent Coordination Policy

### For Other Agents
When this policy is injected into other agents:
1. Read this file first: `.claude/EXECUTION_POLICY.md`
2. Apply all standards to your work
3. Report work using the template in Section 2
4. Commit following Section 3 standards
5. Respect the schedule in Section 4

### Policy Injection Methods
- **Primary**: Copy this file path in initial prompt
- **Fallback**: Reference as "Loan4U AVM development policy" in instructions
- **Verification**: Agent confirms policy understanding before starting

### Escalation
- Code review conflicts: Refer to Section 1
- Schedule adjustments: Document in Section 2 ([추가 정보])
- Process changes: Document to this file + commit

## 6. Highest-Delta-Value Priority Order

Execute tasks in this order (rationality metric: value/effort ratio):

| Priority | Task | Impact | Effort | Delta | Status |
|----------|------|--------|--------|-------|--------|
| 1 | Create `.claude/EXECUTION_POLICY.md` | High | Low | ⭐⭐⭐ | ✅ |
| 2 | Update `CLAUDE.md` with policy sections | High | Low | ⭐⭐⭐ | ⏳ |
| 3 | Update `README.md` with policy reference | Medium | Low | ⭐⭐ | ⏳ |
| 4 | Create `.claude/settings.json` policy config | Medium | Medium | ⭐⭐ | ⏳ |
| 5 | Git commit policy distribution | High | Low | ⭐⭐⭐ | ⏳ |
| 6 | Complete Phase 12.G PDF generation | High | High | ⭐⭐ | ⏳ |
| 7 | Complete Phase 12.H validation | High | High | ⭐⭐ | ⏳ |

## 7. Project Scope (Phase 12-13)

### Phase 12 Outputs
- `loan4u_phase12_pipeline.py` - 417 lines ✅ (complete)
- `Loan4U_QC_v1.1_Phase12_Global_Corrected_20260625.xlsx` - 21 sheets (in progress)
- `Loan4U_Phase12_Final_Report.pdf` - 1-page summary (pending)

### Phase 13 Outputs
- Data collection pipeline for 8 countries (1M+ records)
- Trained models: XGBoost, LightGBM, Gradient Boosting
- GPU/NPU optimized inference engine
- FastAPI deployment server
- Weekly automated retraining system

### Key Constants
```python
COUNTRIES = ['UK', 'SG', 'JP', 'DE', 'AU', 'CA', 'TH', 'HK']
TOLERANCE_MAP = {
    'UK': 0.05, 'JP': 0.05, 'SG': 0.08, 'DE': 0.08,
    'HK': 0.08, 'AU': 0.10, 'CA': 0.10, 'TH': 0.15
}
CONFIDENCE_MAP = {'v1.0': 1.0, 'v1.1': 0.98, 'v1.2': 0.95}
GRADE_COLORS = {
    '적정': 'C6EFCE', '확인필요': 'FFEB9C',
    '편차주의': 'FFC7CE', '추가확인': 'FF0000'
}
```

## 8. Documentation Standards

### File Types
- **Implementation specs**: Concise (200-300 lines), code-focused
- **WBS documents**: Task-based with time estimates
- **Code indices**: Architecture maps with function signatures
- **Reports**: Phase completion template (Section 2)

### What NOT to Document
- Redundant explanations (code should be self-explanatory)
- Verbose docstrings (1 line max)
- Old decisions (belongs in commit history, not code)
- Hypothetical future work (only confirmed phases)

## 9. Session Continuity

### For Next Sessions
1. **Context preservation**: Read this policy file first
2. **Git history**: Check latest commits for current state
3. **Pending tasks**: Refer to Section 4 schedule
4. **Code standards**: Section 1 applies to all changes

### Hand-off Format
When handing off to next session:
1. Commit all work with policy-compliant messages (Section 3)
2. Update Section 4 schedule with actual progress
3. Note any blockers in Section 2 template
4. Leave no uncommitted changes

---

**Policy Owner**: Loan4U AVM Development Team  
**Last Updated**: 2026-06-26  
**Next Review**: 2026-07-14 (Phase 13 completion)
