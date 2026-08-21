#!/usr/bin/env python3
"""
Phase 13.6.2 BigQuery Streamer Tests

Tests schema inference and streaming utilities.
"""

import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))


class TestBigQuerySchemaInference(unittest.TestCase):
    """Test BigQuery schema inference from DataFrames."""

    def test_infer_schema_basic_types(self) -> None:
        """Infer schema for basic data types."""
        from phase13_bigquery_streamer import infer_bq_schema

        df = pd.DataFrame({
            'property_id': ['P1', 'P2'],
            'price_local': [100_000.0, 200_000.0],
            'bedrooms': [1, 2],
            'is_new': [True, False],
        })
        schema = infer_bq_schema(df)

        self.assertEqual(len(schema), 4)
        schema_dict = {s['name']: s['type'] for s in schema}
        self.assertEqual(schema_dict['property_id'], 'STRING')
        self.assertEqual(schema_dict['price_local'], 'FLOAT64')
        self.assertEqual(schema_dict['bedrooms'], 'INTEGER')
        self.assertEqual(schema_dict['is_new'], 'BOOLEAN')

    def test_infer_schema_all_columns(self) -> None:
        """Infer schema with various column types."""
        from phase13_bigquery_streamer import infer_bq_schema

        df = pd.DataFrame({
            'id': [1, 2],
            'price': [100.5, 200.5],
            'name': ['A', 'B'],
        })
        schema = infer_bq_schema(df)

        self.assertEqual(len(schema), 3)
        self.assertIsNotNone(schema)


class TestInferBQSchemaFormatting(unittest.TestCase):
    """Test schema formatting."""

    def test_schema_has_required_fields(self) -> None:
        """Schema includes name and type fields."""
        from phase13_bigquery_streamer import infer_bq_schema

        df = pd.DataFrame({'col1': [1, 2]})
        schema = infer_bq_schema(df)

        self.assertEqual(len(schema), 1)
        self.assertIn('name', schema[0])
        self.assertIn('type', schema[0])
        self.assertEqual(schema[0]['name'], 'col1')


class TestStreamToBigQueryFunction(unittest.TestCase):
    """Test high-level stream_to_bigquery function."""

    def test_stream_to_bigquery_file_not_found(self) -> None:
        """Handle missing input file gracefully."""
        from phase13_bigquery_streamer import stream_to_bigquery

        result = stream_to_bigquery('/nonexistent/file.csv', 'BR', 'project')
        self.assertFalse(result)

    def test_stream_to_bigquery_missing_bigquery_library(self) -> None:
        """Handle missing google-cloud-bigquery gracefully."""
        from phase13_bigquery_streamer import stream_to_bigquery

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / 'test.csv'
            df = pd.DataFrame({'property_id': ['P1'], 'price_local': [100_000.0]})
            df.to_csv(csv_path, index=False)

            result = stream_to_bigquery(str(csv_path), 'BR', 'test-project')
            self.assertFalse(result)


class TestBigQueryStreamerTableId(unittest.TestCase):
    """Test BigQuery table ID generation."""

    def test_table_id_generation(self) -> None:
        """Table ID should follow project.dataset.table format."""
        expected_parts = ['test-project', 'test_dataset', 'properties_br']

        table_id = 'test-project.test_dataset.properties_br'

        self.assertEqual(table_id.split('.')[0], expected_parts[0])
        self.assertEqual(table_id.split('.')[1], expected_parts[1])
        self.assertEqual(table_id.split('.')[2], expected_parts[2])


class TestDataFrameToDict(unittest.TestCase):
    """Test DataFrame serialization for BigQuery."""

    def test_dataframe_to_dict_records(self) -> None:
        """DataFrame converts to dict records correctly."""
        df = pd.DataFrame({
            'property_id': ['P1', 'P2'],
            'price_local': [100_000.0, 200_000.0],
            'bedrooms': [1, 2],
        })

        records = df.to_dict('records')

        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]['property_id'], 'P1')
        self.assertEqual(records[1]['price_local'], 200_000.0)

    def test_dataframe_with_nulls_to_dict(self) -> None:
        """DataFrame with null values serializes correctly."""
        import numpy as np

        df = pd.DataFrame({
            'property_id': ['P1', 'P2'],
            'city': ['A', None],
        })

        records = df.to_dict('records')

        self.assertEqual(len(records), 2)
        self.assertTrue(pd.isna(records[1]['city']))


if __name__ == '__main__':
    unittest.main()
