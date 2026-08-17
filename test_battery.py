#!/usr/bin/env python3
"""battery.py 파서·조치 로직 검증 — 기기 연결 없이 실행 가능

실제 dumpsys / ioregentry 출력 형식을 픽스처로 사용합니다.

실행:  python test_battery.py
"""

import sys
import plistlib

from battery import (
    BATTERY_HEALTH,
    disp_width,
    pad,
    subject_particle,
    parse_battery,
    parse_deviceidle_whitelist,
    parse_ios_battery,
    parse_power_use,
    parse_screen_settings,
    parse_wakelocks,
    recommend,
)

# ── 픽스처 ──────────────────────────────────────────────────────────────────

DUMPSYS_BATTERY = """Current Battery Service state:
  AC powered: false
  USB powered: true
  Wireless powered: false
  Max charging current: 500000
  present: true
  status: 2
  health: 3
  level: 43
  scale: 100
  voltage: 3856
  temperature: 412
  technology: Li-ion
"""

BATTERYSTATS = """
  Estimated power use (mAh):
    Capacity: 4352, Computed drain: 1876, actual drain: 1902
    screen: 742
    Uid u0a234: 310 ( cpu=180 wifi=90 wake=40 )
    cell-standby: 205
    Uid u0a119: 96.5
    idle: 61.2
    wifi: 44
    bluetooth: 3.1

  Statistics since last charge:
"""

WAKELOCKS = """
    Wake lock u0a234 *alarm*: 1h 12m 3s partial (18 times) realtime
    Wake lock u0a119 NlpWakeLock: 4m 51s partial (7 times) realtime
    Wake lock u0a55 nothing here
"""

DEVICEIDLE = """system,com.google.android.gms,10012
system,com.android.vending,10015
user,com.kakao.talk,10234
user,com.nhn.android.band,10251
"""

IOS_PLIST = plistlib.dumps({
    "Status": "Success",
    "Diagnostics": {
        "CycleCount": 612,
        "DesignCapacity": 3095,
        "AppleRawMaxCapacity": 2410,
        "CurrentCapacity": 61,
        "Temperature": 3180,
        "BatteryInstalled": True,
    },
})


# ── 검증 ────────────────────────────────────────────────────────────────────

FAILURES: list[str] = []


def check(name: str, cond: bool, got=None):
    if cond:
        print(f"  ✓ {name}")
    else:
        print(f"  ✗ {name}  got={got!r}")
        FAILURES.append(name)


def test_parse_battery():
    print("── parse_battery (dumpsys battery) ──")
    b = parse_battery(DUMPSYS_BATTERY)
    check("level=43", b.get("level") == 43, b.get("level"))
    check("온도 412 → 41.2°C", b.get("temp_c") == 41.2, b.get("temp_c"))
    check("전압 3856 → 3.856V", b.get("volt_v") == 3.856, b.get("volt_v"))
    check("health=3 → 과열", BATTERY_HEALTH[b["health"]] == "과열")
    check("USB powered → True", b.get("usb powered") is True)
    check("빈 입력 안전", parse_battery("") == {})
    return b


def test_parse_power_use():
    print("\n── parse_power_use (batterystats) ──")
    items, summary = parse_power_use(BATTERYSTATS)
    check("항목 7개 파싱", len(items) == 7, len(items))
    check("mAh 내림차순 (screen 최상위)", items[0] == ("screen", 742.0), items[0])
    check("Uid 접두어 제거", ("u0a234", 310.0) in items)
    check("소수점 값 유지", ("u0a119", 96.5) in items)
    check("Capacity 요약 파싱", summary.get("capacity") == 4352.0, summary)
    check("computed drain", summary.get("computed_drain") == 1876.0)
    check("actual drain", summary.get("actual_drain") == 1902.0)
    check("Capacity 를 항목으로 오인하지 않음",
          not any(n.lower() == "capacity" for n, _ in items))
    check("구간 없으면 빈 결과", parse_power_use("아무 내용 없음") == ([], {}))
    return items


def test_parse_wakelocks():
    print("\n── parse_wakelocks ──")
    locks = parse_wakelocks(WAKELOCKS)
    check("partial wakelock 2개만", len(locks) == 2, locks)
    check("소유자와 보유시간 추출",
          locks[0][0].startswith("u0a234") and "1h" in locks[0][1], locks[0])
    return locks


def test_parse_deviceidle():
    print("\n── parse_deviceidle_whitelist ──")
    wl = parse_deviceidle_whitelist(DEVICEIDLE)
    check("user 항목만 추출 (system 제외)",
          wl == ["com.kakao.talk", "com.nhn.android.band"], wl)
    return wl


def test_parse_screen():
    print("\n── parse_screen_settings ──")
    s = parse_screen_settings("204", "120000")
    check("밝기 204/255 → 80%", s.get("brightness_pct") == 80.0, s.get("brightness_pct"))
    check("자동꺼짐 120000ms → 120초", s.get("screen_off_sec") == 120, s.get("screen_off_sec"))
    check("'null' 입력 안전", parse_screen_settings("null", "null") == {})
    return s


def test_parse_ios():
    print("\n── parse_ios_battery (ioregentry plist) ──")
    ios = parse_ios_battery(IOS_PLIST)
    check("충전 사이클 612", ios.get("cycles") == 612, ios.get("cycles"))
    check("건강도 2410/3095 → 77.9%", ios.get("health_pct") == 77.9, ios.get("health_pct"))
    check("온도 3180 → 31.8°C", ios.get("temp_c") == 31.8, ios.get("temp_c"))
    check("plist 아닌 입력 안전", parse_ios_battery(b"not a plist") == {})
    return ios


def test_recommend(b, ios, s, items, wl, locks):
    print("\n── recommend (측정값 → 조치) ──")
    recs = recommend({
        "battery": b, "ios": ios, "screen": s,
        "power_use": items, "doze_whitelist": wl, "wakelocks": locks,
    })
    txt = " | ".join(t for _, t in recs)

    check("건강 77.9% → 교체 권고", "교체를 권장" in txt)
    check("41.2°C → 발열 즉시 조치", "41.2" in txt and "즉시" in txt)
    check("health=3 → 과열 반영", "과열" in txt)
    check("밝기 80% → 경고", "밝기" in txt)
    check("자동꺼짐 120초 → 경고", "120초" in txt)
    check("화면 최대 소모 지적", "화면이 전체 소모" in txt)
    check("Doze 예외 앱 지적", "com.kakao.talk" in txt)
    check("사이클 612 → 수명 후반 언급", "612" in txt)
    check("우선순위 '높음' 우선 정렬", recs[0][0] == "높음", recs[0][0])

    clean = recommend({"battery": {"health": 2, "level": 80, "temp_c": 25.0},
                       "ios": {}, "screen": {"brightness_pct": 40.0, "screen_off_sec": 30},
                       "power_use": [], "doze_whitelist": [], "wakelocks": []})
    check("이상 없으면 정보 항목만", clean[0][0] == "정보", clean[0])

    print(f"\n  → 조치 {len(recs)}건 (높음 {sum(1 for p, _ in recs if p == '높음')}건)")


def test_korean_helpers():
    print("\n── 한글 출력 보조 (조사·정렬) ──")
    cases = [
        ("셀룰러 대기", "가"), ("화면", "이"), ("무선 통신", "이"),
        ("GPS", "가"), ("u0a234", "가"), ("u0a231", "이"),
        ("블루투스", "가"), ("손전등", "이"), ("Wi-Fi", "가"), ("", "가"),
    ]
    wrong = [(w, subject_particle(w), exp) for w, exp in cases
             if subject_particle(w) != exp]
    check("주격 조사 이/가 선택", not wrong, wrong)

    check("한글 표시 폭 2칸 계산", disp_width("화면") == 4, disp_width("화면"))
    check("영문 표시 폭 1칸 계산", disp_width("wifi") == 4, disp_width("wifi"))
    check("한글·영문 라벨 폭 정렬 일치",
          disp_width(pad("화면", 14)) == disp_width(pad("Wi-Fi", 14)) == 14)


def main():
    print("=" * 46)
    print("  battery.py 검증")
    print("=" * 46 + "\n")

    b = test_parse_battery()
    items = test_parse_power_use()
    locks = test_parse_wakelocks()
    wl = test_parse_deviceidle()
    s = test_parse_screen()
    ios = test_parse_ios()
    test_recommend(b, ios, s, items, wl, locks)
    test_korean_helpers()

    print("\n" + "=" * 46)
    if FAILURES:
        print(f"  실패 {len(FAILURES)}건: {', '.join(FAILURES)}")
        sys.exit(1)
    print("  전체 통과")


if __name__ == "__main__":
    main()
