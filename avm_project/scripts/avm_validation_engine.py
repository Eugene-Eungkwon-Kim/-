"""WP 2.4: Validation Engine - 이상탐지, 신뢰도 구간, 공시가격 검증."""

import logging
from typing import Any, Dict, List, Optional

import numpy as np

log = logging.getLogger(__name__)

Z_SCORE_95 = 1.96
Z_SCORE_99 = 2.576
APPRAISAL_WARNING = 0.10   # 10% 편차 → 경고
APPRAISAL_CRITICAL = 0.20  # 20% 편차 → 위험
# 고가 꼬리(정상이나 희소)의 과민 탐지를 줄이기 위해 0.05 → 0.02
ANOMALY_CONTAMINATION = 0.02


class ValidationEngine:
    """예측값 종합 검증."""

    def __init__(self, contamination: float = ANOMALY_CONTAMINATION) -> None:
        self._detector = None
        self.is_fitted = False
        self.contamination = contamination

    def fit(self, X: np.ndarray) -> 'ValidationEngine':
        """이상탐지 모델 학습."""
        try:
            from sklearn.ensemble import IsolationForest
            self._detector = IsolationForest(contamination=self.contamination, random_state=42)
            self._detector.fit(X)
            self.is_fitted = True
            log.info(f"Anomaly detector fitted on {len(X)} samples")
        except Exception as e:
            log.warning(f"Anomaly detector fit failed: {e}")
        return self

    def check_anomaly(self, features: np.ndarray) -> Dict[str, Any]:
        """이상치 감지."""
        if not self.is_fitted or self._detector is None:
            return {'is_anomaly': False, 'anomaly_score': 0.0, 'status': 'not_fitted'}

        pred = self._detector.predict([features])[0]
        score = float(self._detector.score_samples([features])[0])
        return {
            'is_anomaly': bool(pred == -1),
            'anomaly_score': score,
            'status': 'anomaly' if pred == -1 else 'normal',
        }

    def estimate_confidence_interval(
        self,
        predicted_price: float,
        std: Optional[float] = None,
        confidence_level: float = 0.95,
    ) -> Dict[str, float]:
        """Z-score 기반 신뢰도 구간."""
        if std is None or std <= 0:
            std = abs(predicted_price) * 0.05
        z = Z_SCORE_95 if confidence_level == 0.95 else Z_SCORE_99
        margin = z * std
        return {
            'prediction': predicted_price,
            'lower_bound': predicted_price - margin,
            'upper_bound': predicted_price + margin,
            'std': std,
            'confidence_level': confidence_level,
        }

    def check_appraisal_range(
        self,
        predicted_price: float,
        public_appraisal_price: float,
    ) -> Dict[str, Any]:
        """공시가격 편차 검증."""
        deviation = abs(predicted_price - public_appraisal_price) / public_appraisal_price
        if deviation <= APPRAISAL_WARNING:
            status = 'acceptable'
        elif deviation <= APPRAISAL_CRITICAL:
            status = 'warning'
        else:
            status = 'critical'
        return {
            'deviation_pct': round(deviation * 100, 2),
            'status': status,
            'message': f"Deviation {deviation*100:.1f}% vs public appraisal",
        }

    def validate(
        self,
        features: np.ndarray,
        predicted_price: float,
        public_appraisal_price: Optional[float] = None,
        price_std: Optional[float] = None,
    ) -> Dict[str, Any]:
        """종합 검증: 이상탐지 + 신뢰도 구간 + 공시가격.

        price_std: 앙상블 모델 간 불일치도(표준편차). 주어지면 신뢰구간을
                   하드코딩 5%가 아닌 실제 불확실성으로 추정한다.
        """
        is_valid = True
        risk_level = 'low'

        anomaly = self.check_anomaly(features)
        if anomaly['is_anomaly']:
            is_valid = False
            risk_level = 'high'

        ci = self.estimate_confidence_interval(predicted_price, std=price_std)

        appraisal_check: Optional[Dict] = None
        if public_appraisal_price:
            appraisal_check = self.check_appraisal_range(predicted_price, public_appraisal_price)
            if appraisal_check['status'] == 'critical':
                is_valid = False
                risk_level = 'high'
            elif appraisal_check['status'] == 'warning' and risk_level == 'low':
                risk_level = 'medium'

        return {
            'is_valid': is_valid,
            'risk_level': risk_level,
            'anomaly': anomaly,
            'confidence_interval': ci,
            'appraisal_check': appraisal_check,
        }
