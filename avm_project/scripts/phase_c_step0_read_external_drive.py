#!/usr/bin/env python3
"""
Step 0: 외장하드에서 데이터 읽기 (필수 단계)
- 외장하드 마운트/감지
- CSV 파일 자동 찾기
- 프로젝트 폴더로 복사
"""

import shutil
from pathlib import Path
import sys

try:
    from .data_locator import resolve_data_root
except ImportError:
    from data_locator import resolve_data_root

def detect_external_drives() -> list[dict[str, str]]:
    root = resolve_data_root().root
    return [{"path": str(root)}]



def search_csv_files(search_path):
    """CSV 파일 재귀 검색"""

    print("\n" + "=" * 100)
    print(f"🔎 CSV 파일 검색: {search_path}")
    print("=" * 100)

    if not Path(search_path).exists():
        print(f"❌ 경로 없음: {search_path}")
        return []

    csv_files = list(Path(search_path).rglob("*.csv"))

    if csv_files:
        print(f"\n✅ 발견된 CSV 파일 ({len(csv_files)}개):\n")
        for i, csv_file in enumerate(csv_files[:20], 1):  # 처음 20개만 표시
            size_mb = csv_file.stat().st_size / (1024**2)
            print(f"  {i}. {csv_file.name}")
            print(f"     경로: {csv_file}")
            print(f"     크기: {size_mb:.1f}MB\n")

        if len(csv_files) > 20:
            print(f"  ... 외 {len(csv_files) - 20}개 파일")
    else:
        print(f"\n❌ CSV 파일 없음")
        print(f"   경로: {search_path}")
        print(f"   → 부동산 거래 데이터(*.csv)를 확인해주세요")

    return csv_files

def select_and_copy_file(csv_files):
    """파일 선택 및 복사"""

    if not csv_files:
        return False

    print("\n" + "=" * 100)
    print("📋 파일 선택")
    print("=" * 100)

    # 크기 순 정렬 (큰 파일 = 데이터 많음)
    csv_files = sorted(csv_files, key=lambda x: x.stat().st_size, reverse=True)

    for i, csv_file in enumerate(csv_files[:10], 1):
        size_mb = csv_file.stat().st_size / (1024**2)
        print(f"\n  {i}. {csv_file.name} ({size_mb:.1f}MB)")

    try:
        choice = input("\n선택 (번호 입력, 예: 1): ").strip()
        idx = int(choice) - 1

        if 0 <= idx < len(csv_files):
            selected_file = csv_files[idx]
            print(f"\n✅ 선택: {selected_file.name}")

            # 목표 경로
            target_dir = Path("avm_project/data/raw")
            target_dir.mkdir(parents=True, exist_ok=True)
            target_file = target_dir / "real_estate_2024.csv"

            print(f"\n📂 파일 복사 중...")
            print(f"   원본: {selected_file}")
            print(f"   대상: {target_file}")

            # 복사 (진행 표시)
            size_bytes = selected_file.stat().st_size
            size_mb = size_bytes / (1024**2)

            if size_mb > 100:
                print(f"   크기: {size_mb:.1f}MB")
                print(f"   예상 시간: 1-3분\n")

            shutil.copy2(selected_file, target_file)

            print(f"✅ 복사 완료!")
            print(f"   저장: {target_file}")
            print(f"   크기: {target_file.stat().st_size / (1024**2):.1f}MB")

            return True
        else:
            print("\n❌ 잘못된 선택")
            return False

    except Exception as e:
        print(f"\n❌ 오류: {e}")
        return False

def main():
    """메인 프로세스"""

    if sys.platform == "win32":
        print("BLOCKED_OPERATIONAL_ADMISSION_REQUIRED: use the approved E: ingestion runner")
        return False

    print("\n")
    print("=" * 100)
    print("🚀 Step 0: 외장하드에서 데이터 읽기")
    print("=" * 100)

    # Step 1: 드라이브 감지
    drives = detect_external_drives()

    # Step 2: 경로 입력
    print("\n" + "=" * 100)
    print("📝 외장하드 경로 입력")
    print("=" * 100)

    print("\n💡 경로 예시:")
    if sys.platform == "win32":
        print("   D:\\")
        print("   E:\\부동산데이터\\")
        print("   F:\\avm_data\\")
    else:
        print("   /Volumes/외장하드")
        print("   /mnt/drive1")
        print("   /media/user/backup")

    drive_path = input("\n외장하드 경로를 입력하세요: ").strip()

    if not drive_path:
        print("\n❌ 경로 입력 필요")
        return False

    # 인용부호 제거
    drive_path = drive_path.strip('"').strip("'")

    # Step 3: CSV 파일 검색
    csv_files = search_csv_files(drive_path)

    if not csv_files:
        print("\n❌ 데이터를 찾을 수 없습니다")
        print("\n💡 다음을 확인하세요:")
        print("   1. 외장하드가 연결되었는가?")
        print("   2. 경로가 올바른가?")
        print("   3. CSV 파일이 존재하는가?")
        return False

    # Step 4: 파일 선택 및 복사
    if select_and_copy_file(csv_files):
        print("\n" + "=" * 100)
        print("✅ Step 0 완료!")
        print("=" * 100)
        print("\n다음 단계:")
        print("  python avm_project/scripts/phase_c_step2_validate_and_preprocess.py")
        return True
    else:
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
