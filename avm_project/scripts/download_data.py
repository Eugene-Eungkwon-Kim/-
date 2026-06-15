"""
Data.go.kr + Vworld 데이터 다운로드 (라벨링 포함)
"""

import requests
import json
import os
from datetime import datetime
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API 키값
DATAGOVKR_API_KEY = '9+Sz4Yn+RoH4bEhkrqfzS+AJz9ldaehP57wEhL3sEKmDMZW5t7UnTs7rPOA3BNcczF8AI/OX0YJ51PmPAAEZFw=='
VWORLD_API_KEY = '50D9ECCF-3977-37F1-B323-4997BEAAE387'

# 경로
D_DRIVE_PATH = r'D:\LG_AVM_Workspace_Data_Moved_20260604'
TIMESTAMP = datetime.now().strftime('%Y-%m-%d')


class DataDownloader:
    def __init__(self):
        self.base_path = Path(D_DRIVE_PATH)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()

    def create_labeled_folder(self, source: str) -> Path:
        """라벨링된 폴더 생성"""
        folder_name = f"{TIMESTAMP}_{source}_Downloaded"
        folder_path = self.base_path / folder_name
        folder_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ 폴더 생성: {folder_path}")
        return folder_path

    def download_datagovkr(self):
        """Data.go.kr 데이터 다운로드"""
        logger.info("\n" + "="*60)
        logger.info("Data.go.kr 데이터 다운로드 시작")
        logger.info("="*60)

        folder = self.create_labeled_folder("DataGovKr")

        # 부동산 실거래 정보
        url = 'https://apis.data.go.kr/1613000/RealEstateTransactionService/getRealEstateTransactionList'

        params = {
            'LAWD_CD': '27110',
            'DEAL_YMD': '202406',
            'pageNo': '1',
            'numOfRows': '1000',
            'serviceKey': DATAGOVKR_API_KEY
        }

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            # 데이터 저장
            filename = folder / f"real_estate_202406.json"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(response.text)

            logger.info(f"✅ Data.go.kr 다운로드 완료: {filename}")
            return filename

        except Exception as e:
            logger.error(f"❌ Data.go.kr 다운로드 실패: {e}")
            return None

    def download_vworld(self):
        """Vworld 데이터 다운로드"""
        logger.info("\n" + "="*60)
        logger.info("Vworld 데이터 다운로드 시작")
        logger.info("="*60)

        folder = self.create_labeled_folder("Vworld")

        # Vworld 건물정보
        url = 'https://api.vworld.kr/req/data'

        params = {
            'service': 'data',
            'version': 'v2',
            'request': 'GetFeature',
            'data': 'LP_PA_CBND',
            'key': VWORLD_API_KEY,
            'format': 'json'
        }

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            # 데이터 저장
            filename = folder / f"vworld_building_info.json"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(response.text)

            logger.info(f"✅ Vworld 다운로드 완료: {filename}")
            return filename

        except Exception as e:
            logger.error(f"❌ Vworld 다운로드 실패: {e}")
            return None

    def create_manifest(self, sources: dict):
        """메타데이터 매니페스트 생성"""
        manifest = {
            'timestamp': TIMESTAMP,
            'data_source': sources,
            'base_path': str(self.base_path)
        }

        manifest_file = self.base_path / f"manifest_{TIMESTAMP}.json"
        with open(manifest_file, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ 매니페스트 생성: {manifest_file}")

    def run(self):
        """전체 다운로드 실행"""
        logger.info(f"\n🚀 데이터 다운로드 시작 ({TIMESTAMP})")

        sources = {}

        # Data.go.kr 다운로드
        datagovkr_file = self.download_datagovkr()
        if datagovkr_file:
            sources['data_go_kr'] = str(datagovkr_file)

        # Vworld 다운로드
        vworld_file = self.download_vworld()
        if vworld_file:
            sources['vworld'] = str(vworld_file)

        # 매니페스트 생성
        if sources:
            self.create_manifest(sources)
            logger.info(f"\n✅ 모든 다운로드 완료\n경로: {self.base_path}")
            return True
        else:
            logger.error("\n❌ 다운로드 실패")
            return False


if __name__ == "__main__":
    downloader = DataDownloader()
    downloader.run()
