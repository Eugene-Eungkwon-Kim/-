#!/usr/bin/env python3
"""모바일 파일 정리 및 데이터 수집 통합 실행 스크립트"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_organize(args):
    """organize.py 실행"""
    cmd = ["python", "organize.py", args.source, args.dest]
    if args.dry_run:
        cmd.append("--dry-run")
    subprocess.run(cmd)


def run_migrate(args):
    """migrate.py 실행"""
    cmd = ["python", "migrate.py", args.dest]
    if args.source:
        cmd.extend(["--source", args.source])
    if args.android:
        cmd.append("--android")
    if args.dry_run:
        cmd.append("--dry-run")
    subprocess.run(cmd)


def run_iphone(args):
    """iphone_migrate.py 실행"""
    cmd = ["python", "iphone_migrate.py", args.source, args.dest]
    if args.dry_run:
        cmd.append("--dry-run")
    subprocess.run(cmd)


def run_realestate(args):
    """fetch_realestate.py 실행"""
    cmd = ["python", "fetch_realestate.py"]
    cmd.extend(["--lawd", args.lawd, "--start", args.start, "--end", args.end])
    if args.key:
        cmd.extend(["--key", args.key])
    if args.out:
        cmd.extend(["--out", args.out])
    if args.delay:
        cmd.extend(["--delay", str(args.delay)])
    subprocess.run(cmd)


def run_cleanup(args):
    """cleanup.py 실행"""
    cmd = ["python", "cleanup.py"]
    if args.path:
        cmd.append(args.path)
    if args.android:
        cmd.append("--android")
    if args.apply:
        cmd.append("--apply")
    if args.top:
        cmd.extend(["--top", str(args.top)])
    if args.min_size:
        cmd.extend(["--min-size", args.min_size])
    if args.report:
        cmd.extend(["--report", args.report])
    subprocess.run(cmd)


def run_battery(args):
    """battery.py 실행"""
    cmd = ["python", "battery.py"]
    if args.android:
        cmd.append("--android")
    elif args.iphone:
        cmd.append("--iphone")
    else:
        cmd.append("--advice")
    if args.report:
        cmd.extend(["--report", args.report])
    if args.no_checklist:
        cmd.append("--no-checklist")
    subprocess.run(cmd)


def main():
    parser = argparse.ArgumentParser(
        description="모바일 파일 정리 & 데이터 수집 통합 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:

1. iPhone 파일 정리:
   python run.py iphone ~/Desktop/iPhone_내보내기 ~/Desktop/정리결과

2. Android 파일 정리:
   python run.py migrate --android ./정리결과

3. 로컬 폴더 정리:
   python run.py organize ~/Downloads/phone_files ./정리결과

4. 저장공간 정리:
   python run.py cleanup ~/Desktop/정리결과                 # 분석만
   python run.py cleanup ~/Desktop/정리결과 --apply         # 중복·캐시 삭제
   python run.py cleanup --android                          # 기기 용량 리포트

5. 배터리 효율 진단:
   python run.py battery --iphone                           # iPhone 배터리 상태
   python run.py battery --android                          # Android 소모 진단
   python run.py battery                                    # 체크리스트만

6. 부동산 데이터 수집:
   python run.py realestate --lawd 11680 --start 202401 --end 202406
   또는 환경변수 사용:
   export DATA_GO_KR_KEY=발급키
   python run.py realestate --lawd 11680 --start 202401 --end 202406
""",
    )

    subparsers = parser.add_subparsers(dest="command", help="실행할 작업")

    # organize 서브명령
    organize_parser = subparsers.add_parser("organize", help="로컬 폴더 파일 정리")
    organize_parser.add_argument("source", help="정리할 원본 폴더 경로")
    organize_parser.add_argument("dest", help="정리된 파일을 저장할 폴더 경로")
    organize_parser.add_argument("--dry-run", action="store_true", help="미리보기 모드")
    organize_parser.set_defaults(func=run_organize)

    # migrate 서브명령
    migrate_parser = subparsers.add_parser("migrate", help="Android 마이그레이션 또는 로컬 폴더 정리")
    migrate_parser.add_argument("dest", help="정리된 파일을 저장할 폴더 경로")
    migrate_parser.add_argument("--source", help="로컬 폴더 경로 (지정 시 ADB 대신 로컬 폴더 사용)")
    migrate_parser.add_argument("--android", action="store_true", help="ADB로 Android 기기에서 직접 가져오기")
    migrate_parser.add_argument("--dry-run", action="store_true", help="미리보기 모드")
    migrate_parser.set_defaults(func=run_migrate)

    # iphone 서브명령
    iphone_parser = subparsers.add_parser("iphone", help="iPhone 13 Pro 파일 정리 (HEIC/Live Photo 지원)")
    iphone_parser.add_argument("source", help="정리할 원본 폴더 경로")
    iphone_parser.add_argument("dest", help="정리된 파일을 저장할 폴더 경로")
    iphone_parser.add_argument("--dry-run", action="store_true", help="미리보기 모드")
    iphone_parser.set_defaults(func=run_iphone)

    # realestate 서브명령
    realestate_parser = subparsers.add_parser("realestate", help="부동산 실거래가 데이터 수집 (data.go.kr)")
    realestate_parser.add_argument("--lawd", required=True, help="지역코드 5자리 (법정동코드 앞 5자리)")
    realestate_parser.add_argument("--start", required=True, help="시작 거래년월 (YYYYMM)")
    realestate_parser.add_argument("--end", required=True, help="종료 거래년월 (YYYYMM)")
    realestate_parser.add_argument("--key", help="data.go.kr 일반 인증키(디코딩). 미지정 시 환경변수 DATA_GO_KR_KEY 사용")
    realestate_parser.add_argument("--out", help="저장할 CSV 파일명 (기본: apt_지역_시작_종료.csv)")
    realestate_parser.add_argument("--delay", type=float, help="월별 요청 간 대기 시간(초, 기본: 0.3)")
    realestate_parser.set_defaults(func=run_realestate)

    # cleanup 서브명령
    cleanup_parser = subparsers.add_parser("cleanup", help="저장공간 분석 및 중복·캐시 정리")
    cleanup_parser.add_argument("path", nargs="?", help="분석할 폴더 경로")
    cleanup_parser.add_argument("--android", action="store_true", help="기기 용량 리포트만 출력 (읽기 전용)")
    cleanup_parser.add_argument("--apply", action="store_true", help="중복·캐시·빈폴더 실제 삭제 (기본은 분석만)")
    cleanup_parser.add_argument("--top", type=int, help="상위 목록 개수 (기본: 15)")
    cleanup_parser.add_argument("--min-size", help="대용량 파일 기준 (기본: 50MB)")
    cleanup_parser.add_argument("--report", help="JSON 보고서 저장 경로")
    cleanup_parser.set_defaults(func=run_cleanup)

    # battery 서브명령
    battery_parser = subparsers.add_parser("battery", help="배터리 효율 진단 및 최적화 조치")
    battery_group = battery_parser.add_mutually_exclusive_group()
    battery_group.add_argument("--android", action="store_true", help="Android 진단 (ADB)")
    battery_group.add_argument("--iphone", action="store_true", help="iPhone 배터리 상태 (libimobiledevice)")
    battery_parser.add_argument("--report", help="JSON 보고서 저장 경로")
    battery_parser.add_argument("--no-checklist", action="store_true", help="체크리스트 생략")
    battery_parser.set_defaults(func=run_battery)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
