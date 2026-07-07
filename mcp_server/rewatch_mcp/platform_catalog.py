"""Load platform catalog (query runners, viz types) without importing Flask."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_CATALOG_PATH = _REPO_ROOT / "rewatch" / "assistant" / "catalog.py"

platform_catalog: Optional[ModuleType] = None

if _CATALOG_PATH.is_file():
    spec = importlib.util.spec_from_file_location("rewatch_platform_catalog", _CATALOG_PATH)
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        platform_catalog = mod

__all__ = ["platform_catalog"]
