"""Relative errors using the existing discrepancy validation definition."""

from __future__ import annotations

from typing import Sequence

import numpy as np


def relative_errors_pct(actual: Sequence[float], predicted: Sequence[float]) -> np.ndarray:
    truth, estimate = np.asarray(actual, dtype=float), np.asarray(predicted, dtype=float)
    if truth.ndim != 1 or truth.shape != estimate.shape or not truth.size:
        raise ValueError("Expected matching nonempty one-dimensional predictions")
    if not np.isfinite(truth).all() or not np.isfinite(estimate).all() or (truth <= 0).any():
        raise ValueError("Prices must be finite and actual prices must be positive")
    return np.abs(truth - estimate) / truth * 100
