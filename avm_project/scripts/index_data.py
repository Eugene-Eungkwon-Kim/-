"""
데이터 인덱싱 및 메타데이터 생성
검색 인덱스 생성, 메타-인덱싱, 성능 최적화
"""

import json
import logging
from pathlib import Path
from datetime import datetime
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

D_DRIVE_PATH = r'D:\LG_AVM_Workspace_Data_Moved_20260604'
TIMESTAMP = datetime.now().strftime('%Y-%m-%d')


class DataIndexer:
    def __init__(self):
        self.base_path = Path(D_DRIVE_PATH)
        self.raw_data_path = self.base_path / 'Raw_Data'
        self.indexed_path = self.base_path / 'Indexed_Data'
        self.indexed_path.mkdir(parents=True, exist_ok=True)
        self.index_metadata = {}

    def create_csv_index(self):
        """CSV 파일 인덱스 생성"""
        logger.info("\n" + "="*70)
        logger.info("CSV 파일 인덱싱 중...")
        logger.info("="*70)

        csv_files = list(self.raw_data_path.glob('*.csv'))

        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file)

                # 컬럼별 통계
                column_stats = {}
                for col in df.columns:
                    if df[col].dtype in ['int64', 'float64']:
                        column_stats[col] = {
                            'type': 'numeric',
                            'min': float(df[col].min()),
                            'max': float(df[col].max()),
                            'mean': float(df[col].mean()),
                            'null_count': int(df[col].isnull().sum())
                        }
                    else:
                        column_stats[col] = {
                            'type': 'categorical',
                            'unique': int(df[col].nunique()),
                            'null_count': int(df[col].isnull().sum())
                        }

                self.index_metadata[csv_file.name] = {
                    'type': 'csv',
                    'rows': len(df),
                    'columns': len(df.columns),
                    'column_info': column_stats,
                    'memory_mb': round(df.memory_usage(deep=True).sum() / (1024 ** 2), 2)
                }

                logger.info(f"✅ {csv_file.name}: {len(df)} 행 인덱싱 완료")

            except Exception as e:
                logger.error(f"❌ {csv_file.name}: {str(e)}")

    def create_json_index(self):
        """JSON 파일 인덱스 생성"""
        logger.info("\n" + "="*70)
        logger.info("JSON 파일 인덱싱 중...")
        logger.info("="*70)

        json_files = list(self.raw_data_path.glob('*.json'))

        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                if isinstance(data, list):
                    record_count = len(data)
                    sample_keys = list(data[0].keys()) if data else []
                else:
                    record_count = 1
                    sample_keys = list(data.keys())

                self.index_metadata[json_file.name] = {
                    'type': 'json',
                    'records': record_count,
                    'sample_keys': sample_keys[:10],
                    'file_size_mb': round(json_file.stat().st_size / (1024 ** 2), 2)
                }

                logger.info(f"✅ {json_file.name}: {record_count} 레코드 인덱싱 완료")

            except Exception as e:
                logger.error(f"❌ {json_file.name}: {str(e)}")

    def create_master_index(self):
        """마스터 인덱스 생성 및 저장"""
        logger.info("\n" + "="*70)
        logger.info("마스터 인덱스 생성 중...")
        logger.info("="*70)

        master_index = {
            'generated_at': TIMESTAMP,
            'data_source_path': str(self.raw_data_path),
            'total_files': len(self.index_metadata),
            'files': self.index_metadata
        }

        index_file = self.indexed_path / f"master_index_{TIMESTAMP}.json"
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(master_index, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ 마스터 인덱스 생성: {index_file}")

    def create_search_index(self):
        """검색 인덱스 생성 (파일명, 컬럼명 기반)"""
        logger.info("\n" + "="*70)
        logger.info("검색 인덱스 생성 중...")
        logger.info("="*70)

        search_index = {
            'files': {},
            'columns': {},
            'timestamp': TIMESTAMP
        }

        # 파일 기반 인덱싱
        for filename, metadata in self.index_metadata.items():
            search_index['files'][filename] = {
                'type': metadata.get('type'),
                'size': metadata.get('memory_mb') or metadata.get('file_size_mb')
            }

            # 컬럼 기반 인덱싱 (CSV만)
            if metadata.get('type') == 'csv' and 'column_info' in metadata:
                for col_name, col_info in metadata['column_info'].items():
                    if col_name not in search_index['columns']:
                        search_index['columns'][col_name] = []
                    search_index['columns'][col_name].append(filename)

        search_index_file = self.indexed_path / f"search_index_{TIMESTAMP}.json"
        with open(search_index_file, 'w', encoding='utf-8') as f:
            json.dump(search_index, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ 검색 인덱스 생성: {search_index_file}")

    def generate_index_report(self):
        """인덱싱 리포트 생성"""
        logger.info("\n" + "="*70)
        logger.info("인덱싱 리포트 생성 중...")
        logger.info("="*70)

        report_content = f"""# 📑 데이터 인덱싱 리포트

**생성일:** {TIMESTAMP}
**인덱스 경로:** {self.indexed_path}

## 📊 인덱싱 요약

- **총 파일 수:** {len(self.index_metadata)}
- **CSV 파일:** {sum(1 for m in self.index_metadata.values() if m.get('type') == 'csv')}
- **JSON 파일:** {sum(1 for m in self.index_metadata.values() if m.get('type') == 'json')}

## 📁 인덱싱된 파일 목록

"""

        for filename, metadata in self.index_metadata.items():
            report_content += f"\n### {filename}\n"
            report_content += f"- **타입:** {metadata.get('type')}\n"

            if metadata.get('type') == 'csv':
                report_content += f"- **행:** {metadata.get('rows')}\n"
                report_content += f"- **컬럼:** {metadata.get('columns')}\n"
                report_content += f"- **메모리:** {metadata.get('memory_mb')} MB\n"
            else:
                report_content += f"- **레코드:** {metadata.get('records')}\n"
                report_content += f"- **크기:** {metadata.get('file_size_mb')} MB\n"

        report_content += f"""

## 🔍 생성된 인덱스 파일

- `master_index_{TIMESTAMP}.json` - 모든 파일의 상세 메타데이터
- `search_index_{TIMESTAMP}.json` - 파일 및 컬럼 검색 인덱스

---

**상태:** ✅ 인덱싱 완료
"""

        report_path = self.indexed_path / f"INDEXING_REPORT_{TIMESTAMP}.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)

        logger.info(f"✅ 인덱싱 리포트: {report_path}")

    def run(self):
        """인덱싱 실행"""
        if not self.raw_data_path.exists():
            logger.warning(f"⚠️ Raw_Data 경로 없음: {self.raw_data_path}")
            return False

        logger.info(f"\n📑 데이터 인덱싱 시작\n경로: {self.raw_data_path}")

        self.create_csv_index()
        self.create_json_index()
        self.create_master_index()
        self.create_search_index()
        self.generate_index_report()

        logger.info("\n✅ 인덱싱 완료\n")
        return True


if __name__ == "__main__":
    indexer = DataIndexer()
    indexer.run()
