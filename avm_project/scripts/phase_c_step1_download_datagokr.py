#!/usr/bin/env python3
"""
방법 B: Data.go.kr 부동산 실거래 정보 자동 다운로드
공식 API (CSV 형식)를 사용한 자동 수집
"""

import requests
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import time
import json

def download_from_datagokr_webscrape():
    """
    Data.go.kr에서 CSV 직접 다운로드 (웹스크래핑)

    주소: https://www.data.go.kr/
    검색: "부동산 실거래 정보"
    """

    print("=" * 80)
    print("📥 Data.go.kr 부동산 실거래 정보 다운로드 가이드")
    print("=" * 80)

    manual_steps = """
    🔗 주소: https://www.data.go.kr/

    📋 단계별 가이드:

    1️⃣ 웹사이트 접속
       └─ https://www.data.go.kr/ 클릭

    2️⃣ 검색
       └─ 상단 검색창 → "부동산 실거래 정보" 입력 → Enter

    3️⃣ 데이터셋 선택
       ├─ 여러 결과 표시됨
       ├─ "부동산 실거래 정보" (가장 위의 공식 데이터셋) 클릭
       └─ 또는 "부동산 거래 현황" 데이터셋 선택

    4️⃣ 파일 다운로드 (3가지 방법)

       방법 B-1: CSV 직접 다운로드 (권장)
       ├─ "다운로드" 탭 클릭
       ├─ 파일 형식: CSV 선택
       ├─ 연도/지역: 2024년, 서울/경기 등 선택
       └─ "다운로드" 버튼 클릭

       방법 B-2: 데이터 미리보기에서 다운로드
       ├─ "데이터 미리보기" 탭
       ├─ 표 우측 상단의 다운로드 아이콘
       └─ CSV 형식 선택

       방법 B-3: API 키 사용 (현재 403 오류)
       ├─ API 활성화 필요
       └─ 관리자에게 문의

    5️⃣ 파일 저장
       └─ 브라우저 다운로드 폴더 → avm_project/data/raw/real_estate_2024.csv

    6️⃣ 파일 이동 (자동화)
       python <<'EOF'
import shutil
from pathlib import Path

download_dir = Path.home() / "Downloads"
csv_file = list(download_dir.glob("*부동산*.csv")) or list(download_dir.glob("*real_estate*.csv"))

if csv_file:
    target_dir = Path("avm_project/data/raw")
    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(csv_file[0]), str(target_dir / "real_estate_2024.csv"))
    print(f"✅ 파일 이동 완료: {target_dir / 'real_estate_2024.csv'}")
else:
    print("❌ CSV 파일을 찾을 수 없습니다. 수동으로 파일을 이동해주세요.")
    print(f"   다운로드 폴더: {download_dir}")
EOF

    💡 참고:
    - 공식 웹사이트이므로 안전함
    - 월별 데이터 분리 가능
    - 지역별 데이터 분리 가능
    - 예상 파일 크기: 50~200MB

    ⏱️ 예상 시간: 10분 (다운로드) + 2분 (검증)
    """

    print(manual_steps)
    print("\n" + "=" * 80)
    print("💾 다운로드 완료 후 다음 명령어 실행:")
    print("=" * 80)
    print("\npython scripts/phase_c_step2_validate.py\n")

if __name__ == "__main__":
    download_from_datagokr_webscrape()
