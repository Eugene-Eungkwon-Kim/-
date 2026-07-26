# -*- coding: utf-8 -*-
"""
Phase 7 Track C: 주소 파싱 개선 (동 추출률 향상)
Session 22 (2026-07-03)

발견: onbid_auction_results의 address_raw는 address_sigungu로 안 잡히는
구/읍/면 하위 행정단위가 dong 앞에 남아있어 정규식이 실패했음
(예: "마산회원구 회원동...", "덕양구 주교동...").
수정: 동/리/가 매칭 전에 optional 구/읍/면 토큰을 건너뛰도록 정규식 보강.

출력: results/phase7_c_match_improvement.md
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
print("Phase 7 Track C: 주소 파싱 개선")
print("=" * 70)


def strip_sido_sigungu(addr_raw, sido, sigungu):
    s = str(addr_raw)
    if sido and s.startswith(str(sido)):
        s = s[len(str(sido)):].strip()
    if sigungu and s.startswith(str(sigungu)):
        s = s[len(str(sigungu)):].strip()
    return s


# v1: 구/읍/면 접두 미고려
def extract_dong_v1(remainder):
    m = re.match(r"\s*([가-힣0-9]+(?:동|리|가))", remainder)
    return m.group(1) if m else None


# v2: optional 구/읍/면 토큰을 먼저 건너뛴 뒤 동/리/가 캡처
def extract_dong_v2(remainder):
    m = re.match(r"\s*(?:[가-힣0-9]+(?:구|읍|면)\s+)?([가-힣0-9]+(?:동|리|가))", str(remainder))
    return m.group(1) if m else None


def extract_jibun(remainder):
    m = re.search(r"(\d+(?:-\d+)?)", str(remainder))
    return m.group(1) if m else None


def extract_complex_name(remainder):
    m = re.search(r"([가-힣0-9]+(?:아파트|맨션|타운|파크|캐슬|팰리스|빌리지|하이츠|스위트|그린빌|힐스))", str(remainder))
    return m.group(1) if m else None


def normalize_name(name):
    return re.sub(r"[^가-힣0-9]", "", str(name)) if name else ""


print("\n[1] 검증셋 로드 중...")
conn = sqlite3.connect(NPL_DB)
df = pd.read_sql_query(
    """
    SELECT id, address_sido, address_sigungu, address_raw, building_area_sqm,
           appraisal_amount, hammer_price, hammer_rate
    FROM onbid_auction_results
    WHERE asset_type_norm = '주거용건물'
      AND hammer_price IS NOT NULL AND hammer_price > 0
      AND building_area_sqm IS NOT NULL AND building_area_sqm > 0
    """,
    conn,
)
conn.close()
print(f"  [OK] {len(df)}건")

df["remainder"] = df.apply(lambda r: strip_sido_sigungu(r["address_raw"], r["address_sido"], r["address_sigungu"]), axis=1)
df["dong_v1"] = df["remainder"].apply(extract_dong_v1)
df["dong_v2"] = df["remainder"].apply(extract_dong_v2)

n_v1 = df["dong_v1"].notna().sum()
n_v2 = df["dong_v2"].notna().sum()
print(f"\n[2] 동 추출률 비교")
print(f"  v1 (기존): {n_v1}/{len(df)}건 ({n_v1/len(df)*100:.1f}%)")
print(f"  v2 (구/읍/면 스킵 추가): {n_v2}/{len(df)}건 ({n_v2/len(df)*100:.1f}%)")

df["jibun"] = df["remainder"].apply(extract_jibun)
df["complex_norm"] = df["remainder"].apply(extract_complex_name).apply(normalize_name)

print("\n[3] RTMS 비교사례 로드 및 재매칭 중...")
rcon = duckdb.connect(RTMS_DUCKDB, read_only=True)
rtms = rcon.execute(
    "SELECT umd_nm, complex_name_norm, jibun_norm, exclusive_area_sqm, price_per_sqm FROM rtms_comparable_mart"
).fetchdf()
rcon.close()
rtms_by_dong = {d: g for d, g in rtms.groupby("umd_nm")}


def match_with_dong_col(dong_col):
    tiers, grounded = [], []
    for _, row in df.iterrows():
        cand = rtms_by_dong.get(row[dong_col])
        tier, ppsqm = "T3", None
        if cand is not None and row["jibun"]:
            exact = cand[cand["jibun_norm"] == row["jibun"]]
            if len(exact) > 0:
                tier, ppsqm = "T1", exact["price_per_sqm"].median()
        if tier == "T3" and cand is not None and row["complex_norm"]:
            fuzzy = cand[cand["complex_name_norm"].apply(normalize_name) == row["complex_norm"]]
            area = row["building_area_sqm"]
            fuzzy = fuzzy[(fuzzy["exclusive_area_sqm"] >= area * 0.85) & (fuzzy["exclusive_area_sqm"] <= area * 1.15)]
            if len(fuzzy) > 0:
                tier, ppsqm = "T2", fuzzy["price_per_sqm"].median()
        tiers.append(tier)
        grounded.append(ppsqm * row["building_area_sqm"] if ppsqm else None)
    return tiers, grounded


tiers_v1, grounded_v1 = match_with_dong_col("dong_v1")
tiers_v2, grounded_v2 = match_with_dong_col("dong_v2")

matched_v1 = sum(1 for t in tiers_v1 if t != "T3")
matched_v2 = sum(1 for t in tiers_v2 if t != "T3")

print(f"\n[4] 매칭 성공 표본 비교")
print(f"  v1 (기존): {matched_v1}건")
print(f"  v2 (개선): {matched_v2}건")

df["tier_v2"] = tiers_v2
df["grounded_market_price_v2"] = grounded_v2

matched_v2_df = df[df["grounded_market_price_v2"].notna()].copy()
if len(matched_v2_df) > 0:
    mape_a_v2 = np.mean(np.abs(matched_v2_df["grounded_market_price_v2"] - matched_v2_df["appraisal_amount"]) / matched_v2_df["appraisal_amount"]) * 100
    print(f"\n[5] 검증 A (v2 확대 표본): MAPE {mape_a_v2:.2f}% (n={len(matched_v2_df)})")
else:
    mape_a_v2 = None

report = f"""# Phase 7 Track C: 주소 파싱 개선 결과

**실행일**: 2026-07-03

## 동 추출률 개선

| 버전 | 추출 성공 | 비율 |
|---|---:|---:|
| v1 (기존, 구/읍/면 미고려) | {n_v1}/{len(df)} | {n_v1/len(df)*100:.1f}% |
| v2 (구/읍/면 optional skip 추가) | {n_v2}/{len(df)} | {n_v2/len(df)*100:.1f}% |

## 매칭 성공 표본 개선 (T1+T2)

| 버전 | 표본 수 |
|---|---:|
| v1 | {matched_v1}건 |
| v2 | {matched_v2}건 |

## 검증 A 재실행 (v2, 확대 표본)

- MAPE: {f'{mape_a_v2:.2f}%' if mape_a_v2 is not None else 'N/A'} (n={len(matched_v2_df) if mape_a_v2 is not None else 0})
- 참고: Session 21 원래 결과는 MAPE 9.40% (n=32)

## 남은 미매칭 사례 (v2 기준)

여전히 동 추출에 실패하는 케이스는 도로명주소 형식(예: "강릉대로 303번길...") 또는
마스킹된 지번("**-**")으로, 본 정규식 접근으로는 해결 불가 — 별도 도로명-지번 변환
테이블 또는 원본 데이터 재확인이 필요함 (Go/No-Go: 이번 라운드에서는 보류).
"""
with open(RESULTS_DIR / "phase7_c_match_improvement.md", "w", encoding="utf-8") as f:
    f.write(report)

print(f"\n[OK] {RESULTS_DIR / 'phase7_c_match_improvement.md'}")

# v2 매칭 결과를 다음 트랙(D)에서 재사용할 수 있도록 저장
df.to_csv(RESULTS_DIR / "phase7_c_validation_set_v2.csv", index=False, encoding="utf-8-sig")
print(f"[OK] {RESULTS_DIR / 'phase7_c_validation_set_v2.csv'} (Track D에서 재사용)")

print("\n" + "=" * 70)
print("[DONE] Track C 완료")
print("=" * 70)
