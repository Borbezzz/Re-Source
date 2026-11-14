"""Root test configuration: shared domain fixtures. Helpers live in tests/domain_helpers.py."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import pytest  # noqa: E402

from domain_helpers import *  # noqa: E402,F401,F403
from domain_helpers import Catalog, load_catalog  # noqa: E402


@pytest.fixture(scope="session")
def cat() -> Catalog:
    return load_catalog()
