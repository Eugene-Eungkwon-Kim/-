#!/usr/bin/env python3
"""
시간 기반 분할 평가 파이프라인 (Temporal Split)
실거래 AVM의 누수 없는 평가를 위한 핵심 인프라.

랜덤 K-fold는 "미래 거래를 보고 과거를 맞추는" 누수를 허용한다.
실전(미래 예측)을 모사하려면 반드시 시간순으로 분할해야 한다:
  학습(과거) → 검증 → 테스트(미래, 1회 개봉)
"""

import argparse
import json
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error


def temporal_split(df: pd.DataFrame, time_col: str, ratios=(0.7, 0.15, 0.15)):
    """시간순 정렬 후 train/val/test 분할."""
    df = df.sort_values(time_col).reset_index(drop=True)
    n = len(df)
    a = int(n * ratios[0])
    b = int(n * (ratios[0] + ratios[1]))
    return df.iloc[:a], df.iloc[a:b], df.iloc[b:]


def evaluate(df, features, target, time_col):
    train, val, test = temporal_split(df, time_col)
    print(f"   분할: train={len(train)}  val={len(val)}  test={len(test)}")

    def xy(part):
        X = part[features].fillna(train[features].median())
        return X, part[target]

    Xtr, ytr = xy(train)
    Xva, yva = xy(val)
    Xte, yte = xy(test)

    model = GradientBoostingRegressor(random_state=42)
    model.fit(Xtr, ytr)

    res = {}
    for name, (X, y) in {"val": (Xva, yva), "test": (Xte, yte)}.items():
        pred = model.predict(X)
        res[name] = {
            "r2": float(r2_score(y, pred)),
            "rmse": float(np.sqrt(mean_squared_error(y, pred))),
            "mae": float(mean_absolute_error(y, pred)),
        }
    return res


def main():
    ap = argparse.ArgumentParser(description="시간 기반 분할 평가")
    ap.add_argument("--data", required=True)
    ap.add_argument("--target", required=True)
    ap.add_argument("--time-col", required=True, help="거래일/시점 컬럼 (필수)")
    ap.add_argument("--features", nargs="*", default=None,
                    help="사용할 특성 (미지정 시 수치형 전체 - 타겟/시점 제외)")
    args = ap.parse_args()

    print("=" * 60)
    print("⏳ 시간 기반 분할 평가 (Temporal Split)")
    print("=" * 60)

    df = pd.read_csv(args.data)
    if args.time_col not in df.columns:
        raise SystemExit(
            f"❌ 시간 컬럼 '{args.time_col}' 없음.\n"
            f"   실거래 데이터는 거래일 컬럼이 필수입니다.\n"
            f"   사용 가능 컬럼: {list(df.columns)}"
        )

    if args.features:
        features = args.features
    else:
        drop = {args.target, args.time_col}
        features = [c for c in df.select_dtypes(include=[np.number]).columns if c not in drop]

    print(f"데이터: {args.data}  ({len(df):,}행)")
    print(f"타겟:   {args.target}   시점: {args.time_col}")
    print(f"특성:   {len(features)}개\n")

    res = evaluate(df, features, args.target, args.time_col)

    print("\n📊 결과 (미래 데이터 기준 — 실전 성능)")
    print("-" * 60)
    for split in ("val", "test"):
        m = res[split]
        print(f"   {split:5s}  R²={m['r2']:.4f}  RMSE={m['rmse']:.1f}  MAE={m['mae']:.1f}")

    out = Path("output") / f"temporal_eval_{datetime.now():%Y%m%d_%H%M%S}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({
        "timestamp": datetime.now().isoformat(),
        "data": args.data, "target": args.target, "time_col": args.time_col,
        "n_features": len(features), "results": res,
    }, indent=2, ensure_ascii=False))
    print(f"\n📁 저장: {out}")

    test_r2 = res["test"]["r2"]
    print(f"\n🎯 테스트셋(미래) R² = {test_r2:.4f}")
    if test_r2 >= 0.95:
        print("   🚨 0.95 도달 — 게이트 D 발동: leakage_audit.py 강제 재실행 필요")
    elif test_r2 >= 0.85:
        print("   ✅ 업계 수준 진입")
    else:
        print("   ⚠️  추가 데이터/특성 필요")


if __name__ == "__main__":
    main()
