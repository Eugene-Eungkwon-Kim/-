#!/usr/bin/env python3
"""
실거래 데이터 검증 스크립트
CSV 다운로드 후 실행하여 데이터 품질 확인
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path

def validate_real_estate_data(csv_path, verbose=True):
    """실거래 데이터 검증"""

    print("=" * 80)
    print("✅ 실거래 데이터 검증 시작")
    print("=" * 80)
    print(f"파일: {csv_path}\n")

    # 파일 존재 확인
    if not Path(csv_path).exists():
        print(f"❌ 파일 없음: {csv_path}")
        return False

    # 파일 로드
    try:
        df = pd.read_csv(csv_path)
        print(f"✅ 파일 로드 성공")
        print(f"   행 수: {len(df):,}")
        print(f"   컬럼 수: {len(df.columns)}\n")
    except Exception as e:
        print(f"❌ 파일 로드 실패: {e}")
        return False

    # 컬럼 확인
    print("=" * 80)
    print("🔍 컬럼 검증")
    print("=" * 80)

    required_cols = ['거래금액', '거래일', '면적']
    optional_cols = ['건축년도', '층수', '지역', '방_개수', '욕실_개수', '엘리베이터', '주차장']

    # 컬럼명 표준화 시도
    col_mapping = {
        '거래가격': '거래금액',
        '가격': '거래금액',
        '판매가': '거래금액',
        '거래개월': '거래일',
        '거래월': '거래일',
        '거래년월': '거래일',
        '넓이': '면적',
        '건물면적': '면적',
        '지역코드': '지역',
    }

    for old, new in col_mapping.items():
        if old in df.columns and new not in df.columns:
            df.rename(columns={old: new}, inplace=True)
            print(f"   ℹ️ 컬럼명 변경: {old} → {new}")

    # 필수 컬럼 확인
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"\n❌ 필수 컬럼 부족: {missing_cols}")
        print(f"   현재 컬럼: {list(df.columns)}")
        return False
    else:
        print(f"✅ 필수 컬럼 완비: {required_cols}")

    # 선택 컬럼 확인
    available_cols = [col for col in optional_cols if col in df.columns]
    print(f"✅ 선택 컬럼: {available_cols} ({len(available_cols)}/{len(optional_cols)})")

    # 데이터 품질 검증
    print("\n" + "=" * 80)
    print("📊 데이터 품질 검증")
    print("=" * 80)

    checks = []

    # 1. 행 수
    print(f"\n1️⃣ 행 수: {len(df):,}행")
    if len(df) >= 5000:
        print(f"   ✅ 요구사항 충족 (최소 5,000행)")
        checks.append(True)
    else:
        print(f"   ⚠️ 부족 (권장: 10,000행+)")
        checks.append(False)

    # 2. 거래금액
    print(f"\n2️⃣ 거래금액")
    print(f"   결측치: {df['거래금액'].isna().sum()}개 ({df['거래금액'].isna().sum()/len(df)*100:.2f}%)")
    if df['거래금액'].isna().sum() == 0:
        print(f"   ✅ 결측치 없음")
        checks.append(True)
    else:
        print(f"   ❌ 결측치 있음")
        checks.append(False)

    print(f"   범위: {df['거래금액'].min():,.0f} ~ {df['거래금액'].max():,.0f}")
    print(f"   평균: {df['거래금액'].mean():,.0f}")
    print(f"   표준편차: {df['거래금액'].std():,.0f}")

    # 3. 거래일
    print(f"\n3️⃣ 거래일")
    print(f"   결측치: {df['거래일'].isna().sum()}개")
    try:
        df['거래일'] = pd.to_datetime(df['거래일'], errors='coerce')
        print(f"   범위: {df['거래일'].min()} ~ {df['거래일'].max()}")
        date_range_days = (df['거래일'].max() - df['거래일'].min()).days
        print(f"   기간: {date_range_days}일 ({date_range_days/365:.1f}년)")
        if date_range_days >= 180:
            print(f"   ✅ 요구사항 충족 (최소 6개월)")
            checks.append(True)
        else:
            print(f"   ⚠️ 기간 부족 (최소 6개월 필요)")
            checks.append(False)
    except Exception as e:
        print(f"   ❌ 날짜 파싱 실패: {e}")
        checks.append(False)

    # 4. 면적
    print(f"\n4️⃣ 면적")
    print(f"   결측치: {df['면적'].isna().sum()}개")
    print(f"   범위: {df['면적'].min():.1f} ~ {df['면적'].max():.1f}")
    if (df['면적'] > 20) & (df['면적'] < 300):
        print(f"   ✅ 범위 정상 (20~300 ㎡)")
        checks.append(True)
    else:
        outliers = len(df[(df['면적'] <= 20) | (df['면적'] >= 300)])
        print(f"   ⚠️ 범위 밖 {outliers}개 ({outliers/len(df)*100:.1f}%)")

    # 5. 결측치율
    print(f"\n5️⃣ 전체 결측치율")
    missing_rate = df.isna().sum().sum() / (len(df) * len(df.columns)) * 100
    print(f"   결측치: {missing_rate:.2f}%")
    if missing_rate < 5:
        print(f"   ✅ 양호 (< 5%)")
        checks.append(True)
    else:
        print(f"   ⚠️ 높음 (> 5%)")
        checks.append(False)

    # 6. 누수 검사
    print(f"\n6️⃣ 누수 특성 검사")
    leakage_cols = ['감정가', '평가가', '공시지가', '추정가', '가격지수', '지수']
    found_leakage = [col for col in leakage_cols if col in df.columns]
    if found_leakage:
        print(f"   ❌ 누수 특성 발견: {found_leakage}")
        print(f"   → 이 컬럼들을 제거하고 다시 실행하세요")
        checks.append(False)
    else:
        print(f"   ✅ 누수 특성 없음")
        checks.append(True)

    # 7. 지역 다양성
    if '지역' in df.columns:
        print(f"\n7️⃣ 지역 다양성")
        unique_regions = df['지역'].nunique()
        print(f"   고유 지역: {unique_regions}개")
        if unique_regions >= 3:
            print(f"   ✅ 충분 (3개 이상)")
            checks.append(True)
        else:
            print(f"   ⚠️ 부족 (3개 이상 권장)")
            checks.append(False)

    # 최종 판정
    print("\n" + "=" * 80)
    print("🎯 최종 판정")
    print("=" * 80)

    passed_checks = sum(checks)
    total_checks = len(checks)

    print(f"\n점수: {passed_checks}/{total_checks} ({passed_checks/total_checks*100:.0f}%)")

    if passed_checks >= total_checks - 1:
        print(f"\n✅ 데이터 검증 통과 - Phase C 진행 가능")
        print(f"\n다음 명령어 실행:")
        print(f"  python scripts/temporal_split.py \\")
        print(f"    --data {csv_path} \\")
        print(f"    --target 거래금액 \\")
        print(f"    --time-col 거래일")
        return True
    else:
        print(f"\n⚠️ 데이터 전처리 필요")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python validate_real_estate_data.py <csv_파일_경로>")
        print("\n예시:")
        print("  python validate_real_estate_data.py data/raw/real_estate_2024.csv")
        sys.exit(1)

    csv_path = sys.argv[1]
    result = validate_real_estate_data(csv_path)
    sys.exit(0 if result else 1)
