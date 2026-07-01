"""특성 스키마"""
import json
from typing import Any, Dict

from data_path_config import get_models_path


def load_schema() -> Dict[str, Any]:
    """models/feature_schema.json에서 학습 시점 특성 스키마를 로드한다."""
    schema_path = get_models_path() / "feature_schema.json"
    with open(schema_path, encoding="utf-8") as f:
        return json.load(f)
