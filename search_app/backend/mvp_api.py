from __future__ import annotations

# Backward-compatible entry point.
# Usage: python -m backend.mvp_api  OR  python backend/mvp_api.py
from .server import main

if __name__ == "__main__":
    main()
