import json
import logging
from io import BytesIO
from typing import List, Optional, Any, Dict

import pandas as pd

logger = logging.getLogger(__name__)


class ExportManager:
    """다양한 포맷으로 데이터 내보내기"""

    SUPPORTED_FORMATS = ["csv", "excel", "json", "parquet", "hdf5", "sqlite"]

    @staticmethod
    def export_data(
        data: List[Dict[str, Any]],
        format: str = "csv",
        filename: Optional[str] = None,
        compression: Optional[str] = None,
    ) -> bytes:
        """
        데이터를 지정된 포맷으로 내보내기

        Args:
            data: 내보낼 데이터 (딕셔너리 리스트)
            format: 내보내기 포맷 (csv, excel, json, parquet, hdf5)
            filename: 파일명 (HDF5 등에서 필요)
            compression: 압축 방식 (gzip, brotli, snappy 등)

        Returns:
            바이너리 데이터
        """
        if format not in ExportManager.SUPPORTED_FORMATS:
            raise ValueError(
                f"지원하지 않는 포맷: {format}. "
                f"지원 포맷: {', '.join(ExportManager.SUPPORTED_FORMATS)}"
            )

        df = pd.DataFrame(data)

        if format == "csv":
            return ExportManager._export_csv(df, compression)
        elif format == "excel":
            return ExportManager._export_excel(df, compression)
        elif format == "json":
            return ExportManager._export_json(df, compression)
        elif format == "parquet":
            return ExportManager._export_parquet(df, compression)
        elif format == "hdf5":
            if not filename:
                raise ValueError("HDF5 내보내기에는 filename이 필요합니다")
            return ExportManager._export_hdf5(df, filename, compression)
        elif format == "sqlite":
            if not filename:
                raise ValueError("SQLite 내보내기에는 filename이 필요합니다")
            return ExportManager._export_sqlite(df, filename)

    @staticmethod
    def _export_csv(df: pd.DataFrame, compression: Optional[str] = None) -> bytes:
        """CSV 형식 내보내기"""
        try:
            buffer = BytesIO()
            df.to_csv(
                buffer,
                index=False,
                encoding="utf-8-sig",
                compression=compression,
            )
            buffer.seek(0)
            return buffer.getvalue()
        except Exception as e:
            logger.error(f"CSV 내보내기 실패: {str(e)}")
            raise

    @staticmethod
    def _export_excel(df: pd.DataFrame, compression: Optional[str] = None) -> bytes:
        """Excel 형식 내보내기"""
        try:
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name="Data", index=False)

                # 열 너비 자동 조정
                worksheet = writer.sheets["Data"]
                for idx, col in enumerate(df.columns):
                    max_length = max(
                        df[col].astype(str).apply(len).max(),
                        len(str(col)),
                    )
                    worksheet.column_dimensions[
                        chr(65 + idx)
                    ].width = min(max_length + 2, 50)

            buffer.seek(0)
            return buffer.getvalue()
        except Exception as e:
            logger.error(f"Excel 내보내기 실패: {str(e)}")
            raise

    @staticmethod
    def _export_json(df: pd.DataFrame, compression: Optional[str] = None) -> bytes:
        """JSON 형식 내보내기"""
        try:
            data = df.to_dict(orient="records")
            json_str = json.dumps(data, ensure_ascii=False, indent=2)
            json_bytes = json_str.encode("utf-8")

            if compression:
                import gzip

                if compression == "gzip":
                    json_bytes = gzip.compress(json_bytes)
                elif compression == "brotli":
                    try:
                        import brotli

                        json_bytes = brotli.compress(json_bytes)
                    except ImportError:
                        logger.warning("brotli 라이브러리가 설치되지 않았습니다")

            return json_bytes
        except Exception as e:
            logger.error(f"JSON 내보내기 실패: {str(e)}")
            raise

    @staticmethod
    def _export_parquet(df: pd.DataFrame, compression: Optional[str] = None) -> bytes:
        """Parquet 형식 내보내기 (대용량 고속 처리)"""
        try:
            import pyarrow.parquet as pq
            import pyarrow as pa

            buffer = BytesIO()
            table = pa.Table.from_pandas(df)
            pq.write_table(table, buffer, compression=compression or "snappy")
            buffer.seek(0)
            return buffer.getvalue()
        except ImportError:
            logger.error("pyarrow 라이브러리가 필요합니다: pip install pyarrow")
            raise
        except Exception as e:
            logger.error(f"Parquet 내보내기 실패: {str(e)}")
            raise

    @staticmethod
    def _export_hdf5(
        df: pd.DataFrame, filename: str, compression: Optional[str] = None
    ) -> bytes:
        """HDF5 형식 내보내기 (계층 구조 데이터)"""
        try:
            import h5py

            buffer = BytesIO()
            with h5py.File(buffer, "w") as f:
                # 메타데이터
                f.attrs["source"] = "NPL AVM API"
                f.attrs["rows"] = len(df)
                f.attrs["columns"] = len(df.columns)

                # 컬럼별 데이터 저장
                for col in df.columns:
                    data = df[col].values
                    f.create_dataset(col, data=data, compression=compression)

            buffer.seek(0)
            return buffer.getvalue()
        except ImportError:
            logger.error("h5py 라이브러리가 필요합니다: pip install h5py")
            raise
        except Exception as e:
            logger.error(f"HDF5 내보내기 실패: {str(e)}")
            raise

    @staticmethod
    def _export_sqlite(df: pd.DataFrame, filename: str) -> bytes:
        """SQLite 데이터베이스로 내보내기"""
        try:
            import sqlite3

            buffer = BytesIO()
            conn = sqlite3.connect(":memory:")
            df.to_sql("data", conn, if_exists="replace", index=False)

            # 메모리 DB를 파일로 변환
            with open(":memory:", "rb") as f:
                return f.read()

        except Exception as e:
            logger.error(f"SQLite 내보내기 실패: {str(e)}")
            raise

    @staticmethod
    def get_content_type(format: str) -> str:
        """포맷별 Content-Type 반환"""
        content_types = {
            "csv": "text/csv",
            "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "json": "application/json",
            "parquet": "application/octet-stream",
            "hdf5": "application/octet-stream",
            "sqlite": "application/octet-stream",
        }
        return content_types.get(format, "application/octet-stream")

    @staticmethod
    def get_file_extension(format: str) -> str:
        """포맷별 파일 확장자 반환"""
        extensions = {
            "csv": "csv",
            "excel": "xlsx",
            "json": "json",
            "parquet": "parquet",
            "hdf5": "h5",
            "sqlite": "db",
        }
        return extensions.get(format, format)


export_manager = ExportManager()
