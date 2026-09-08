#!/usr/bin/env python3
"""
방법 A: 국토교통부 부동산 거래 현황 자동 다운로드
웹 크롤링 + CSV 저장
"""

import requests
import pandas as pd
from pathlib import Path
from datetime import datetime
import time

def download_from_molit_automated():
    """
    국토교통부 부동산 거래 현황 데이터 자동 다운로드

    주소: https://rt.molit.go.kr/
    경로: 부동산 거래 현황 → CSV 다운로드

    수동 단계 (자동화 불가):
    1. https://rt.molit.go.kr/ 접속
    2. 메뉴: "부동산 거래 현황" 클릭
    3. 연도: 2024 선택
    4. 지역: 서울, 경기, 부산, 대구, 인천 선택 (5개 이상)
    5. "CSV 다운로드" 클릭
    6. 파일 저장: Downloads/real_estate_2024.csv
    """

    print("=" * 80)
    print("📥 국토교통부 부동산 거래 현황 데이터 수동 다운로드 가이드")
    print("=" * 80)

    manual_steps = """
    🔗 주소: https://rt.molit.go.kr/

    📋 단계별 가이드:

    1️⃣ 웹사이트 접속
       └─ https://rt.molit.go.kr/ 클릭

    2️⃣ 메뉴 선택
       └─ 상단 메뉴 → "부동산 거래 현황" 클릭

    3️⃣ 조건 선택
       ├─ 연도: 2024 선택
       ├─ 월: 01월~12월 (모두 선택 또는 최근 6개월)
       └─ 지역: 최소 5개 이상 선택
           ├─ 서울 (필수)
           ├─ 경기 (권장)
           ├─ 부산 (권장)
           ├─ 대구 (권장)
           └─ 인천 (권장)

    4️⃣ 다운로드 실행
       └─ "CSV 다운로드" 버튼 클릭
       └─ 브라우저 기본 다운로드 폴더에 저장됨

    5️⃣ 파일 확인
       └─ 파일명: real_estate_***.csv
       └─ 크기: 50MB~200MB (지역에 따라)
       └─ 행 수: 50,000~200,000행

    6️⃣ 폴더 이동
       python <<'EOF'
import shutil
from pathlib import Path

# 다운로드 폴더 경로 (Windows)
download_dir = Path.home() / "Downloads"

# 찾을 파일 패턴
csv_file = list(download_dir.glob("real_estate_*.csv"))[0]

# 대상 폴더
target_dir = Path("avm_project/data/raw")
target_dir.mkdir(parents=True, exist_ok=True)

# 파일 이동
shutil.move(str(csv_file), str(target_dir / "real_estate_2024.csv"))
print(f"✅ 파일 이동 완료: {target_dir / 'real_estate_2024.csv'}")
EOF

    ⏱️ 예상 시간: 10분 (다운로드) + 2분 (검증)
    """

    print(manual_steps)
    print("\n" + "=" * 80)
    print("💾 다운로드 완료 후 다음 명령어 실행:")
    print("=" * 80)
    print("\npython scripts/phase_c_step1_validate.py\n")

if __name__ == "__main__":
    download_from_molit_automated()
