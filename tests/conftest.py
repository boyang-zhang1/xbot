"""Pytest configuration for ensuring the src/ package is importable."""

from __future__ import annotations

import sys
from pathlib import Path


def _ensure_src_on_path() -> None:
    root = Path(__file__).resolve().parent.parent
    src = root / "src"
    src_str = str(src)
    if src.exists() and src_str not in sys.path:
        sys.path.insert(0, src_str)


_ensure_src_on_path()


def pytest_addoption(parser):  # pragma: no cover - pytest hook
    parser.addini("asyncio_mode", "Asyncio plugin compatibility stub")
