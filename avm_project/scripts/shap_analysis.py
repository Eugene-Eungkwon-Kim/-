#!/usr/bin/env python3
"""
SHAP 모델 설명성 분석
최고 성능 모델 (Gradient Boosting)의 특성 중요도 분석
"""

import numpy as np
import pandas as pd
import json
from datetime import datetime
from pathlib import Path
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import r2_score

try:
    import shap
    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False
    print("⚠️  shap 라이브러리 미설치. 'pip install shap' 실행 후 재시도하세요.")

def temporal_split(df, time_col, ratios=(0.7, 0.15, 0.15)):
    """시간순 정렬 후 train/val/test 분할."""
    df = df.sort_values(time_col).reset_index(drop=True)
    n = len(df)
    a = int(n * ratios[0])
    b = int(n * (ratios[0] + ratios[1]))
    return df.iloc[:a], df.iloc[a:b], df.iloc[b:]

def shap_analysis(data_path, target_col, time_col):
    """SHAP 분석 실행"""

    print("=" * 80)
    print("🔍 SHAP 모델 설명성 분석")
    print("=" * 80)

    if not HAS_SHAP:
        print("❌ SHAP 라이브러리 필요. 설치 후 재실행하세요.")
        return

    # 데이터 로드
    df = pd.read_csv(data_path)
    print(f"✅ 데이터 로드: {len(df):,}행\n")

    # 시간순 분할
    train, val, test = temporal_split(df, time_col)

    def prepare_data(part):
        X = part.select_dtypes(include=[np.number]).drop(columns=[target_col] if target_col in part.columns else [])
        X = X.fillna(train.select_dtypes(include=[np.number]).median())
        y = part[target_col]
        return X, y

    X_train, y_train = prepare_data(train)
    X_test, y_test = prepare_data(test)

    print(f"특성: {list(X_train.columns)}\n")

    # Gradient Boosting 모델 학습
    print("📊 최고 성능 모델 학습 중 (Gradient Boosting)...")
    model = GradientBoostingRegressor(n_estimators=100, learning_rate=0.1, random_state=42)
    model.fit(X_train, y_train)

    # 테스트 성능
    y_pred = model.predict(X_test)
    r2 = r2_score(y_test, y_pred)
    print(f"✅ 테스트 R² = {r2:.4f}\n")

    # SHAP 분석
    print("🔍 SHAP 값 계산 중 (이것은 시간이 걸릴 수 있습니다)...")
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_test)

    # 특성 중요도 (평균 |SHAP|)
    feature_importance = np.abs(shap_values).mean(axis=0)
    importance_df = pd.DataFrame({
        '특성': X_train.columns,
        'SHAP_중요도': feature_importance,
        '상대_중요도': feature_importance / feature_importance.sum()
    }).sort_values('SHAP_중요도', ascending=False)

    print("\n" + "=" * 80)
    print("📈 특성 중요도 (SHAP 기반)")
    print("=" * 80)
    print(importance_df.to_string(index=False))

    # 결과 저장
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / f'shap_analysis_{datetime.now():%Y%m%d_%H%M%S}.json'
    output_file.write_text(json.dumps({
        'timestamp': datetime.now().isoformat(),
        'model': 'Gradient Boosting',
        'r2_score': float(r2),
        'feature_importance': [
            {
                'feature': str(row['특성']),
                'importance': float(row['SHAP_중요도']),
                'relative_importance': float(row['상대_중요도'])
            }
            for _, row in importance_df.iterrows()
        ]
    }, indent=2, ensure_ascii=False))

    print(f"\n📁 결과 저장: {output_file}")

    # 요약
    print("\n" + "=" * 80)
    print("📋 핵심 인사이트")
    print("=" * 80)
    top_3 = importance_df.head(3)
    for idx, row in top_3.iterrows():
        print(f"  #{idx+1} {row['특성']}: {row['상대_중요도']:.1%}")

if __name__ == "__main__":
    try:
        shap_analysis(
            data_path='avm_project/data/raw/signal_real_estate_202401_202412.csv',
            target_col='거래금액',
            time_col='거래일'
        )
    except Exception as e:
        print(f"❌ SHAP 분석 오류: {e}")
        print("\n💡 해결책: pip install shap")
