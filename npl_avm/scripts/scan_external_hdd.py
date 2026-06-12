"""
LG 외장하드(D:) 데이터 스캔 및 활용 가능성 분석

목표:
  1. loan4u_avm_data 구조 파악
  2. 활용 가능한 데이터 식별
  3. NPL AVM DB와 통합 전략 수립
"""

import os
import sys
import json
from pathlib import Path
from collections import defaultdict
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ─── 외장하드 경로 ─────────────────────────────────

EXTERNAL_HDD = Path("D:")
LOAN4U_AVM_DATA = EXTERNAL_HDD / "loan4u_avm_data"
LG_AVM_WORKSPACE = EXTERNAL_HDD / "LG_AVM_Workspace_Data_Moved_20260604"
REB_RONE_AVM = EXTERNAL_HDD / "REB_RONE_AVM_사이드카"
NPL_전례 = EXTERNAL_HDD / "NPL전례"

# ─── 스캔 함수 ────────────────────────────────────

def scan_directory_structure(root_path, max_depth=2, current_depth=0):
    """디렉토리 구조 스캔"""
    structure = {
        "dirs": [],
        "files": defaultdict(list),
    }

    if not root_path.exists():
        return structure

    try:
        for item in sorted(root_path.iterdir()):
            if item.is_dir() and current_depth < max_depth:
                structure["dirs"].append({
                    "name": item.name,
                    "path": str(item),
                })
            elif item.is_file():
                ext = item.suffix.lower()
                structure["files"][ext].append({
                    "name": item.name,
                    "size_mb": item.stat().st_size / (1024 * 1024),
                    "modified": item.stat().st_mtime,
                })
    except PermissionError:
        pass

    return structure


def analyze_loan4u_avm_data():
    """loan4u_avm_data 분석"""
    print("\n" + "="*60)
    print("1️⃣  loan4u_avm_data 데이터 구조 분석")
    print("="*60)

    if not LOAN4U_AVM_DATA.exists():
        print("❌ loan4u_avm_data 경로 없음:", LOAN4U_AVM_DATA)
        return {}

    analysis = {
        "csv_files": [],
        "json_files": [],
        "sqlite_files": [],
        "jsonl_files": [],
        "directories": [],
        "api_key_files": [],
        "config_files": [],
    }

    # 모든 파일 스캔
    try:
        for root, dirs, files in os.walk(LOAN4U_AVM_DATA):
            # 디렉토리 수집
            for d in dirs:
                rel_path = os.path.relpath(os.path.join(root, d), LOAN4U_AVM_DATA)
                analysis["directories"].append(rel_path)

            # 파일 분류
            for f in files:
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, LOAN4U_AVM_DATA)
                file_size = os.path.getsize(full_path) / (1024 * 1024)  # MB

                if f.endswith(".csv"):
                    analysis["csv_files"].append({
                        "name": f,
                        "path": rel_path,
                        "size_mb": round(file_size, 2)
                    })
                elif f.endswith(".json"):
                    analysis["json_files"].append({
                        "name": f,
                        "path": rel_path,
                        "size_mb": round(file_size, 2)
                    })
                elif f.endswith(".jsonl"):
                    analysis["jsonl_files"].append({
                        "name": f,
                        "path": rel_path,
                        "size_mb": round(file_size, 2)
                    })
                elif f.endswith(".sqlite") or f.endswith(".db"):
                    analysis["sqlite_files"].append({
                        "name": f,
                        "path": rel_path,
                        "size_mb": round(file_size, 2)
                    })
                elif f.lower() in [".env", ".env.example", "config.json", "secrets.json"]:
                    analysis["config_files"].append({
                        "name": f,
                        "path": rel_path,
                    })
                elif "api" in f.lower() or "key" in f.lower():
                    analysis["api_key_files"].append({
                        "name": f,
                        "path": rel_path,
                    })
    except Exception as e:
        print(f"⚠️  스캔 오류: {e}")

    # 결과 출력
    print(f"\n📁 디렉토리 ({len(analysis['directories'])}개):")
    for d in sorted(set(analysis["directories"]))[:15]:
        print(f"   - {d}")

    print(f"\n📊 CSV 파일 ({len(analysis['csv_files'])}개):")
    for f in sorted(analysis["csv_files"], key=lambda x: x["size_mb"], reverse=True)[:10]:
        print(f"   - {f['name']:50} {f['size_mb']:8.2f} MB  ({f['path']})")

    print(f"\n📋 JSON/JSONL 파일 ({len(analysis['json_files']) + len(analysis['jsonl_files'])}개):")
    for f in sorted(analysis["json_files"] + analysis["jsonl_files"],
                    key=lambda x: x["size_mb"], reverse=True)[:10]:
        print(f"   - {f['name']:50} {f['size_mb']:8.2f} MB  ({f['path']})")

    print(f"\n🗄️  SQLite DB 파일 ({len(analysis['sqlite_files'])}개):")
    for f in analysis["sqlite_files"]:
        print(f"   - {f['name']:50} {f['size_mb']:8.2f} MB  ({f['path']})")

    print(f"\n🔐 API 키/설정 파일 ({len(analysis['config_files']) + len(analysis['api_key_files'])}개):")
    for f in analysis["config_files"] + analysis["api_key_files"]:
        print(f"   - {f['name']:50} ({f['path']})")

    return analysis


def analyze_rtms_data():
    """RTMS 실거래 데이터 분석"""
    print("\n" + "="*60)
    print("2️⃣  RTMS 실거래 데이터 분석")
    print("="*60)

    rtms_files = []

    if LOAN4U_AVM_DATA.exists():
        for root, dirs, files in os.walk(LOAN4U_AVM_DATA):
            for f in files:
                if "rtms" in f.lower():
                    full_path = os.path.join(root, f)
                    rel_path = os.path.relpath(full_path, LOAN4U_AVM_DATA)
                    file_size = os.path.getsize(full_path) / (1024 * 1024)

                    rtms_files.append({
                        "name": f,
                        "path": rel_path,
                        "size_mb": round(file_size, 2),
                    })

    print(f"\n🔍 발견된 RTMS 파일 ({len(rtms_files)}개):")
    for f in sorted(rtms_files, key=lambda x: x["size_mb"], reverse=True):
        print(f"   - {f['name']:50} {f['size_mb']:8.2f} MB  ({f['path']})")

    return rtms_files


def analyze_vworld_data():
    """V-World 토지 권리 데이터 분석"""
    print("\n" + "="*60)
    print("3️⃣  V-World 토지 권리 데이터 분석")
    print("="*60)

    vworld_files = []

    if LOAN4U_AVM_DATA.exists():
        for root, dirs, files in os.walk(LOAN4U_AVM_DATA):
            for f in files:
                if "vworld" in f.lower() or "land" in f.lower():
                    full_path = os.path.join(root, f)
                    rel_path = os.path.relpath(full_path, LOAN4U_AVM_DATA)
                    file_size = os.path.getsize(full_path) / (1024 * 1024)

                    vworld_files.append({
                        "name": f,
                        "path": rel_path,
                        "size_mb": round(file_size, 2),
                    })

    print(f"\n🗺️  발견된 V-World 파일 ({len(vworld_files)}개):")
    for f in sorted(vworld_files, key=lambda x: x["size_mb"], reverse=True)[:15]:
        print(f"   - {f['name']:50} {f['size_mb']:8.2f} MB  ({f['path']})")

    # SQLite DB 내용 분석
    sqlite_vworld = [f for f in vworld_files if f["name"].endswith(".sqlite")]
    if sqlite_vworld:
        print(f"\n📖 V-World SQLite DB 스키마:")
        for vworld_db in sqlite_vworld[:1]:
            try:
                db_path = LOAN4U_AVM_DATA / vworld_db["path"]
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()

                # 테이블 목록
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()

                print(f"\n   DB: {vworld_db['name']}")
                print(f"   테이블 ({len(tables)}개):")
                for table_name in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name[0]}")
                    count = cursor.fetchone()[0]
                    print(f"      - {table_name[0]}: {count:,}건")

                conn.close()
            except Exception as e:
                print(f"   ⚠️  DB 분석 오류: {e}")

    return vworld_files


def analyze_building_register():
    """건물 레지스터 데이터 분석"""
    print("\n" + "="*60)
    print("4️⃣  건물/호실 레지스터 데이터 분석")
    print("="*60)

    building_files = []

    if LOAN4U_AVM_DATA.exists():
        for root, dirs, files in os.walk(LOAN4U_AVM_DATA):
            for f in files:
                if "building" in f.lower() or "unit" in f.lower():
                    full_path = os.path.join(root, f)
                    rel_path = os.path.relpath(full_path, LOAN4U_AVM_DATA)
                    file_size = os.path.getsize(full_path) / (1024 * 1024)

                    building_files.append({
                        "name": f,
                        "path": rel_path,
                        "size_mb": round(file_size, 2),
                    })

    print(f"\n🏢 발견된 건물/호실 파일 ({len(building_files)}개):")
    for f in sorted(building_files, key=lambda x: x["size_mb"], reverse=True)[:15]:
        print(f"   - {f['name']:50} {f['size_mb']:8.2f} MB  ({f['path']})")

    return building_files


def generate_integration_plan(analysis):
    """통합 계획 생성"""
    print("\n" + "="*60)
    print("💡 NPL AVM DB 통합 계획")
    print("="*60)

    plan = []

    # RTMS 데이터
    if analysis.get("rtms_files"):
        plan.append({
            "source": "loan4u_avm_data/RTMS",
            "target": "transactions 테이블",
            "type": "CSV/JSONL",
            "count": len(analysis.get("rtms_files", [])),
            "action": "건별 실거래가격 적재",
            "priority": "HIGH"
        })

    # V-World 토지 권리
    vworld_sqlite = [f for f in analysis.get("vworld_files", [])
                     if f["name"].endswith(".sqlite")]
    if vworld_sqlite:
        plan.append({
            "source": "loan4u_avm_data/vworld_land_rights.sqlite",
            "target": "properties 테이블 (토지권리 컬럼)",
            "type": "SQLite",
            "count": 1,
            "action": "토지 권리 정보 매핑",
            "priority": "MEDIUM"
        })

    # 건물 레지스터
    if analysis.get("building_files"):
        plan.append({
            "source": "loan4u_avm_data/building_register",
            "target": "complexes / units 테이블",
            "type": "JSON/JSONL",
            "count": len(analysis.get("building_files", [])),
            "action": "단지/호실 정보 적재",
            "priority": "HIGH"
        })

    # 공공데이터
    if analysis.get("csv_files"):
        plan.append({
            "source": "loan4u_avm_data/data_go_kr",
            "target": "transactions 테이블",
            "type": "CSV",
            "count": len([f for f in analysis.get("csv_files", [])
                         if "data_go" in f.get("path", "").lower()]),
            "action": "국토부 공공API 데이터 적재",
            "priority": "HIGH"
        })

    print("\n통합 순서:")
    for i, p in enumerate(plan, 1):
        print(f"\n{i}. [{p['priority']}] {p['source']} → {p['target']}")
        print(f"   파일: {p['count']}개 | 형식: {p['type']}")
        print(f"   작업: {p['action']}")

    return plan


def main():
    print("\n" + "🔍 LG 외장하드 데이터 활용 분석 " + "="*50)

    # 1단계: loan4u_avm_data 구조 분석
    analysis = analyze_loan4u_avm_data()

    # 2단계: RTMS 데이터 분석
    rtms_files = analyze_rtms_data()
    analysis["rtms_files"] = rtms_files

    # 3단계: V-World 데이터 분석
    vworld_files = analyze_vworld_data()
    analysis["vworld_files"] = vworld_files

    # 4단계: 건물 레지스터 분석
    building_files = analyze_building_register()
    analysis["building_files"] = building_files

    # 5단계: 통합 계획 생성
    plan = generate_integration_plan(analysis)

    # 결과 저장
    output_file = Path(__file__).parent.parent / "data" / "external_hdd_analysis.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "analysis": {k: v for k, v in analysis.items() if k != "config_files"},
            "plan": plan,
        }, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 분석 결과 저장: {output_file}")

    # 다음 단계 추천
    print("\n" + "="*60)
    print("🚀 다음 단계")
    print("="*60)
    print("\n1. scripts/import_external_hdd_data.py 실행")
    print("   → RTMS + 건물 레지스터 자동 적재")
    print("\n2. loan4u_avm_data 에서 API 키 확인")
    print("   → 환경변수에 설정")
    print("\n3. Step 2 공공API 수집 진행")


if __name__ == "__main__":
    main()
