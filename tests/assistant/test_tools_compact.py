"""Tests for smarter tool result compaction."""

import json

from rewatch.assistant.tools import _compact, _shrink_payload


def test_compact_preserves_columns_when_truncating_rows():
    payload = {
        "columns": ["date", "value"],
        "validation": {"status": "ok"},
        "rows": [{"date": f"2024-01-{i:02d}", "value": i} for i in range(1, 100)],
        "query_id": 12,
    }
    shrunk = _shrink_payload(payload)
    assert shrunk["columns"] == ["date", "value"]
    assert shrunk["query_id"] == 12
    assert len(shrunk["rows"]) < len(payload["rows"])

    text = _compact(payload)
    parsed = json.loads(text)
    assert parsed["columns"] == ["date", "value"]
    assert parsed["query_id"] == 12


def test_shrink_schema_keeps_column_names():
    schema = {
        "schema": [
            {
                "name": "users",
                "columns": [{"name": f"col_{i}"} for i in range(300)],
            }
        ]
    }
    shrunk = _shrink_payload(schema)
    table = shrunk["schema"][0]
    assert table["columns"][0] == "col_0"
    assert table.get("column_count") == 300
