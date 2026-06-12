# MVP API

This backend is a no-dependency MVP API for the current local development environment.

The planned production stack remains FastAPI, but the bundled Python runtime currently has `duckdb` and `pydantic` while `fastapi` and `uvicorn` are not installed. This server uses Python's standard library so the project can be run immediately.

Run:

```powershell
$env:LOAN4U_BUILDING_REGISTER_DB='D:\hub_building_register\db\hub_building_register.duckdb'
& 'C:\Users\eungk\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' backend\mvp_api.py
```

Default URL:

```text
http://127.0.0.1:8055
```

Implemented endpoints:

- `GET /api/healthz`
- `GET /api/datasets/catalog`
- `GET /api/columns/service-fields`
- `GET /api/quality/checks`
- `GET /api/stations/search`
- `GET /api/stations/{station_id}`

`/api/stations/*` returns a controlled `STATION_MART_NOT_BUILT` error until station source tables and `station_search_mart` are created.
