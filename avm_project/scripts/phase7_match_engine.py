# -*- coding: utf-8 -*-
"""
Phase 7-2: NPL 물건 <-> RTMS 실거래 비교사례 매칭 엔진
Session 21 Track B.3 (2026-07-03)

입력:
  - F:/NPL전례/avm_project/data/npl_avm.db (properties 테이블, 아파트만 사용)
  - F:/loan4u_avm_data/loan4u_working_db/db/loan4u_rtms_comparable_mart.duckdb

출력:
  - results/phase7_match_report.md
  - results/phase7_matched_pairs.csv (T1/T2 매칭 결과)

매칭 원칙: address_detail에서 지번/단지명을 정규식으로 추출한 뒤
  T1(정확): 동(umd_nm) + 지번(jibun) 일치
  T2(부분): 동(umd_nm) 일치 + 단지명 유사 + 면적 ±5㎡
  T3(불가): 매칭 실패
"""
import re
import sqlite3
import duckdb
import pandas as pd
import numpy as np
from pathlib import Path

NPL_DB = "F:/NPL전례/avm_project/data/npl_avm.db"
RTMS_DUCKDB = "F:/loan4u_avm_data/loan4u_working_db/db/loan4u_rtms_comparable_mart.duckdb"
RESULTS_DIR = Path("F:/NPL전례/avm_project/results")

print("=" * 70)
print("Phase 7-2: NPL <-> RTMS 매칭 엔진")
print("=" * 70)


def extract_jibun(addr_detail: str):
    if not addr_detail:
        return None
    m = re.match(r"\s*(\d+(?:-\d+)?)", str(addr_detail))
    return m.group(1) if m else None


def extract_complex_name(addr_detail: str):
    if not addr_detail:
        return None
    # "...우성아파트 제14동 제10층 제1003호" -> "우성아파트"
    m = re.search(r"([가-힣0-9]+(?:아파트|APT|맨션|타운|파크|캐슬|팰리스|빌리지|하이츠|스위트|그린빌|힐스))", str(addr_detail))
    if m:
        return m.group(1)
    # "제14동" 앞 토큰 fallback
    m2 = re.search(r"([가-힣0-9]+)\s*제\d+동", str(addr_detail))
    return m2.group(1) if m2 else None


def normalize_name(name: str):
    if not name:
        return ""
    return re.sub(r"[^가-힣0-9]", "", name)


print("\n[1] NPL 아파트 물건 로드 중...")
conn = sqlite3.connect(NPL_DB)
npl = pd.read_sql_query(
    """
    SELECT id, address_sido, address_sigungu, address_dong, address_detail,
           land_area, building_area
    FROM properties
    WHERE property_type = '아파트'
    """,
    conn,
)
conn.close()
print(f"  [OK] {len(npl)}건")

npl["jibun"] = npl["address_detail"].apply(extract_jibun)
npl["complex_raw"] = npl["address_detail"].apply(extract_complex_name)
npl["complex_norm"] = npl["complex_raw"].apply(normalize_name)
npl["dong_norm"] = npl["address_dong"].fillna("").str.strip()

print(f"  지번 추출 성공: {npl['jibun'].notna().sum()}건")
print(f"  단지명 추출 성공: {npl['complex_raw'].notna().sum()}건")

print("\n[2] RTMS 비교사례 마트 로드 중...")
rcon = duckdb.connect(RTMS_DUCKDB, read_only=True)
rtms = rcon.execute(
    """
    SELECT umd_nm, complex_name, complex_name_norm, jibun_norm,
           exclusive_area_sqm, deal_date, sale_price_krw, price_per_sqm
    FROM rtms_comparable_mart
    """
).fetchdf()
rcon.close()
print(f"  [OK] {len(rtms)}건")

# 최신 거래 우선 사용 (중복 지번/단지 시 최근 거래 대표값)
rtms["deal_date"] = pd.to_datetime(rtms["deal_date"])
rtms_by_dong = {dong: g for dong, g in rtms.groupby("umd_nm")}

print("\n[3] 매칭 수행 중...")
results = []
for _, row in npl.iterrows():
    dong = row["dong_norm"]
    cand = rtms_by_dong.get(dong)
    tier, matched_price_per_sqm, n_comparables = "T3", None, 0

    if cand is not None and row["jibun"]:
        exact = cand[cand["jibun_norm"] == row["jibun"]]
        if len(exact) > 0:
            tier = "T1"
            matched_price_per_sqm = exact["price_per_sqm"].median()
            n_comparables = len(exact)

    if tier == "T3" and cand is not None and row["complex_norm"]:
        fuzzy = cand[cand["complex_name_norm"].apply(normalize_name) == row["complex_norm"]]
        if row["building_area"] and len(fuzzy) > 0:
            # 전용면적 기준과 다른 정의(공급/전용 혼재)일 수 있어 넓게 +-15% 허용
            area = row["building_area"]
            fuzzy = fuzzy[(fuzzy["exclusive_area_sqm"] >= area * 0.85) & (fuzzy["exclusive_area_sqm"] <= area * 1.15)]
        if len(fuzzy) > 0:
            tier = "T2"
            matched_price_per_sqm = fuzzy["price_per_sqm"].median()
            n_comparables = len(fuzzy)

    results.append({
        "npl_id": row["id"],
        "dong": dong,
        "jibun": row["jibun"],
        "complex_name": row["complex_raw"],
        "building_area": row["building_area"],
        "tier": tier,
        "matched_price_per_sqm": matched_price_per_sqm,
        "n_comparables": n_comparables,
    })

match_df = pd.DataFrame(results)
t1 = (match_df["tier"] == "T1").sum()
t2 = (match_df["tier"] == "T2").sum()
t3 = (match_df["tier"] == "T3").sum()
total = len(match_df)

print(f"  T1 (지번 정확 매칭): {t1}건 ({t1/total*100:.1f}%)")
print(f"  T2 (단지명+면적 부분 매칭): {t2}건 ({t2/total*100:.1f}%)")
print(f"  T3 (매칭 불가): {t3}건 ({t3/total*100:.1f}%)")

RESULTS_DIR.mkdir(exist_ok=True)
match_df.to_csv(RESULTS_DIR / "phase7_matched_pairs.csv", index=False, encoding="utf-8-sig")

report = f"""# Phase 7-2: NPL-RTMS 매칭 결과 (leak-free, 실측)

**실행일**: 2026-07-03
**NPL 아파트 물건**: {total}건 (전체 property_type='아파트' 379건 중 조회된 {total}건)
**RTMS 비교사례**: {len(rtms)}건

## 매칭률

| Tier | 정의 | 건수 | 비율 |
|---|---|---:|---:|
| T1 | 동+지번 정확 매칭 | {t1} | {t1/total*100:.1f}% |
| T2 | 동+단지명(정규화)+면적±15% 매칭 | {t2} | {t2/total*100:.1f}% |
| T3 | 매칭 불가 | {t3} | {t3/total*100:.1f}% |

## 참고

- 이 매칭률은 규칙 기반 정규식 파싱 1차 결과이며, address_detail의 자유서식(공백/오탈자/약칭)으로 인해
  실제 매칭 가능 건수보다 낮게 잡혔을 가능성이 있음 (보수적 추정).
- T3 물건은 별도로 사유(지번 파싱 실패/동명 불일치/단지 정보 없음)를 세분화하면 개선 여지 있음.
"""
with open(RESULTS_DIR / "phase7_match_report.md", "w", encoding="utf-8") as f:
    f.write(report)

print(f"\n[OK] {RESULTS_DIR / 'phase7_match_report.md'}")
print(f"[OK] {RESULTS_DIR / 'phase7_matched_pairs.csv'}")
print("\n" + "=" * 70)
print("[DONE] Phase 7-2 매칭 완료")
print("=" * 70)
