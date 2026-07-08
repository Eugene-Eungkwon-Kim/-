# -*- coding: utf-8 -*-
"""
Phase 7-3/7-4: 시세 그라운딩 예측기 + 정직한 검증
Session 21 Track B.4/B.5 (2026-07-03)

검증 대상: onbid_auction_results 중 '주거용건물' (실제 hammer_price 보유, 124건)
  - 이 표본은 p6 학습에 이미 쓰인 데이터와 겹칠 수 있으나(같은 소스),
    RTMS 그라운딩 예측기 자체는 이 데이터로 훈련되지 않았으므로
    "그라운딩 방식이 실제로 작동하는가"를 보는 데는 문제 없음.

방법:
  1) address_raw에서 동/지번 추출 -> RTMS 비교사례 매칭 (T1/T2/T3)
  2) 매칭된 비교사례의 price_per_sqm 중앙값 x 건물면적 = 그라운딩 시세 추정치
  3) 검증 A: 그라운딩 시세 추정치 vs 실제 appraisal_amount (감정가) - 시세 추정 자체의 타당성
  4) 검증 B: 그라운딩 시세 추정치 x 평균 낙찰가율(leave-one-out) vs 실제 hammer_price
     - 낙찰가율 자체는 검증되지 않은 단순 평균이므로 참고치로만 사용
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
print("Phase 7-3/7-4: 시세 그라운딩 예측기 검증")
print("=" * 70)

SIDO_SUFFIX = r"(?:특별시|광역시|특별자치시|특별자치도|도)"


def strip_sido_sigungu(addr_raw, sido, sigungu):
    s = str(addr_raw)
    if sido and s.startswith(str(sido)):
        s = s[len(str(sido)):].strip()
    if sigungu and s.startswith(str(sigungu)):
        s = s[len(str(sigungu)):].strip()
    return s


def extract_dong(remainder):
    m = re.match(r"\s*([가-힣0-9]+(?:동|리|가))", remainder)
    return m.group(1) if m else None


def extract_jibun(remainder):
    m = re.search(r"(\d+(?:-\d+)?)", remainder)
    return m.group(1) if m else None


def extract_complex_name(remainder):
    m = re.search(r"([가-힣0-9]+(?:아파트|맨션|타운|파크|캐슬|팰리스|빌리지|하이츠|스위트|그린빌|힐스))", remainder)
    return m.group(1) if m else None


def normalize_name(name):
    if not name:
        return ""
    return re.sub(r"[^가-힣0-9]", "", str(name))


print("\n[1] 검증용 데이터 로드 중 (onbid 주거용건물, 실제 hammer_price 보유)...")
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
df["dong"] = df["remainder"].apply(extract_dong)
df["jibun"] = df["remainder"].apply(extract_jibun)
df["complex_norm"] = df["remainder"].apply(extract_complex_name).apply(normalize_name)

print(f"  동 추출: {df['dong'].notna().sum()}건, 지번 추출: {df['jibun'].notna().sum()}건")

print("\n[2] RTMS 비교사례 로드 중...")
rcon = duckdb.connect(RTMS_DUCKDB, read_only=True)
rtms = rcon.execute(
    "SELECT umd_nm, complex_name_norm, jibun_norm, exclusive_area_sqm, price_per_sqm FROM rtms_comparable_mart"
).fetchdf()
rcon.close()
rtms_by_dong = {d: g for d, g in rtms.groupby("umd_nm")}
print(f"  [OK] {len(rtms)}건")

print("\n[3] 매칭 및 그라운딩 시세 산출 중...")
tiers, grounded = [], []
for _, row in df.iterrows():
    cand = rtms_by_dong.get(row["dong"])
    tier, ppsqm, n = "T3", None, 0

    if cand is not None and row["jibun"]:
        exact = cand[cand["jibun_norm"] == row["jibun"]]
        if len(exact) > 0:
            tier, ppsqm, n = "T1", exact["price_per_sqm"].median(), len(exact)

    if tier == "T3" and cand is not None and row["complex_norm"]:
        fuzzy = cand[cand["complex_name_norm"].apply(normalize_name) == row["complex_norm"]]
        area = row["building_area_sqm"]
        fuzzy = fuzzy[(fuzzy["exclusive_area_sqm"] >= area * 0.85) & (fuzzy["exclusive_area_sqm"] <= area * 1.15)]
        if len(fuzzy) > 0:
            tier, ppsqm, n = "T2", fuzzy["price_per_sqm"].median(), len(fuzzy)

    tiers.append(tier)
    grounded.append(ppsqm * row["building_area_sqm"] if ppsqm else None)

df["tier"] = tiers
df["grounded_market_price"] = grounded

t1n, t2n, t3n = (df["tier"] == "T1").sum(), (df["tier"] == "T2").sum(), (df["tier"] == "T3").sum()
print(f"  T1: {t1n}건, T2: {t2n}건, T3(매칭실패): {t3n}건")

matched = df[df["grounded_market_price"].notna()].copy()
print(f"  매칭 성공(T1+T2): {len(matched)}건 / 전체 {len(df)}건")

print("\n[4] 검증 A: 그라운딩 시세 추정치 vs 실제 감정가(appraisal_amount)...")
if len(matched) > 0:
    mape_a = np.mean(np.abs(matched["grounded_market_price"] - matched["appraisal_amount"]) / matched["appraisal_amount"]) * 100
    print(f"  MAPE (그라운딩 시세 vs 감정가): {mape_a:.2f}%  (n={len(matched)})")
else:
    mape_a = None
    print("  매칭된 표본 없음")

print("\n[5] 검증 B: 그라운딩 시세 x 평균 낙찰가율(leave-one-out) vs 실제 hammer_price...")
mape_b_list = []
for i in matched.index:
    others = matched.drop(index=i)
    if len(others) < 2:
        continue
    loo_rate = (others["hammer_price"] / others["appraisal_amount"]).mean()
    pred_hammer = matched.loc[i, "grounded_market_price"] * loo_rate
    actual_hammer = matched.loc[i, "hammer_price"]
    mape_b_list.append(abs(pred_hammer - actual_hammer) / actual_hammer * 100)

mape_b = np.mean(mape_b_list) if mape_b_list else None
within5_b = np.mean([m <= 5 for m in mape_b_list]) * 100 if mape_b_list else None
if mape_b is not None:
    print(f"  MAPE (그라운딩x낙찰가율 vs 실제 hammer_price, leave-one-out): {mape_b:.2f}%  (n={len(mape_b_list)})")
    print(f"  +-5% 달성률: {within5_b:.1f}%")

report = f"""# Phase 7-3/7-4: 시세 그라운딩 예측기 검증 결과 (실측)

**실행일**: 2026-07-03
**검증 표본**: onbid_auction_results '주거용건물' 중 hammer_price 보유 {len(df)}건

## 매칭 결과

| Tier | 건수 | 비율 |
|---|---:|---:|
| T1 (지번 정확) | {t1n} | {t1n/len(df)*100:.1f}% |
| T2 (단지명+면적) | {t2n} | {t2n/len(df)*100:.1f}% |
| T3 (매칭 실패) | {t3n} | {t3n/len(df)*100:.1f}% |

## 검증 A: 그라운딩 시세 추정치 vs 실제 감정가

- MAPE: {f'{mape_a:.2f}%' if mape_a is not None else 'N/A'} (n={len(matched)})
- 의미: RTMS 실거래 비교사례로 산출한 시세 추정치가 감정평가사의 감정가와 얼마나 가까운지

## 검증 B: 그라운딩 시세 x 낙찰가율 vs 실제 낙찰가 (참고치)

- MAPE: {f'{mape_b:.2f}%' if mape_b is not None else 'N/A'} (leave-one-out, n={len(mape_b_list) if mape_b_list else 0})
- +-5% 달성률: {f'{within5_b:.1f}%' if within5_b is not None else 'N/A'}
- **주의**: 낙찰가율은 검증된 모델이 아니라 나머지 표본의 단순 평균(leave-one-out)이다.
  따라서 이 수치에는 (1) 시세 매칭 오차 + (2) 낙찰가율 단순화 오차가 함께 섞여 있다.

## 기존 방식과 비교

| 방식 | 표본 | MAPE |
|---|---:|---:|
| 순수 회귀 (p6, 589건, leak-free holdout) | 118 | 66.64% |
| 시세 그라운딩 (검증 A, 감정가 대비) | {len(matched)} | {f'{mape_a:.2f}%' if mape_a is not None else 'N/A'} |
| 시세 그라운딩 x 낙찰가율 (검증 B, 실제 낙찰가 대비) | {len(mape_b_list) if mape_b_list else 0} | {f'{mape_b:.2f}%' if mape_b is not None else 'N/A'} |
"""
RESULTS_DIR.mkdir(exist_ok=True)
with open(RESULTS_DIR / "phase7_final_report.md", "w", encoding="utf-8") as f:
    f.write(report)

print(f"\n[OK] {RESULTS_DIR / 'phase7_final_report.md'}")
print("\n" + "=" * 70)
print("[DONE] Phase 7-3/7-4 완료")
print("=" * 70)
