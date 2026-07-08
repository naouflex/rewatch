import pytest

from rewatch.assistant import dashboard_builder
from rewatch.assistant.dashboard_builder import (
    DashboardBuildError,
    build_dashboard_from_spec,
    create_query_with_visualizations,
    refresh_queries_and_wait,
    resolve_visualization_spec,
)


class FakeApi:
    """Simulates the Rewatch REST API for builder tests.

    ``results_by_query`` maps a substring of query text to (columns, rows);
    queries matching no entry fail with an error.
    """

    def __init__(self, results_by_query=None):
        self.results_by_query = results_by_query or {}
        self.calls = []
        self.queries = {}
        self.visualizations = {}
        self.widgets = {}
        self.dashboards = {}
        self._next_id = {"query": 100, "viz": 200, "widget": 300, "dashboard": 9, "result": 500}
        self.published_queries = set()
        self.refreshed_queries = []

    def _new_id(self, kind):
        self._next_id[kind] += 1
        return self._next_id[kind]

    def _result_for(self, query_text):
        for fragment, (columns, rows) in self.results_by_query.items():
            if fragment in query_text:
                return columns, rows
        raise RuntimeError(f"query failed: no fake result for {query_text!r}")

    def __call__(self, method, path, *, params=None, body=None):
        self.calls.append((method, path, body))

        if method == "POST" and path == "/api/query_results":
            columns, rows = self._result_for(body["query"])
            return {
                "query_result": {
                    "id": self._new_id("result"),
                    "data": {"columns": [{"name": c} for c in columns], "rows": rows},
                }
            }

        if method == "POST" and path == "/api/queries":
            query_id = self._new_id("query")
            self.queries[query_id] = dict(body, id=query_id, version=1)
            return {"id": query_id, "version": 1, "name": body["name"]}

        if method == "POST" and path.startswith("/api/queries/") and path.endswith("/refresh"):
            query_id = int(path.split("/")[3])
            self.refreshed_queries.append(query_id)
            return {
                "job": {
                    "id": f"job-{query_id}",
                    "status": 3,
                    "query_result_id": self._new_id("result"),
                }
            }

        if method == "POST" and path.startswith("/api/queries/"):
            query_id = int(path.split("/")[3])
            if body.get("is_draft") is False:
                self.published_queries.add(query_id)
            return {"id": query_id, **body}

        if method == "POST" and path == "/api/visualizations":
            viz_id = self._new_id("viz")
            self.visualizations[viz_id] = dict(body, id=viz_id)
            return {"id": viz_id, **body}

        if method == "POST" and path == "/api/dashboards":
            dashboard_id = self._new_id("dashboard")
            self.dashboards[dashboard_id] = {
                "id": dashboard_id,
                "name": body["name"],
                "slug": body["name"].lower().replace(" ", "-"),
                "version": 1,
                "is_draft": True,
                "widgets": [],
            }
            return dict(self.dashboards[dashboard_id])

        if method == "POST" and path.startswith("/api/dashboards/"):
            dashboard_id = int(path.split("/")[3])
            self.dashboards[dashboard_id].update({k: v for k, v in body.items() if k != "version"})
            return dict(self.dashboards[dashboard_id])

        if method == "POST" and path == "/api/widgets":
            widget_id = self._new_id("widget")
            widget = dict(body, id=widget_id)
            self.widgets[widget_id] = widget
            self.dashboards[body["dashboard_id"]]["widgets"].append(widget)
            return widget

        if method == "GET" and path.startswith("/api/dashboards/"):
            dashboard_id = int(path.split("/")[3])
            return dict(self.dashboards[dashboard_id])

        if method == "GET" and path == "/api/data_sources":
            return [
                {"id": 1, "name": "Query Results", "type": "results"},
                {"id": 10, "name": "DefiLlama", "type": "defillama"},
            ]

        raise AssertionError(f"Unexpected API call: {method} {path}")


TVL_RESULT = (["datetime", "tvl"], [{"datetime": "2026-01-01", "tvl": 100.0}, {"datetime": "2026-01-02", "tvl": 110.0}])
SUMMARY_RESULT = (["total", "avg_score"], [{"total": 42, "avg_score": 7.5}])


def test_build_dashboard_from_spec_full_flow():
    api = FakeApi(
        results_by_query={
            "endpoint: tvl": TVL_RESULT,
            "SELECT total": SUMMARY_RESULT,
            "cached_query_": (["name", "tvl_b"], [{"name": "Lido", "tvl_b": 15.9}]),
        }
    )
    result = build_dashboard_from_spec(
        api,
        name="Test Dashboard",
        queries=[
            {
                "key": "tvl",
                "name": "TVL History",
                "data_source_id": 10,
                "query": "endpoint: tvl",
                "visualizations": [
                    {"type": "CHART", "name": "TVL Chart", "chart_type": "area",
                     "column_mapping": {"datetime": "x", "tvl": "y"}},
                ],
            },
            {
                "name": "Summary",
                "data_source_id": 10,
                "query": "SELECT total",
                "visualizations": [
                    {"type": "COUNTER", "name": "Total", "counter_column": "total"},
                    {"type": "COUNTER", "name": "Avg Score", "counter_column": "avg_score"},
                ],
            },
        ],
        derived=[
            {
                "name": "Top Entries",
                "query": "SELECT name, tvl_b FROM {{cached_query.tvl}} ORDER BY tvl_b DESC",
                "visualizations": [{"type": "TABLE", "name": "Top Table"}],
            }
        ],
        widgets=[
            {"text": "# Test Dashboard"},
            {"visualization": "Total"},
            {"visualization": "Avg Score"},
            {"visualization": "TVL Chart", "role": "full"},
            {"visualization": "Top Table"},
        ],
    )

    assert result["dashboard_id"] in api.dashboards
    assert len(result["queries"]) == 3
    assert result["warnings"] == []
    # Base queries were refreshed before the derived phase.
    base_ids = [q["query_id"] for q in result["queries"][:2]]
    assert set(base_ids) <= set(api.refreshed_queries)
    # cached_query placeholder was substituted with the real query id.
    tvl_id = result["queries"][0]["query_id"]
    derived_body = next(q for q in api.queries.values() if q["name"] == "Top Entries")
    assert f"cached_query_{tvl_id}" in derived_body["query"]
    # All queries were published.
    assert set(api.published_queries) == {q["query_id"] for q in result["queries"]}
    # Dashboard was published.
    assert api.dashboards[result["dashboard_id"]]["is_draft"] is False
    # 5 widgets created with positions.
    assert len(result["widgets"]) == 5
    assert all(w["position"] for w in result["widgets"])


def test_build_dashboard_fails_fast_on_bad_query():
    api = FakeApi(results_by_query={"good query": TVL_RESULT})
    with pytest.raises(DashboardBuildError, match="nothing was created"):
        build_dashboard_from_spec(
            api,
            name="Broken",
            queries=[
                {"name": "OK", "data_source_id": 10, "query": "good query"},
                {"name": "Bad", "data_source_id": 10, "query": "broken query"},
            ],
            widgets=[],
        )
    assert not api.queries
    assert not api.dashboards


def test_build_dashboard_counters_pack_into_kpi_row():
    api = FakeApi(results_by_query={"SELECT total": SUMMARY_RESULT})
    result = build_dashboard_from_spec(
        api,
        name="KPIs",
        queries=[
            {
                "name": "Summary",
                "data_source_id": 10,
                "query": "SELECT total",
                "visualizations": [
                    {"type": "COUNTER", "name": f"KPI {i}", "counter_column": "total"} for i in range(4)
                ],
            }
        ],
        widgets=[{"visualization": f"KPI {i}"} for i in range(4)],
    )
    positions = [w["position"] for w in result["widgets"]]
    # Four 3-wide counters share one row.
    assert [p["col"] for p in positions] == [0, 3, 6, 9]
    assert len({p["row"] for p in positions}) == 1
    assert all(p["sizeX"] == 3 and p["sizeY"] == 8 for p in positions)


def test_build_dashboard_skips_unknown_widget_refs_with_warning():
    api = FakeApi(results_by_query={"SELECT total": SUMMARY_RESULT})
    result = build_dashboard_from_spec(
        api,
        name="Warned",
        queries=[
            {
                "name": "Summary",
                "data_source_id": 10,
                "query": "SELECT total",
                "visualizations": [{"type": "COUNTER", "name": "Total", "counter_column": "total"}],
            }
        ],
        widgets=[{"visualization": "Total"}, {"visualization": "Nope"}],
    )
    assert len(result["widgets"]) == 1
    assert any("Nope" in w for w in result["warnings"])


def test_create_query_with_visualizations_creates_all():
    api = FakeApi(results_by_query={"SELECT total": SUMMARY_RESULT})
    result = create_query_with_visualizations(
        api,
        name="Multi",
        query="SELECT total",
        data_source_id=10,
        visualizations=[
            {"type": "COUNTER", "name": "Total", "counter_column": "total"},
            {"type": "COUNTER", "name": "Avg", "counter_column": "avg_score"},
            {"type": "TABLE", "name": "Raw"},
        ],
    )
    assert result["columns"] == ["total", "avg_score"]
    assert len(result["visualizations"]) == 3
    assert result["query_id"] in api.published_queries


def test_create_query_with_visualizations_rejects_empty_result():
    api = FakeApi(results_by_query={"SELECT nothing": ([], [])})
    with pytest.raises(DashboardBuildError, match="no columns"):
        create_query_with_visualizations(
            api, name="Empty", query="SELECT nothing", data_source_id=10, visualizations=[]
        )
    assert not api.queries


def test_refresh_queries_and_wait_reports_failures():
    api = FakeApi()

    def flaky(method, path, *, params=None, body=None):
        if "42" in path:
            raise RuntimeError("boom")
        return api(method, path, params=params, body=body)

    api.dashboards[1] = {"id": 1, "widgets": []}
    result = refresh_queries_and_wait(flaky, [101, 42])
    assert [r["query_id"] for r in result["refreshed"]] == [101]
    assert result["failures"][0]["query_id"] == 42


def test_resolve_visualization_spec_counter_maps_column():
    viz_type, name, options, corrections = resolve_visualization_spec(
        {"type": "COUNTER", "name": "Total", "counter_column": "Total"},
        ["total", "avg_score"],
        [{"total": 42, "avg_score": 7.5}],
    )
    assert viz_type == "COUNTER"
    assert options["counterColName"] == "total"


def test_resolve_visualization_spec_chart_fixes_bad_mapping():
    _, _, options, corrections = resolve_visualization_spec(
        {"type": "CHART", "name": "C", "chart_type": "line", "column_mapping": {"timestamp": "x", "value": "y"}},
        ["datetime", "tvl"],
        [{"datetime": "2026-01-01", "tvl": 1.0}],
    )
    assert options["columnMapping"]["datetime"] == "x"
    assert options["columnMapping"]["tvl"] == "y"
    assert corrections


def test_substitute_cached_query_refs_unknown_key():
    with pytest.raises(DashboardBuildError, match="unknown base query key"):
        dashboard_builder._substitute_cached_query_refs("SELECT * FROM {{cached_query.missing}}", {"tvl": 5})
