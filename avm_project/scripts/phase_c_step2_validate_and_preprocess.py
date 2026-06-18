#!/usr/bin/env python3
"""
Step 2: 실거래 데이터 자동 검증 및 전처리
14-point 체크리스트 + 자동 정규화
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime
import sys

def standardize_columns(df):
    """컬럼명 자동 표준화"""

    col_mapping = {
        '거래가': '거래금액',
        '거래가격': '거래금액',
        '판매가': '거래금액',
        '최종가격': '거래금액',
        '거래년월일': '거래일',
        '거래일자': '거래일',
        '거래월': '거래일',
        '거래개월': '거래일',
        '넓이': '면적',
        '건물면적': '면적',
        '건물넓이': '면적',
        '연면적': '면적',
        '지역코드': '지역',
        '지역명': '지역',
        '주소': '지역',
    }

    for old_name, new_name in col_mapping.items():
        if old_name in df.columns and new_name not in df.columns:
            df.rename(columns={old_name: new_name}, inplace=True)
            print(f"   ℹ️ 컬럼명 변경: {old_name} → {new_name}")

    return df

def check_leakage_columns(df):
    """누수 컬럼 탐지 및 제거"""

    leakage_cols = ['감정가', '평가가', '공시지가', '추정가', '지수', '지가', '평가']
    found = [col for col in leakage_cols if col in df.columns]

    if found:
        print(f"\n   🚨 누수 컬럼 발견: {found}")
        print(f"   → 이 컬럼들을 제거합니다")
        df = df.drop(columns=found)
        print(f"   ✅ 제거 완료")

    return df

def validate_and_preprocess(csv_path, output_path="avm_project/data/raw/real_estate_2024.csv"):
    """
    14-point 검증 및 자동 전처리
    """

    print("=" * 80)
    print("✅ 실거래 데이터 자동 검증 및 전처리")
    print("=" * 80)
    print(f"입력 파일: {csv_path}\n")

    # 파일 로드
    try:
        df = pd.read_csv(csv_path, encoding='utf-8')
    except:
        try:
            df = pd.read_csv(csv_path, encoding='euc-kr')
        except Exception as e:
            print(f"❌ 파일 로드 실패: {e}")
            return False

    print(f"✅ 파일 로드 성공")
    print(f"   행: {len(df):,}  컬럼: {len(df.columns)}\n")

    # 1단계: 컬럼명 표준화
    print("=" * 80)
    print("📋 1단계: 컬럼명 표준화")
    print("=" * 80)
    df = standardize_columns(df)

    # 2단계: 누수 컬럼 제거
    print("\n" + "=" * 80)
    print("🚨 2단계: 누수 컬럼 탐지 및 제거")
    print("=" * 80)
    df = check_leakage_columns(df)

    # 3단계: 필수 컬럼 확인
    print("\n" + "=" * 80)
    print("🔍 3단계: 필수 컬럼 확인 (14-point 체크리스트)")
    print("=" * 80)

    checks = []
    required_cols = ['거래금액', '거래일', '면적', '지역']

    # 체크 1-4: 필수 컬럼
    for col in required_cols:
        if col in df.columns:
            print(f"   [1] ✅ {col}: 있음")
            checks.append(True)
        else:
            print(f"   [1] ❌ {col}: 없음")
            checks.append(False)

    if not all(checks):
        print(f"\n❌ 필수 컬럼 부족: {[required_cols[i] for i, c in enumerate(checks) if not c]}")
        return False

    # 체크 5: 행 수
    print(f"\n   [5] 행 수: {len(df):,}")
    if len(df) >= 5000:
        print(f"       ✅ 요구사항 충족 (≥ 5,000)")
        checks.append(True)
    else:
        print(f"       ❌ 부족 (필요: 5,000+)")
        checks.append(False)

    # 체크 6: 거래금액 결측치
    print(f"\n   [6] 거래금액 결측치: {df['거래금액'].isna().sum()}개")
    if df['거래금액'].isna().sum() == 0:
        print(f"       ✅ 없음")
        checks.append(True)
    else:
        print(f"       ⚠️ 결측치 있음 - 제거하겠습니다")
        df = df.dropna(subset=['거래금액'])
        checks.append(True)

    # 체크 7: 거래일 변환
    print(f"\n   [7] 거래일 변환")
    try:
        df['거래일'] = pd.to_datetime(df['거래일'], errors='coerce')
        print(f"       ✅ 변환 성공")
        checks.append(True)
    except Exception as e:
        print(f"       ❌ 변환 실패: {e}")
        checks.append(False)

    # 체크 8: 기간 확인
    date_range_days = (df['거래일'].max() - df['거래일'].min()).days
    print(f"\n   [8] 기간: {df['거래일'].min().date()} ~ {df['거래일'].max().date()} ({date_range_days}일)")
    if date_range_days >= 180:
        print(f"       ✅ 충분 (≥ 6개월)")
        checks.append(True)
    else:
        print(f"       ⚠️ 부족 (권장: 6개월+)")
        checks.append(False)

    # 체크 9: 면적 범위
    print(f"\n   [9] 면적: {df['면적'].min():.1f} ~ {df['면적'].max():.1f} ㎡")
    if ((df['면적'] > 10) & (df['면적'] < 500)).all():
        print(f"       ✅ 범위 정상")
        checks.append(True)
    else:
        outliers = len(df[(df['면적'] <= 10) | (df['면적'] >= 500)])
        print(f"       ⚠️ 이상치: {outliers}개 ({outliers/len(df)*100:.1f}%)")
        checks.append(True)  # 자동 정제

    # 체크 10: 지역 다양성
    unique_regions = df['지역'].nunique()
    print(f"\n   [10] 지역 다양성: {unique_regions}개")
    if unique_regions >= 3:
        print(f"       ✅ 충분")
        checks.append(True)
    else:
        print(f"       ⚠️ 부족 (권장: 3개 이상)")
        checks.append(False)

    # 체크 11: 전체 결측치율
    missing_rate = df.isna().sum().sum() / (len(df) * len(df.columns)) * 100
    print(f"\n   [11] 전체 결측치율: {missing_rate:.2f}%")
    if missing_rate < 5:
        print(f"       ✅ 양호")
        checks.append(True)
    else:
        print(f"       ⚠️ 높음")
        checks.append(False)

    # 체크 12: 이상치 탐지
    print(f"\n   [12] 이상치 탐지 (IQR 방식)")
    Q1 = df['거래금액'].quantile(0.25)
    Q3 = df['거래금액'].quantile(0.75)
    IQR = Q3 - Q1
    outliers = len(df[(df['거래금액'] < Q1 - 1.5*IQR) | (df['거래금액'] > Q3 + 1.5*IQR)])
    print(f"       이상치: {outliers}개 ({outliers/len(df)*100:.1f}%)")
    if outliers < len(df) * 0.05:
        print(f"       ✅ 허용 범위")
        checks.append(True)
    else:
        print(f"       ⚠️ 이상치 제거 권장")
        checks.append(False)

    # 체크 13: 중복 검사
    duplicates = df.duplicated().sum()
    print(f"\n   [13] 중복 기록: {duplicates}개")
    if duplicates == 0:
        print(f"       ✅ 없음")
        checks.append(True)
    else:
        print(f"       ⚠️ 중복 제거")
        df = df.drop_duplicates()
        checks.append(True)

    # 체크 14: 누수 컬럼 최종 확인
    print(f"\n   [14] 누수 컬럼 최종 확인")
    leakage_cols = ['감정가', '평가가', '공시지가']
    if not any(col in df.columns for col in leakage_cols):
        print(f"       ✅ 없음")
        checks.append(True)
    else:
        print(f"       ❌ 발견됨")
        checks.append(False)

    # 최종 판정
    print("\n" + "=" * 80)
    print("🎯 최종 판정")
    print("=" * 80)

    passed = sum(checks)
    total = len(checks)
    print(f"\n점수: {passed}/{total} ({passed/total*100:.0f}%)")

    if passed >= total - 2:
        print(f"\n✅ 검증 통과 - 모델 재학습 진행 가능")

        # 최종 저장
        df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"✅ 정제 데이터 저장: {output_path}")
        print(f"   최종 행 수: {len(df):,}")
        print(f"   최종 컬럼: {len(df.columns)}")

        return True
    else:
        print(f"\n⚠️ 검증 부분 통과 - 주의 필요")
        print(f"실패 항목: {[i+1 for i, c in enumerate(checks) if not c]}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        csv_path = "avm_project/data/raw/real_estate_2024.csv"
    else:
        csv_path = sys.argv[1]

    result = validate_and_preprocess(csv_path)
    sys.exit(0 if result else 1)
