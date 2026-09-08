#!/usr/bin/env python3
"""휴대폰 배터리 효율 진단 — 소모 원인 측정 및 최적화 조치 제시

Android는 ADB로, iPhone은 libimobiledevice로 기기에서 직접 값을 읽습니다.
기기를 연결하지 않아도 --advice 로 최적화 체크리스트만 볼 수 있습니다.

읽기 전용입니다. 기기 설정을 변경하지 않습니다.

사용 예:
  python battery.py --android            # Android 배터리 진단 (ADB)
  python battery.py --iphone             # iPhone 배터리 상태 (libimobiledevice)
  python battery.py --advice             # 기기 없이 체크리스트만
"""

import re
import sys
import unicodedata
import json
import plistlib
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

# dumpsys battery 의 health 코드
BATTERY_HEALTH = {
    1: "알 수 없음", 2: "양호", 3: "과열", 4: "수명 종료",
    5: "과전압", 6: "원인 불명 고장", 7: "저온",
}

BATTERY_STATUS = {
    1: "알 수 없음", 2: "충전 중", 3: "방전 중",
    4: "충전 안 함", 5: "완충",
}

# 배터리를 크게 먹는 시스템 항목 (앱이 아니라 하드웨어/OS 단위)
SYSTEM_DRAIN_KEYS = {
    "screen": "화면",
    "cell-standby": "셀룰러 대기",
    "cell": "셀룰러",
    "radio": "무선 통신",
    "wifi": "Wi-Fi",
    "bluetooth": "블루투스",
    "idle": "유휴",
    "phone": "통화",
    "gps": "GPS",
    "sensors": "센서",
    "camera": "카메라",
    "flashlight": "손전등",
    "memory": "메모리",
    "overcounted": "과다 집계",
    "unaccounted": "미집계",
}

# 기기 없이도 제시할 수 있는 최적화 조치
CHECKLIST = [
    ("화면", [
        "자동 밝기를 켜고, 수동 밝기는 50% 이하로 유지 — 화면은 보통 최대 소모원입니다.",
        "화면 자동 꺼짐을 30초~1분으로 설정.",
        "iPhone: 다크 모드 사용 (OLED라 검은 화면이 실제로 전력을 덜 씁니다).",
        "iPhone 13 Pro: 설정 → 손쉬운 사용 → 동작 → '프레임 속도 제한'으로 120Hz를 60Hz로 낮추면 절전됩니다.",
        "'항상 표시' 계열 기능과 들어서 깨우기를 끄기.",
    ]),
    ("백그라운드 활동", [
        "안 쓰는 앱의 백그라운드 앱 새로 고침 끄기 (iPhone: 설정 → 일반 → 백그라운드 앱 새로 고침).",
        "Android: 설정 → 앱 → 각 앱 → 배터리 → '제한'으로 변경.",
        "위치 권한을 '항상 허용'에서 '앱 사용 중에만'으로 변경.",
        "쓰지 않는 위젯과 실시간 활동(Live Activity) 제거.",
    ]),
    ("네트워크", [
        "신호가 약한 곳에서 셀룰러는 전력을 크게 씁니다 — 가능하면 Wi-Fi 사용.",
        "5G가 불안정한 지역이면 LTE 고정 (iPhone: 설정 → 셀룰러 → 음성 및 데이터 → LTE).",
        "안 쓸 때 블루투스·핫스팟·AirDrop 끄기.",
        "신호가 아예 없는 곳에서는 비행기 모드 (기지국 재탐색이 배터리를 크게 먹습니다).",
    ]),
    ("충전 습관", [
        "20~80% 구간에서 충전하는 것이 리튬이온 수명에 가장 좋습니다.",
        "iPhone: 최적화된 배터리 충전 켜기 (설정 → 배터리 → 배터리 건강 및 충전).",
        "Android: 적응형 충전 / 충전 최적화 켜기.",
        "충전 중 고사양 게임은 발열을 키워 수명을 깎습니다 — 피하세요.",
        "35°C 이상 환경과 차량 대시보드 직사광선을 피하세요. 열이 배터리 수명의 최대 적입니다.",
    ]),
    ("점검", [
        "배터리 성능 최대치가 80% 미만이면 교체를 고려하세요 (iPhone: 설정 → 배터리 → 배터리 건강).",
        "충전 사이클 500회 전후부터 체감 열화가 시작됩니다.",
        "설정 → 배터리에서 지난 24시간·10일 소모 상위 앱을 확인하고 상위 항목부터 조치하세요.",
    ]),
]


# ── 유틸리티 ────────────────────────────────────────────────────────────────

def run(cmd: list[str], timeout: int = 60) -> tuple[int, str]:
    """외부 명령 실행. (종료코드, stdout) 반환."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip()
    except FileNotFoundError:
        return -1, f"{cmd[0]} 명령을 찾을 수 없습니다."
    except subprocess.TimeoutExpired:
        return -1, f"{cmd[0]} 명령 시간 초과"


def run_bytes(cmd: list[str], timeout: int = 60) -> tuple[int, bytes]:
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout)
        return r.returncode, r.stdout
    except FileNotFoundError:
        return -1, b""
    except subprocess.TimeoutExpired:
        return -1, b""


def adb(*args, timeout: int = 60) -> tuple[int, str]:
    return run(["adb", *args], timeout=timeout)


def bar(pct: float, width: int = 20) -> str:
    filled = max(0, min(width, round(pct / 100 * width)))
    return "█" * filled + "·" * (width - filled)


def disp_width(text: str) -> int:
    """터미널 표시 폭 — 한글·CJK 문자는 2칸으로 계산."""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)


def pad(text: str, width: int) -> str:
    """표시 폭 기준으로 오른쪽 공백을 채운다 (한글 정렬용)."""
    return text + " " * max(0, width - disp_width(text))


# 읽는 소리에 받침이 있는 숫자/영문자 (예: 1=일, 6=육, L=엘 → '이')
_JONG_DIGITS = set("013678")
_JONG_LETTERS = set("LMNRlmnr")


def subject_particle(word: str) -> str:
    """'이/가' 주격 조사를 앞말의 받침 유무에 따라 선택.

    한글은 종성으로, 숫자·영문자는 읽는 소리로 판단한다.
    (4=사 → '가', 1=일 → '이', S=에스 → '가', L=엘 → '이')
    """
    if not word:
        return "가"
    last = word[-1]
    if "가" <= last <= "힣":
        return "가" if (ord(last) - 0xAC00) % 28 == 0 else "이"
    if last.isdigit():
        return "이" if last in _JONG_DIGITS else "가"
    if last.isalpha():
        return "이" if last in _JONG_LETTERS else "가"
    return "가"


# ── 파서 (순수 함수 — 기기 없이 테스트 가능) ────────────────────────────────

def parse_battery(text: str) -> dict:
    """`dumpsys battery` 출력을 파싱."""
    out: dict = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip().lower()
        val = val.strip()
        if key in ("level", "scale", "voltage", "temperature", "health",
                   "status", "current now", "charge counter"):
            try:
                out[key] = int(val)
            except ValueError:
                pass
        elif key in ("ac powered", "usb powered", "wireless powered", "present"):
            out[key] = val.lower() == "true"
    if "temperature" in out:
        out["temp_c"] = out["temperature"] / 10.0
    if "voltage" in out:
        out["volt_v"] = out["voltage"] / 1000.0
    return out


def parse_power_use(text: str) -> tuple[list[tuple[str, float]], dict]:
    """`dumpsys batterystats` 의 'Estimated power use (mAh)' 구간을 파싱.

    (항목별 mAh 내림차순, 요약) 을 반환.
    """
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if "Estimated power use (mAh)" in line:
            start = i + 1
            break
    if start is None:
        return [], {}

    items: list[tuple[str, float]] = []
    summary: dict = {}

    entry = re.compile(r"^\s*(?:Uid\s+)?([\w\-.]+):\s*([\d.]+)", re.IGNORECASE)

    for line in lines[start:]:
        stripped = line.strip()
        if not stripped:
            break
        # 들여쓰기가 사라지면 구간 종료
        if not line.startswith((" ", "\t")):
            break

        if stripped.lower().startswith("capacity:"):
            for key, pat in (("capacity", r"Capacity:\s*([\d.]+)"),
                             ("computed_drain", r"Computed drain:\s*([\d.]+)"),
                             ("actual_drain", r"actual drain:\s*([\d.]+)")):
                m = re.search(pat, stripped, re.IGNORECASE)
                if m:
                    summary[key] = float(m.group(1))
            continue

        m = entry.match(stripped)
        if m:
            name, value = m.group(1), float(m.group(2))
            if name.lower() in ("capacity", "computed", "actual"):
                continue
            items.append((name, value))

    items.sort(key=lambda kv: -kv[1])
    return items, summary


def parse_wakelocks(text: str) -> list[tuple[str, str]]:
    """`dumpsys batterystats` 의 partial wake lock 목록을 파싱."""
    locks: list[tuple[str, str]] = []
    pat = re.compile(
        r"Wake lock\s+(\S+)\s+(.+?):\s*((?:\d+[dhms]\s*)+)\s*partial", re.IGNORECASE
    )
    for line in text.splitlines():
        m = pat.search(line)
        if m:
            owner = f"{m.group(1)} {m.group(2)}".strip()
            locks.append((owner, m.group(3).strip()))
    return locks


def parse_deviceidle_whitelist(text: str) -> list[str]:
    """`dumpsys deviceidle whitelist` 에서 사용자가 추가한 예외 앱을 추출.

    Doze(절전) 예외 앱은 백그라운드에서 계속 깨어날 수 있어 소모 후보입니다.
    """
    user_apps: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or "," not in line:
            continue
        parts = line.split(",")
        kind = parts[0].strip().lower()
        pkg = parts[1].strip() if len(parts) > 1 else ""
        if kind == "user" and pkg:
            user_apps.append(pkg)
    return user_apps


def parse_screen_settings(brightness: str, timeout: str) -> dict:
    """화면 밝기(0-255)와 자동 꺼짐(ms) 설정을 해석."""
    out: dict = {}
    try:
        b = int(brightness.strip())
        out["brightness_raw"] = b
        out["brightness_pct"] = round(b / 255 * 100, 1)
    except (ValueError, AttributeError):
        pass
    try:
        t = int(timeout.strip())
        out["screen_off_ms"] = t
        out["screen_off_sec"] = round(t / 1000)
    except (ValueError, AttributeError):
        pass
    return out


def parse_ios_battery(data: bytes) -> dict:
    """`idevicediagnostics ioregentry AppleSmartBattery` 의 plist 를 파싱."""
    try:
        plist = plistlib.loads(data)
    except Exception:
        return {}

    # 응답이 {'Status':'Success','Diagnostics':{...}} 형태로 감싸여 올 수 있음
    for key in ("Diagnostics", "IORegistry", "AppleSmartBattery"):
        if isinstance(plist, dict) and key in plist and isinstance(plist[key], dict):
            plist = plist[key]

    out: dict = {}
    for src, dst in (("CycleCount", "cycles"),
                     ("DesignCapacity", "design_mah"),
                     ("AppleRawMaxCapacity", "max_mah"),
                     ("MaxCapacity", "max_capacity_reported"),
                     ("CurrentCapacity", "current"),
                     ("Temperature", "temp_raw"),
                     ("BatteryInstalled", "installed"),
                     ("ExternalConnected", "charging")):
        if isinstance(plist, dict) and src in plist:
            out[dst] = plist[src]

    if out.get("design_mah") and out.get("max_mah"):
        try:
            out["health_pct"] = round(out["max_mah"] / out["design_mah"] * 100, 1)
        except ZeroDivisionError:
            pass
    if "temp_raw" in out:
        try:
            out["temp_c"] = round(out["temp_raw"] / 100.0, 1)
        except TypeError:
            pass
    return out


# ── 조치 제안 ───────────────────────────────────────────────────────────────

def recommend(data: dict) -> list[tuple[str, str]]:
    """측정값에 근거한 조치를 (우선순위, 내용) 목록으로 반환."""
    recs: list[tuple[str, str]] = []
    b = data.get("battery", {})
    ios = data.get("ios", {})
    screen = data.get("screen", {})

    # 배터리 건강
    health_pct = ios.get("health_pct")
    if health_pct is not None:
        if health_pct < 80:
            recs.append(("높음", f"배터리 성능 최대치가 {health_pct}% 입니다. 80% 미만이므로 교체를 권장합니다."))
        elif health_pct < 90:
            recs.append(("보통", f"배터리 성능 최대치 {health_pct}% — 열화가 진행 중입니다. 20~80% 충전 습관을 지키세요."))

    cycles = ios.get("cycles")
    if isinstance(cycles, int) and cycles >= 500:
        recs.append(("보통", f"충전 사이클 {cycles}회 — 수명 후반 구간입니다. 성능 최대치를 함께 확인하세요."))

    health_code = b.get("health")
    if health_code and health_code != 2:
        recs.append(("높음", f"기기가 배터리 상태를 '{BATTERY_HEALTH.get(health_code, health_code)}' 로 보고합니다. 점검이 필요합니다."))

    # 온도
    temp = b.get("temp_c") or ios.get("temp_c")
    if temp is not None:
        if temp >= 40:
            recs.append(("높음", f"배터리 온도 {temp}°C — 즉시 발열 원인을 줄이세요. 고온은 수명을 영구적으로 깎습니다."))
        elif temp >= 35:
            recs.append(("보통", f"배터리 온도 {temp}°C — 다소 높습니다. 충전 중 고사양 사용과 직사광선을 피하세요."))

    # 화면 설정
    if screen.get("brightness_pct", 0) > 60:
        recs.append(("높음", f"화면 밝기가 {screen['brightness_pct']}% 입니다. 자동 밝기를 켜거나 50% 이하로 낮추세요 — 보통 최대 소모원입니다."))
    if screen.get("screen_off_sec", 0) > 60:
        recs.append(("보통", f"화면 자동 꺼짐이 {screen['screen_off_sec']}초입니다. 30~60초로 줄이면 누적 절전 효과가 큽니다."))

    # 소모 상위 항목
    items = data.get("power_use", [])
    total = sum(v for _, v in items) or 1
    for name, mah in items[:5]:
        pct = mah / total * 100
        if pct < 8:
            continue
        label = SYSTEM_DRAIN_KEYS.get(name.lower())
        if label == "화면":
            recs.append(("높음", f"화면이 전체 소모의 {pct:.0f}%({mah:.0f}mAh)입니다. 밝기·자동 꺼짐·주사율을 낮추세요."))
        elif label in ("셀룰러 대기", "셀룰러", "무선 통신"):
            recs.append(("높음", f"{label}{subject_particle(label)} 전체 소모의 {pct:.0f}%입니다. 신호가 약한 환경입니다 — Wi-Fi 사용 또는 LTE 고정을 검토하세요."))
        elif label == "GPS":
            recs.append(("높음", f"GPS가 전체 소모의 {pct:.0f}%입니다. 위치 권한을 '앱 사용 중에만'으로 바꾸세요."))
        elif label is None:
            recs.append(("높음", f"{name}{subject_particle(name)} 전체 소모의 {pct:.0f}%({mah:.0f}mAh)입니다. 해당 앱의 배터리 사용을 '제한'으로 바꾸세요."))

    # Doze 예외 앱
    wl = data.get("doze_whitelist", [])
    if wl:
        recs.append(("보통",
                     f"절전(Doze) 예외 앱이 {len(wl)}개 있습니다: {', '.join(wl[:5])}"
                     f"{' 외' if len(wl) > 5 else ''}. "
                     "필요 없는 앱은 배터리 최적화를 다시 켜세요."))

    # Wakelock
    locks = data.get("wakelocks", [])
    if locks:
        top = ", ".join(f"{o} ({t})" for o, t in locks[:3])
        recs.append(("보통", f"기기를 깨우고 있는 wakelock 상위: {top}. 해당 앱의 백그라운드 활동을 제한하세요."))

    if not recs:
        recs.append(("정보", "측정값에서 특별한 이상은 발견되지 않았습니다. 아래 체크리스트를 참고하세요."))

    order = {"높음": 0, "보통": 1, "정보": 2}
    recs.sort(key=lambda r: order.get(r[0], 3))
    return recs


# ── 리포트 ──────────────────────────────────────────────────────────────────

def print_checklist():
    print(f"\n{'=' * 56}")
    print("  배터리 효율 최적화 체크리스트")
    print(f"{'=' * 56}")
    for section, items in CHECKLIST:
        print(f"\n── {section} ──")
        for item in items:
            print(f"  • {item}")


def print_report(data: dict):
    b = data.get("battery", {})
    ios = data.get("ios", {})
    screen = data.get("screen", {})

    print(f"\n{'=' * 56}")
    print(f"  배터리 진단: {data.get('device', '알 수 없는 기기')}")
    print(f"{'=' * 56}")

    if b:
        level = b.get("level")
        print(f"\n── 현재 상태 ──")
        if level is not None:
            print(f"  잔량        {level}%  {bar(level)}")
        if "status" in b:
            print(f"  상태        {BATTERY_STATUS.get(b['status'], b['status'])}")
        if "health" in b:
            print(f"  건강        {BATTERY_HEALTH.get(b['health'], b['health'])}")
        if "temp_c" in b:
            print(f"  온도        {b['temp_c']}°C")
        if "volt_v" in b:
            print(f"  전압        {b['volt_v']}V")

    if ios:
        print(f"\n── 배터리 수명 ──")
        if "health_pct" in ios:
            print(f"  성능 최대치  {ios['health_pct']}%  {bar(ios['health_pct'])}")
        if "design_mah" in ios and "max_mah" in ios:
            print(f"  용량        {ios['max_mah']}mAh / 설계 {ios['design_mah']}mAh")
        if "cycles" in ios:
            print(f"  충전 사이클  {ios['cycles']}회")
        if "temp_c" in ios:
            print(f"  온도        {ios['temp_c']}°C")

    if screen:
        print(f"\n── 화면 설정 ──")
        if "brightness_pct" in screen:
            print(f"  밝기        {screen['brightness_pct']}%  {bar(screen['brightness_pct'])}")
        if "screen_off_sec" in screen:
            print(f"  자동 꺼짐    {screen['screen_off_sec']}초")

    items = data.get("power_use", [])
    if items:
        total = sum(v for _, v in items) or 1
        print(f"\n── 소모 상위 항목 (추정 mAh) ──")
        for name, mah in items[:12]:
            label = SYSTEM_DRAIN_KEYS.get(name.lower(), name)
            pct = mah / total * 100
            print(f"  {pad(label, 14)} {mah:>8.1f}  {pct:5.1f}%  {bar(pct, 14)}")

    recs = data.get("recommendations", [])
    if recs:
        print(f"\n{'=' * 56}")
        print("  조치 (측정값 근거, 우선순위 순)")
        print(f"{'=' * 56}")
        for prio, text in recs:
            print(f"\n  [{prio}] {text}")


# ── Android ─────────────────────────────────────────────────────────────────

def check_android_device() -> str | None:
    code, out = adb("devices")
    if code != 0:
        print(f"ADB 오류: {out}")
        return None
    devices = [l for l in out.splitlines()[1:] if l.strip() and "device" in l]
    if not devices:
        print("연결된 Android 기기가 없습니다.")
        print("  1. 설정 → 개발자 옵션에서 USB 디버깅 활성화")
        print("  2. USB 케이블 연결 후 기기에서 '허용' 선택")
        return None
    return devices[0].split()[0]


def diagnose_android() -> dict | None:
    serial = check_android_device()
    if not serial:
        return None

    code, model = adb("shell", "getprop", "ro.product.model")
    device = model.strip() if code == 0 and model.strip() else serial
    print(f"기기: {device}")

    data: dict = {"device": device, "platform": "Android"}

    print("  배터리 상태 조회 중...")
    code, out = adb("shell", "dumpsys", "battery")
    if code == 0:
        data["battery"] = parse_battery(out)

    print("  화면 설정 조회 중...")
    _, brightness = adb("shell", "settings", "get", "system", "screen_brightness")
    _, timeout = adb("shell", "settings", "get", "system", "screen_off_timeout")
    data["screen"] = parse_screen_settings(brightness, timeout)

    print("  소모 통계 조회 중... (시간이 걸릴 수 있습니다)")
    code, out = adb("shell", "dumpsys", "batterystats", "--charged", timeout=180)
    if code == 0:
        items, summary = parse_power_use(out)
        data["power_use"] = items
        data["drain_summary"] = summary
        data["wakelocks"] = parse_wakelocks(out)

    print("  절전 예외 앱 조회 중...")
    code, out = adb("shell", "dumpsys", "deviceidle", "whitelist")
    if code == 0:
        data["doze_whitelist"] = parse_deviceidle_whitelist(out)

    return data


# ── iPhone ──────────────────────────────────────────────────────────────────

def diagnose_iphone() -> dict | None:
    code, out = run(["idevice_id", "-l"])
    if code != 0:
        print("libimobiledevice 가 필요합니다.")
        print("  macOS:  brew install libimobiledevice")
        print("  Linux:  sudo apt install libimobiledevice-utils")
        return None
    udids = [l.strip() for l in out.splitlines() if l.strip()]
    if not udids:
        print("연결된 iPhone 이 없습니다. USB로 연결하고 '이 컴퓨터를 신뢰'를 선택하세요.")
        return None

    code, name = run(["ideviceinfo", "-k", "DeviceName"])
    device = name.strip() if code == 0 and name.strip() else udids[0]
    print(f"기기: {device}")

    data: dict = {"device": device, "platform": "iOS"}

    print("  배터리 정보 조회 중...")
    code, raw = run_bytes(["idevicediagnostics", "ioregentry", "AppleSmartBattery"])
    if code == 0 and raw:
        data["ios"] = parse_ios_battery(raw)

    if not data.get("ios"):
        print("  배터리 상세를 읽지 못했습니다. iOS 버전에 따라 제한될 수 있습니다.")

    print("\n  ※ iOS는 앱별 소모 통계를 외부에서 읽을 수 없습니다.")
    print("     설정 → 배터리 에서 지난 24시간·10일 상위 앱을 직접 확인하세요.")

    return data


# ── 메인 ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="휴대폰 배터리 효율 진단 및 최적화 조치 제시 (읽기 전용)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python battery.py --android              # Android 진단 (ADB 필요)
  python battery.py --iphone               # iPhone 배터리 상태 (libimobiledevice 필요)
  python battery.py --advice                # 기기 없이 체크리스트만
  python battery.py --android --report b.json

기기 설정을 변경하지 않습니다. 값을 읽어 진단만 수행합니다.
""",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--android", action="store_true", help="Android 기기 진단 (ADB)")
    group.add_argument("--iphone", action="store_true", help="iPhone 배터리 상태 (libimobiledevice)")
    group.add_argument("--advice", action="store_true", help="기기 연결 없이 체크리스트만 출력")

    parser.add_argument("--report", help="JSON 보고서 저장 경로")
    parser.add_argument("--no-checklist", action="store_true", help="체크리스트 생략")
    args = parser.parse_args()

    if args.advice:
        print_checklist()
        return

    data = diagnose_android() if args.android else diagnose_iphone()
    if data is None:
        sys.exit(1)

    data["recommendations"] = recommend(data)
    data["실행일시"] = datetime.now().isoformat()

    print_report(data)

    if not args.no_checklist:
        print_checklist()

    if args.report:
        out = Path(args.report).resolve()
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str),
                       encoding="utf-8")
        print(f"\n  보고서: {out}")


if __name__ == "__main__":
    main()
