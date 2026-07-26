# Session 25B Candidate Review Packet

- Approval status: `HUMAN_APPROVED_MINIMUM_DRYRUN`
- Approved crosswalks: 1
- Approved type rules: 1
- Customer-safe candidates before approval: 0

## Crosswalk Candidates

| Rule | Query | Candidate | Evidence | Status |
|---|---|---|---:|---|
| DW-0001 | 화성시 | 화성만세구 | 45 | NEEDS_REVIEW |
| DW-0002 | 화성시 | 화성효행구 | 5 | NEEDS_REVIEW |
| DW-0003 | 화성시 만세구 | 화성시 | 43 | NEEDS_REVIEW |

## Candidate Queue

| Queue | Query | Candidate | Rules | Evidence |
|---|---|---|---|---:|
| CQ-0001 | 화성시 만세구 공장 | 화성시 공장 | DW-0003 / TW-0013 | 4 |
| CQ-0002 | 화성시 만세구 공장 | 화성시 창고 | DW-0003 / TW-0082 | 1 |
| CQ-0003 | 화성시 만세구 공장 | 화성시 창고용지 | DW-0003 / TW-0083 | 1 |

## Key Type Rules

| Rule | Raw Type | Class | Flags |
|---|---|---|---|
| TW-0004 | 아파트형공장 | KNOWLEDGE_INDUSTRIAL_CENTER | APARTMENT_SUBSTRING_NOT_RESIDENTIAL |
| TW-0012 | 아파트 | RESIDENTIAL_APARTMENT |  |
| TW-0013 | 공장 | FACTORY |  |
| TW-0082 | 창고 | FACTORY |  |
| TW-0083 | 창고용지 | FACTORY |  |
