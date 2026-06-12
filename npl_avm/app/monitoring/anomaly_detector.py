import logging
import math
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class AnomalyRule:
    """이상 탐지 규칙"""

    def __init__(
        self,
        name: str,
        metric: str,
        threshold: float,
        operator: str = ">",  # ">", "<", "=", "!="
        severity: str = "warning",  # "info", "warning", "critical"
    ):
        self.name = name
        self.metric = metric
        self.threshold = threshold
        self.operator = operator
        self.severity = severity

    def check(self, value: float) -> Tuple[bool, str]:
        """규칙 확인 및 메시지 반환"""
        is_anomaly = False
        message = ""

        if self.operator == ">":
            is_anomaly = value > self.threshold
            message = f"{self.name}: {value} > {self.threshold}"
        elif self.operator == "<":
            is_anomaly = value < self.threshold
            message = f"{self.name}: {value} < {self.threshold}"
        elif self.operator == "=":
            is_anomaly = value == self.threshold
            message = f"{self.name}: {value} == {self.threshold}"
        elif self.operator == "!=":
            is_anomaly = value != self.threshold
            message = f"{self.name}: {value} != {self.threshold}"

        return is_anomaly, message


class StatisticalAnomalyDetector:
    """통계 기반 이상 탐지 (Sigma 방식)"""

    def __init__(self, sigma: float = 2.0):
        self.sigma = sigma  # 표준편차 배수

    def detect(self, values: List[float]) -> Tuple[List[int], Dict]:
        """
        이상 탐지 (Z-score 방식)

        Returns:
            (이상 인덱스 리스트, 통계 정보)
        """
        if len(values) < 2:
            return [], {"mean": 0, "std": 0, "anomalies": []}

        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std = math.sqrt(variance)

        if std == 0:
            return [], {"mean": mean, "std": 0, "anomalies": []}

        anomalies = []
        for i, value in enumerate(values):
            z_score = abs((value - mean) / std)
            if z_score > self.sigma:
                anomalies.append(i)

        return anomalies, {"mean": mean, "std": std, "anomalies": anomalies}


class IsolationForestAnomalyDetector:
    """Isolation Forest를 이용한 이상 탐지"""

    def __init__(self, contamination: float = 0.1):
        self.contamination = contamination  # 이상 비율 추정

    def detect(self, values: List[float]) -> Tuple[List[int], Dict]:
        """
        이상 탐지

        주의: 간단한 구현 (실제로는 scikit-learn 사용 권장)
        """
        try:
            from sklearn.ensemble import IsolationForest

            X = [[v] for v in values]
            detector = IsolationForest(
                contamination=self.contamination,
                random_state=42,
            )
            predictions = detector.fit_predict(X)

            anomalies = [i for i, pred in enumerate(predictions) if pred == -1]

            return anomalies, {
                "method": "IsolationForest",
                "contamination": self.contamination,
                "anomalies": anomalies,
            }
        except ImportError:
            logger.warning("scikit-learn이 설치되지 않았습니다")
            # Fallback: 간단한 사분위수 방식
            return IsolationForestAnomalyDetector._iqr_method(values)

    @staticmethod
    def _iqr_method(values: List[float]) -> Tuple[List[int], Dict]:
        """Interquartile Range (IQR) 방식 (Fallback)"""
        sorted_vals = sorted(values)
        n = len(sorted_vals)

        q1_idx = n // 4
        q3_idx = (3 * n) // 4
        q1 = sorted_vals[q1_idx]
        q3 = sorted_vals[q3_idx]

        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        anomalies = [
            i for i, v in enumerate(values)
            if v < lower_bound or v > upper_bound
        ]

        return anomalies, {
            "method": "IQR",
            "q1": q1,
            "q3": q3,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "anomalies": anomalies,
        }


class AnomalyDetector:
    """종합 이상 탐지 엔진"""

    def __init__(self):
        self.rules: List[AnomalyRule] = []
        self.statistical_detector = StatisticalAnomalyDetector(sigma=2.0)
        self.isolation_detector = IsolationForestAnomalyDetector(contamination=0.1)

    def add_rule(self, rule: AnomalyRule):
        """규칙 추가"""
        self.rules.append(rule)
        logger.info(f"이상 탐지 규칙 추가: {rule.name}")

    def check_threshold_rules(self, metrics: Dict[str, float]) -> List[Dict]:
        """임계값 기반 규칙 확인"""
        anomalies = []

        for rule in self.rules:
            if rule.metric not in metrics:
                continue

            value = metrics[rule.metric]
            is_anomaly, message = rule.check(value)

            if is_anomaly:
                anomalies.append({
                    "type": "threshold",
                    "rule": rule.name,
                    "severity": rule.severity,
                    "metric": rule.metric,
                    "value": value,
                    "threshold": rule.threshold,
                    "message": message,
                })

        return anomalies

    def check_statistical_anomalies(
        self,
        values: List[float],
        metric_name: str,
    ) -> List[Dict]:
        """통계 기반 이상 탐지"""
        anomaly_indices, stats = self.statistical_detector.detect(values)

        return [
            {
                "type": "statistical",
                "metric": metric_name,
                "index": idx,
                "value": values[idx],
                "mean": stats["mean"],
                "std": stats["std"],
                "message": f"{metric_name}의 비정상 값: {values[idx]}",
            }
            for idx in anomaly_indices
        ]

    def check_isolation_forest_anomalies(
        self,
        values: List[float],
        metric_name: str,
    ) -> List[Dict]:
        """Isolation Forest 이상 탐지"""
        anomaly_indices, stats = self.isolation_detector.detect(values)

        return [
            {
                "type": "isolation_forest",
                "metric": metric_name,
                "index": idx,
                "value": values[idx],
                "message": f"{metric_name}의 이상 패턴: {values[idx]}",
            }
            for idx in anomaly_indices
        ]

    def detect_all(
        self,
        metrics: Dict[str, float],
        historical_data: Optional[Dict[str, List[float]]] = None,
    ) -> Dict:
        """종합 이상 탐지"""
        all_anomalies = []

        # 1. 임계값 기반 규칙
        threshold_anomalies = self.check_threshold_rules(metrics)
        all_anomalies.extend(threshold_anomalies)

        # 2. 통계 기반 이상 탐지 (히스토리가 있을 경우)
        if historical_data:
            for metric_name, values in historical_data.items():
                if len(values) >= 10:  # 최소 10개 데이터
                    stat_anomalies = self.check_statistical_anomalies(
                        values, metric_name
                    )
                    all_anomalies.extend(stat_anomalies)

                    # Isolation Forest (20개 이상 데이터)
                    if len(values) >= 20:
                        iso_anomalies = self.check_isolation_forest_anomalies(
                            values, metric_name
                        )
                        all_anomalies.extend(iso_anomalies)

        # 심각도별 정렬
        severity_order = {"info": 0, "warning": 1, "critical": 2}
        all_anomalies.sort(
            key=lambda x: severity_order.get(x.get("severity"), 0),
            reverse=True,
        )

        return {
            "anomaly_count": len(all_anomalies),
            "anomalies": all_anomalies,
            "has_critical": any(a.get("severity") == "critical" for a in all_anomalies),
        }


# 글로벌 이상 탐지 엔진
anomaly_detector = AnomalyDetector()

# 기본 규칙 설정
anomaly_detector.add_rule(
    AnomalyRule("p95_latency_high", "p95_latency_ms", 500, ">", "warning")
)
anomaly_detector.add_rule(
    AnomalyRule("p99_latency_high", "p99_latency_ms", 1000, ">", "critical")
)
anomaly_detector.add_rule(
    AnomalyRule("error_rate_high", "error_rate", 0.05, ">", "warning")
)
anomaly_detector.add_rule(
    AnomalyRule("cpu_usage_high", "cpu_percent", 80, ">", "warning")
)
anomaly_detector.add_rule(
    AnomalyRule("memory_usage_high", "memory_percent", 85, ">", "critical")
)
