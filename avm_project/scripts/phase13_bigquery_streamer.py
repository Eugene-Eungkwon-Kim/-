#!/usr/bin/env python3
"""
Phase 13.6.2 - BigQuery Streaming Module (Optional)
검증된 부동산 데이터를 BigQuery로 스트리밍하는 선택적 모듈.

실행:
    python scripts/phase13_bigquery_streamer.py --input data/raw/BR_real.csv --country BR
    python scripts/phase13_bigquery_streamer.py --input data/raw/SG_real.csv --country SG --project my-gcp-project

환경변수:
    GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json (GCP 인증)
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

BATCH_SIZE = 1000


class BigQueryStreamer:
    """Stream validated property records to BigQuery."""

    def __init__(self, project_id: str, dataset_id: str = 'avm_data') -> None:
        """Initialize BigQuery streamer.

        Args:
            project_id: GCP project ID
            dataset_id: BigQuery dataset name (default: avm_data)
        """
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.client = None
        self.table_ref = None

        try:
            from google.cloud import bigquery
            self.client = bigquery.Client(project=project_id)
            log.info(f"✅ Connected to BigQuery: {project_id}.{dataset_id}")
        except ImportError:
            log.error("❌ google-cloud-bigquery not installed")
            log.info("   Install with: pip install google-cloud-bigquery")
            raise
        except Exception as e:
            log.error(f"❌ BigQuery auth failed: {e}")
            log.info("   Ensure GOOGLE_APPLICATION_CREDENTIALS is set")
            raise

    def get_table_id(self, country: str) -> str:
        """Get table ID for country."""
        return f"{self.project_id}.{self.dataset_id}.properties_{country.lower()}"

    def create_table_if_needed(self, country: str, schema: List[Dict]) -> bool:
        """Create BigQuery table if it doesn't exist."""
        from google.cloud import bigquery

        table_id = self.get_table_id(country)
        try:
            self.client.get_table(table_id)
            log.info(f"✅ Table exists: {table_id}")
            return True
        except Exception:
            log.info(f"Creating table: {table_id}")
            bq_schema = [
                bigquery.SchemaField(col['name'], col['type'].upper(), mode='NULLABLE')
                for col in schema
            ]
            table = bigquery.Table(table_id, schema=bq_schema)
            self.client.create_table(table)
            log.info(f"✅ Table created: {table_id}")
            return True

    def stream_records(
        self, country: str, df: pd.DataFrame, skip_errors: bool = False
    ) -> Dict[str, int]:
        """Stream validated records to BigQuery in batches.

        Args:
            country: Country code (e.g., 'BR', 'SG')
            df: DataFrame with validated records
            skip_errors: Skip records with errors (default False)

        Returns:
            Dictionary with stream stats {rows_streamed, rows_failed, rows_skipped}
        """
        if self.client is None:
            return {'rows_streamed': 0, 'rows_failed': 1, 'rows_skipped': len(df)}

        table_id = self.get_table_id(country)
        rows_streamed = 0
        rows_failed = 0
        rows_skipped = 0

        for i in range(0, len(df), BATCH_SIZE):
            batch = df.iloc[i : i + BATCH_SIZE]
            errors = self.client.insert_rows_json(table_id, batch.to_dict('records'))

            if errors:
                if skip_errors:
                    rows_failed += len(errors)
                    log.warning(f"⚠️  {len(errors)} row insert errors (skipped)")
                else:
                    raise Exception(f"BigQuery insert failed: {errors}")
            else:
                rows_streamed += len(batch)
                if (i // BATCH_SIZE + 1) % 10 == 0:
                    log.info(f"  Streamed {rows_streamed:,} records...")

        return {
            'rows_streamed': rows_streamed,
            'rows_failed': rows_failed,
            'rows_skipped': rows_skipped,
        }


def infer_bq_schema(df: pd.DataFrame) -> List[Dict]:
    """Infer BigQuery schema from DataFrame."""
    type_map = {
        'int64': 'INTEGER',
        'float64': 'FLOAT64',
        'object': 'STRING',
        'datetime64': 'TIMESTAMP',
        'bool': 'BOOLEAN',
    }
    schema = []
    for col, dtype in df.dtypes.items():
        bq_type = type_map.get(str(dtype), 'STRING')
        schema.append({'name': col, 'type': bq_type})
    return schema


def stream_to_bigquery(
    input_csv: str, country: str, project_id: str, dataset_id: str = 'avm_data'
) -> bool:
    """Load CSV and stream to BigQuery.

    Args:
        input_csv: Path to validated CSV file
        country: Country code
        project_id: GCP project ID
        dataset_id: BigQuery dataset name

    Returns:
        True if successful, False otherwise
    """
    csv_path = Path(input_csv)
    if not csv_path.exists():
        log.error(f"❌ File not found: {input_csv}")
        return False

    try:
        log.info(f"📖 Loading: {input_csv}")
        df = pd.read_csv(csv_path)
        log.info(f"Loaded {len(df):,} records, {len(df.columns)} columns")

        log.info(f"🔗 Connecting to BigQuery: {project_id}")
        streamer = BigQueryStreamer(project_id, dataset_id)

        schema = infer_bq_schema(df)
        streamer.create_table_if_needed(country, schema)

        log.info(f"📤 Streaming to BigQuery...")
        stats = streamer.stream_records(country, df)

        log.info(f"\n✅ Streaming complete:")
        log.info(f"  Streamed: {stats['rows_streamed']:,}")
        log.info(f"  Failed: {stats['rows_failed']:,}")
        log.info(f"  Skipped: {stats['rows_skipped']:,}")

        return stats['rows_failed'] == 0

    except ImportError:
        log.error("❌ google-cloud-bigquery not installed")
        return False
    except Exception as e:
        log.error(f"❌ Streaming failed: {e}")
        return False


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description='Phase 13.6.2 BigQuery Streamer')
    parser.add_argument('--input', required=True, help='Input validated CSV')
    parser.add_argument('--country', required=True, help='Country code (e.g., BR, SG)')
    parser.add_argument('--project', required=True, help='GCP project ID')
    parser.add_argument('--dataset', default='avm_data', help='BigQuery dataset')
    args = parser.parse_args()

    success = stream_to_bigquery(args.input, args.country, args.project, args.dataset)
    exit(0 if success else 1)


if __name__ == '__main__':
    main()
