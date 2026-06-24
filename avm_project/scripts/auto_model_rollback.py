#!/usr/bin/env python3
import os
from pathlib import Path

def rollback_to_previous_model():
    """이전 모델로 복원"""
    models = sorted(Path("models").glob("gradient_boosting_auto_*.joblib"))

    if len(models) < 2:
        print("⚠️ 이전 모델 없음")
        return False

    # 마지막 모델 2개 중 이전 것으로 복원
    previous_model = models[-2]
    latest_link = Path("models/gradient_boosting_latest.joblib")

    if latest_link.exists():
        latest_link.unlink()

    os.symlink(previous_model, latest_link)
    print(f"✅ Rolled back to {previous_model.name}")
    return True

if __name__ == "__main__":
    rollback_to_previous_model()
