-- VWorld 14개 API 레이어 통합 SQLite 스키마
-- 생성일: 2026-07-24
-- 목적: 원본 데이터 저장소 (14개 테이블)

-- ============================================================
-- Layer 1-3: 지리 정보 (search, geocode, WMS/WFS 참조)
-- ============================================================

-- Layer 1: search20 (검색 API 2.0)
CREATE TABLE IF NOT EXISTS layer1_search20 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    api_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    address TEXT,
    search_type TEXT,
    category TEXT,
    lat REAL,
    lon REAL,
    geom TEXT,
    data_json TEXT,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(api_id, search_type, category)
);
CREATE INDEX IF NOT EXISTS idx_search20_address ON layer1_search20(address);
CREATE INDEX IF NOT EXISTS idx_search20_geom ON layer1_search20(lat, lon);

-- Layer 2: geocoder20 (지오코더 API 2.0)
CREATE TABLE IF NOT EXISTS layer2_geocoder20 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    address TEXT UNIQUE NOT NULL,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    level TEXT,
    accuracy TEXT,
    crs TEXT,
    data_json TEXT,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_geocoder20_coords ON layer2_geocoder20(lat, lon);

-- Layer 3: WMS/WFS 참조
CREATE TABLE IF NOT EXISTS layer3_wfs_reference (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    layer_name TEXT UNIQUE NOT NULL,
    layer_id TEXT,
    description TEXT,
    srs TEXT,
    geom_type TEXT,
    feature_count INTEGER,
    data_json TEXT,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- Layer 4-7: 건물/토지 정보 (WFS 피처)
-- ============================================================

-- Layer 4: continuous_cadastral_map (연속지적도)
CREATE TABLE IF NOT EXISTS layer4_cadastral_map (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quad_id TEXT UNIQUE NOT NULL,
    lot_number TEXT,
    area REAL,
    owner TEXT,
    zoning TEXT,
    geom TEXT,
    data_json TEXT,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_cadastral_quad ON layer4_cadastral_map(quad_id);

-- Layer 5: building_by_use (용도별 건물)
CREATE TABLE IF NOT EXISTS layer5_building_by_use (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    building_id TEXT UNIQUE NOT NULL,
    use_code TEXT,
    use_name TEXT,
    count INTEGER,
    data_json TEXT,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_building_use ON layer5_building_by_use(use_code);

-- Layer 6: gis_building_general (GIS 건물 일반)
CREATE TABLE IF NOT EXISTS layer6_gis_building_general (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    building_id TEXT UNIQUE NOT NULL,
    geom TEXT NOT NULL,
    height REAL,
    stories INTEGER,
    material TEXT,
    address TEXT,
    data_json TEXT,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_building_general_addr ON layer6_gis_building_general(address);

-- Layer 7: gis_building_integrated (GIS 건물 통합)
CREATE TABLE IF NOT EXISTS layer7_gis_building_integrated (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    building_id TEXT UNIQUE NOT NULL,
    address TEXT,
    geom TEXT NOT NULL,
    attributes TEXT,
    data_json TEXT,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_building_integrated_addr ON layer7_gis_building_integrated(address);

-- ============================================================
-- Layer 8-10: 토지 특성 (토지 정보)
-- ============================================================

-- Layer 8: land_characteristics (토지 특성)
CREATE TABLE IF NOT EXISTS layer8_land_characteristics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lot_id TEXT UNIQUE NOT NULL,
    slope TEXT,
    soil_type TEXT,
    water_accessibility TEXT,
    data_json TEXT,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_land_char_lot ON layer8_land_characteristics(lot_id);

-- Layer 9: land_use_plan (토지 이용계획)
CREATE TABLE IF NOT EXISTS layer9_land_use_plan (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    area_id TEXT UNIQUE NOT NULL,
    plan_zone TEXT,
    height_limit REAL,
    coverage_rate REAL,
    data_json TEXT,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_useplan_area ON layer9_land_use_plan(area_id);

-- Layer 10: land_right_register (대지권 등록)
CREATE TABLE IF NOT EXISTS layer10_land_right_register (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lot_id TEXT,
    right_type TEXT,
    owner TEXT,
    registration_date TEXT,
    data_json TEXT,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(lot_id, right_type, owner)
);
CREATE INDEX IF NOT EXISTS idx_land_right_lot ON layer10_land_right_register(lot_id);

-- ============================================================
-- Layer 11-14: 가격 정보 (공시가격 + 변동률)
-- ============================================================

-- Layer 11: apart_housing_price (공동주택가격)
CREATE TABLE IF NOT EXISTS layer11_apart_housing_price (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    apt_id TEXT,
    address TEXT NOT NULL,
    price_per_m2 REAL,
    price_total REAL,
    price_date TEXT,
    data_json TEXT,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(apt_id, price_date)
);
CREATE INDEX IF NOT EXISTS idx_apart_addr ON layer11_apart_housing_price(address);
CREATE INDEX IF NOT EXISTS idx_apart_date ON layer11_apart_housing_price(price_date);

-- Layer 12: individual_house_price (개별주택가격)
CREATE TABLE IF NOT EXISTS layer12_individual_house_price (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    house_id TEXT,
    address TEXT NOT NULL,
    price_per_m2 REAL,
    price_total REAL,
    price_date TEXT,
    data_json TEXT,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(house_id, price_date)
);
CREATE INDEX IF NOT EXISTS idx_house_addr ON layer12_individual_house_price(address);
CREATE INDEX IF NOT EXISTS idx_house_date ON layer12_individual_house_price(price_date);

-- Layer 13: land_price_region (지역별 지가변동)
CREATE TABLE IF NOT EXISTS layer13_land_price_region (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    region_code TEXT NOT NULL,
    year INTEGER NOT NULL,
    change_rate REAL,
    index REAL,
    data_json TEXT,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(region_code, year)
);
CREATE INDEX IF NOT EXISTS idx_price_region_code ON layer13_land_price_region(region_code);

-- Layer 14: land_price_usage (용도별 지가변동)
CREATE TABLE IF NOT EXISTS layer14_land_price_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    use_code TEXT NOT NULL,
    year INTEGER NOT NULL,
    change_rate REAL,
    index REAL,
    data_json TEXT,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(use_code, year)
);
CREATE INDEX IF NOT EXISTS idx_price_usage_code ON layer14_land_price_usage(use_code);

-- ============================================================
-- 메타데이터 + 감시
-- ============================================================

-- API 호출 기록
CREATE TABLE IF NOT EXISTS api_call_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    api_name TEXT NOT NULL,
    layer TEXT,
    http_status INTEGER,
    rows_fetched INTEGER,
    error_message TEXT,
    call_time_ms INTEGER,
    called_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 데이터 품질 메트릭
CREATE TABLE IF NOT EXISTS data_quality_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    layer TEXT UNIQUE NOT NULL,
    total_rows INTEGER,
    null_count INTEGER,
    duplicate_count INTEGER,
    null_rate REAL,
    quality_score REAL,
    measured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
