"""
데이터 검증 및 디버깅
다운로드된 데이터 품질 확인, 오류 로깅, QA 리포트 생성
"""

import json
import logging
from pathlib import Path
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv

from data_path_config import get_data_path
from exceptions import DataValidationError

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

D_DRIVE_PATH = get_data_path()
TIMESTAMP = datetime.now().strftime('%Y-%m-%d')


class DataDebugger:
    def __init__(self):
        self.base_path = Path(D_DRIVE_PATH)
        self.raw_data_path = self.base_path / 'Raw_Data'
        self.qa_report = {}

    def validate_json_files(self):
        """JSON 파일 검증"""
        logger.info("\n" + "="*70)
        logger.info("JSON 파일 검증 중...")
        logger.info("="*70)

        json_files = list(self.raw_data_path.glob('*.json'))
        valid_count = 0

        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                file_size = json_file.stat().st_size / (1024 * 1024)  # MB
                record_count = len(data) if isinstance(data, list) else 1

                logger.info(f"✅ {json_file.name}: {record_count} 레코드, {file_size:.2f} MB")
                self.qa_report[json_file.name] = {
                    'status': 'valid',
                    'records': record_count,
                    'size_mb': round(file_size, 2)
                }
                valid_count += 1
            except Exception as e:
                logger.error(f"❌ {json_file.name}: {str(e)}")
                self.qa_report[json_file.name] = {'status': 'error', 'error': str(e)}

        return valid_count

    def validate_csv_files(self):
        """CSV 파일 검증"""
        logger.info("\n" + "="*70)
        logger.info("CSV 파일 검증 중...")
        logger.info("="*70)

        csv_files = list(self.raw_data_path.glob('*.csv'))
        valid_count = 0

        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file)
                file_size = csv_file.stat().st_size / (1024 * 1024)

                logger.info(f"✅ {csv_file.name}: {len(df)} 행, {len(df.columns)} 열, {file_size:.2f} MB")
                self.qa_report[csv_file.name] = {
                    'status': 'valid',
                    'rows': len(df),
                    'columns': len(df.columns),
                    'size_mb': round(file_size, 2),
                    'missing_values': df.isnull().sum().to_dict()
                }
                valid_count += 1
            except Exception as e:
                logger.error(f"❌ {csv_file.name}: {str(e)}")
                self.qa_report[csv_file.name] = {'status': 'error', 'error': str(e)}

        return valid_count

    def check_manifest(self):
        """매니페스트 파일 검증"""
        logger.info("\n" + "="*70)
        logger.info("메타데이터 매니페스트 검증")
        logger.info("="*70)

        manifest_files = list(self.base_path.glob('manifest_*.json'))

        for manifest_file in manifest_files:
            try:
                with open(manifest_file, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)

                logger.info(f"✅ {manifest_file.name}")
                logger.info(f"   타임스탬프: {manifest.get('timestamp')}")
                logger.info(f"   데이터소스: {list(manifest.get('data_source', {}).keys())}")
                self.qa_report['manifest'] = {'status': 'valid'}
            except Exception as e:
                logger.error(f"❌ 매니페스트 오류: {str(e)}")
                self.qa_report['manifest'] = {'status': 'error', 'error': str(e)}

    def generate_qa_report(self):
        """QA 리포트 생성"""
        logger.info("\n" + "="*70)
        logger.info("QA 리포트 생성 중...")
        logger.info("="*70)

        report_content = f"""# 📋 데이터 검증 리포트

**생성일:** {TIMESTAMP}
**경로:** {self.base_path}

## ✅ 검증 결과

### 파일 상태
"""

        for filename, status in self.qa_report.items():
            if isinstance(status, dict):
                report_content += f"\n- **{filename}**: {status.get('status', 'unknown')}\n"
                if status.get('status') == 'valid':
                    if 'rows' in status:
                        report_content += f"  - 행: {status['rows']}\n"
                    if 'records' in status:
                        report_content += f"  - 레코드: {status['records']}\n"
                    report_content += f"  - 크기: {status.get('size_mb', 0):.2f} MB\n"
                if 'error' in status:
                    report_content += f"  - 오류: {status['error']}\n"

        report_content += f"""

## 📊 요약

- 총 검증 파일: {len(self.qa_report)}
- 유효한 파일: {sum(1 for v in self.qa_report.values() if isinstance(v, dict) and v.get('status') == 'valid')}
- 오류 파일: {sum(1 for v in self.qa_report.values() if isinstance(v, dict) and v.get('status') == 'error')}

---

**상태:** {'✅ 모든 파일 유효' if all(v.get('status') == 'valid' for v in self.qa_report.values() if isinstance(v, dict)) else '⚠️ 일부 파일 오류'}
"""

        report_path = self.base_path / f"QA_REPORT_{TIMESTAMP}.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)

        logger.info(f"✅ QA 리포트 생성: {report_path}")

    def run(self):
        """데이터 디버깅 실행"""
        if not self.raw_data_path.exists():
            logger.warning(f"⚠️ Raw_Data 경로 없음: {self.raw_data_path}")
            return False

        logger.info(f"\n🔍 데이터 검증 시작\n경로: {self.raw_data_path}")

        self.validate_json_files()
        self.validate_csv_files()
        self.check_manifest()
        self.generate_qa_report()

        logger.info("\n✅ 데이터 검증 완료\n")
        return True


if __name__ == "__main__":
    debugger = DataDebugger()
    debugger.run()
