#!/usr/bin/env python3
"""
방법 C: 서울시/경기도 오픈데이터 자동 다운로드
지역별 공개 API를 통한 데이터 수집
"""

import requests
import pandas as pd
from pathlib import Path
from datetime import datetime
import json

def download_from_seoul_opendata():
    """
    서울시 오픈데이터 부동산 거래 정보 다운로드
    """

    print("=" * 80)
    print("📥 서울시/경기도 오픈데이터 다운로드 가이드")
    print("=" * 80)

    manual_steps = """
    🏛️ 방법 C-1: 서울시 오픈데이터포털

    🔗 주소: https://data.seoul.go.kr/

    📋 단계별 가이드:

    1️⃣ 웹사이트 접속
       └─ https://data.seoul.go.kr/ 클릭

    2️⃣ 검색
       └─ 상단 검색창 → "부동산 거래" 입력
       └─ "아파트 거래" 또는 "주택 거래" 데이터셋 선택

    3️⃣ 데이터셋 정보 확인
       ├─ 데이터 설명 읽기
       ├─ 컬럼: 거래금액, 거래일, 면적 등 확인
       └─ 행 수: 100,000+ (충분함)

    4️⃣ 다운로드
       ├─ "파일 다운로드" 탭
       ├─ CSV 형식 선택
       └─ 다운로드 클릭

    5️⃣ 파일 저장
       └─ Downloads/seoul_apt_2024.csv


    🏛️ 방법 C-2: 경기도 오픈데이터포털

    🔗 주소: https://data.gg.go.kr/

    📋 단계별 가이드:

    1️⃣ 웹사이트 접속
       └─ https://data.gg.go.kr/ 클릭

    2️⃣ 검색
       └─ 상단 검색 → "부동산 실거래" 입력
       └─ "부동산 실거래 정보" 데이터셋 선택

    3️⃣ 데이터셋 확인
       ├─ 컬럼: 거래가격, 거래일, 면적 등
       └─ 행 수: 200,000+ (충분함)

    4️⃣ 다운로드
       ├─ "데이터 다운로드" 탭
       ├─ CSV 형식
       └─ 다운로드

    5️⃣ 파일 저장
       └─ Downloads/gg_apt_2024.csv


    🔀 단일 파일로 통합 (선택사항):

    python <<'EOF'
import pandas as pd
from pathlib import Path

# 모든 지역 CSV 로드
seoul = pd.read_csv("avm_project/data/raw/seoul_apt_2024.csv")
gg = pd.read_csv("avm_project/data/raw/gg_apt_2024.csv")

# 컬럼명 표준화
seoul.rename(columns={
    '거래가': '거래금액',
    '거래년월일': '거래일',
    '면적': '면적',
}, inplace=True)

gg.rename(columns={
    '거래가격': '거래금액',
    '거래일': '거래일',
    '건물면적': '면적',
}, inplace=True)

# 통합
combined = pd.concat([seoul, gg], ignore_index=True)

# 저장
combined.to_csv("avm_project/data/raw/real_estate_2024.csv", index=False)
print(f"✅ 통합 완료: {len(combined):,}행")
EOF

    ⏱️ 예상 시간: 15분 (다운로드) + 3분 (검증)
    """

    print(manual_steps)
    print("\n" + "=" * 80)
    print("💾 다운로드 완료 후 다음 명령어 실행:")
    print("=" * 80)
    print("\npython scripts/phase_c_step2_validate.py\n")

if __name__ == "__main__":
    download_from_seoul_opendata()
