"""경로 설정"""
from pathlib import Path
from typing import Dict

def get_models_path():
    return Path(__file__).parent.parent / "models"

def get_data_path():
    return Path(__file__).parent.parent / "data" / "raw"

def get_output_path():
    return Path(__file__).parent.parent / "output"

def get_subpath(name: str) -> Path:
    """get_data_path() 하위의 지정된 서브디렉토리 경로 반환"""
    return get_data_path() / name

def validate_paths() -> Dict[str, bool]:
    """주요 경로들의 존재 여부 확인"""
    paths = {
        "models": get_models_path(),
        "data": get_data_path(),
        "output": get_output_path(),
    }
    return {name: path.exists() for name, path in paths.items()}
