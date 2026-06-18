"""경로 설정"""
from pathlib import Path

def get_models_path():
    return Path(__file__).parent.parent / "models"

def get_data_path():
    return Path(__file__).parent.parent / "data" / "raw"

def get_output_path():
    return Path(__file__).parent.parent / "output"
