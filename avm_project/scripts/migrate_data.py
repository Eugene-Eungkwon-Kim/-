"""
D드라이브로 데이터 마이그레이션
"""

import shutil
import json
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

D_DRIVE_PATH = r'D:\LG_AVM_Workspace_Data_Moved_20260604'
TIMESTAMP = datetime.now().strftime('%Y-%m-%d')


class DataMigrator:
    def __init__(self):
        self.base_path = Path(D_DRIVE_PATH)
        self.local_path = Path('/home/user/-/avm_project/data/raw')

    def migrate_from_local(self):
        """로컬 데이터를 D드라이브로 마이그레이션"""
        logger.info(f"\n마이그레이션 시작: {self.local_path} → {self.base_path}")

        if not self.local_path.exists():
            logger.warning(f"⚠️ 로컬 경로 없음: {self.local_path}")
            return False

        try:
            # 날짜별 폴더 생성
            migration_folder = self.base_path / f"Migration_{TIMESTAMP}"
            migration_folder.mkdir(parents=True, exist_ok=True)

            # 파일 복사
            count = 0
            for file in self.local_path.glob('*.csv'):
                dst = migration_folder / file.name
                shutil.copy2(file, dst)
                count += 1
                logger.info(f"✅ 복사: {file.name}")

            for file in self.local_path.glob('*.json'):
                dst = migration_folder / file.name
                shutil.copy2(file, dst)
                count += 1
                logger.info(f"✅ 복사: {file.name}")

            logger.info(f"\n✅ 마이그레이션 완료: {count}개 파일")
            return True

        except Exception as e:
            logger.error(f"❌ 마이그레이션 실패: {e}")
            return False

    def create_structure(self):
        """D드라이브 표준 폴더 구조 생성"""
        logger.info("\n표준 폴더 구조 생성 중...")

        folders = [
            'Raw_Data',
            'Processed_Data',
            'Indexed_Data',
            'Cleansed_Data',
            'Archived'
        ]

        for folder in folders:
            path = self.base_path / folder
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"✅ 생성: {path}")

    def run(self):
        """마이그레이션 실행"""
        self.create_structure()
        self.migrate_from_local()
        logger.info(f"\n✅ 모든 마이그레이션 완료\n경로: {self.base_path}")


if __name__ == "__main__":
    migrator = DataMigrator()
    migrator.run()
