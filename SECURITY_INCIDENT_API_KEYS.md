# 보안 사고 기록: AVM API 키 노출 및 재발급 체크리스트

## 무슨 일이 있었나

`avm_project/` 개발 과정에서 실제 API 키가 소스코드·설정 JSON·문서(.md)에
평문으로 커밋되어 있었습니다. 두 차례에 걸쳐 발견·수정되었습니다.

1. **커밋 `7b082b8a`** (2026-09-07) — 코드/설정/문서 전체를 스캔해 7종의 키를
   찾아 환경변수 참조로 교체. 영향 파일 22개(스크립트 11, 설정 JSON 2, 문서 7,
   `.env.example` 1, 테스트 스크립트 1).
2. **PR #4 작업 중** (이 세션) — `opinet_data_collector.py`/`vworld_data_collector.py`의
   `main()`에 남아있던 Opinet·VWorld 키를 환경변수로 이관(위 스캔 이후 별도
   브랜치에서 독립적으로 발견됨 — 스캔이 모든 파일을 다 훑지는 못했다는 뜻).

**현재 저장소의 어떤 브랜치에도 평문 키는 남아있지 않습니다** (`grep`으로 직접 확인).
문제는 **git 히스토리** — 아래 커밋들의 diff에는 원래 키 값이 그대로 남아 있고,
이 저장소를 클론한 적이 있거나 접근 권한이 있었던 누구나 `git log`로 볼 수 있습니다.

## 재발급이 필요한 키 목록

| 제공처 | 키 종류 | 환경변수명 | 비고 |
|---|---|---|---|
| VWorld (국토교통부 공간정보포털) | API 키 | `VWORLD_API_KEY` | 지오코딩·건물정보 |
| data.go.kr (공공데이터포털) | 일반 인증키 (짧은 형식) | `DATAGOVKR_API_KEY`, `KOREA_API_KEY` | 두 변수, 같은 값 |
| data.go.kr | 디코딩 키 (긴 base64 형식) | `DATAGOVKR_DECODING_KEY` | 위와 별개 형식 |
| 주소정보누리집 (Juso) | 승인키 (정보제공용) | `JUSO_API_KEY_PROVIDE` | |
| 주소정보누리집 (Juso) | 승인키 (정보용) | `JUSO_API_KEY_INFO` | |
| 한국석유공사 오피넷 (Opinet) | API 키 | `OPINET_API_KEY` | PR #4에서 별도 발견 |
| 한국은행 (BOK) | API 키 | `BOK_API_KEY` | |

`JUSO_API_KEY_POPUP`, `FISIS_API_KEY`, `MOLIT_STATS_KEY`, `NCP_CLIENT_ID`,
`NCP_CLIENT_SECRET`은 `.env.example`에 자리는 있지만, 이번 스캔에서 실제
하드코딩된 값이 발견되지는 않았습니다 — 사용 중이라면 확인 차원에서 같이
재발급하는 것을 권장하되, 이 사고 기록의 확인된 범위에는 포함되지 않습니다.

## 왜 코드 수정만으로는 부족한가

git은 파일을 지워도 과거 커밋을 지우지 않습니다. 현재 파일에서 키를 빼도
`git log -p`로 과거 diff를 보면 원래 값이 그대로 나옵니다. **저장소가 한 번이라도
공개되었거나, 접근 권한이 있던 사람이 로컬에 클론해 둔 적이 있다면, 코드 수정과
무관하게 그 키는 이미 유출된 것으로 간주해야 합니다.**

확실한 조치는 하나뿐입니다: **각 발급처에서 키를 즉시 재발급(무효화 후 재발급)받는 것.**

## 체크리스트

- [ ] VWorld — https://www.vworld.kr (마이페이지 → 인증키 관리)에서 재발급
- [ ] data.go.kr — https://www.data.go.kr (마이페이지 → 개발계정 → 활용신청 현황)에서
      일반 인증키·디코딩 키 재발급
- [ ] 주소정보누리집 — https://www.juso.go.kr (오픈API 신청현황)에서 두 승인키 재발급
- [ ] Opinet — https://www.opinet.co.kr (오픈API 신청)에서 재발급
- [ ] 한국은행 — https://ecos.bok.or.kr (Open API 인증키 관리)에서 재발급
- [ ] 재발급된 값을 각자의 로컬 `.env`(커밋되지 않는 파일)에만 반영 — 저장소에는
      절대 실제 값을 커밋하지 않는다
- [ ] (선택, 별도 승인 필요) git 히스토리 자체에서 과거 키 값을 제거하려면
      `git filter-repo` 또는 BFG Repo-Cleaner로 히스토리를 재작성해야 합니다.
      이는 모든 기존 클론을 무효화하는 파괴적 작업이라, 재발급으로 키 자체가
      무력화된 뒤에는 실익이 크지 않을 수 있습니다 — 필요하다고 판단되면
      별도로 명시적으로 요청해 주세요.

## 재발자 참고

앞으로 새 API 통합을 추가할 때는 `fetch_realestate.py`, `avm_project/scripts/opinet_data_collector.py`,
`avm_project/scripts/vworld_data_collector.py`의 패턴(환경변수에서만 키를 읽고,
기본값에 실제 값을 두지 않음)을 따르세요. `CLAUDE.md`의 "저장소 전역 원칙"에도
관련 규약이 있습니다.
