import re

from flask_restful import abort

from rewatch import models
from rewatch.query_runner import get_query_runner

TABLE_NAME_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)?$")
DEFAULT_PREVIEW_LIMIT = 25
MAX_PREVIEW_LIMIT = 100


def validate_target_table(table_name):
    if not table_name or not TABLE_NAME_PATTERN.match(table_name):
        abort(400, message="Invalid target table name.")


def resolve_target_table(indexer):
    options = indexer.options or {}
    return options.get("target_table") or "indexed_data_{0}".format(indexer.id)


def fetch_indexer_table_preview(indexer, limit=DEFAULT_PREVIEW_LIMIT):
    limit = min(max(int(limit or DEFAULT_PREVIEW_LIMIT), 1), MAX_PREVIEW_LIMIT)

    data_source_id = indexer.data_source_id
    if not data_source_id and indexer.options:
        data_source_id = indexer.options.get("data_source_id")

    if not data_source_id:
        abort(400, message="Indexer has no target data source configured.")

    data_source = models.DataSource.query.get(data_source_id)
    if data_source is None:
        abort(400, message="Target data source not found.")

    target_table = resolve_target_table(indexer)
    validate_target_table(target_table)

    query_runner = get_query_runner(data_source.type, data_source.options)
    if not query_runner:
        abort(400, message="Target data source type is not supported for table preview.")

    preview_query = "SELECT * FROM {table} LIMIT {limit}".format(table=target_table, limit=limit)
    if getattr(query_runner, "supports_auto_limit", False):
        preview_query = query_runner.apply_auto_limit(preview_query, True)

    data, error = query_runner.run_query(preview_query, None)
    if error:
        abort(400, message=error)

    rows = (data or {}).get("rows") or []
    columns = (data or {}).get("columns") or []

    if not columns and rows:
        columns = [{"name": key, "friendly_name": key, "type": "string"} for key in rows[0].keys()]

    return {
        "target_table": target_table,
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "limit": limit,
    }
