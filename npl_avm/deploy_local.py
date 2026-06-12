#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NPL AVM 시스템 - 로컬 배포 스크립트
FastAPI 서버 시작 및 로컬 접근 설정
"""

import os
import sys
import subprocess
import time
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 프로젝트 경로
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
DB_FILE = DATA_DIR / "npl_avm.db"

class LocalDeployment:
    """로컬 배포 관리"""

    @staticmethod
    def check_dependencies():
        """의존성 설치 확인"""
        logger.info("=" * 80)
        logger.info("[STEP 1] 의존성 확인")
        logger.info("=" * 80)

        try:
            import fastapi
            import uvicorn
            import sqlalchemy
            import pandas
            import numpy
            import sklearn

            logger.info("✅ 모든 필수 라이브러리 설치됨")
            logger.info(f"   - FastAPI {fastapi.__version__}")
            logger.info(f"   - SQLAlchemy {sqlalchemy.__version__}")
            logger.info(f"   - Pandas {pandas.__version__}")
            return True
        except ImportError as e:
            logger.error(f"❌ 누락된 라이브러리: {e}")
            logger.info("💡 다음 명령어로 설치하세요:")
            logger.info(f"   pip install -r {PROJECT_ROOT}/requirements.txt")
            return False

    @staticmethod
    def setup_database():
        """데이터베이스 초기화"""
        logger.info("\n" + "=" * 80)
        logger.info("[STEP 2] 데이터베이스 초기화")
        logger.info("=" * 80)

        # 디렉토리 생성
        DATA_DIR.mkdir(exist_ok=True)
        logger.info(f"✅ 디렉토리 준비: {DATA_DIR}")

        # 데이터베이스 초기화
        try:
            from app.db.database import init_db
            init_db()
            logger.info(f"✅ 데이터베이스 초기화: {DB_FILE}")
            logger.info(f"   - 크기: {DB_FILE.stat().st_size / 1024:.1f} KB")
            return True
        except Exception as e:
            logger.error(f"❌ 데이터베이스 초기화 실패: {e}")
            return False

    @staticmethod
    def validate_database():
        """데이터베이스 검증"""
        logger.info("\n[STEP 3] 데이터베이스 검증")

        try:
            from sqlalchemy import create_engine, inspect, text
            from app.db.models import Base

            engine = create_engine(f"sqlite:///{DB_FILE}")
            inspector = inspect(engine)

            tables = inspector.get_table_names()
            logger.info(f"✅ 테이블 생성 확인: {len(tables)}개")

            # 테이블별 행 수
            with engine.connect() as conn:
                for table in tables:
                    if table.startswith("sqlite_"):
                        continue
                    row_count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                    logger.info(f"   - {table}: {row_count}행")

            return True
        except Exception as e:
            logger.error(f"❌ 데이터베이스 검증 실패: {e}")
            return False

    @staticmethod
    def start_server(host="127.0.0.1", port=8000, reload=True):
        """FastAPI 서버 시작"""
        logger.info("\n" + "=" * 80)
        logger.info("[STEP 4] FastAPI 서버 시작")
        logger.info("=" * 80)

        try:
            logger.info(f"🚀 서버 시작: {host}:{port}")
            logger.info(f"   - 모드: {'개발 (자동 재시작)' if reload else '운영'}")
            logger.info(f"   - 문서: http://{host}:{port}/docs")
            logger.info(f"   - 스키마: http://{host}:{port}/openapi.json")

            # 환경 변수 설정
            os.environ["PYTHONPATH"] = str(PROJECT_ROOT)

            # uvicorn 실행
            import uvicorn

            config = uvicorn.Config(
                "app.main:app",
                host=host,
                port=port,
                reload=reload,
                log_level="info",
            )

            server = uvicorn.Server(config)
            return server

        except Exception as e:
            logger.error(f"❌ 서버 시작 실패: {e}")
            return None


def print_banner():
    """배포 배너"""
    banner = """
================================================================================

              NPL AVM 시스템 - 로컬 배포
              Automated Valuation Model for Non-Performing Loans

================================================================================
"""
    print(banner)


def print_api_info(host="127.0.0.1", port=8000):
    """API 정보 출력"""
    info = f"""
================================================================================
                    [배포 완료] API 정보
================================================================================

  기본 URL:    http://{host}:{port}

  API 문서:
     - Swagger UI:   http://{host}:{port}/docs
     - ReDoc:        http://{host}:{port}/redoc
     - OpenAPI:      http://{host}:{port}/openapi.json

  주요 엔드포인트:
     - POST /api/v1/avm/estimate      감정가 추정
     - GET  /api/v1/precedents        유사 물건 조회
     - GET  /api/v1/auction-stats     낙찰가율 통계
     - GET  /api/v1/batch/estimate    일괄 처리
     - GET  /api/v1/filter/search     필터 검색

  테스트 방법:
     1. 웹 브라우저에서 /docs 접속
     2. "Try it out" 버튼으로 API 테스트
     3. curl 또는 Postman으로 요청

  데이터베이스:
     경로: data/npl_avm.db
     엔진: SQLite

  종료:  Ctrl+C 입력

================================================================================
"""
    print(info)


def main():
    """메인 배포 함수"""
    print_banner()

    # 1. 의존성 확인
    if not LocalDeployment.check_dependencies():
        sys.exit(1)

    # 2. 데이터베이스 초기화
    if not LocalDeployment.setup_database():
        sys.exit(1)

    # 3. 데이터베이스 검증
    if not LocalDeployment.validate_database():
        logger.warning("⚠️  데이터베이스 검증 실패했지만 계속 진행합니다")

    # 4. 서버 시작
    logger.info("\n" + "=" * 80)
    logger.info("[STEP 4] FastAPI 서버 시작")
    logger.info("=" * 80)

    host = "127.0.0.1"
    port = 8000

    print_api_info(host, port)

    try:
        import uvicorn
        os.environ["PYTHONPATH"] = str(PROJECT_ROOT)

        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=True,
            log_level="info",
        )
    except KeyboardInterrupt:
        logger.info("\n\n✅ 서버 정상 종료")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ 서버 오류: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
