"""Shared plumbing for the create_*_dashboard.py scripts.

Exposes the ``rewatch.assistant.dashboard_builder`` module (importable even
without the Flask app dependencies) and a REST ``request`` callable
authenticated with the workspace API key.
"""

from __future__ import annotations

import json
import sys
import types
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://rewatch.naoufel.io"


def _read_api_key() -> str:
    env_text = (REPO_ROOT / ".env").read_text()
    return env_text.split("REWATCH_API_KEY=")[1].split("\n")[0].strip()


def _ensure_rewatch_importable() -> None:
    """Allow ``rewatch.assistant.*`` imports without Flask installed."""
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    if "rewatch" in sys.modules:
        return
    try:
        import rewatch  # noqa: F401
    except Exception:
        stub = types.ModuleType("rewatch")
        stub.__path__ = [str(REPO_ROOT / "rewatch")]
        sys.modules["rewatch"] = stub


_ensure_rewatch_importable()

from rewatch.assistant import dashboard_builder  # noqa: E402

_API_KEY = _read_api_key()


def request(method: str, path: str, *, params: dict | None = None, body: dict | None = None) -> dict:
    """REST call matching the dashboard_builder RequestFn signature."""
    url = f"{BASE_URL}{path}"
    if params:
        from urllib.parse import urlencode

        url += "?" + urlencode(params)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method.upper(),
        headers={"Authorization": f"Key {_API_KEY}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw else {}


def build_and_report(**spec) -> dict:
    """Run build_dashboard_from_spec and print a short summary."""
    result = dashboard_builder.build_dashboard_from_spec(request, **spec)
    print(f"\nDashboard: {BASE_URL}{result['url_path']}")
    print(f"Queries: {[q['query_id'] for q in result['queries']]}")
    print(f"Widgets: {len(result['widgets'])}")
    for warning in result["warnings"]:
        print(f"WARNING: {warning}")
    return result
