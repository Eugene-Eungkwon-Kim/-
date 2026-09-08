#!/usr/bin/env python3
"""
SHAP 기반 모델 설명성 및 특성 기여도 분석

기능:
  1. SHAP TreeExplainer로 모델 해석
  2. 특성별 평균 절댓값 영향도 (Mean Absolute SHAP)
  3. 개별 예측 설명 (단일 샘플 SHAP)
  4. 전역 특성 중요도 시각화
  5. 의존도 플롯 (Feature Dependence)

실행: python3 scripts/model_explainability.py
"""

from __future__ import annotations

import json
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import joblib
import shap
from sklearn.preprocessing import MinMaxScaler

warnings.filterwarnings('ignore')

PROJECT_ROOT = Path(__file__).parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"

MODELS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class ModelExplainer:
    """SHAP 기반 모델 설명성"""

    def __init__(self):
        self.model = None
        self.explainer = None
        self.shap_values = None
        self.feature_names = None

    def load_model(self) -> bool:
        """학습된 모델 로드"""
        print("📥 모델 로드")

        model_file = MODELS_DIR / "production_model.joblib"
        if not model_file.exists():
            print("   ⚠️  프로덕션 모델 없음 — 테스트용 모델 생성")
            return self._create_test_model()

        self.model = joblib.load(model_file)
        print(f"   ✅ 로드: {model_file.name}")
        return True

    def _create_test_model(self) -> bool:
        """테스트용 RandomForest 모델 생성"""
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.pipeline import Pipeline

        np.random.seed(42)
        n_samples = 500
        n_features = 19

        X = np.random.randn(n_samples, n_features)
        y = X @ np.random.randn(n_features) + np.random.randn(n_samples)

        model = Pipeline([
            ('scaler', MinMaxScaler()),
            ('rf', RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42))
        ])
        model.fit(X, y)

        # 저장
        joblib.dump(model, MODELS_DIR / "test_model.joblib")
        self.model = model
        print(f"   ✅ 테스트 모델 생성: RandomForest (500 × 19)")
        return True

    def load_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """데이터 로드"""
        print("\n📊 데이터 로드")

        # 처리된 데이터 찾기
        processed_files = list(DATA_DIR.glob("processed/*.csv"))
        if processed_files:
            latest_file = max(processed_files, key=lambda x: x.stat().st_mtime)
            df = pd.read_csv(latest_file)
            X = df.iloc[:, :-1].values
            y = df.iloc[:, -1].values
            print(f"   ✅ 로드: {latest_file.name} ({X.shape[0]:,} × {X.shape[1]})")
            return X, y

        # 샘플 생성
        print("   ⚠️  처리된 데이터 없음 — 샘플 생성")
        np.random.seed(42)
        n_samples = 500
        n_features = 19

        X = np.random.randn(n_samples, n_features)
        y = X @ np.random.randn(n_features) + np.random.randn(n_samples)

        self.feature_names = [f"Feature_{i}" for i in range(n_features)]
        print(f"   ✅ 샘플 생성: {n_samples} × {n_features}")
        return X, y

    def global_feature_importance(self, X: np.ndarray, limit: int = 10) -> Dict:
        """전역 특성 중요도 (SHAP 기반)"""
        print(f"\n[Step 1/4] 전역 특성 중요도")
        print(f"{'='*70}")

        # SHAP 값 계산
        print(f"   계산 중... (샘플: {len(X)}개)")

        # 트리 기반 모델의 경우 TreeExplainer 사용
        if hasattr(self.model, 'named_steps'):
            # Pipeline의 경우 마지막 estimator 추출
            base_model = self.model.named_steps.get('rf') or self.model.named_steps.get('xgb') or self.model.named_steps.get('lgb')
            if base_model is None:
                base_model = list(self.model.named_steps.values())[-1]
        else:
            base_model = self.model

        try:
            explainer = shap.TreeExplainer(base_model)
            shap_values = explainer.shap_values(X)
        except Exception as e:
            print(f"   ⚠️  TreeExplainer 오류: {e}")
            print(f"   대체: KernelExplainer 사용")
            explainer = shap.KernelExplainer(self.model.predict, X[:50])
            shap_values = explainer.shap_values(X)

        self.explainer = explainer
        self.shap_values = shap_values

        # SHAP 값이 2D 배열인지 확인 (회귀는 1D)
        if len(shap_values.shape) == 1:
            shap_values = shap_values.reshape(-1, 1)

        # 평균 절댓값 SHAP
        mean_abs_shap = np.abs(shap_values).mean(axis=0)

        # 상위 N개 특성
        if self.feature_names is None:
            self.feature_names = [f"Feature_{i}" for i in range(len(mean_abs_shap))]

        importance = pd.Series(
            mean_abs_shap,
            index=self.feature_names
        ).sort_values(ascending=False)

        print(f"\n📊 상위 {min(limit, len(importance))}개 특성 (SHAP 영향도)")
        for i, (feat, score) in enumerate(importance.head(limit).items(), 1):
            print(f"   {i}. {feat}: {score:.6f}")

        return {
            "total_features": len(importance),
            "top_features": importance.head(limit).to_dict(),
            "mean_abs_shap": importance.to_dict()
        }

    def individual_prediction_explanation(self, X: np.ndarray, idx: int = 0) -> Dict:
        """개별 예측 설명 (단일 샘플)"""
        print(f"\n[Step 2/4] 개별 예측 설명")
        print(f"{'='*70}")

        if self.shap_values is None:
            print("   ⚠️  SHAP 값 미계산 — 건너뜀")
            return {}

        idx = min(idx, len(X) - 1)
        prediction = self.model.predict(X[idx:idx+1])[0]

        # SHAP 값 추출
        if len(self.shap_values.shape) == 1:
            sample_shap = self.shap_values[idx]
        else:
            sample_shap = self.shap_values[idx]

        # 절댓값 기준 정렬
        if isinstance(sample_shap, np.ndarray):
            if len(sample_shap.shape) == 1:
                contrib_idx = np.argsort(np.abs(sample_shap))[::-1][:5]
                top_features = [(self.feature_names[i], sample_shap[i], X[idx, i])
                               for i in contrib_idx]
            else:
                sample_shap = sample_shap.flatten()
                contrib_idx = np.argsort(np.abs(sample_shap))[::-1][:5]
                top_features = [(self.feature_names[i], sample_shap[i], X[idx, i])
                               for i in contrib_idx]
        else:
            top_features = []

        print(f"\n🔍 샘플 #{idx} 예측")
        print(f"   예측값: {prediction:.4f}")
        print(f"\n   상위 5개 영향 특성:")
        for feat, shap_val, feat_val in top_features:
            direction = "↑" if shap_val > 0 else "↓"
            print(f"     {direction} {feat}: {feat_val:.4f} (SHAP: {shap_val:.6f})")

        return {
            "sample_idx": idx,
            "prediction": float(prediction),
            "top_contributing_features": [
                {
                    "feature": feat,
                    "shap_value": float(shap_val),
                    "feature_value": float(feat_val)
                }
                for feat, shap_val, feat_val in top_features
            ]
        }

    def feature_dependence_analysis(self, X: np.ndarray, feature_idx: int = 0) -> Dict:
        """의존도 분석 (특성-SHAP 관계)"""
        print(f"\n[Step 3/4] 특성 의존도 분석")
        print(f"{'='*70}")

        if self.shap_values is None:
            print("   ⚠️  SHAP 값 미계산 — 건너뜀")
            return {}

        feature_idx = min(feature_idx, X.shape[1] - 1)
        feat_name = self.feature_names[feature_idx]

        # SHAP 값 추출
        if len(self.shap_values.shape) == 1:
            shap_for_feature = self.shap_values
        else:
            shap_for_feature = self.shap_values[:, feature_idx]

        # 상관관계
        feature_values = X[:, feature_idx]
        correlation = np.corrcoef(feature_values, shap_for_feature)[0, 1]

        # 통계
        stats = {
            "feature_name": feat_name,
            "feature_min": float(np.min(feature_values)),
            "feature_max": float(np.max(feature_values)),
            "feature_mean": float(np.mean(feature_values)),
            "shap_min": float(np.min(shap_for_feature)),
            "shap_max": float(np.max(shap_for_feature)),
            "shap_mean": float(np.mean(shap_for_feature)),
            "correlation": float(correlation) if not np.isnan(correlation) else 0.0
        }

        print(f"\n📈 {feat_name} 의존도")
        print(f"   특성값: [{stats['feature_min']:.4f}, {stats['feature_max']:.4f}] (평균: {stats['feature_mean']:.4f})")
        print(f"   SHAP값: [{stats['shap_min']:.6f}, {stats['shap_max']:.6f}] (평균: {stats['shap_mean']:.6f})")
        print(f"   상관도: {stats['correlation']:.4f}")

        if abs(correlation) > 0.5:
            trend = "강한 양의 관계" if correlation > 0 else "강한 음의 관계"
        elif abs(correlation) > 0.3:
            trend = "중간 양의 관계" if correlation > 0 else "중간 음의 관계"
        else:
            trend = "약한 관계 (비선형일 가능성)"

        print(f"   해석: {trend}")

        return stats

    def model_decision_path(self, X: np.ndarray, idx: int = 0) -> Dict:
        """모델 의사결정 경로 (TreeExplainer 기반)"""
        print(f"\n[Step 4/4] 모델 의사결정 경로")
        print(f"{'='*70}")

        idx = min(idx, len(X) - 1)
        prediction = self.model.predict(X[idx:idx+1])[0]

        # SHAP 값에서 Base value 추출 (있다면)
        base_value = getattr(self.explainer, 'expected_value', None)
        if base_value is None:
            if hasattr(self.explainer, 'expected_value'):
                base_value = self.explainer.expected_value
            else:
                base_value = 0.0

        print(f"\n🌳 샘플 #{idx} 의사결정 경로")
        print(f"   Base value (모델 기본값): {base_value:.4f}")

        # SHAP 값 추출
        if len(self.shap_values.shape) == 1:
            sample_shap = self.shap_values[idx]
        else:
            sample_shap = self.shap_values[idx]

        # 누적 기여도
        if isinstance(sample_shap, np.ndarray):
            cumulative = float(base_value) + float(np.sum(sample_shap))
            print(f"   모든 특성 기여도 합: +{np.sum(sample_shap):.4f}")
            print(f"   최종 예측값: {cumulative:.4f}")
        else:
            print(f"   최종 예측값: {prediction:.4f}")

        return {
            "sample_idx": idx,
            "base_value": float(base_value) if base_value is not None else 0.0,
            "final_prediction": float(prediction),
            "total_contribution": float(np.sum(sample_shap)) if isinstance(sample_shap, np.ndarray) else 0.0
        }

    def generate_report(self,
                       global_importance: Dict,
                       individual_explanation: Dict,
                       dependence_analysis: Dict,
                       decision_path: Dict) -> Dict:
        """최종 설명성 리포트"""
        print(f"\n{'='*70}")
        print(f"📋 모델 설명성 분석 리포트")
        print(f"{'='*70}")

        report = {
            "timestamp": datetime.now().isoformat(),
            "model_type": str(type(self.model).__name__),
            "explainer_type": "SHAP TreeExplainer",
            "global_importance": global_importance,
            "individual_explanation": individual_explanation,
            "dependence_analysis": dependence_analysis,
            "decision_path": decision_path,
            "insights": {
                "top_3_features": list(global_importance.get("top_features", {}).keys())[:3],
                "most_influential_sample": individual_explanation.get("sample_idx", 0),
                "average_model_prediction": float(decision_path.get("final_prediction", 0))
            }
        }

        # 저장
        report_file = OUTPUT_DIR / f"model_explainability_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n✅ 상위 3개 특성: {', '.join(report['insights']['top_3_features'])}")
        print(f"✅ 설명성 분석 완료")
        print(f"\n📁 리포트: {report_file.name}")

        return report


def run_explainability() -> Dict:
    """전체 설명성 분석 파이프라인"""
    print(f"\n{'='*80}")
    print(f"🚀 SHAP 기반 모델 설명성 분석")
    print(f"{'='*80}")

    explainer = ModelExplainer()

    # 모델 로드
    if not explainer.load_model():
        print("❌ 모델 로드 실패")
        return {}

    # 데이터 로드
    X, y = explainer.load_data()

    # Step 1: 전역 특성 중요도
    global_importance = explainer.global_feature_importance(X)

    # Step 2: 개별 예측 설명
    individual_explanation = explainer.individual_prediction_explanation(X, idx=0)

    # Step 3: 특성 의존도
    dependence_analysis = explainer.feature_dependence_analysis(X, feature_idx=0)

    # Step 4: 의사결정 경로
    decision_path = explainer.model_decision_path(X, idx=0)

    # 리포트 생성
    report = explainer.generate_report(
        global_importance,
        individual_explanation,
        dependence_analysis,
        decision_path
    )

    print(f"\n{'='*80}")
    print(f"✅ 모델 설명성 분석 완료")
    print(f"{'='*80}")

    return report


if __name__ == "__main__":
    try:
        report = run_explainability()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
