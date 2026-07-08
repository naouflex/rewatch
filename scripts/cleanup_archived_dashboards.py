#!/usr/bin/env python3
"""Permanently delete archived dashboards and their associated queries."""

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
    """Include base feed queries referenced via cached_query_{id} in derived SQL."""
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
        archived_dashboards = fetchall(
            cur, "SELECT id, name FROM dashboards WHERE is_archived = true ORDER BY id"
        )
        if not archived_dashboards:
            print("No archived dashboards found.")
            return 0

        archived_dashboard_ids = [row["id"] for row in archived_dashboards]
        print("Archived dashboards:")
        for row in archived_dashboards:
            print(f"  {row['id']}: {row['name']}")

        queries_on_archived = {
            row["query_id"]
            for row in fetchall(
                cur,
                """
                SELECT DISTINCT v.query_id
                FROM widgets w
                JOIN visualizations v ON v.id = w.visualization_id
                WHERE w.dashboard_id = ANY(%s)
                """,
                (archived_dashboard_ids,),
            )
        }

        archived_queries = {
            row["id"] for row in fetchall(cur, "SELECT id FROM queries WHERE is_archived = true")
        }

        queries_still_used = {
            row["query_id"]
            for row in fetchall(
                cur,
                """
                SELECT DISTINCT v.query_id
                FROM widgets w
                JOIN visualizations v ON v.id = w.visualization_id
                JOIN dashboards d ON d.id = w.dashboard_id
                WHERE d.is_archived = false
                """,
            )
        }

        active_feed_ids = set()
        for row in fetchall(
            cur,
            """
            SELECT q.query
            FROM queries q
            JOIN visualizations v ON v.query_id = q.id
            JOIN widgets w ON w.visualization_id = v.id
            JOIN dashboards d ON d.id = w.dashboard_id
            WHERE d.is_archived = false
            """,
        ):
            for match in CACHED_QUERY_RE.finditer(row["query"] or ""):
                active_feed_ids.add(int(match.group(1)))

        seed = (queries_on_archived | archived_queries) - queries_still_used
        query_ids_to_delete = expand_feed_queries(cur, seed) - queries_still_used - active_feed_ids
        query_ids_to_delete = sorted(query_ids_to_delete)

        print(f"\nQueries to delete ({len(query_ids_to_delete)}):")
        for qid in query_ids_to_delete:
            name = fetchall(cur, "SELECT name FROM queries WHERE id = %s", (qid,))
            label = name[0]["name"] if name else "?"
            print(f"  {qid}: {label}")

        viz_ids_to_delete = [
            row["id"]
            for row in fetchall(
                cur,
                "SELECT id FROM visualizations WHERE query_id = ANY(%s)",
                (query_ids_to_delete or [-1],),
            )
        ]

        cur.execute("DELETE FROM widgets WHERE dashboard_id = ANY(%s)", (archived_dashboard_ids,))
        deleted_widgets_archived = cur.rowcount

        if viz_ids_to_delete:
            cur.execute("DELETE FROM widgets WHERE visualization_id = ANY(%s)", (viz_ids_to_delete,))
        deleted_widgets_viz = cur.rowcount

        cur.execute(
            "DELETE FROM favorites WHERE (object_type = 'Dashboard' AND object_id = ANY(%s))"
            " OR (object_type = 'Query' AND object_id = ANY(%s))",
            (archived_dashboard_ids, query_ids_to_delete or [-1]),
        )
        deleted_favorites = cur.rowcount

        cur.execute(
            "DELETE FROM api_keys WHERE object_type = 'Dashboard' AND object_id = ANY(%s)",
            (archived_dashboard_ids,),
        )
        deleted_api_keys = cur.rowcount

        cur.execute("DELETE FROM dashboards WHERE id = ANY(%s)", (archived_dashboard_ids,))
        deleted_dashboards = cur.rowcount

        if viz_ids_to_delete:
            cur.execute("DELETE FROM visualizations WHERE id = ANY(%s)", (viz_ids_to_delete,))
        deleted_visualizations = cur.rowcount

        deleted_query_results = 0
        deleted_queries = 0
        if query_ids_to_delete:
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
        f"\nDeleted: {deleted_dashboards} dashboards, {deleted_queries} queries, "
        f"{deleted_visualizations} visualizations, {deleted_widgets_archived + deleted_widgets_viz} widgets, "
        f"{deleted_query_results} query results, {deleted_favorites} favorites, {deleted_api_keys} api keys."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
