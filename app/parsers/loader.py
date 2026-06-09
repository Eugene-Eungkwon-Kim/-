"""
딜 폴더를 스캔해서 금융기관을 자동 감지하고 적절한 파서로 로딩
"""
import re
from pathlib import Path
from app.parsers.base_parser import DealRecord
from app.parsers.ibk_parser import IBKParser
from app.parsers.kb_parser import KBParser
from app.parsers.dgb_parser import DGBParser
from app.parsers.sh_parser import SHParser
from app.parsers.hana_parser import HANAParser
from app.parsers.ibk_alloc_parser import IBKAllocParser


PARSER_MAP = {
    "IBK": IBKParser,
    "IBK_ALLOC": IBKAllocParser,
    "KB": KBParser,
    "DGB": DGBParser,
    "SH": SHParser,
    "HANA": HANAParser,
    # "NH": NHParser,
    # "JBB": JBBParser,
    # "우리FNI": WooriFNIParser,
}


def detect_institution(file_path: str) -> str:
    stem = Path(file_path).stem.upper()
    parent = Path(file_path).parent.name.upper()
    combined = f"{parent} {stem}"

    if "IBK" in combined:
        return "IBK"
    if re.search(r"\bKB\b", combined):
        return "KB"
    if re.search(r"MG NPL|MG\d|새마을", combined):
        return "MG"
    if re.search(r"\bDGB\b", combined):
        return "DGB"
    if re.search(r"우리FNI|우리F&I|WOORI", combined):
        return "우리FNI"
    if re.search(r"삼정|SAMJONG", combined):
        return "삼정FNI"
    if re.search(r"JBB|JJB|전북은행", combined):
        return "JBB"
    if re.search(r"SH|서울주택", combined):
        return "SH"
    if re.search(r"\bNH\b|농협", combined):
        return "NH"
    if re.search(r"HANA|하나", combined):
        return "HANA"
    return "UNKNOWN"


# 메인 Data Disk 파일 식별 패턴 (배정/연락처/기계기구/가격입력 등 제외)
_MAIN_DISK_INCLUDE = re.compile(
    r"(Data[\s_-]*Disk|Datadisk|감정평가대상목록|가격입력파일|가격입력\])",
    re.IGNORECASE,
)
_MAIN_DISK_EXCLUDE = re.compile(
    r"(Allocation|Contact|기계기구|^가격입력_|IRF[\s_]?Box|Loan[\s_]?File|연락처|수수료|Pre[\s_-]?Data|권리분석|보증서|분리|Assign|박상훈|한권흠|김경학|서무연|롤업|Short|Mark.?up|\bPF\b)",
    re.IGNORECASE,
)


def find_data_disk_files(root_dir: str) -> list[dict]:
    """루트 폴더에서 메인 Data Disk Excel 파일만 탐색"""
    root = Path(root_dir)
    candidates = []

    for f in root.rglob("*.xlsx"):
        if f.name.startswith("~$"):
            continue
        name = f.name
        if _MAIN_DISK_INCLUDE.search(name) and not _MAIN_DISK_EXCLUDE.search(name):
            inst = detect_institution(str(f))
            candidates.append({
                "file": str(f),
                "institution": inst,
                "folder": f.parent.name,
            })

    # 같은 폴더 내 같은 기관의 파일이 여러 개면 가장 최신(파일명 정렬 기준 마지막) 1개만
    from collections import defaultdict
    by_folder_inst: dict = defaultdict(list)
    for c in candidates:
        key = (Path(c["file"]).parent, c["institution"])
        by_folder_inst[key].append(c)

    unique = []
    for key, group in by_folder_inst.items():
        # 버전 번호가 높은 것 우선 (파일명 내림차순)
        group.sort(key=lambda x: Path(x["file"]).name, reverse=True)
        unique.append(group[0])

    return unique


def parse_file(file_path: str, institution: str = None) -> DealRecord | None:
    if institution is None:
        institution = detect_institution(file_path)

    parser_cls = PARSER_MAP.get(institution)
    if parser_cls is None:
        print(f"[SKIP] 파서 미구현: {institution} - {file_path}")
        return None

    try:
        parser = parser_cls()
        return parser.parse(file_path)
    except Exception as e:
        print(f"[ERROR] {file_path}: {e}")
        return None
