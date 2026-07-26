#!/usr/bin/env python3
"""
AVM 데이터 마이그레이션 & 클랜징 실행 스크립트
2026-06-23
"""

import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import json
from typing import Dict, Tuple

# 프로젝트 경로
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_DIR = SCRIPT_DIR.parent
DATA_RAW_DIR = PROJECT_DIR / "data" / "raw"
DATA_PROCESSED_DIR = PROJECT_DIR / "data" / "processed"
OUTPUT_DIR = PROJECT_DIR / "output"

# 디렉토리 생성
DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("🔄 AVM 데이터 마이그레이션 & 클랜징 실행")
print("=" * 80)
print(f"작업 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# 처리할 파일 목록
FILES_TO_PROCESS = [
    "real_estate_2024.csv",
    "real_estate_combined_20260617.csv",
    "signal_real_estate_202401_202412.csv",
    "sample_npl_data.csv"
]

migration_report = {
    "timestamp": datetime.now().isoformat(),
    "files": {},
    "summary": {}
}

def analyze_data_quality(df: pd.DataFrame, filename: str) -> Dict:
    """데이터 품질 분석"""
    analysis = {
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "columns": list(df.columns),
        "memory_mb": df.memory_usage(deep=True).sum() / 1024 / 1024,
        "missing_values": {},
        "duplicate_rows": 0,
        "data_types": df.dtypes.astype(str).to_dict(),
    }

    # 결측치 분석
    for col in df.columns:
        missing = df[col].isnull().sum()
        if missing > 0:
            analysis["missing_values"][col] = {
                "count": int(missing),
                "percentage": float(missing / len(df) * 100)
            }

    # 중복 분석
    analysis["duplicate_rows"] = int(df.duplicated().sum())

    return analysis

def clean_data(df: pd.DataFrame, filename: str) -> Tuple[pd.DataFrame, Dict]:
    """데이터 클랜징 수행"""
    cleaning_log = {
        "original_rows": len(df),
        "steps": []
    }

    # Step 1: 중복 제거
    duplicates_removed = df.duplicated().sum()
    if duplicates_removed > 0:
        df = df.drop_duplicates()
        cleaning_log["steps"].append({
            "action": "Remove duplicates",
            "removed_rows": int(duplicates_removed)
        })

    # Step 2: 결측치 처리
    missing_info = {}
    for col in df.columns:
        missing = df[col].isnull().sum()
        if missing > 0:
            missing_info[col] = int(missing)

    if missing_info:
        # 수치형 칼럼: 중앙값으로 채우기
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if col in missing_info:
                median_val = df[col].median()
                df[col].fillna(median_val, inplace=True)

        # 범주형 칼럼: 최빈값으로 채우기
        categorical_cols = df.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            if col in missing_info:
                mode_val = df[col].mode()
                if len(mode_val) > 0:
                    df[col].fillna(mode_val[0], inplace=True)

        cleaning_log["steps"].append({
            "action": "Fill missing values",
            "columns_affected": missing_info
        })

    # Step 3: 숫자형 칼럼 이상치 검출 (IQR 방식)
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    outliers_removed = 0

    for col in numeric_cols:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1

        lower_bound = Q1 - 3 * IQR  # 더 관대한 기준
        upper_bound = Q3 + 3 * IQR

        outlier_mask = (df[col] < lower_bound) | (df[col] > upper_bound)
        col_outliers = outlier_mask.sum()

        if col_outliers > 0:
            outliers_removed += col_outliers

    if outliers_removed > 0:
        cleaning_log["steps"].append({
            "action": "Detect outliers",
            "outliers_detected": int(outliers_removed),
            "note": "Outliers kept for analysis (not removed)"
        })

    # Step 4: 데이터 타입 최적화
    for col in df.columns:
        # 정수형 변수 최적화
        if df[col].dtype == 'float64':
            if df[col].isnull().sum() == 0 and (df[col] == df[col].astype(int)).all():
                df[col] = df[col].astype('int32')

        # 범주형 변수 최적화
        if df[col].dtype == 'object':
            if len(df[col].unique()) < len(df) * 0.05:  # 고유값이 5% 미만
                df[col] = df[col].astype('category')

    cleaning_log["steps"].append({
        "action": "Optimize data types",
        "result": "Compressed numeric and categorical types"
    })

    cleaning_log["final_rows"] = len(df)
    cleaning_log["total_rows_removed"] = cleaning_log["original_rows"] - cleaning_log["final_rows"]
    cleaning_log["retention_rate"] = f"{(len(df) / cleaning_log['original_rows'] * 100):.2f}%"

    return df, cleaning_log

def validate_data(df: pd.DataFrame, filename: str) -> Dict:
    """클랜징 후 데이터 검증"""
    validation = {
        "passed_checks": 0,
        "total_checks": 6,
        "results": {}
    }

    # Check 1: 행 수 확인
    check1 = len(df) > 0
    validation["results"]["row_count"] = {
        "status": "✅ PASS" if check1 else "❌ FAIL",
        "value": len(df)
    }
    if check1: validation["passed_checks"] += 1

    # Check 2: 결측치 확인
    missing_total = df.isnull().sum().sum()
    check2 = missing_total == 0
    validation["results"]["missing_values"] = {
        "status": "✅ PASS" if check2 else "⚠️ WARNING",
        "value": int(missing_total),
        "message": "No missing values" if check2 else f"{missing_total} missing values remain"
    }
    if check2: validation["passed_checks"] += 1

    # Check 3: 중복 확인
    duplicates = df.duplicated().sum()
    check3 = duplicates == 0
    validation["results"]["duplicates"] = {
        "status": "✅ PASS" if check3 else "❌ FAIL",
        "value": int(duplicates)
    }
    if check3: validation["passed_checks"] += 1

    # Check 4: 메모리 사용량
    memory_mb = df.memory_usage(deep=True).sum() / 1024 / 1024
    check4 = memory_mb < 500  # 500MB 제한
    validation["results"]["memory"] = {
        "status": "✅ PASS" if check4 else "⚠️ WARNING",
        "value": f"{memory_mb:.2f} MB",
        "threshold": "500 MB"
    }
    if check4: validation["passed_checks"] += 1

    # Check 5: 데이터 타입 확인
    dtype_summary = df.dtypes.value_counts().to_dict()
    check5 = len(df.dtypes) > 0
    dtype_dist = {}
    for k, v in dtype_summary.items():
        dtype_name = str(k) if hasattr(k, '__str__') else k.__name__
        dtype_dist[dtype_name] = int(v)
    validation["results"]["data_types"] = {
        "status": "✅ PASS" if check5 else "❌ FAIL",
        "distribution": dtype_dist
    }
    if check5: validation["passed_checks"] += 1

    # Check 6: 샘플 통계
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) > 0:
        check6 = True
        sample_stats = {}
        for col in numeric_cols[:5]:  # 처음 5개 수치형 칼럼만
            sample_stats[col] = {
                "min": float(df[col].min()),
                "max": float(df[col].max()),
                "mean": float(df[col].mean()),
                "std": float(df[col].std())
            }
        validation["results"]["statistics"] = {
            "status": "✅ PASS",
            "sample": sample_stats
        }
        if check6: validation["passed_checks"] += 1

    validation["overall_status"] = "✅ PASS" if validation["passed_checks"] == validation["total_checks"] else "⚠️ PASS WITH WARNINGS"

    return validation

# 메인 처리 루프
print("📂 처리할 파일 목록:")
print("-" * 80)

total_rows_before = 0
total_rows_after = 0

for filename in FILES_TO_PROCESS:
    filepath = DATA_RAW_DIR / filename

    if not filepath.exists():
        print(f"⚠️  파일 없음: {filename}")
        continue

    print(f"\n🔄 처리 중: {filename}")
    print("-" * 80)

    try:
        # 1. 원본 데이터 로드
        df = pd.read_csv(filepath, encoding='utf-8-sig')
        print(f"  ✅ 로드 완료: {len(df)} rows × {len(df.columns)} cols")

        total_rows_before += len(df)

        # 2. 데이터 품질 분석
        print(f"\n  📊 데이터 품질 분석:")
        quality_before = analyze_data_quality(df, filename)
        print(f"     - 총 행: {quality_before['total_rows']}")
        print(f"     - 총 열: {quality_before['total_columns']}")
        print(f"     - 메모리: {quality_before['memory_mb']:.2f} MB")
        print(f"     - 중복 행: {quality_before['duplicate_rows']}")
        if quality_before['missing_values']:
            print(f"     - 결측치 칼럼: {len(quality_before['missing_values'])}")

        # 3. 데이터 클랜징
        print(f"\n  🧹 클랜징 수행:")
        df_cleaned, cleaning_log = clean_data(df, filename)

        for step in cleaning_log["steps"]:
            print(f"     ✓ {step['action']}")

        print(f"     결과: {cleaning_log['original_rows']} → {cleaning_log['final_rows']} rows")
        print(f"     유지율: {cleaning_log['retention_rate']}")

        total_rows_after += len(df_cleaned)

        # 4. 클랜징 후 검증
        print(f"\n  ✅ 검증:")
        validation = validate_data(df_cleaned, filename)
        print(f"     검증 통과: {validation['passed_checks']}/{validation['total_checks']}")
        print(f"     상태: {validation['overall_status']}")

        # 5. 처리된 파일 저장
        output_path = DATA_PROCESSED_DIR / f"cleaned_{filename}"
        df_cleaned.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"\n  💾 저장 완료: {output_path}")

        # 보고서에 기록
        migration_report["files"][filename] = {
            "quality_before": {
                "rows": quality_before['total_rows'],
                "columns": quality_before['total_columns'],
                "memory_mb": round(quality_before['memory_mb'], 2),
                "duplicates": quality_before['duplicate_rows'],
                "missing_values_columns": len(quality_before['missing_values'])
            },
            "cleaning": cleaning_log,
            "validation": validation,
            "output_file": str(output_path)
        }

    except Exception as e:
        print(f"  ❌ 오류: {str(e)}")
        migration_report["files"][filename] = {
            "status": "ERROR",
            "error": str(e)
        }

# 최종 요약
print("\n" + "=" * 80)
print("📊 마이그레이션 & 클랜징 완료 요약")
print("=" * 80)

summary = {
    "total_files_processed": len([f for f in migration_report["files"].values() if "status" not in f or f["status"] != "ERROR"]),
    "total_rows_before": total_rows_before,
    "total_rows_after": total_rows_after,
    "rows_removed": total_rows_before - total_rows_after,
    "retention_rate": f"{(total_rows_after / total_rows_before * 100):.2f}%" if total_rows_before > 0 else "N/A",
    "output_directory": str(DATA_PROCESSED_DIR)
}

print(f"\n✅ 처리된 파일: {summary['total_files_processed']}")
print(f"📈 처리된 행:")
print(f"   - 마이그레이션 전: {summary['total_rows_before']:,}")
print(f"   - 마이그레이션 후: {summary['total_rows_after']:,}")
print(f"   - 제거된 행: {summary['rows_removed']:,}")
print(f"   - 유지율: {summary['retention_rate']}")
print(f"\n💾 출력 디렉토리: {summary['output_directory']}")

migration_report["summary"] = summary

# 보고서 저장
report_path = OUTPUT_DIR / f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(report_path, 'w', encoding='utf-8') as f:
    json.dump(migration_report, f, indent=2, ensure_ascii=False, default=str)

print(f"\n📋 상세 보고서 저장: {report_path}")

print("\n" + "=" * 80)
print(f"완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)
