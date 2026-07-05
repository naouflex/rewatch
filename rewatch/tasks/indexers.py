import datetime
import json

from rewatch import models, utils
from rewatch.query_runner import get_query_runner
from rewatch.worker import get_job_logger, job

logger = get_job_logger(__name__)


def _column_type_for(sample_value):
    if isinstance(sample_value, bool):
        return "BOOLEAN"
    if isinstance(sample_value, int):
        return "INTEGER"
    if isinstance(sample_value, float):
        return "DOUBLE PRECISION"
    if isinstance(sample_value, datetime.datetime):
        return "TIMESTAMP"
    return "TEXT"


def _format_sql_value(val):
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, datetime.datetime):
        return "'{0}'".format(val.isoformat())
    return "'{0}'".format(str(val).replace("'", "''"))


def index_query_results(indexer, query_result):
    """Copy ``query_result.data`` rows into the indexer's target data source.

    Returns ``True`` on success, ``False`` on a handled error. The function
    runs synchronously; it is invoked by ``check_indexers_for_query`` after
    a query finishes executing.
    """
    logger.info("Starting indexing process for indexer %d", indexer.id)

    try:
        options = indexer.options or {}
        if isinstance(options, str):
            options = json.loads(options)

        # Resolve the target data source. The model's `data_source_id` foreign
        # key is the source of truth, but to stay compatible with the
        # inverse-watch payload we also accept `options.data_source_id` as a
        # fallback override (useful for ad-hoc edits via the API).
        data_source_id = options.get("data_source_id") or indexer.data_source_id
        if not data_source_id:
            logger.error("Indexer %d has no data source configured", indexer.id)
            return False

        data_source = models.DataSource.query.get(data_source_id)
        if data_source is None:
            logger.error("Indexer %d points at missing data source %s", indexer.id, data_source_id)
            return False

        query_runner = get_query_runner(data_source.type, data_source.options)
        if not query_runner:
            logger.error("No query runner registered for data source type %s", data_source.type)
            return False

        if isinstance(query_result.data, dict):
            data = query_result.data
        else:
            data = json.loads(query_result.data)

        rows = data.get("rows", []) or []
        logger.info("Found %d rows to index for indexer %d", len(rows), indexer.id)
        if not rows:
            return True

        target_table = options.get("target_table") or "indexed_data_{0}".format(indexer.id)

        # Optionally backfill a timestamp column with `now()` for rows that
        # don't already include one.
        timestamp_field = options.get("timestamp_field")
        if timestamp_field:
            for row in rows:
                if timestamp_field not in row or row[timestamp_field] is None:
                    row[timestamp_field] = utils.utcnow()

        columns = list(rows[0].keys())
        column_defs = [
            '"{name}" {ctype}'.format(name=col, ctype=_column_type_for(rows[0][col]))
            for col in columns
        ]
        quoted_columns = ['"{0}"'.format(col) for col in columns]

        create_sql = "CREATE TABLE IF NOT EXISTS {table} ({cols})".format(
            table=target_table, cols=", ".join(column_defs)
        )
        logger.info("Creating target table if needed: %s", create_sql)
        query_runner.run_query(create_sql, None)

        strategy = options.get("insert_strategy", "append")
        if strategy not in models.Indexer.INSERT_STRATEGIES:
            logger.warning(
                "Indexer %d unknown insert_strategy %r, falling back to 'append'",
                indexer.id,
                strategy,
            )
            strategy = "append"

        if strategy == "overwrite":
            logger.info("Truncating %s before insert (overwrite strategy)", target_table)
            query_runner.run_query("DELETE FROM {table}".format(table=target_table), None)

        for i, row in enumerate(rows):
            formatted_values = [_format_sql_value(row.get(col)) for col in columns]
            insert_sql = "INSERT INTO {table} ({cols}) VALUES ({vals})".format(
                table=target_table,
                cols=", ".join(quoted_columns),
                vals=", ".join(formatted_values),
            )
            if i == 0:
                logger.info("Sample insert: %s", insert_sql)
            query_runner.run_query(insert_sql, None)

        # Optional dedupe pass — only safe when the target table has an `id`
        # column we can use as a tie-breaker.
        if options.get("remove_duplicates"):
            if "id" in columns:
                quoted_partition = ['"{0}"'.format(col) for col in columns]
                dedupe_sql = (
                    "DELETE FROM {table} WHERE id IN ("
                    "SELECT id FROM ("
                    "SELECT id, ROW_NUMBER() OVER (PARTITION BY {part} ORDER BY id) AS rn "
                    "FROM {table}) t WHERE rn > 1)"
                ).format(table=target_table, part=", ".join(quoted_partition))
                logger.info("Removing duplicates from %s", target_table)
                query_runner.run_query(dedupe_sql, None)
            else:
                logger.warning(
                    "Indexer %d requested remove_duplicates but target has no `id` column; skipping",
                    indexer.id,
                )

        indexer.last_triggered_at = utils.utcnow()
        models.db.session.add(indexer)
        models.db.session.commit()

        logger.info("Successfully indexed %d rows into %s", len(rows), target_table)
        return True

    except Exception:
        logger.exception("Indexer %d failed", indexer.id)
        models.db.session.rollback()
        return False


@job("default", timeout=300)
def check_indexers_for_query(query_id):
    """RQ entry point: run all non-archived indexers tied to ``query_id``."""
    logger.info("Checking query %d for indexers", query_id)

    query = models.Query.query.get(query_id)
    if not query:
        logger.error("Query %d not found", query_id)
        return

    latest_result = (
        models.QueryResult.query.filter(
            models.QueryResult.query_hash == query.query_hash,
            models.QueryResult.data_source_id == query.data_source_id,
        )
        .order_by(models.QueryResult.retrieved_at.desc())
        .first()
    )

    if not latest_result:
        logger.warning("No results found for query %d", query_id)
        return

    for indexer in query.indexers:
        if indexer.is_archived:
            continue
        logger.info("Running indexer %d for query %d", indexer.id, query_id)
        index_query_results(indexer, latest_result)
