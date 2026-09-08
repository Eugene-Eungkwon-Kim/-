"""ADB로 안드로이드 기기에서 파일을 받아온다."""

import subprocess
from pathlib import Path

ANDROID_PATHS = [
    "/sdcard/DCIM",
    "/sdcard/Pictures",
    "/sdcard/Movies",
    "/sdcard/Music",
    "/sdcard/Download",
    "/sdcard/Documents",
    "/sdcard/WhatsApp",
    "/sdcard/Telegram",
    "/sdcard/KakaoTalk",
]

RAW_DIR_NAME = "raw_from_device"


def adb(*args, timeout: int = 300) -> tuple[int, str]:
    try:
        result = subprocess.run(["adb", *args], capture_output=True, text=True, timeout=timeout)
        return result.returncode, (result.stdout or result.stderr).strip()
    except FileNotFoundError:
        return -1, "adb 명령을 찾을 수 없습니다. Android SDK Platform Tools를 설치하세요."
    except subprocess.TimeoutExpired:
        return -1, "ADB 명령 시간 초과"


CONNECTION_HELP = (
    "연결된 Android 기기가 없습니다.\n"
    "  1. 설정 → 개발자 옵션에서 USB 디버깅을 켜세요\n"
    "  2. USB 케이블로 기기를 연결하세요\n"
    "  3. 기기 화면에서 'USB 디버깅 허용'을 선택하세요"
)


def find_device() -> tuple[str | None, str]:
    """(기기 ID, 문제 안내문). 기기를 찾으면 안내문은 빈 문자열이다."""
    code, out = adb("devices", timeout=30)
    if code == -1:
        return None, out  # adb 자체가 없거나 응답하지 않음
    if code != 0:
        return None, f"ADB 오류: {out}"
    for line in out.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            return parts[0], ""
    return None, CONNECTION_HELP


def path_exists(remote: str) -> bool:
    """기기에 해당 경로가 있는지 확인한다.

    `adb shell` 은 기기에 따라 종료 코드를 전달하지 않는 경우가 있어
    출력 문자열까지 함께 본다.
    """
    code, out = adb("shell", f"ls -d {remote} 2>/dev/null", timeout=30)
    if code != 0:
        return False
    return bool(out) and "No such file" not in out and "not found" not in out.lower()


def pull_all(dest: Path, dry_run: bool = False) -> tuple[Path, int]:
    """기기의 표준 폴더를 `dest/raw_from_device` 아래로 받아온다."""
    raw_root = dest / RAW_DIR_NAME
    pulled = 0
    for remote in ANDROID_PATHS:
        if not path_exists(remote):
            continue
        local = raw_root / remote.lstrip("/")
        print(f"  받는 중: {remote}")
        if not dry_run:
            local.mkdir(parents=True, exist_ok=True)
            code, out = adb("pull", "-a", remote, str(local))
            if code != 0:
                print(f"  [경고] {remote} 가져오기 실패: {out}")
                continue
        pulled += 1
    return raw_root, pulled
