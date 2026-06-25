# Phase 12 WBS - Concise Edition

## Summary
- **Total Tasks**: 10 main tasks
- **Duration**: 5-7 days (2-3 hours actual development)
- **Team**: 1 developer
- **Deliverable**: loan4u_phase12_pipeline.py (500-700 lines)

---

## Task Breakdown

| Task | Description | Time | Dependencies | Status |
|------|-------------|------|--------------|--------|
| 12.1 | Setup: imports, constants, logging | 30m | - | ⏳ |
| 12.2 | Data models: @dataclass × 3 | 20m | 12.1 | ⏳ |
| 12.3 | Utilities: normalize, styling, headers | 45m | 12.2 | ⏳ |
| 12.4 | Price validation: classify_* functions | 45m | 12.3 | ⏳ |
| 12.5 | Domestic sheet processing | 40m | 12.4 | ⏳ |
| 12.6 | Country sheet creation (8 countries) | 60m | 12.4 | ⏳ |
| 12.7 | Report sheet & integration | 30m | 12.6 | ⏳ |
| 12.8 | Formatting & styling | 30m | 12.7 | ⏳ |
| 12.9 | PDF generation | 30m | 12.8 | ⏳ |
| 12.10 | Testing & debug | 30m | 12.9 | ⏳ |

**Total: ~360 minutes = 6 hours**

---

## Execution Schedule

**Day 1 (Monday)**
- 12.1-12.4: Core modules (2.5 hours)

**Day 2 (Tuesday)**  
- 12.5-12.10: Integration & output (3.5 hours)

**Day 3-7**
- Testing, validation, pdf generation, finalization

---

## Code Quality Standards (Fixed Policy)

### Must Haves
- [ ] Single Responsibility Principle per function
- [ ] Max 50 lines per function (stretch to 100 for complex logic)
- [ ] Type hints on all function signatures
- [ ] Comments only for non-obvious logic
- [ ] DRY: No code repetition (use loops/helpers)
- [ ] Variable names: clear and concise (not abbreviated)
- [ ] No commented-out code

### Structure
- No class-based verbose objects (use @dataclass for data only)
- Flat module structure (no nested classes)
- Pure functions where possible
- Minimize dependencies

### Before Commit
- [ ] Code review: Is every line necessary?
- [ ] Remove: Debug prints, unused variables, verbose comments
- [ ] Check: Can any 3+ repeated lines become a loop/function?
