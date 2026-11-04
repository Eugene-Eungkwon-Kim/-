"""실데이터 평가 하네스 (DEV-3).

PoC(R² 0.9983)가 데이터 누수 영향인지 가려내기 위해, 시간순 분할 +
누수 감사를 통과한 수치만 성능으로 보고하는 것이 목표다. 전체
파이프라인(`run()`: 데이터 로드 → 검증 → 분할 → 누수 감사 → 7개 모델
학습·평가 → 보고서)은 DEV-2(`real_data_contract.py`의 Manifest 로딩)가
아직 Manifest 형식 미확인으로 막혀 있어 구현하지 않았다 — 지금은 실데이터
없이도 테스트 가능한 평가·합격선 판정 부분만 둔다.

괴리율(discrepancy rate)은 기존 `discrepancy_rate_validation.py`의
정의를 재사용할 예정이었으나, 그 파일이 임포트 시점에 고정 데이터
파일을 읽어 5개 모델을 학습하는 최상위 스크립트라(가드 없음) 그대로
임포트할 수 없다. 괴리율은 `run()` 구현 시 해당 스크립트를 먼저
함수로 분리한 뒤 추가한다.
"""

from typing import Any

import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, r2_score

R2_TARGET = 0.84
MAPE_TARGET = 0.105


def evaluate_model(model: Any, X_test: pd.DataFrame, y_test: pd.Series) -> dict[str, float]:
    """테스트셋 기준 R²/MAPE/MAE를 계산한다."""
    pred = model.predict(X_test)
    return {
        "r2": float(r2_score(y_test, pred)),
        "mape": float(mean_absolute_percentage_error(y_test, pred)),
        "mae": float(mean_absolute_error(y_test, pred)),
    }


def gate(metrics: dict[str, float]) -> list[str]:
    """`CLAUDE.md` 합격선(R²>0.84, MAPE<10.5%) 미달 사유 목록. 비어 있으면 합격."""
    reasons = []
    r2 = metrics.get("r2", 0.0)
    if r2 <= R2_TARGET:
        reasons.append(f"R² {r2:.4f} <= {R2_TARGET}")
    mape = metrics.get("mape", 1.0)
    if mape >= MAPE_TARGET:
        reasons.append(f"MAPE {mape:.4f} >= {MAPE_TARGET}")
    return reasons
