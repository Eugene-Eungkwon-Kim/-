"""
Structured logging configuration for AVM project
JSON 포맷 로깅으로 운영 환경에서 로그 분석 용이
"""

import logging
import logging.handlers
import os
from pathlib import Path
from datetime import datetime

try:
    from pythonjsonlogger import jsonlogger
    HAS_JSON_LOGGER = True
except ImportError:
    HAS_JSON_LOGGER = False


class LoggerSetup:
    """로깅 시스템 설정"""

    @staticmethod
    def setup(
        log_file: str = 'logs/app.log',
        log_level: str = None,
        format_type: str = 'json'
    ) -> logging.Logger:
        """
        로깅 시스템 초기화

        Args:
            log_file: 로그 파일 경로
            log_level: 로그 레벨 (환경변수 우선)
            format_type: 'json' 또는 'text'

        Returns:
            logging.Logger: 설정된 로거
        """

        # 로그 레벨 결정 (환경변수 우선)
        level_str = os.getenv('LOG_LEVEL', log_level or 'INFO').upper()
        level = getattr(logging, level_str, logging.INFO)

        # 로그 디렉토리 생성
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # 루트 로거 설정
        logger = logging.getLogger()
        logger.setLevel(level)

        # 기존 핸들러 제거 (중복 방지)
        logger.handlers.clear()

        # ===== 파일 핸들러 (회전 기능) =====
        file_handler = logging.handlers.RotatingFileHandler(
            str(log_path),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,  # 최대 5개 백업
            encoding='utf-8'
        )
        file_handler.setLevel(level)

        # ===== 포매터 선택 =====
        if format_type == 'json' and HAS_JSON_LOGGER:
            formatter = jsonlogger.JsonFormatter(
                '%(timestamp)s %(level)s %(name)s %(message)s %(funcName)s %(lineno)d'
            )
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )

        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # ===== 콘솔 핸들러 =====
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)

        # 콘솔은 일반 텍스트 형식 (읽기 쉽게)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # 첫 로그
        logger.info(f"🚀 로깅 시스템 초기화 완료")
        logger.info(f"   레벨: {level_str}")
        logger.info(f"   파일: {log_path}")
        logger.info(f"   포맷: {format_type}")

        return logger


def get_logger(name: str) -> logging.Logger:
    """
    모듈별 로거 취득

    Args:
        name: 로거 이름 (보통 __name__ 사용)

    Returns:
        logging.Logger: 설정된 로거
    """
    return logging.getLogger(name)


# 기본 로거 초기화
if __name__ != "__main__":
    # 모듈 import 시 자동 초기화
    log_file = os.getenv('LOG_FILE', 'logs/app.log')
    log_level = os.getenv('LOG_LEVEL', 'INFO')

    try:
        LoggerSetup.setup(
            log_file=log_file,
            log_level=log_level,
            format_type='json'
        )
    except Exception as e:
        # 로깅 설정 실패 시 기본 설정 사용
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logging.warning(f"⚠️ 로깅 설정 실패, 기본 설정 사용: {e}")
