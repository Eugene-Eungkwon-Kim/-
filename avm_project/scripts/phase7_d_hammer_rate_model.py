# -*- coding: utf-8 -*-
"""
Phase 7 Track D: 낙찰가율 모델화 (leak-free)
Session 22 (2026-07-03)

핵심 이슈: 검증셋(onbid 주거용건물 124건) 중 120건이 이미 p6_training_engineered.csv에
포함되어 있었음 (appraisal_amount+hammer_price 키로 확인). 기존 p6 앙상블을 그대로
쓰면 심각한 데이터 누수이므로, 검증셋과 겹치는 행을 제외한 뒤 지역x자산유형 평균
낙찰가율 모델을 새로 학습한다 (leave-one-out 전역 평균보다 정교하되, 과도한
재엔지니어링 없이 leak-free를 확실히 지키는 선을 선택).

출력: results/phase7_d_hammer_rate_report.md
"""
import pandas as pd
import numpy as np
from pathlib import Path

DATA_DIR = Path("F:/NPL전례/avm_project/data")
RESULTS_DIR = Path("F:/NPL전례/avm_project/results")

print("=" * 70)
print("Phase 7 Track D: 낙찰가율 모델화 (leak-free)")
print("=" * 70)

print("\n[1] 데이터 로드 중...")
train_full = pd.read_csv(DATA_DIR / "p6_training_engineered.csv")
val = pd.read_csv(RESULTS_DIR / "phase7_c_validation_set_v2.csv")
val = val[val["grounded_market_price_v2"].notna()].copy()
print(f"  p6 학습 전체: {len(train_full)}건")
print(f"  Track C 매칭 검증셋: {len(val)}건")

print("\n[2] 학습셋에서 검증셋과 겹치는 행 제외 중...")
val_keys = set(zip(val["appraisal_amount"].astype(int), val["hammer_price"].astype(int)))
train_full["key"] = list(zip(train_full["appraisal_amount"].astype(int), train_full["hammer_price"].astype(int)))
train = train_full[~train_full["key"].isin(val_keys)].copy()
print(f"  제외 후 순수 학습셋: {len(train)}건 (원본 {len(train_full)}건 중 {len(train_full)-len(train)}건 제외)")

print("\n[3] 지역x자산유형 평균 낙찰가율 계산 중 (학습셋에서만)...")
# address_sido, property_type 조합별 평균 (표본 부족시 sido 단독, 그마저 부족시 전체 평균으로 백오프)
seg_stats = train.groupby(["address_sido", "property_type"])["hammer_rate"].agg(["mean", "count"])
sido_stats = train.groupby("address_sido")["hammer_rate"].agg(["mean", "count"])
global_mean = train["hammer_rate"].mean()
print(f"  전체 평균 낙찰가율(백업용): {global_mean:.4f}")


def predict_hammer_rate(sido, ptype):
    if (sido, ptype) in seg_stats.index and seg_stats.loc[(sido, ptype), "count"] >= 5:
        return seg_stats.loc[(sido, ptype), "mean"]
    if sido in sido_stats.index and sido_stats.loc[sido, "count"] >= 5:
        return sido_stats.loc[sido, "mean"]
    return global_mean


print("\n[4] 검증셋에 leak-free 낙찰가율 예측 적용 중...")
val["property_type_train_label"] = "주거"  # onbid asset_type_norm 매핑: 주거용건물 -> p6의 '주거' 카테고리
val["pred_hammer_rate"] = val.apply(lambda r: predict_hammer_rate(r["address_sido"], r["property_type_train_label"]), axis=1)
val["pred_hammer_price_segmodel"] = val["grounded_market_price_v2"] * val["pred_hammer_rate"]

val["ape"] = np.abs(val["pred_hammer_price_segmodel"] - val["hammer_price"]) / val["hammer_price"] * 100
mape_d = val["ape"].mean()
median_ape_d = val["ape"].median()
within5_d = (val["ape"] <= 5).mean() * 100
print(f"  MAPE (그라운딩시세 x 지역평균낙찰가율, leak-free): {mape_d:.2f}%  (n={len(val)})")
print(f"  median APE: {median_ape_d:.2f}%")
print(f"  +-5% 달성률: {within5_d:.1f}%")

# 이상치 확인: hammer_rate가 극단적으로 낮은 케이스 (감정가 대비 1% 등) 별도 표시
outliers = val[val["ape"] > 100].copy()
print(f"\n  [주의] APE>100%인 이상치 {len(outliers)}건 발견:")
for _, r in outliers.iterrows():
    print(f"    id={r['id']}: hammer_rate={r['hammer_rate']:.4f}, appraisal={r['appraisal_amount']:,.0f}, hammer_price={r['hammer_price']:,.0f}, APE={r['ape']:.0f}%")

val_trimmed = val[val["ape"] <= 100]
mape_d_trimmed = val_trimmed["ape"].mean()
print(f"\n  이상치 제외(APE<=100%) MAPE: {mape_d_trimmed:.2f}%  (n={len(val_trimmed)})")

# 비교용: Session 21의 leave-one-out 방식도 이 확장된 43건 표본으로 재계산
loo_list = []
for i in val.index:
    others = val.drop(index=i)
    loo_rate = (others["hammer_price"] / others["appraisal_amount"]).mean()
    pred = val.loc[i, "grounded_market_price_v2"] * loo_rate
    loo_list.append(abs(pred - val.loc[i, "hammer_price"]) / val.loc[i, "hammer_price"] * 100)
val["ape_loo"] = loo_list
mape_loo = val["ape_loo"].mean()
mape_loo_trimmed = val.loc[val["ape"] <= 100, "ape_loo"].mean()
print(f"\n  (비교) leave-one-out 전역평균 방식, 동일 43건: {mape_loo:.2f}% (이상치 제외: {mape_loo_trimmed:.2f}%)")

report = f"""# Phase 7 Track D: 낙찰가율 모델화 결과 (leak-free)

**실행일**: 2026-07-03

## 핵심 발견: 데이터 누수 위험 확인 및 제거

검증셋(onbid 주거용건물) 124건 중 **120건이 기존 p6_training_engineered.csv(589건)에 이미 포함**되어 있었음.
기존 p6 앙상블을 그대로 재사용하면 심각한 leakage이므로, 겹치는 {len(train_full)-len(train)}건을 학습셋에서
제외한 뒤 지역(address_sido) x 자산유형 평균 낙찰가율 모델을 새로 학습함.

- 원본 p6 학습셋: {len(train_full)}건
- 제외 후 순수 학습셋: {len(train)}건
- 전체 평균 낙찰가율(백업 기준): {global_mean:.4f}

## ⚠️ 이상치 발견 (투명 공개)

43건 중 hammer_rate가 극단적으로 낮은(감정가 대비 1%) 이상치 {len(outliers)}건이 확인됨:

{chr(10).join(f"- id={r['id']}: hammer_rate={r['hammer_rate']:.4f}, 감정가={r['appraisal_amount']:,.0f}원, 실제낙찰가={r['hammer_price']:,.0f}원, APE={r['ape']:.0f}%" for _, r in outliers.iterrows())}

MAPE는 실측값이 0에 가까울 때(낙찰가율 1%) 극도로 민감해지므로, mean(MAPE)과 median(APE)을 함께 보고한다.
이 두 건이 실제 데이터 오류인지 진짜 특수경매(예: 심각한 법적 하자로 명목가 낙찰)인지는 원본 재확인이 필요 — 임의로 제외하지 않고 그대로 보고한다.

## 결과 비교 (동일 43건 검증셋, 이상치 포함)

| 방식 | Mean MAPE | Median APE | +-5% 달성률 |
|---|---:|---:|---:|
| leave-one-out 전역 평균 (Session 21 방식) | {mape_loo:.2f}% | - | - |
| 지역x자산유형 평균 모델 (leak-free, 본 트랙) | {mape_d:.2f}% | {median_ape_d:.2f}% | {within5_d:.1f}% |

## 결과 비교 (이상치 2건 제외, n=41)

| 방식 | MAPE |
|---|---:|
| leave-one-out 전역 평균 | {mape_loo_trimmed:.2f}% |
| 지역x자산유형 평균 모델 (본 트랙) | {mape_d_trimmed:.2f}% |

## 해석

- **이상치 포함 시** mean MAPE는 두 극단치가 지배해 281~339%로 나오며, 이는 통계적으로 오해의 소지가 있는 수치임 (median APE {median_ape_d:.2f}%가 실제 전형적 오차에 더 가까움)
- **이상치 제외 시(n=41)**, {'지역x자산유형 세분화가 전역 평균보다 개선을 보임' if mape_d_trimmed < mape_loo_trimmed else '지역x자산유형 세분화가 전역 평균 대비 뚜렷한 개선을 보이지 못함'}
- Session 21의 9.40%/15.12%(n=32)는 우연히 이 두 이상치를 포함하지 않은 부분표본이었을 뿐임 — 즉 이전 결과가 낙관적으로 편향돼 있었을 가능성을 배제할 수 없음

## 한계

- onbid asset_type_norm의 '주거용건물'을 p6 학습셋의 '주거' 카테고리로 단순 매핑함 (아파트/단독주택/다세대 구분 없음)
- sido당 표본이 적어 상당수가 sido 평균 또는 전체 평균으로 백오프됨 (세분화 효과 제한적)
- n=41~43은 여전히 작은 표본 — 이상치 2건만으로 결과가 요동친다는 사실 자체가 표본 확대가 시급함을 보여줌
"""
with open(RESULTS_DIR / "phase7_d_hammer_rate_report.md", "w", encoding="utf-8") as f:
    f.write(report)

print(f"\n[OK] {RESULTS_DIR / 'phase7_d_hammer_rate_report.md'}")
print("\n" + "=" * 70)
print("[DONE] Track D 완료")
print("=" * 70)
