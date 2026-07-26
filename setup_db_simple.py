#!/usr/bin/env python3
"""VWorld SQLite 데이터베이스 초기화 (테이블만)"""

import sqlite3
from pathlib import Path

db_path = Path(r"D:\loan4u_avm_data\vworld_wfs_multi_layer\db\vworld_wfs_multi_layer.sqlite")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 14개 레이어 테이블 생성
tables = [
    ("layer1_search20", "api_id TEXT PRIMARY KEY, name TEXT, address TEXT, lat REAL, lon REAL, data_json TEXT, collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ("layer2_geocoder20", "address TEXT PRIMARY KEY, lat REAL, lon REAL, level TEXT, data_json TEXT, collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ("layer3_wfs_reference", "layer_name TEXT PRIMARY KEY, layer_id TEXT, geom_type TEXT, data_json TEXT, collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ("layer4_cadastral_map", "quad_id TEXT PRIMARY KEY, lot_number TEXT, area REAL, owner TEXT, geom TEXT, data_json TEXT, collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ("layer5_building_by_use", "building_id TEXT PRIMARY KEY, use_code TEXT, use_name TEXT, count INTEGER, data_json TEXT, collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ("layer6_gis_building_general", "building_id TEXT PRIMARY KEY, geom TEXT, height REAL, stories INTEGER, address TEXT, data_json TEXT, collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ("layer7_gis_building_integrated", "building_id TEXT PRIMARY KEY, address TEXT, geom TEXT, attributes TEXT, data_json TEXT, collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ("layer8_land_characteristics", "lot_id TEXT PRIMARY KEY, slope TEXT, soil_type TEXT, data_json TEXT, collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ("layer9_land_use_plan", "area_id TEXT PRIMARY KEY, plan_zone TEXT, height_limit REAL, data_json TEXT, collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ("layer10_land_right_register", "id INTEGER PRIMARY KEY AUTOINCREMENT, lot_id TEXT, right_type TEXT, owner TEXT, data_json TEXT, collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ("layer11_apart_housing_price", "id INTEGER PRIMARY KEY AUTOINCREMENT, apt_id TEXT, address TEXT, price_per_m2 REAL, price_total REAL, price_date TEXT, data_json TEXT, collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ("layer12_individual_house_price", "id INTEGER PRIMARY KEY AUTOINCREMENT, house_id TEXT, address TEXT, price_per_m2 REAL, price_total REAL, price_date TEXT, data_json TEXT, collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ("layer13_land_price_region", "region_code TEXT PRIMARY KEY, year INTEGER, change_rate REAL, price_index REAL, data_json TEXT, collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ("layer14_land_price_usage", "use_code TEXT PRIMARY KEY, year INTEGER, change_rate REAL, price_index REAL, data_json TEXT, collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ("api_call_log", "id INTEGER PRIMARY KEY AUTOINCREMENT, api_name TEXT, http_status INTEGER, rows_fetched INTEGER, call_time_ms INTEGER, called_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ("data_quality_metrics", "layer TEXT PRIMARY KEY, total_rows INTEGER, null_count INTEGER, quality_score REAL, measured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
]

for table_name, columns in tables:
    sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns})"
    cursor.execute(sql)

conn.commit()

cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables_created = [row[0] for row in cursor.fetchall()]
print(f"✓ Created {len(tables_created)} tables:")
for t in tables_created[:5]:
    print(f"  - {t}")
print(f"  ... ({len(tables_created) - 5} more)")

conn.close()
print(f"\n✓ Database: {db_path}")
print(f"  Size: {db_path.stat().st_size:,} bytes")
