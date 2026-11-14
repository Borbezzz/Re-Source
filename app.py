"""Vercel FastAPI entrypoint. Public traffic uses /api/v1; static UI is its own service."""
import os
import sys
from pathlib import Path

os.environ.setdefault("PYTHON_DOTENV_DISABLED", "1")
sys.path.insert(0, str(Path(__file__).parent / "backend"))
from recovery.api.app import app  # noqa: E402,F401
