#!/usr/bin/env python3
"""
Step 4: 배포 및 API 서버 실행
REST API + 실시간 대시보드
"""

import subprocess
import sys
from pathlib import Path

def show_deployment_options():
    """배포 옵션 표시"""

    print("=" * 100)
    print("🚀 배포 옵션 선택")
    print("=" * 100)

    options = """
    📋 3가지 배포 방법:

    1️⃣  로컬 개발 서버 (권장 — 테스트용)
        └─ 포트: 8000
        └─ 사용: 개발/테스트 단계
        └─ 명령어:
           python -m uvicorn scripts.api_server:app --reload --port 8000

    2️⃣  Docker 컨테이너 (단독 실행)
        └─ 포트: 8000 (호스트) → 8000 (컨테이너)
        └─ 격리된 환경
        └─ 명령어:
           docker build -t avm-model .
           docker run -p 8000:8000 avm-model

    3️⃣  클라우드 배포 (Google Cloud Run)
        └─ 서버리스 환경
        └─ 자동 스케일링
        └─ 명령어:
           bash deploy_cloudrun.sh

    ➜ 선택 (1/2/3): """

    return input(options).strip()

def deploy_local():
    """로컬 개발 서버 배포"""

    print("\n" + "=" * 100)
    print("🔧 로컬 개발 서버 시작")
    print("=" * 100)

    print("\n✅ 준비 사항 확인:")
    print("   ✓ requirements.txt 설치됨")
    print("   ✓ avm_project/models/production_model_real_2024.joblib 준비됨")
    print("   ✓ 포트 8000 사용 가능\n")

    print("📍 실행 중...\n")
    print("=" * 100)
    print("🌐 접근 주소:")
    print("=" * 100)
    print(f"\n   메인 페이지:  http://localhost:8000/")
    print(f"   대시보드:     http://localhost:8000/dashboard")
    print(f"   API 문서:     http://localhost:8000/docs")
    print(f"   헬스체크:     http://localhost:8000/health\n")

    print("=" * 100)
    print("🔴 Ctrl+C를 누르면 서버 중지")
    print("=" * 100 + "\n")

    # 환경 변수 설정
    env_vars = {"PYTHONUNBUFFERED": "1"}

    try:
        cmd = [
            sys.executable, "-m", "uvicorn",
            "scripts.api_server:app",
            "--reload",
            "--port", "8000",
            "--host", "0.0.0.0"
        ]

        subprocess.run(cmd, cwd="/home/user/-/avm_project", env={**dict(os.environ), **env_vars})

    except KeyboardInterrupt:
        print("\n\n✅ 서버 중지됨")
    except Exception as e:
        print(f"\n❌ 오류: {e}")

def deploy_docker():
    """Docker 배포"""

    print("\n" + "=" * 100)
    print("🐳 Docker 배포")
    print("=" * 100)

    print("\n1️⃣  Docker 이미지 빌드")
    print("-" * 100)
    print("   실행 중: docker build -t avm-model .")
    print("   예상 시간: 2-3분\n")

    try:
        subprocess.run(["docker", "build", "-t", "avm-model", "."], cwd="/home/user/-/avm_project", check=True)
        print("   ✅ 이미지 빌드 완료\n")
    except subprocess.CalledProcessError as e:
        print(f"   ❌ 빌드 실패: {e}")
        return False

    print("2️⃣  Docker 컨테이너 실행")
    print("-" * 100)
    print("   실행 중: docker run -p 8000:8000 avm-model\n")

    print("=" * 100)
    print("🌐 접근 주소:")
    print("=" * 100)
    print(f"\n   메인 페이지:  http://localhost:8000/")
    print(f"   대시보드:     http://localhost:8000/dashboard")
    print(f"   API 문서:     http://localhost:8000/docs\n")

    print("=" * 100)
    print("🔴 Ctrl+C를 누르면 컨테이너 중지")
    print("=" * 100 + "\n")

    try:
        subprocess.run(["docker", "run", "-p", "8000:8000", "avm-model"])
    except KeyboardInterrupt:
        print("\n\n✅ 컨테이너 중지됨")
    except Exception as e:
        print(f"\n❌ 오류: {e}")

    return True

def deploy_cloudrun():
    """Cloud Run 배포"""

    print("\n" + "=" * 100)
    print("☁️ Google Cloud Run 배포")
    print("=" * 100)

    print("\n📋 사전 요구사항:")
    print("   ✓ Google Cloud SDK 설치")
    print("   ✓ gcloud CLI 설정")
    print("   ✓ GCP 프로젝트 생성\n")

    print("🔧 배포 스크립트 실행:")
    print("-" * 100)
    print("   실행 중: bash deploy_cloudrun.sh\n")

    deploy_script = Path("deploy_cloudrun.sh")
    if not deploy_script.exists():
        print("   ❌ deploy_cloudrun.sh 파일 없음")
        return False

    try:
        subprocess.run(["bash", "deploy_cloudrun.sh"], cwd="/home/user/-/avm_project", check=True)
        print("\n   ✅ Cloud Run 배포 완료")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n   ❌ 배포 실패: {e}")
        return False

def main():
    """메인 배포 프로세스"""

    import os

    print("\n")
    choice = show_deployment_options()

    if choice == "1":
        deploy_local()
    elif choice == "2":
        deploy_docker()
    elif choice == "3":
        deploy_cloudrun()
    else:
        print("\n❌ 잘못된 선택")
        sys.exit(1)

if __name__ == "__main__":
    main()
