"""
데이터 클렌징 및 정규화
결측치 처리, 아웃라이어 제거, 정규화
"""

import logging
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

D_DRIVE_PATH = r'D:\LG_AVM_Workspace_Data_Moved_20260604'
TIMESTAMP = datetime.now().strftime('%Y-%m-%d')


class DataCleaner:
    def __init__(self):
        self.base_path = Path(D_DRIVE_PATH)
        self.raw_path = self.base_path / 'Raw_Data'
        self.cleansed_path = self.base_path / 'Cleansed_Data'
        self.cleansed_path.mkdir(parents=True, exist_ok=True)
        self.cleansing_report = {}

    def handle_missing_values(self, df, filename):
        """결측치 처리"""
        missing_before = df.isnull().sum().sum()

        # 수치형 컬럼: 평균으로 대체
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if df[col].isnull().any():
                df[col].fillna(df[col].mean(), inplace=True)

        # 범주형 컬럼: 최빈값으로 대체
        categorical_cols = df.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            if df[col].isnull().any():
                df[col].fillna(df[col].mode()[0] if not df[col].mode().empty else 'Unknown', inplace=True)

        missing_after = df.isnull().sum().sum()

        logger.info(f"  • 결측치 처리: {missing_before} → {missing_after}")
        self.cleansing_report[filename]['missing_values'] = {
            'before': int(missing_before),
            'after': int(missing_after),
            'handled': int(missing_before - missing_after)
        }

        return df

    def remove_outliers(self, df, filename):
        """아웃라이어 제거 (IQR 방법)"""
        rows_before = len(df)

        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1

            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR

            # 아웃라이어 제거
            df = df[(df[col] >= lower_bound) & (df[col] <= upper_bound)]

        rows_after = len(df)
        outliers_removed = rows_before - rows_after

        logger.info(f"  • 아웃라이어 제거: {rows_before} → {rows_after} ({outliers_removed} 행 제거)")
        self.cleansing_report[filename]['outliers'] = {
            'rows_before': int(rows_before),
            'rows_after': int(rows_after),
            'removed': int(outliers_removed)
        }

        return df

    def normalize_data(self, df, filename):
        """데이터 정규화 (Min-Max)"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns

        if len(numeric_cols) > 0:
            scaler = MinMaxScaler()
            df[numeric_cols] = scaler.fit_transform(df[numeric_cols])

            logger.info(f"  • 데이터 정규화: {len(numeric_cols)} 개 수치형 컬럼")
            self.cleansing_report[filename]['normalization'] = {
                'normalized_columns': int(len(numeric_cols)),
                'method': 'MinMaxScaler'
            }

        return df

    def cleanse_csv_files(self):
        """CSV 파일 클렌징"""
        logger.info("\n" + "="*70)
        logger.info("CSV 파일 클렌징 중...")
        logger.info("="*70)

        csv_files = list(self.raw_path.glob('*.csv'))

        for csv_file in csv_files:
            try:
                logger.info(f"\n📄 {csv_file.name}")
                self.cleansing_report[csv_file.name] = {}

                df = pd.read_csv(csv_file)

                # 단계별 클렌징
                df = self.handle_missing_values(df, csv_file.name)
                df = self.remove_outliers(df, csv_file.name)
                df = self.normalize_data(df, csv_file.name)

                # 클렌징된 데이터 저장
                output_file = self.cleansed_path / csv_file.name
                df.to_csv(output_file, index=False, encoding='utf-8')

                logger.info(f"  ✅ 저장: {output_file}")
                self.cleansing_report[csv_file.name]['status'] = 'success'

            except Exception as e:
                logger.error(f"❌ {csv_file.name}: {str(e)}")
                self.cleansing_report[csv_file.name]['status'] = 'error'
                self.cleansing_report[csv_file.name]['error'] = str(e)

    def copy_json_files(self):
        """JSON 파일 복사 (클렌징 불필요)"""
        logger.info("\n" + "="*70)
        logger.info("JSON 파일 처리 중...")
        logger.info("="*70)

        json_files = list(self.raw_path.glob('*.json'))

        for json_file in json_files:
            try:
                import shutil
                output_file = self.cleansed_path / json_file.name
                shutil.copy2(json_file, output_file)

                logger.info(f"✅ 복사: {json_file.name}")
                self.cleansing_report[json_file.name] = {
                    'status': 'copied',
                    'note': 'JSON files copied without modification'
                }

            except Exception as e:
                logger.error(f"❌ {json_file.name}: {str(e)}")

    def generate_cleansing_report(self):
        """클렌징 리포트 생성"""
        logger.info("\n" + "="*70)
        logger.info("클렌징 리포트 생성 중...")
        logger.info("="*70)

        report_content = f"""# 🧹 데이터 클렌징 리포트

**생성일:** {TIMESTAMP}
**클렌싱 경로:** {self.cleansed_path}

## 📊 클렌징 요약

- **처리된 파일:** {len(self.cleansing_report)}
- **성공:** {sum(1 for r in self.cleansing_report.values() if r.get('status') in ['success', 'copied'])}
- **실패:** {sum(1 for r in self.cleansing_report.values() if r.get('status') == 'error')}

## 📁 파일별 클렌징 상세

"""

        for filename, report in self.cleansing_report.items():
            report_content += f"\n### {filename}\n"
            report_content += f"- **상태:** {report.get('status', 'unknown')}\n"

            if report.get('status') == 'success':
                missing = report.get('missing_values', {})
                outliers = report.get('outliers', {})
                normalize = report.get('normalization', {})

                if missing:
                    report_content += f"- **결측치:** {missing.get('before')} → {missing.get('after')} (처리: {missing.get('handled')})\n"
                if outliers:
                    report_content += f"- **아웃라이어:** {outliers.get('removed')}개 제거 ({outliers.get('rows_before')} → {outliers.get('rows_after')} 행)\n"
                if normalize:
                    report_content += f"- **정규화:** {normalize.get('normalized_columns')} 컬럼 ({normalize.get('method')})\n"

            elif report.get('status') == 'copied':
                report_content += f"- **처리:** {report.get('note')}\n"

            if report.get('error'):
                report_content += f"- **오류:** {report.get('error')}\n"

        report_content += f"""

## 🎯 클렌징 프로세스

1. **결측치 처리:** 수치형은 평균값, 범주형은 최빈값으로 대체
2. **아웃라이어 제거:** IQR(사분위수범위) 방법 사용
3. **정규화:** Min-Max 스케일링 (0-1 범위)

---

**상태:** ✅ 클렌징 완료
"""

        report_path = self.cleansed_path / f"CLEANSING_REPORT_{TIMESTAMP}.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)

        logger.info(f"✅ 클렌징 리포트: {report_path}")

    def run(self):
        """클렌징 실행"""
        if not self.raw_path.exists():
            logger.warning(f"⚠️ Raw_Data 경로 없음: {self.raw_path}")
            return False

        logger.info(f"\n🧹 데이터 클렌징 시작\n경로: {self.raw_path}")

        self.cleanse_csv_files()
        self.copy_json_files()
        self.generate_cleansing_report()

        logger.info("\n✅ 클렌징 완료\n")
        return True


if __name__ == "__main__":
    cleaner = DataCleaner()
    cleaner.run()
