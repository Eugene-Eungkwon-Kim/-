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
    """한 달치 실거래가 데이터를 조회하여 항목 리스트로 반환."""
    params = {
        "serviceKey": service_key,   # 디코딩 키 (urlencode가 다시 인코딩)
        "LAWD_CD": lawd_cd,
        "DEAL_YMD": deal_ymd,
        "pageNo": "1",
        "numOfRows": str(num_rows),
    }
    url = f"{API_URL}?{urlencode(params, quote_via=quote_plus)}"

    req = Request(url, headers={"User-Agent": "Loan4u-AVM/1.0"})
    with urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")

    root = ET.fromstring(raw)

    # 오류 응답 처리
    result_code = root.findtext(".//resultCode")
    if result_code not in (None, "00", "000"):
        msg = root.findtext(".//resultMsg") or "알 수 없는 오류"
        raise RuntimeError(f"API 오류 [{result_code}] {msg}")

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

    try:
        months = list(month_range(args.start, args.end))
    except ValueError as e:
        print(f"오류: {e}")
        sys.exit(1)

    for ymd in months:
        try:
            rows = fetch_month(service_key, args.lawd, ymd)
            all_rows.extend(rows)
            print(f"  [{ymd}] {len(rows):>4}건 수집")
            stats["성공"] += 1
        except (HTTPError, URLError) as e:
            print(f"  [{ymd}] 네트워크 오류: {e}")
            stats["실패"] += 1
        except (ET.ParseError, RuntimeError) as e:
            print(f"  [{ymd}] 응답 오류: {e}")
            stats["실패"] += 1
        time.sleep(args.delay)

    if not all_rows:
        print("\n수집된 데이터가 없습니다. 인증키/지역코드/기간을 확인하세요.")
        sys.exit(1)

    columns = [col for _, col in FIELDS]
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(all_rows)

    print("\n" + "=" * 45)
    print(f"완료: 총 {len(all_rows)}건 저장 → {out_path}")
    print(f"조회 성공 {stats['성공']}개월 | 실패 {stats['실패']}개월")


if __name__ == "__main__":
    main()
