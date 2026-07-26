#!/usr/bin/env python3
"""
실거래 데이터 요구사항 상세 분석
현재 신호 데이터 vs 필요한 실거래 데이터
"""

import pandas as pd
import numpy as np
from pathlib import Path

def analyze_current_data():
    """현재 신호 데이터 분석"""

    print("=" * 100)
    print("📊 현재 신호 데이터 상세 분석 (signal_real_estate_202401_202412.csv)")
    print("=" * 100)

    df = pd.read_csv('avm_project/data/raw/signal_real_estate_202401_202412.csv')

    print(f"\n✅ 기본 정보")
    print(f"  행 수: {len(df):,}")
    print(f"  컬럼 수: {len(df.columns)}")
    print(f"  기간: {df['거래일'].min()} ~ {df['거래일'].max()}")

    print(f"\n✅ 컬럼별 상세 정보")
    print("-" * 100)
    print(f"{'컬럼명':<12} | {'타입':<10} | {'결측치':<6} | {'최소':<15} | {'평균':<15} | {'최대':<15}")
    print("-" * 100)

    for col in df.columns:
        dtype = str(df[col].dtype)
        missing = f"{(df[col].isna().sum() / len(df) * 100):.1f}%"

        if df[col].dtype in [np.int64, np.float64]:
            min_val = f"{df[col].min():.2e}" if abs(df[col].min()) > 1e6 else f"{df[col].min()}"
            mean_val = f"{df[col].mean():.2e}" if abs(df[col].mean()) > 1e6 else f"{df[col].mean():.1f}"
            max_val = f"{df[col].max():.2e}" if abs(df[col].max()) > 1e6 else f"{df[col].max()}"
        else:
            min_val = df[col].nunique()
            mean_val = "범주형"
            max_val = "—"

        print(f"{col:<12} | {dtype:<10} | {missing:<6} | {min_val:<15} | {mean_val:<15} | {max_val:<15}")

    print(f"\n✅ 통계 요약")
    print(df.describe().T)

    return df

def get_real_estate_requirements():
    """실거래 데이터 요구사항"""

    print("\n\n" + "=" * 100)
    print("🔍 실거래 데이터 요구사항 (Phase C)")
    print("=" * 100)

    requirements = {
        "기본 요구사항": {
            "행 수": "최소 5,000행 (권장: 10,000+)",
            "기간": "최소 6개월 (권장: 1년 이상)",
            "형식": "CSV 또는 Excel (UTF-8 인코딩)",
            "완성도": "결측치 < 5%",
        },
        "필수 컬럼 (반드시 포함)": {
            "거래금액": "숫자형, 단위: 원, 결측치 없음",
            "거래일": "날짜형 (YYYY-MM-DD), 결측치 없음",
            "면적": "숫자형, 단위: ㎡, 범위: 20~300",
            "지역": "문자형 또는 숫자형, 지역 구분 가능",
        },
        "권장 컬럼 (성능 향상)": {
            "건축년도": "숫자형, 범위: 1960~2024",
            "층수": "숫자형, 범위: 1~50",
            "방_개수": "숫자형, 범위: 1~5",
            "욕실_개수": "숫자형, 범위: 1~3",
            "엘리베이터": "0/1 또는 예/아니오",
            "주차장": "숫자형 또는 0/1",
        },
        "피해야 할 컬럼 (누수 원인)": {
            "감정가": "❌ 이미 예측된 가격",
            "평가가": "❌ 이미 예측된 가격",
            "공시지가": "❌ 과거 거래 기반",
            "추정가": "❌ 이미 예측된 가격",
            "가격지수": "❌ 외부 지표",
        },
    }

    for category, items in requirements.items():
        print(f"\n🔹 {category}")
        for key, value in items.items():
            print(f"   • {key}: {value}")

    return requirements

def detailed_comparison():
    """현재 데이터 vs 필요한 데이터 비교"""

    print("\n\n" + "=" * 100)
    print("📋 상세 비교: 현재 신호 데이터 vs 필요한 실거래 데이터")
    print("=" * 100)

    comparison = pd.DataFrame({
        "항목": [
            "데이터 소스",
            "행 수",
            "기간",
            "형식",
            "거래금액 범위",
            "거래금액 통계",
            "신호 특성",
            "누수 위험",
            "검증 상태",
            "모델 적용",
        ],
        "현재 신호 데이터": [
            "합성 생성 (Python)",
            "5,000행",
            "2024-01-01 ~ 2024-12-30",
            "CSV (완벽한 구조)",
            "1.04억 ~ 19.24억",
            "평균: 8.72억, σ: 3.59억",
            "강한 신호 (의도적 설계)",
            "없음 (제어됨)",
            "✅ Phase A/B 통과",
            "✅ 가능 (R² = 0.9810)",
        ],
        "필요한 실거래 데이터": [
            "Data.go.kr 또는 공개 CSV",
            "최소 5,000행 (권장 10,000+)",
            "최소 6개월 (권장 1년+)",
            "CSV/Excel (표준화 필요)",
            "지역/시기별로 다양",
            "예측 불가능 (현실 데이터)",
            "약~중간 신호 (현실적)",
            "높음 (주의 필요)",
            "🔴 검증 필요 (Phase C)",
            "❓ 신호 수준에 따라 다름",
        ],
    })

    print("\n" + comparison.to_string(index=False))

def data_collection_methods():
    """데이터 수집 방법별 비교"""

    print("\n\n" + "=" * 100)
    print("🔗 데이터 수집 방법별 상세 비교")
    print("=" * 100)

    methods = pd.DataFrame({
        "수집 방법": [
            "1. Data.go.kr API",
            "2. 국토교통부 CSV",
            "3. 한국부동산원",
            "4. 지자체 오픈데이터",
            "5. 부동산 중개소",
            "6. Kaggle/공개자료",
        ],
        "데이터 품질": [
            "⭐⭐⭐⭐⭐ (최고)",
            "⭐⭐⭐⭐ (매우 좋음)",
            "⭐⭐⭐⭐ (좋음)",
            "⭐⭐⭐ (보통)",
            "⭐⭐ (낮음)",
            "⭐⭐⭐ (다양함)",
        ],
        "접근성": [
            "🔴 API 키 필요 (현재 불가)",
            "🟢 CSV 직접 다운로드",
            "🟢 웹사이트 다운로드",
            "🟢 CSV 다운로드",
            "🔴 연락/수집 필요",
            "🟢 온라인 접근",
        ],
        "완성도": [
            "95%+ (완벽)",
            "90%+ (매우 좋음)",
            "85-90% (좋음)",
            "70-80% (보통)",
            "50-70% (낮음)",
            "60-80% (다양함)",
        ],
        "처리 난이도": [
            "낮음 (JSON 파싱)",
            "낮음 (CSV)",
            "중간 (전처리 필요)",
            "중간-높음 (정제 필요)",
            "높음 (수작업)",
            "중간-높음 (검증 필요)",
        ],
        "권장도": [
            "✅ 최우선 (막히면 2번)",
            "✅ 2순위 (추천)",
            "⭐ 3순위",
            "⭐ 4순위",
            "❌ 비추천",
            "❓ 검증 후 사용",
        ],
    })

    print("\n" + methods.to_string(index=False))

def validation_checklist():
    """실거래 데이터 검증 체크리스트"""

    print("\n\n" + "=" * 100)
    print("✅ 실거래 데이터 수집 후 검증 체크리스트")
    print("=" * 100)

    checklist = [
        ("파일 형식", "CSV/Excel 형식인가?", "필수"),
        ("인코딩", "UTF-8 또는 EUC-KR인가?", "필수"),
        ("행 수", "최소 5,000행 이상인가?", "필수"),
        ("기간", "최소 6개월 이상 데이터인가?", "필수"),
        ("거래금액", "숫자형이고 결측치 없는가?", "필수"),
        ("거래일", "날짜형이고 결측치 없는가?", "필수"),
        ("면적", "숫자형이고 20~300 범위인가?", "필수"),
        ("지역", "지역 구분이 명확한가?", "필수"),
        ("결측치율", "전체 결측치 < 5%인가?", "권장"),
        ("이상치", "거래금액이 극단적이지 않은가?", "권장"),
        ("시간순서", "시간이 진행 방향으로 정렬되는가?", "권장"),
        ("중복", "중복 거래 기록이 없는가?", "권장"),
        ("누수 특성", "감정가/평가가 등이 없는가?", "중요"),
        ("신호 강도", "특성과 가격의 상관이 있는가?", "검증"),
    ]

    print(f"\n{'#':<3} | {'검증 항목':<20} | {'확인 사항':<40} | {'우선도':<8}")
    print("-" * 100)
    for idx, (item, check, priority) in enumerate(checklist, 1):
        print(f"{idx:<3} | {item:<20} | {check:<40} | {priority:<8}")

def sample_structure():
    """샘플 데이터 구조"""

    print("\n\n" + "=" * 100)
    print("📝 예상 데이터 구조 (실거래 CSV)")
    print("=" * 100)

    sample = pd.DataFrame({
        '거래일': ['2024-01-15', '2024-01-15', '2024-01-16', '2024-01-16', '2024-01-17'],
        '지역': ['서울', '서울', '경기', '서울', '경기'],
        '면적': [85.5, 102.3, 76.8, 95.2, 68.4],
        '건축년도': [2010, 2015, 2005, 2018, 2000],
        '층수': [12, 8, 15, 25, 3],
        '방_개수': [3, 3, 2, 3, 2],
        '욕실_개수': [2, 2, 1, 2, 1],
        '엘리베이터': [1, 1, 1, 1, 0],
        '주차장': [2, 2, 1, 3, 0],
        '거래금액': [350000000, 420000000, 280000000, 480000000, 200000000],
    })

    print("\n✅ 예상 구조 (CSV 포맷):")
    print(sample.to_string(index=False))
    print(f"\n컬럼 수: {len(sample.columns)}")
    print(f"필수: 4개 (거래일, 지역, 면적, 거래금액)")
    print(f"권장: {len(sample.columns) - 4}개 (추가 특성)")

def main():
    print("\n")
    print("🎯 Phase C 데이터 요구사항 상세 분석")
    print("=" * 100)

    # 1. 현재 데이터 분석
    current_df = analyze_current_data()

    # 2. 요구사항
    get_real_estate_requirements()

    # 3. 상세 비교
    detailed_comparison()

    # 4. 수집 방법 비교
    data_collection_methods()

    # 5. 검증 체크리스트
    validation_checklist()

    # 6. 샘플 구조
    sample_structure()

    # 7. 권장 액션
    print("\n\n" + "=" * 100)
    print("🚀 권장 다음 액션")
    print("=" * 100)
    print("""
1️⃣  국토교통부 CSV 다운로드 (가장 빠른 방법)
    → https://rt.molit.go.kr/ (부동산 거래 현황 > CSV 다운로드)
    → 2024년 데이터 선택
    → 5개 이상 지역/광역시 선택

2️⃣  또는 Data.go.kr 웹사이트에서 직접 CSV 다운로드
    → https://www.data.go.kr/
    → "부동산 실거래 정보" 검색
    → API 대신 데이터셋 직접 다운로드 (CSV)

3️⃣  또는 서울시/경기도 오픈데이터포털
    → https://data.seoul.go.kr/ (서울)
    → https://data.gg.go.kr/ (경기)
    → 2024년 부동산 거래 데이터

4️⃣  다운로드 후 검증
    → avm_project/data/raw/real_estate_2024.csv에 저장
    → python scripts/validate_data.py 실행 (검증 스크립트)

5️⃣  데이터 검증 통과 후
    → python scripts/temporal_split.py --data data/raw/real_estate_2024.csv --target 거래금액 --time-col 거래일
    → python scripts/leakage_audit.py --data data/raw/real_estate_2024.csv --target 거래금액 --time-col 거래일
    → python scripts/build_ensemble.py --data data/raw/real_estate_2024.csv --target 거래금액 --time-col 거래일
    """)

if __name__ == "__main__":
    main()
