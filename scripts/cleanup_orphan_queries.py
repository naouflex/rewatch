#!/usr/bin/env python3
"""Permanently delete queries that are not used on any dashboard."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import psycopg2
import psycopg2.extras

REPO_ROOT = Path(__file__).resolve().parents[1]
DB_URL = REPO_ROOT.joinpath(".env").read_text().split("REDASH_DATABASE_URL=")[1].split("\n")[0].strip()

CACHED_QUERY_RE = re.compile(r"cached_query_(\d+)")


def fetchall(cur, sql, params=None):
    cur.execute(sql, params or ())
    return cur.fetchall()


def expand_feed_queries(cur, query_ids: set[int]) -> set[int]:
    expanded = set(query_ids)
    pending = list(query_ids)
    while pending:
        batch = pending
        pending = []
        rows = fetchall(
            cur,
            "SELECT id, query FROM queries WHERE id = ANY(%s)",
            (batch,),
        )
        for row in rows:
            for match in CACHED_QUERY_RE.finditer(row["query"] or ""):
                feed_id = int(match.group(1))
                if feed_id not in expanded:
                    expanded.add(feed_id)
                    pending.append(feed_id)
    return expanded


def main() -> int:
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        on_dashboard = {
            row["query_id"]
            for row in fetchall(
                cur,
                """
                SELECT DISTINCT v.query_id
                FROM widgets w
                JOIN visualizations v ON v.id = w.visualization_id
                """,
            )
        }

        dashboard_query_ids = list(on_dashboard)
        feed_ids = expand_feed_queries(cur, set(on_dashboard))

        protected = set(feed_ids)
        for table, label in (
            ("alerts", "alert"),
            ("ml_models", "ml_model"),
            ("indexers", "indexer"),
        ):
            for row in fetchall(cur, f"SELECT DISTINCT query_id FROM {table}"):
                protected.add(row["query_id"])

        all_queries = {row["id"] for row in fetchall(cur, "SELECT id FROM queries")}
        query_ids_to_delete = sorted(all_queries - on_dashboard - protected)

        skipped = sorted((all_queries - on_dashboard) & protected - feed_ids)
        print(f"Keeping {len(on_dashboard)} dashboard queries and {len(feed_ids)} feed/base queries.")
        if skipped:
            print(f"Skipping {len(skipped)} orphan queries used elsewhere (alerts/models/indexers): {skipped}")

        print(f"\nQueries to delete ({len(query_ids_to_delete)}):")
        for qid in query_ids_to_delete:
            name = fetchall(cur, "SELECT name FROM queries WHERE id = %s", (qid,))
            print(f"  {qid}: {name[0]['name'] if name else '?'}")

        if not query_ids_to_delete:
            print("\nNothing to delete.")
            return 0

        viz_ids = [
            row["id"]
            for row in fetchall(
                cur,
                "SELECT id FROM visualizations WHERE query_id = ANY(%s)",
                (query_ids_to_delete,),
            )
        ]
        if viz_ids:
            cur.execute("DELETE FROM widgets WHERE visualization_id = ANY(%s)", (viz_ids,))
        cur.execute(
            "DELETE FROM favorites WHERE object_type = 'Query' AND object_id = ANY(%s)",
            (query_ids_to_delete,),
        )
        if viz_ids:
            cur.execute("DELETE FROM visualizations WHERE id = ANY(%s)", (viz_ids,))
        deleted_visualizations = len(viz_ids)

        result_ids = [
            row["latest_query_data_id"]
            for row in fetchall(
                cur,
                """
                SELECT latest_query_data_id FROM queries
                WHERE id = ANY(%s) AND latest_query_data_id IS NOT NULL
                """,
                (query_ids_to_delete,),
            )
        ]
        cur.execute(
            "UPDATE queries SET latest_query_data_id = NULL WHERE id = ANY(%s)",
            (query_ids_to_delete,),
        )
        deleted_query_results = 0
        if result_ids:
            cur.execute(
                """
                DELETE FROM query_results qr
                WHERE qr.id = ANY(%s)
                  AND NOT EXISTS (
                    SELECT 1 FROM queries q WHERE q.latest_query_data_id = qr.id
                  )
                """,
                (result_ids,),
            )
            deleted_query_results = cur.rowcount

        cur.execute("DELETE FROM queries WHERE id = ANY(%s)", (query_ids_to_delete,))
        deleted_queries = cur.rowcount

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    print(
        f"\nDeleted: {deleted_queries} queries, {deleted_visualizations} visualizations, "
        f"{deleted_query_results} query results."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
