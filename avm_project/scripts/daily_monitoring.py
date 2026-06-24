#!/usr/bin/env python3
"""
일일 모니터링 및 로그 수집
2026-06-24
"""

from pathlib import Path
from datetime import datetime
import json

PROJECT_DIR = Path(__file__).parent.parent
EXTERNAL_DRIVE_DIR = Path("/mnt/avm_data")
LOG_DIR = PROJECT_DIR / "logs" / "cron"

print("=" * 100)
print("📊 일일 모니터링 및 로그 수집")
print("=" * 100)
print(f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# 1. 외부 드라이브 상태 확인
total_size = 0
file_count = 0
for root, dirs, files in os.walk(EXTERNAL_DRIVE_DIR):
    for file in files:
        file_path = Path(root) / file
        total_size += file_path.stat().st_size
        file_count += 1

print(f"✓ 외부 드라이브 상태:")
print(f"  - 파일 수: {file_count}개")
print(f"  - 총 크기: {total_size / 1024 / 1024:.2f} MB")

# 2. 최근 로그 확인
log_files = list(LOG_DIR.glob("*.log"))
print(f"✓ 로그 파일: {len(log_files)}개")

print("=" * 100)
