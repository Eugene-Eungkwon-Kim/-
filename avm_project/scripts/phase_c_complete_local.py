#!/usr/bin/env python3
"""
Phase C 완전 자동화 (로컬 머신용)
외장하드 → 검증 → 재학습 → 배포까지 자동 진행
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description):
    """명령어 실행 (진행 상황 표시)"""
    print("\n" + "=" * 100)
    print(f"🚀 {description}")
    print("=" * 100 + "\n")

    try:
        result = subprocess.run(cmd, shell=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 오류 발생: {e}")
        return False

def main():
    """Phase C 완전 자동화"""

    print("\n")
    print("=" * 100)
    print("🎯 Phase C 완전 자동화 (로컬 머신용)")
    print("=" * 100)
    print("\n📋 실행 순서:")
    print("   Step 0: 외장하드에서 데이터 읽기 (5분)")
    print("   Step 2: 데이터 검증 및 전처리 (5분)")
    print("   Step 3: 6-모델 앙상블 재학습 (2-4시간)")
    print("   Step 4: API 배포 선택 (10분)")
    print("\n⏱️ 예상 총 시간: 2시간 20분 ~ 4시간 20분\n")

    # Step 0: 외장하드 읽기
    if not run_command(
        f"{sys.executable} scripts/phase_c_step0_read_external_drive.py",
        "Step 0: 외장하드에서 데이터 읽기"
    ):
        print("\n❌ Step 0 실패: 외장하드에서 파일을 읽을 수 없습니다")
        return False

    # Step 2: 데이터 검증
    if not run_command(
        f"{sys.executable} scripts/phase_c_step2_validate_and_preprocess.py",
        "Step 2: 데이터 검증 및 전처리"
    ):
        print("\n❌ Step 2 실패: 데이터 검증에 실패했습니다")
        return False

    # Step 3: 모델 재학습
    print("\n" + "=" * 100)
    print("⚠️ Step 3: 모델 재학습 (2-4시간 소요)")
    print("=" * 100)
    print("\n💡 Tips:")
    print("   • 이 단계는 시간이 오래 걸립니다")
    print("   • 실시간 모니터링: output/retrain_results_*.json")
    print("   • Ctrl+C로 중단 가능하지만, 진행 상황이 손실됩니다")
    print("   • 백그라운드 실행 권장\n")

    response = input("계속 진행하시겠습니까? (y/n): ").strip().lower()
    if response != 'y':
        print("Step 3 건너뜀")
        print("\n다음 수동 실행:")
        print("   python scripts/phase_c_step3_retrain_models.py")
        return True

    if not run_command(
        f"{sys.executable} scripts/phase_c_step3_retrain_models.py",
        "Step 3: 6-모델 앙상블 재학습"
    ):
        print("\n❌ Step 3 실패: 모델 재학습에 실패했습니다")
        print("\n다시 시도: python scripts/phase_c_step3_retrain_models.py")
        return False

    # Step 4: 배포
    print("\n" + "=" * 100)
    print("✅ Step 4: API 배포")
    print("=" * 100)
    print("\n📋 배포 옵션:")
    print("   1. 로컬 개발 서버 (권장)")
    print("      python -m uvicorn scripts.api_server:app --reload --port 8000")
    print("")
    print("   2. Docker 배포")
    print("      docker build -t avm-model .")
    print("      docker run -p 8000:8000 avm-model")
    print("")
    print("   3. Cloud Run 배포")
    print("      bash deploy_cloudrun.sh\n")

    choice = input("배포 방법 선택 (1/2/3, 또는 Enter로 건너뛰기): ").strip()

    if choice == "1":
        run_command(
            f"{sys.executable} -m uvicorn scripts.api_server:app --reload --port 8000",
            "로컬 개발 서버 시작"
        )
    elif choice == "2":
        run_command("docker build -t avm-model .", "Docker 이미지 빌드")
        run_command("docker run -p 8000:8000 avm-model", "Docker 컨테이너 실행")
    elif choice == "3":
        run_command("bash deploy_cloudrun.sh", "Cloud Run 배포")
    else:
        print("\n배포 건너뜀")
        print("다음 수동 실행:")
        print("   python -m uvicorn scripts.api_server:app --port 8000")

    return True

if __name__ == "__main__":
    success = main()

    if success:
        print("\n" + "=" * 100)
        print("✅ Phase C 완료!")
        print("=" * 100)
        print("\n🌐 API 접속:")
        print("   메인 페이지: http://localhost:8000/")
        print("   대시보드: http://localhost:8000/dashboard")
        print("   API 문서: http://localhost:8000/docs\n")
    else:
        print("\n" + "=" * 100)
        print("⚠️ Phase C 실패")
        print("=" * 100)
        print("\n다시 시도:")
        print("   python scripts/phase_c_complete_local.py\n")

    sys.exit(0 if success else 1)
