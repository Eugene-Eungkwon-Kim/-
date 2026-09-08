"""
Application configuration management
환경변수 기반 설정으로 개발/스테이징/프로덕션 환경 분리
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path
from typing import List
import os


class Settings(BaseSettings):
    """
    애플리케이션 전역 설정

    우선순위:
    1. 환경변수
    2. .env 파일
    3. 기본값
    """

    # ===== API 설정 =====
    api_host: str = Field(
        default="0.0.0.0",
        description="API 서버 호스트"
    )
    api_port: int = Field(
        default=8000,
        description="API 서버 포트"
    )
    api_workers: int = Field(
        default=4,
        description="Uvicorn 워커 수"
    )
    api_reload: bool = Field(
        default=False,
        description="개발 모드에서 자동 리로드"
    )

    # ===== 데이터 경로 =====
    data_path: Path = Field(
        default="/mnt/avm_data",
        description="데이터 저장소 경로"
    )
    models_path: Path = Field(
        default="./models",
        description="모델 저장소 경로"
    )
    logs_path: Path = Field(
        default="./logs",
        description="로그 파일 경로"
    )

    # ===== 모델 설정 =====
    model_r2_threshold: float = Field(
        default=0.90,
        description="모델 성능 임계값 (R²)"
    )
    prediction_timeout: int = Field(
        default=30,
        description="예측 타임아웃 (초)"
    )
    batch_size_max: int = Field(
        default=100,
        description="배치 예측 최대 크기"
    )

    # ===== 로깅 설정 =====
    log_level: str = Field(
        default="INFO",
        description="로깅 레벨 (DEBUG/INFO/WARNING/ERROR)"
    )
    log_file: str = Field(
        default="logs/app.log",
        description="로그 파일 경로"
    )
    log_format: str = Field(
        default="json",
        description="로그 포맷 (json/text)"
    )

    # ===== CORS 설정 =====
    allowed_origins: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:8080",
            "http://127.0.0.1:3000"
        ],
        description="CORS 허용 출처"
    )

    # ===== 보안 설정 =====
    cors_credentials: bool = Field(
        default=False,
        description="CORS 자격증명 허용"
    )
    allowed_methods: List[str] = Field(
        default=["GET", "POST"],
        description="허용 HTTP 메서드"
    )
    allowed_headers: List[str] = Field(
        default=["Content-Type", "Authorization"],
        description="허용 헤더"
    )

    # ===== 환경 설정 =====
    environment: str = Field(
        default="development",
        description="실행 환경 (development/staging/production)"
    )
    debug: bool = Field(
        default=False,
        description="디버그 모드"
    )

    # ===== 데이터베이스 (선택사항) =====
    database_url: str = Field(
        default="",
        description="데이터베이스 연결 문자열"
    )

    class Config:
        """Pydantic 설정"""
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = False

    @property
    def is_production(self) -> bool:
        """프로덕션 환경 확인"""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """개발 환경 확인"""
        return self.environment == "development"

    def __init__(self, **kwargs):
        """설정 초기화"""
        super().__init__(**kwargs)

        # 경로 생성
        Path(self.logs_path).mkdir(parents=True, exist_ok=True)
        Path(self.data_path).mkdir(parents=True, exist_ok=True)
        Path(self.models_path).mkdir(parents=True, exist_ok=True)


# 글로벌 설정 인스턴스
settings = Settings()
