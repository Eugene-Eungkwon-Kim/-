#!/usr/bin/env python3
"""공공데이터포털 국토교통부 아파트 매매 실거래가 수집 스크립트 (Loan4u / AVM용)

data.go.kr 에서 발급받은 일반 인증키(디코딩 키)를 사용해
지역·기간별 아파트 실거래가를 조회하여 CSV로 저장합니다.

사용 예:
  python fetch_realestate.py --key 발급키 --lawd 11680 --start 202401 --end 202406
  python fetch_realestate.py --key 발급키 --lawd 11680 --start 202401 --end 202401 --out gangnam.csv
"""

import os
import sys
import csv
import time
import argparse
from datetime import datetime
from urllib.parse import urlencode, quote_plus
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import xml.etree.ElementTree as ET

# 국토교통부_아파트 매매 실거래가 상세 자료
API_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev"

# 재시도(지수 백오프)는 일시적 오류에만 적용한다. 인증·스키마 오류는 재시도로
# 해결되지 않으므로 별도로 분류해 처리한다 (CLAUDE.md 참고).
MAX_RETRIES = 3
RETRY_BASE_S = 2.0

# data.go.kr 공통 오류 코드 중 서비스키/접근권한 관련 코드. "22"(호출량 제한
# 초과)는 엄밀히는 인증 실패가 아니라 쿼터 초과지만, 재시도로 해결되지 않고
# 즉시 중단해야 한다는 점은 인증 오류와 동일해 같은 버킷으로 묶는다.
AUTH_RESULT_CODES = {"20", "22", "30", "31", "32"}


class TransientFetchError(Exception):
    """재시도하면 해결될 수 있는 오류 (타임아웃, 429, 5xx, 네트워크 오류)."""


class AuthFetchError(Exception):
    """서비스키/인증 문제. 재시도로 해결되지 않으므로 즉시 중단해야 한다."""


class SchemaFetchError(Exception):
    """응답 구조가 예상과 다른 경우 (API 오류 코드, XML 파싱 실패, 필드 변경 등)."""

# 응답 XML 항목 → CSV 컬럼 (한글 태그 대응)
FIELDS = [
    ("sggCd",          "시군구코드"),
    ("umdNm",          "법정동"),
    ("aptNm",          "단지명"),
    ("jibun",          "지번"),
    ("excluUseAr",     "전용면적"),
    ("floor",          "층"),
    ("buildYear",      "건축년도"),
    ("dealYear",       "거래년"),
    ("dealMonth",      "거래월"),
    ("dealDay",        "거래일"),
    ("dealAmount",     "거래금액"),
    ("cdealType",      "해제여부"),
    ("dealingGbn",     "거래유형"),
]


def month_range(start: str, end: str):
    """YYYYMM ~ YYYYMM 범위의 각 월을 순서대로 반환."""
    s = datetime.strptime(start, "%Y%m")
    e = datetime.strptime(end, "%Y%m")
    if s > e:
        raise ValueError("시작월이 종료월보다 늦습니다.")
    y, m = s.year, s.month
    while (y, m) <= (e.year, e.month):
        yield f"{y}{m:02d}"
        m += 1
        if m > 12:
            m = 1
            y += 1


def fetch_month(service_key: str, lawd_cd: str, deal_ymd: str,
                num_rows: int = 1000) -> list[dict]:
    """한 달치 실거래가 데이터를 조회하여 항목 리스트로 반환.

    오류는 TransientFetchError(재시도 가능) / AuthFetchError(즉시 중단) /
    SchemaFetchError(구조 변경, 검토 필요) 중 하나로 분류해 던진다.
    """
    params = {
        "serviceKey": service_key,   # 디코딩 키 (urlencode가 다시 인코딩)
        "LAWD_CD": lawd_cd,
        "DEAL_YMD": deal_ymd,
        "pageNo": "1",
        "numOfRows": str(num_rows),
    }
    url = f"{API_URL}?{urlencode(params, quote_via=quote_plus)}"
    req = Request(url, headers={"User-Agent": "Loan4u-AVM/1.0"})

    try:
        with urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
    except HTTPError as e:
        if e.code in (401, 403):
            raise AuthFetchError(f"인증 오류 (HTTP {e.code}): {e.reason}") from e
        if e.code == 429 or 500 <= e.code < 600:
            raise TransientFetchError(f"일시적 HTTP 오류 ({e.code}): {e.reason}") from e
        raise SchemaFetchError(f"예기치 않은 HTTP 오류 ({e.code}): {e.reason}") from e
    except URLError as e:
        raise TransientFetchError(f"네트워크 오류: {e.reason}") from e

    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        raise SchemaFetchError(f"응답 파싱 실패(XML 구조 변경 가능성): {e}") from e

    # 오류 응답 처리
    result_code = root.findtext(".//resultCode")
    if result_code not in (None, "00", "000"):
        msg = root.findtext(".//resultMsg") or "알 수 없는 오류"
        if result_code in AUTH_RESULT_CODES or "서비스키" in msg or "SERVICE_KEY" in msg.upper():
            raise AuthFetchError(f"API 인증/쿼터 오류 [{result_code}] {msg}")
        raise SchemaFetchError(f"API 오류 [{result_code}] {msg}")

    try:
        rows = []
        for item in root.findall(".//item"):
            row = {}
            for tag, col in FIELDS:
                val = item.findtext(tag)
                row[col] = (val or "").strip()
            # 거래금액 정규화 (콤마·공백 제거 → 숫자 만원 단위)
            amt = row.get("거래금액", "").replace(",", "").replace(" ", "")
            row["거래금액"] = amt
            rows.append(row)
    except Exception as e:
        raise SchemaFetchError(f"응답 항목 구조가 예상과 다릅니다: {e}") from e

    return rows


def main():
    parser = argparse.ArgumentParser(
        description="국토교통부 아파트 매매 실거래가 수집 (data.go.kr)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
지역코드(LAWD_CD)는 법정동코드 앞 5자리입니다. (예: 서울 강남구 = 11680)
인증키는 data.go.kr 마이페이지의 '일반 인증키(Decoding)'를 사용하세요.

예시:
  python fetch_realestate.py --key XXXX --lawd 11680 --start 202401 --end 202406
""",
    )
    parser.add_argument("--key", help="data.go.kr 일반 인증키(디코딩). 미지정 시 환경변수 DATA_GO_KR_KEY 사용")
    parser.add_argument("--lawd", required=True, help="지역코드 5자리 (법정동코드 앞 5자리)")
    parser.add_argument("--start", required=True, help="시작 거래년월 (YYYYMM)")
    parser.add_argument("--end", required=True, help="종료 거래년월 (YYYYMM)")
    parser.add_argument("--out", help="저장할 CSV 파일명 (기본: apt_지역_시작_종료.csv)")
    parser.add_argument("--delay", type=float, default=0.3, help="월별 요청 간 대기 시간(초)")
    args = parser.parse_args()

    service_key = args.key or os.environ.get("DATA_GO_KR_KEY")
    if not service_key:
        print("오류: 인증키가 필요합니다. --key 또는 환경변수 DATA_GO_KR_KEY 를 설정하세요.")
        sys.exit(1)

    out_path = args.out or f"apt_{args.lawd}_{args.start}_{args.end}.csv"

    print(f"지역코드: {args.lawd}")
    print(f"기간: {args.start} ~ {args.end}")
    print(f"저장: {out_path}\n")

    all_rows = []
    stats = {"성공": 0, "실패": 0}
    review_needed = []  # 스키마 오류로 건너뛴 월 (사람/AI 검토 필요)

    try:
        months = list(month_range(args.start, args.end))
    except ValueError as e:
        print(f"오류: {e}")
        sys.exit(1)

    for ymd in months:
        attempt = 0
        while True:
            try:
                rows = fetch_month(service_key, args.lawd, ymd)
                all_rows.extend(rows)
                print(f"  [{ymd}] {len(rows):>4}건 수집")
                stats["성공"] += 1
                break
            except TransientFetchError as e:
                attempt += 1
                if attempt > MAX_RETRIES:
                    print(f"  [{ymd}] 일시적 오류, {MAX_RETRIES}회 재시도 후 건너뜀: {e}")
                    stats["실패"] += 1
                    break
                wait = RETRY_BASE_S * (2 ** (attempt - 1))
                print(f"  [{ymd}] 일시적 오류, {wait:.0f}초 후 재시도 ({attempt}/{MAX_RETRIES}): {e}")
                time.sleep(wait)
            except AuthFetchError as e:
                print(f"\n인증/쿼터 오류: {e}")
                print("재시도로 해결되지 않습니다 — 서비스키 또는 일일 호출량 한도를 확인한 뒤 다시 실행하세요.")
                sys.exit(2)
            except SchemaFetchError as e:
                print(f"  [{ymd}] 응답 구조 오류(검토 필요): {e}")
                stats["실패"] += 1
                review_needed.append(ymd)
                break
        time.sleep(args.delay)

    # review_needed(스키마 오류)가 있으면 데이터가 0건이어도 그 사실을 먼저
    # 보고해야 한다 — "인증키를 확인하라"는 일반 메시지 뒤에 묻히면 실제 원인
    # (응답 구조 변경)을 놓치게 된다.
    if not all_rows and not review_needed:
        if stats["실패"] == 0:
            print("\n조회는 모두 성공했지만 수집된 거래가 없습니다. 해당 지역·기간에 실거래가 없을 수 있습니다.")
        else:
            print("\n수집된 데이터가 없습니다. 인증키/지역코드/기간을 확인하세요.")
        sys.exit(1)

    print("\n" + "=" * 45)
    if all_rows:
        columns = [col for _, col in FIELDS]
        with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerows(all_rows)
        print(f"완료: 총 {len(all_rows)}건 저장 → {out_path}")
    else:
        print("완료: 저장할 데이터 없음 (전 구간이 검토 대상으로 건너뛰어짐)")
    print(f"조회 성공 {stats['성공']}개월 | 실패 {stats['실패']}개월")

    if review_needed:
        print(f"\n주의: {len(review_needed)}개월은 응답 구조가 예상과 달라 확인이 필요합니다 → {', '.join(review_needed)}")
        sys.exit(3)


if __name__ == "__main__":
    main()
