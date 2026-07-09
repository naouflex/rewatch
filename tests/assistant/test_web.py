"""Tests for assistant web search and public source discovery."""

import json
from unittest.mock import MagicMock, patch

from rewatch.assistant import web as web_tools


DDG_HTML_SAMPLE = """
<a class="result__a" href="https://duckduckgo.com/l/?uddg=https%3A%2F%2Fapi.example.com%2Fdata.json">Example API</a>
<a class="result__snippet">Public JSON API for train delays</a>
<a class="result__a" href="https://example.com/docs">API Docs</a>
"""

DDG_LITE_SAMPLE = """
<a class="result-link" href="https://duckduckgo.com/l/?uddg=https%3A%2F%2Fdata.example.org%2Fapi">Open Data API</a>
"""

OPENAPI_JSON = json.dumps(
    {
        "openapi": "3.0.0",
        "info": {"title": "Trains"},
        "paths": {"/delays": {"get": {"summary": "List delays"}}},
    }
)

DATA_JSON = json.dumps([{"station": "Paris", "delay_minutes": 5}, {"station": "Lyon", "delay_minutes": 0}])


def test_augment_search_query_api_suffix():
    assert "API documentation" in web_tools._augment_search_query("SNCF trains", search_type="api")


def test_augment_search_query_site_filter():
    query = web_tools._augment_search_query("weather API", site="data.gouv.fr")
    assert query.startswith("site:data.gouv.fr")


def test_parse_ddg_html_results_unwraps_redirects():
    results = web_tools._parse_ddg_html_results(DDG_HTML_SAMPLE, max_results=5)
    assert len(results) >= 1
    assert results[0]["url"] == "https://api.example.com/data.json"
    assert "Example API" in results[0]["title"]


def test_parse_ddg_lite_results():
    results = web_tools._parse_ddg_lite_results(DDG_LITE_SAMPLE, max_results=3)
    assert len(results) == 1
    assert results[0]["url"] == "https://data.example.org/api"


def test_score_search_result_prefers_api_urls():
    api_result = {"title": "API", "url": "https://service.example.com/api/v1/trains.json", "snippet": ""}
    blog_result = {"title": "Blog", "url": "https://medium.com/sncf-trains", "snippet": "opinion"}
    assert web_tools._score_search_result(api_result, "SNCF trains", "json") > web_tools._score_search_result(
        blog_result, "SNCF trains", "json"
    )


def test_extract_candidate_endpoints_from_snippets():
    results = [
        {
            "title": "Docs",
            "url": "https://docs.example.com",
            "snippet": "Download data at https://api.example.com/v1/stations.json for live results.",
        }
    ]
    endpoints = web_tools._extract_candidate_endpoints(results)
    assert endpoints
    assert endpoints[0]["url"] == "https://api.example.com/v1/stations.json"


@patch("rewatch.assistant.web.requests_session")
def test_web_search_falls_back_to_lite(mock_session):
    html_response = MagicMock(status_code=200, text="<html></html>")
    lite_response = MagicMock(status_code=200, text=DDG_LITE_SAMPLE)
    mock_session.post.side_effect = [html_response, lite_response]

    result = web_tools.web_search("open data trains", max_results=3, search_type="api")

    assert result["result_count"] == 1
    assert result["results"][0]["url"] == "https://data.example.org/api"
    assert "duckduckgo_lite" in result["backends_tried"]


@patch("rewatch.assistant.web.requests_session")
def test_discover_public_sources_ranks_results(mock_session):
    html_response = MagicMock(status_code=200, text=DDG_HTML_SAMPLE)
    mock_session.post.return_value = html_response
    mock_session.get.return_value = MagicMock(status_code=200, json=lambda: {})

    result = web_tools.discover_public_sources("SNCF train delays", data_kind="json", max_results=5)

    assert result["topic"] == "SNCF train delays"
    assert result["result_count"] >= 1
    assert result["search_queries"]
    assert "recommended_workflow" in result


@patch("rewatch.assistant.web.requests_session")
def test_fetch_url_detects_json(mock_session):
    response = MagicMock()
    response.status_code = 200
    response.headers = {"Content-Type": "application/json"}
    response.encoding = "utf-8"
    response.iter_content.return_value = [DATA_JSON.encode("utf-8")]
    mock_session.get.return_value = response

    result = web_tools.fetch_url("https://api.example.com/trains.json")

    assert result["format"] == "json"
    assert result["is_valid_json"] is True
    assert "json_preview" in result


@patch("rewatch.assistant.web.requests_session")
def test_fetch_url_detects_openapi(mock_session):
    response = MagicMock()
    response.status_code = 200
    response.headers = {"Content-Type": "application/json"}
    response.encoding = "utf-8"
    response.iter_content.return_value = [OPENAPI_JSON.encode("utf-8")]
    mock_session.get.return_value = response

    result = web_tools.fetch_url("https://api.example.com/openapi.json")

    assert result["openapi_detected"] is True
    assert "paths" in result["json_preview"]


@patch("rewatch.assistant.web.requests_session")
def test_fetch_url_extracts_api_urls_from_html(mock_session):
    html = """
    <html><head><title>Train API Docs</title></head><body>
    <p>Base URL: https://api.example.com/v2/</p>
    <a href="https://api.example.com/v2/stations.json">stations</a>
    </body></html>
    """
    response = MagicMock()
    response.status_code = 200
    response.headers = {"Content-Type": "text/html"}
    response.encoding = "utf-8"
    response.iter_content.return_value = [html.encode("utf-8")]
    mock_session.get.return_value = response

    result = web_tools.fetch_url("https://docs.example.com/trains")

    assert result["format"] == "html"
    assert "https://api.example.com/v2/stations.json" in result["candidate_api_urls"]
