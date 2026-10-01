# drive_audit — 드라이브 간 중복 파일 조사

C:, D:, E: 등 여러 드라이브에 흩어진 **중복 파일**, **통째로 복사된 폴더**,
**같은 git 저장소의 여러 사본**을 찾아 보고서로 만든다.
**읽기 전용** — 어떤 파일도 삭제·이동하지 않는다.

## 실행 (Windows PowerShell)

```powershell
cd <이 저장소 폴더>
python drive_audit\find_duplicates.py C:\ D:\ E:\
```

- 연결되지 않은 드라이브는 경고만 출력하고 건너뛴다 (예: 외장하드가 D:→E: 로 바뀐 경우).
- C:\ 전체가 오래 걸리면 범위를 좁힌다: `python drive_audit\find_duplicates.py C:\Users\eungk D:\ E:\`
- 결과는 `drive_audit_report_날짜_시각\` 폴더에 생성된다 (`--out` 으로 변경 가능).

## 결과물

| 파일 | 내용 |
|---|---|
| `report.md` | 요약 · 드라이브 조합별 중복 용량 · 복사된 폴더 · git 사본 비교 · 큰 중복 파일 TOP 30 |
| `duplicates.csv` | 모든 중복 그룹과 경로 (엑셀에서 바로 열림) |
| `copied_folders.csv` | 같은 하위 구조를 가진 폴더 쌍과 겹침 비율 |
| `git_repos.csv` | git 저장소 사본별 브랜치 · 최신 커밋 · 미커밋 변경 수 |
| `summary.json` | 요약 수치 |

## 동작 방식

1. **스캔** — 시스템 폴더(`Windows`, `Program Files`, `$Recycle.Bin` …)와
   캐시성 폴더(`AppData`, `node_modules`, `.venv`, `.git` …)는 제외. 정션·심볼릭 링크는 따라가지 않는다.
   OneDrive 클라우드 전용 파일은 읽으면 다운로드되므로 건너뛴다.
2. **중복 판정** — 크기가 같은 파일만 → 앞 64KB 해시 → 전체 해시(BLAKE2b) 순으로 좁혀 디스크 읽기를 최소화.
3. **복사된 폴더** — 동일 파일들의 공통 하위 경로를 떼어내 `C:\Users\eungk\AVM ↔ E:\avm_project` 처럼 사본의 최상위 폴더 쌍을 구한다.
4. **git 사본 비교** — 첫 커밋이 같은 저장소끼리 묶고 최신 커밋 순 정렬 (★ = 최신). 미커밋 변경이 있는 사본은 정리 전에 확인 필요.

## 옵션

| 옵션 | 설명 |
|---|---|
| `--out 폴더` | 결과 저장 위치 |
| `--min-size N` | N bytes 미만 파일 무시 (기본 1 = 빈 파일만 제외). 큰 파일만 보려면 `--min-size 1048576` |
| `--exclude 이름` | 추가로 제외할 폴더 이름 (반복 가능) |
| `--include-system` | 기본 제외 폴더까지 검사 |
| `--top N` | 보고서 표 항목 수 (기본 30) |

종료 코드: `0` 정상 (읽기 오류가 일부 있어도 0, 건수는 보고서에 기록) · `1` 검색 가능한 폴더 없음.
