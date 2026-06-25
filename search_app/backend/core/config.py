from __future__ import annotations

import threading

VWORLD_MAP_KEY_ENV_NAMES = ("VWORLD_MAP_KEY", "VWORLD_API_KEY", "VWORLD_MAP_API_KEY")
MAP_LIBRARY_URLS = {
    "openlayers_script_url": "https://unpkg.com/ol/dist/ol.js",
    "openlayers_style_url": "https://unpkg.com/ol/ol.css",
    "openfree_olms_script_url": "https://unpkg.com/ol-mapbox-style/dist/olms.js",
}
DEFAULT_MAP_PROVIDERS = [
    (
        "VWORLD",
        True,
        10,
        "VWorld",
        "https://api.vworld.kr/req/wmts/1.0.0/{key}/Base/{z}/{y}/{x}.png",
        None,
        "VWorld",
        True,
        "VWORLD_MAP_KEY",
        "OPENFREEMAP",
    ),
    (
        "OPENFREEMAP",
        True,
        20,
        "OpenFreeMap",
        None,
        "https://tiles.openfreemap.org/styles/liberty",
        "OpenFreeMap",
        False,
        None,
        "INTERNAL",
    ),
    (
        "INTERNAL",
        True,
        90,
        "내부 좌표지도",
        None,
        None,
        "내부 좌표지도",
        False,
        None,
        None,
    ),
]


LABELS = {
    "site_category": {
        "OIL_STATION": "주유소",
        "CHARGING_STATION": "충전소",
        "HYBRID_FUEL_SITE": "복합시설",
        "LPG_CHARGING_STATION": "LPG 충전소",
        "CNG_CHARGING_STATION": "CNG 충전소",
        "LNG_CHARGING_STATION": "LNG 충전소",
        "LCNG_CHARGING_STATION": "LCNG 충전소",
        "HYDROGEN_CHARGING_STATION": "수소 충전소",
    },
    "business_status": {
        "ACTIVE_SOURCE_LISTED": "운영중",
        "READY": "확인 대기",
        "OPEN": "확인 필요",
        "IN_PROGRESS": "처리 중",
        "RESOLVED": "처리 완료",
    },
    "provider": {
        "OPINET": "오피넷",
        "KGS": "한국가스안전공사",
        "HUB": "건축HUB",
    },
}

CHARGING_SITE_TYPES = (
    "LPG_CHARGING_STATION",
    "CNG_CHARGING_STATION",
    "LNG_CHARGING_STATION",
    "LCNG_CHARGING_STATION",
    "HYDROGEN_CHARGING_STATION",
)

REVIEW_STATUSES = {"OPEN", "IN_PROGRESS", "RESOLVED", "REJECTED"}
ROLE_LEVELS = {"VIEWER": 10, "EXPORTER": 20, "OPERATOR": 30, "AUDITOR": 40, "ADMIN": 50}
EXPORT_DEFAULT_LIMIT = 5000
EXPORT_DAILY_DOWNLOAD_LIMIT = 20
EXPORT_DAILY_ROW_LIMIT = 50000
DEFAULT_EXPORT_TERMS_VERSION = "export-20260603-v1"
DEFAULT_ALLOWED_CORS_ORIGINS = {
    "http://127.0.0.1:8055",
    "http://localhost:8055",
    "null",
}

DB_CONNECT_LOCK = threading.RLock()
