"""Shared VWorld paths; resolve configuration without touching the drive."""

try:
    from .data_locator import configured_vworld_path
except ImportError:
    from data_locator import configured_vworld_path

DATA_ROOT = configured_vworld_path()
DB_PATH = DATA_ROOT / "db" / "vworld_wfs_multi_layer.sqlite"
LEDGER_PATH = DATA_ROOT / "ledger"
