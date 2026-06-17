"""
데이터 경로 설정 모듈
프로젝트 전체에서 사용하는 경로 정의
"""

from pathlib import Path

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent.parent

def get_models_path():
    """모델 파일 경로"""
    return PROJECT_ROOT / "models"

def get_data_path():
    """데이터 파일 경로"""
    return PROJECT_ROOT / "data"

def get_raw_data_path():
    """원본 데이터 경로"""
    return PROJECT_ROOT / "data" / "raw"

def get_processed_data_path():
    """처리된 데이터 경로"""
    return PROJECT_ROOT / "data" / "processed"

def get_output_path():
    """출력 파일 경로"""
    return PROJECT_ROOT / "output"

def get_logs_path():
    """로그 파일 경로"""
    return PROJECT_ROOT / "logs"

def get_config_path():
    """설정 파일 경로"""
    return PROJECT_ROOT / "config"

# 경로 존재 확인 및 생성
for path_func in [get_models_path, get_data_path, get_output_path, get_logs_path, get_config_path]:
    path = path_func()
    path.mkdir(parents=True, exist_ok=True)

print("✅ 데이터 경로 설정 완료")
