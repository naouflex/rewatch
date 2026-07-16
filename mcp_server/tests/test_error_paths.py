"""Error-path and read-only-mode tests for the MCP server (no live API).

Run from mcp_server/: uv run --group dev pytest tests/
"""

import json

import httpx
import pytest
from rewatch_mcp import server


@pytest.fixture(autouse=True)
def writable_mode(monkeypatch):
    monkeypatch.setattr(server, "READ_ONLY", False)


@pytest.fixture
def read_only_mode(monkeypatch):
    monkeypatch.setattr(server, "READ_ONLY", True)


def _client_with_handler(handler):
    return httpx.Client(base_url="http://testserver", transport=httpx.MockTransport(handler))


# ---------------------------------------------------------------------------
# _request error paths
# ---------------------------------------------------------------------------


def test_request_http_error_includes_method_path_and_body(monkeypatch):
    monkeypatch.setattr(
        server, "_client", _client_with_handler(lambda req: httpx.Response(500, text="boom detail"))
    )
    with pytest.raises(RuntimeError) as exc:
        server._request("GET", "/api/queries/1")
    assert "GET /api/queries/1" in str(exc.value)
    assert "500" in str(exc.value)
    assert "boom detail" in str(exc.value)


def test_request_empty_body_returns_status_code(monkeypatch):
    monkeypatch.setattr(server, "_client", _client_with_handler(lambda req: httpx.Response(204)))
    assert server._request("DELETE", "/api/widgets/1") == {"status_code": 204}


def test_request_non_json_body_returns_text(monkeypatch):
    monkeypatch.setattr(
        server, "_client", _client_with_handler(lambda req: httpx.Response(200, text="not json"))
    )
    result = server._request("GET", "/api/thing")
    assert result["status_code"] == 200
    assert result["text"] == "not json"


def test_request_transport_error_is_wrapped_with_context(monkeypatch):
    def handler(req):
        raise httpx.ConnectError("All connection attempts failed")

    monkeypatch.setattr(server, "_client", _client_with_handler(handler))
    with pytest.raises(RuntimeError) as exc:
        server._request("GET", "/api/queries/1")
    message = str(exc.value)
    assert "GET /api/queries/1" in message
    assert server.BASE_URL in message


def test_request_adds_leading_slash(monkeypatch):
    seen = {}

    def handler(req):
        seen["path"] = req.url.path
        return httpx.Response(200, json={})

    monkeypatch.setattr(server, "_client", _client_with_handler(handler))
    server._request("GET", "api/queries")
    assert seen["path"] == "/api/queries"


# ---------------------------------------------------------------------------
# _poll_job
# ---------------------------------------------------------------------------


def test_poll_job_returns_int_result_id():
    job = {"id": "j1", "status": server.JOB_FINISHED, "query_result_id": "42"}
    assert server._poll_job(job, 5) == 42


def test_poll_job_rejects_none_string_result():
    job = {"id": "j1", "status": server.JOB_FINISHED, "result": "None"}
    with pytest.raises(RuntimeError, match="without a query result id"):
        server._poll_job(job, 5)


def test_poll_job_failure_surfaces_error():
    job = {"id": "j1", "status": server.JOB_FAILED, "error": "syntax error near FROM"}
    with pytest.raises(RuntimeError, match="syntax error near FROM"):
        server._poll_job(job, 5)


def test_poll_job_checks_status_before_deadline():
    # Even with a fully exhausted budget, a finished job must not be reported
    # as a timeout.
    job = {"id": "j1", "status": server.JOB_FINISHED, "query_result_id": 7}
    assert server._poll_job(job, 0) == 7


def test_poll_job_pending_job_times_out(monkeypatch):
    job = {"id": "j1", "status": 1}
    with pytest.raises(RuntimeError, match="timed out"):
        server._poll_job(job, 0)


def test_poll_job_rejects_job_without_id():
    with pytest.raises(RuntimeError, match="no id"):
        server._poll_job({"status": 1}, 5)


# ---------------------------------------------------------------------------
# Read-only mode
# ---------------------------------------------------------------------------


def test_read_only_blocks_write_tools(read_only_mode):
    with pytest.raises(RuntimeError, match="read-only"):
        server.create_dashboard("Nope")
    with pytest.raises(RuntimeError, match="read-only"):
        server.delete_alert(1)
    with pytest.raises(RuntimeError, match="read-only"):
        server.archive_query(1)


def test_read_only_blocks_non_get_call_api(read_only_mode):
    with pytest.raises(RuntimeError, match="read-only"):
        server.call_api("POST", "/api/queries", body={"name": "x"})
    with pytest.raises(RuntimeError, match="read-only"):
        server.call_api("DELETE", "/api/users/1")


def test_read_only_allows_get_call_api(read_only_mode, monkeypatch):
    monkeypatch.setattr(server, "_request", lambda *a, **k: {"ok": True})
    assert json.loads(server.call_api("GET", "/api/queries/1")) == {"ok": True}


def test_read_only_blocks_adhoc_query_text(read_only_mode):
    with pytest.raises(RuntimeError, match="ad-hoc query_text"):
        server.run_query(query_text="DROP TABLE users", data_source_id=1)


def test_read_only_allows_saved_query_run(read_only_mode, monkeypatch):
    def fake_request(method, path, *, params=None, body=None):
        assert path == "/api/queries/5/results"
        return {"query_result": {"id": 1, "data": {"columns": [{"name": "n"}], "rows": [{"n": 1}]}}}

    monkeypatch.setattr(server, "_request", fake_request)
    payload = json.loads(server.run_query(query_id=5))
    assert payload["columns"] == ["n"]


def test_read_only_get_query_skips_execution(read_only_mode, monkeypatch):
    calls = []

    def fake_request(method, path, *, params=None, body=None):
        calls.append((method, path))
        return {"id": 5, "name": "Q", "query": "SELECT 1"}

    monkeypatch.setattr(server, "_request", fake_request)
    payload = json.loads(server.get_query(5))
    assert payload["validation"]["status"] == "skipped"
    assert calls == [("GET", "/api/queries/5")]


# ---------------------------------------------------------------------------
# call_api guards
# ---------------------------------------------------------------------------


def test_call_api_rejects_template_placeholders():
    with pytest.raises(RuntimeError, match="template placeholder"):
        server.call_api("GET", "/api/queries/{query_id}")


# ---------------------------------------------------------------------------
# update_alert merges options
# ---------------------------------------------------------------------------


def test_update_alert_merges_partial_options(monkeypatch):
    posted = {}

    def fake_request(method, path, *, params=None, body=None):
        if method == "GET" and path == "/api/alerts/3":
            return {"id": 3, "options": {"column": "cnt", "op": ">", "value": 5, "selector": "first"}}
        if method == "POST" and path == "/api/alerts/3":
            posted.update(body or {})
            return {"id": 3, **(body or {})}
        raise AssertionError(f"Unexpected request: {method} {path}")

    monkeypatch.setattr(server, "_request", fake_request)
    server.update_alert(3, options={"muted": True})
    assert posted["options"] == {
        "column": "cnt",
        "op": ">",
        "value": 5,
        "selector": "first",
        "muted": True,
    }


def test_update_alert_rejects_merged_options_without_column(monkeypatch):
    def fake_request(method, path, *, params=None, body=None):
        if method == "GET" and path == "/api/alerts/3":
            return {"id": 3, "options": {"op": ">", "value": 5}}
        raise AssertionError(f"Unexpected request: {method} {path}")

    monkeypatch.setattr(server, "_request", fake_request)
    with pytest.raises(RuntimeError, match="no trigger column"):
        server.update_alert(3, options={"muted": True})


# ---------------------------------------------------------------------------
# create_alert partial subscription failure
# ---------------------------------------------------------------------------


def test_create_alert_reports_subscription_errors(monkeypatch):
    def fake_request(method, path, *, params=None, body=None):
        if method == "POST" and path == "/api/alerts":
            return {"id": 11, **(body or {})}
        if method == "POST" and path == "/api/alerts/11/subscriptions":
            if body["destination_id"] == 2:
                raise RuntimeError("destination 2 is gone")
            return {"id": 100 + body["destination_id"], "destination_id": body["destination_id"]}
        raise AssertionError(f"Unexpected request: {method} {path}")

    monkeypatch.setattr(server, "_request", fake_request)
    payload = json.loads(
        server.create_alert(
            name="High count",
            query_id=5,
            column="cnt",
            op=">",
            value=10,
            destination_ids=[1, 2],
            validate_column=False,
        )
    )
    assert payload["alert"]["id"] == 11
    assert len(payload["subscriptions"]) == 1
    assert payload["subscription_errors"] == [
        {"destination_id": 2, "error": "destination 2 is gone"}
    ]
    assert "do NOT create a new alert" in payload["note"]


# ---------------------------------------------------------------------------
# Output size cap
# ---------------------------------------------------------------------------


def test_compact_truncates_huge_payloads():
    huge = {"rows": ["x" * 1000] * 1000}
    out = server._compact(huge)
    assert len(out) < len(json.dumps(huge, indent=2)) + 500
    assert "truncated" in out
