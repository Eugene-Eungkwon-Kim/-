#!/usr/bin/env python3
"""
데이터 누수 감사 도구 (Leakage Audit)
R² ≥ 0.95 목표 추진 시 "진짜 성능 vs 누수"를 구별하는 핵심 검증 도구.

핵심 검사:
  1. 특성-타겟 상관 임계 초과 탐지
  2. 단일 특성 제거 시 R² 급락(=누수 의존) 탐지
  3. 시간 기반 분할 vs 랜덤 분할 R² 격차 탐지
"""

import argparse
import json
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import KFold, cross_val_score


# 누수 판정 임계값
CORR_THRESHOLD = 0.95          # 특성-타겟 상관 0.95 초과 = 누수 의심
DROP_R2_THRESHOLD = 0.10       # 단일 특성 제거 시 R² 0.10 이상 급락 = 누수 의존
SPLIT_GAP_THRESHOLD = 0.10     # 랜덤-시간 분할 R² 격차 0.10 초과 = 누수 의심


def audit_correlations(df: pd.DataFrame, target: str) -> list:
    """검사 1: 타겟과 과도하게 상관된 특성 탐지."""
    print("\n[검사 1] 특성-타겟 상관 분석")
    print("-" * 60)
    flags = []
    numeric = df.select_dtypes(include=[np.number])
    if target not in numeric.columns:
        print(f"   ⚠️  타겟 '{target}' 수치형 아님 — 상관 검사 생략")
        return flags

    corr = numeric.corr()[target].drop(target).abs().sort_values(ascending=False)
    for feat, c in corr.items():
        mark = "🚨 누수의심" if c > CORR_THRESHOLD else ("⚠️ 높음" if c > 0.85 else "✅")
        if c > 0.85:
            print(f"   {mark}  {feat}: |r|={c:.4f}")
        if c > CORR_THRESHOLD:
            flags.append({"check": "correlation", "feature": feat, "value": float(c)})
    if not flags:
        print(f"   ✅ 상관 {CORR_THRESHOLD} 초과 특성 없음")
    return flags


def audit_feature_dependence(X: pd.DataFrame, y: pd.Series) -> list:
    """검사 2: 단일 특성 제거 시 R² 급락(=특정 특성에 의존) 탐지."""
    print("\n[검사 2] 단일 특성 제거 민감도 (누수 의존 탐지)")
    print("-" * 60)
    flags = []
    cv = KFold(n_splits=5, shuffle=True, random_state=42)
    model = GradientBoostingRegressor(random_state=42)

    base = cross_val_score(model, X, y, cv=cv, scoring="r2").mean()
    print(f"   기준 R² (전체 특성): {base:.4f}")

    for col in X.columns:
        reduced = cross_val_score(model, X.drop(columns=[col]), y, cv=cv, scoring="r2").mean()
        drop = base - reduced
        if drop > DROP_R2_THRESHOLD:
            print(f"   🚨 {col} 제거 시 R² {base:.4f} → {reduced:.4f} (Δ-{drop:.4f}) 단일 특성 과의존")
            flags.append({"check": "dependence", "feature": col, "r2_drop": float(drop)})
    if not flags:
        print(f"   ✅ 단일 특성 제거로 {DROP_R2_THRESHOLD} 이상 급락하는 특성 없음")
    return flags


def audit_split_gap(df: pd.DataFrame, X: pd.DataFrame, y: pd.Series, time_col: str | None) -> list:
    """검사 3: 랜덤 분할 vs 시간 분할 R² 격차 탐지."""
    print("\n[검사 3] 랜덤 분할 vs 시간 분할 격차")
    print("-" * 60)
    flags = []
    model = GradientBoostingRegressor(random_state=42)

    cv = KFold(n_splits=5, shuffle=True, random_state=42)
    random_r2 = cross_val_score(model, X, y, cv=cv, scoring="r2").mean()
    print(f"   랜덤 K-fold R²: {random_r2:.4f}")

    if time_col and time_col in df.columns:
        order = df[time_col].argsort()
        cut = int(len(df) * 0.8)
        tr, te = order[:cut], order[cut:]
        model.fit(X.iloc[tr], y.iloc[tr])
        time_r2 = model.score(X.iloc[te], y.iloc[te])
        gap = random_r2 - time_r2
        print(f"   시간 분할 R²:  {time_r2:.4f}")
        print(f"   격차: {gap:.4f}")
        if gap > SPLIT_GAP_THRESHOLD:
            print(f"   🚨 격차 {SPLIT_GAP_THRESHOLD} 초과 — 랜덤 분할이 미래 누수로 부풀려졌을 가능성")
            flags.append({"check": "split_gap", "gap": float(gap)})
        else:
            print("   ✅ 격차 허용 범위")
    else:
        print(f"   ⚠️  시간 컬럼('{time_col}') 없음 — 시간 분할 검사 생략")
        print("       (실데이터에서는 거래일 컬럼으로 반드시 재실행 권장)")
    return flags


def main():
    ap = argparse.ArgumentParser(description="데이터 누수 감사 도구")
    ap.add_argument("--data", required=True, help="CSV 경로")
    ap.add_argument("--target", required=True, help="타겟 컬럼명")
    ap.add_argument("--time-col", default=None, help="거래일/시점 컬럼명 (선택)")
    ap.add_argument("--max-rows", type=int, default=5000, help="검사 표본 상한")
    args = ap.parse_args()

    print("=" * 60)
    print("🔍 데이터 누수 감사 (Leakage Audit)")
    print("=" * 60)
    print(f"데이터: {args.data}")
    print(f"타겟:   {args.target}")

    df = pd.read_csv(args.data)
    if len(df) > args.max_rows:
        df = df.sample(args.max_rows, random_state=42).reset_index(drop=True)
        print(f"표본:   {len(df):,}행 (샘플링)")

    if args.target not in df.columns:
        raise SystemExit(f"❌ 타겟 '{args.target}' 컬럼 없음. 사용 가능: {list(df.columns)}")

    y = df[args.target]
    drop_cols = [args.target] + ([args.time_col] if args.time_col else [])
    X = df.drop(columns=[c for c in drop_cols if c in df.columns]).select_dtypes(include=[np.number])
    X = X.fillna(X.median())

    all_flags = []
    all_flags += audit_correlations(df, args.target)
    all_flags += audit_feature_dependence(X, y)
    all_flags += audit_split_gap(df, X, y, args.time_col)

    print("\n" + "=" * 60)
    print("📋 감사 결과 요약")
    print("=" * 60)
    if all_flags:
        print(f"🚨 누수 의심 플래그: {len(all_flags)}건")
        for f in all_flags:
            print(f"   • {f}")
        verdict = "LEAKAGE_SUSPECTED"
    else:
        print("✅ 누수 의심 플래그 없음 — 현재 특성셋은 정직한 것으로 보임")
        verdict = "CLEAN"

    out = Path("output") / f"leakage_audit_{datetime.now():%Y%m%d_%H%M%S}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({
        "timestamp": datetime.now().isoformat(),
        "data": args.data,
        "target": args.target,
        "verdict": verdict,
        "flags": all_flags,
        "thresholds": {
            "correlation": CORR_THRESHOLD,
            "r2_drop": DROP_R2_THRESHOLD,
            "split_gap": SPLIT_GAP_THRESHOLD,
        },
    }, indent=2, ensure_ascii=False))
    print(f"\n📁 리포트 저장: {out}")
    print(f"🎯 판정: {verdict}")


if __name__ == "__main__":
    main()
