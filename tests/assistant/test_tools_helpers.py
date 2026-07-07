"""Tests for assistant tool validation helpers."""

import pytest

from rewatch.assistant.tools import _require_catalog_result, _require_widget_content


def test_require_catalog_result_passes_through_success():
    payload = {"type": "pg", "name": "PostgreSQL"}
    assert _require_catalog_result(payload) is payload


def test_require_catalog_result_raises_on_error_dict():
    with pytest.raises(RuntimeError, match="Query runner type failed"):
        _require_catalog_result(
            {"error": "Unknown type 'foo'.", "known_types": ["pg", "mysql"]},
            "Query runner type",
        )


def test_require_widget_content_requires_one_of_visualization_or_text():
    with pytest.raises(RuntimeError, match="visualization_id"):
        _require_widget_content(None, None)

    _require_widget_content(42, None)
    _require_widget_content(None, "Hello")
