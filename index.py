"""Vercel entrypoint for the repository root.

The FastAPI app stays in backend/app/main.py. This file only puts that
package on the import path and exposes the existing ``app`` instance.
"""

from __future__ import annotations

import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent / "backend"
_backend_path = str(_BACKEND)
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

from app.main import app  # noqa: E402

__all__ = ["app"]
