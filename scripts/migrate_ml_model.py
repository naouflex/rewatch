#!/usr/bin/env python3
"""Migrate an ML model and its linked query from one Rewatch DB to another."""

from __future__ import print_function

import argparse
import os
import sys

import psycopg2
import psycopg2.extras


SOURCE_DS_ID = 39
TARGET_DS_ID = 4
TARGET_USER_ID = 1
TARGET_ORG_ID = 1


def connect(url):
    return psycopg2.connect(url)


def table_columns(cur, table):
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
        """,
        (table,),
    )
    rows = cur.fetchall()
    if not rows:
        return []
    if isinstance(rows[0], dict):
        return [row["column_name"] for row in rows]
    return [row[0] for row in rows]


def remap_row(row, mapping):
    return {mapping.get(k, k): v for k, v in row.items()}


def column_types(cur, table):
    cur.execute(
        """
        SELECT column_name, data_type, udt_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        """,
        (table,),
    )
    rows = cur.fetchall()
    if rows and isinstance(rows[0], dict):
        return {row["column_name"]: (row["data_type"], row["udt_name"]) for row in rows}
    return {row[0]: (row[1], row[2]) for row in rows}


def adapt_value(value, column_type=None):
    if column_type and column_type[0] == "ARRAY":
        return value
    if isinstance(value, dict) or isinstance(value, list):
        return psycopg2.extras.Json(value)
    return value


def copy_rows(src_cur, dst_cur, table, where_sql, params, id_map=None, overrides=None, skip_columns=None):
    src_cur.execute("SELECT * FROM {} WHERE {}".format(table, where_sql), params)
    rows = src_cur.fetchall()
    if not rows:
        return []

    src_cols = list(rows[0].keys())
    dst_cols = set(table_columns(dst_cur, table))
    dst_types = column_types(dst_cur, table)
    skip_columns = set(skip_columns or [])
    insert_cols = [c for c in src_cols if c in dst_cols and c not in skip_columns]
    inserted = []

    for row in rows:
        payload = {col: adapt_value(row[col], dst_types.get(col)) for col in insert_cols}
        if overrides:
            for key, value in overrides(row).items():
                payload[key] = adapt_value(value, dst_types.get(key))
        if id_map is not None and "id" in payload:
            old_id = payload["id"]
            new_id = id_map[old_id]
            payload["id"] = new_id
        write_cols = list(dict.fromkeys(insert_cols + list((overrides(row) if overrides else {}).keys())))
        placeholders = ", ".join(["%({})s".format(c) for c in write_cols])
        columns = ", ".join(write_cols)
        dst_cur.execute(
            "INSERT INTO {} ({}) VALUES ({})".format(table, columns, placeholders),
            payload,
        )
        inserted.append(row["id"] if "id" in row else None)
    return inserted


def next_id(dst_cur, table):
    dst_cur.execute("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM {}".format(table))
    return dst_cur.fetchone()["next_id"]


def migrate(model_id, source_url, target_url, include_predictions=True, dry_run=False):
    src = connect(source_url)
    dst = connect(target_url)
    src_cur = src.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    dst_cur = dst.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    src_cur.execute("SELECT * FROM ml_models WHERE id = %s", (model_id,))
    model = src_cur.fetchone()
    if not model:
        raise SystemExit("Model {} not found in source DB".format(model_id))

    query_id = model["query_id"]
    src_cur.execute("SELECT * FROM queries WHERE id = %s", (query_id,))
    query = src_cur.fetchone()
    if not query:
        raise SystemExit("Query {} not found in source DB".format(query_id))

    dst_cur.execute(
        "SELECT id FROM queries WHERE name = %s AND org_id = %s",
        (query["name"], TARGET_ORG_ID),
    )
    existing = dst_cur.fetchone()
    if existing:
        raise SystemExit(
            "Target already has query named {!r} (id={}). Aborting.".format(
                query["name"], existing["id"]
            )
        )

    dst_cur.execute(
        "SELECT id FROM ml_models WHERE name = %s AND org_id = %s",
        (model["name"], TARGET_ORG_ID),
    )
    existing_model = dst_cur.fetchone()
    if existing_model:
        raise SystemExit(
            "Target already has model named {!r} (id={}). Aborting.".format(
                model["name"], existing_model["id"]
            )
        )

    new_query_id = next_id(dst_cur, "queries")
    new_model_id = next_id(dst_cur, "ml_models")
    new_qr_id = next_id(dst_cur, "query_results") if query["latest_query_data_id"] else None

    qr_id_map = {}
    if query["latest_query_data_id"]:
        qr_id_map[query["latest_query_data_id"]] = new_qr_id

    src_cur.execute("SELECT * FROM visualizations WHERE query_id = %s ORDER BY id", (query_id,))
    viz_rows = src_cur.fetchall()
    viz_id_map = {}
    next_viz_id = next_id(dst_cur, "visualizations")
    for viz in viz_rows:
        viz_id_map[viz["id"]] = next_viz_id
        next_viz_id += 1

    src_cur.execute("SELECT * FROM ml_model_versions WHERE model_id = %s ORDER BY id", (model_id,))
    version_rows = src_cur.fetchall()
    version_id_map = {}
    next_version_id = next_id(dst_cur, "ml_model_versions")
    for version in version_rows:
        version_id_map[version["id"]] = next_version_id
        next_version_id += 1

    src_cur.execute("SELECT * FROM prediction_results WHERE model_id = %s ORDER BY id", (model_id,))
    prediction_rows = src_cur.fetchall()
    pred_id_map = {}
    next_pred_id = next_id(dst_cur, "prediction_results")
    for pred in prediction_rows:
        pred_id_map[pred["id"]] = next_pred_id
        next_pred_id += 1

    print("Planned migration:")
    print("  query {} -> {}".format(query_id, new_query_id))
    print("  model {} -> {}".format(model_id, new_model_id))
    if qr_id_map:
        for old, new in qr_id_map.items():
            print("  query_result {} -> {}".format(old, new))
    print("  visualizations: {}".format(len(viz_id_map)))
    print("  model versions: {}".format(len(version_id_map)))
    print("  predictions: {}".format(len(pred_id_map) if include_predictions else 0))

    if dry_run:
        print("Dry run only; no changes written.")
        return

    try:
        if qr_id_map:
            copy_rows(
                src_cur,
                dst_cur,
                "query_results",
                "id = %s",
                (query["latest_query_data_id"],),
                id_map=qr_id_map,
                overrides=lambda _row: {
                    "org_id": TARGET_ORG_ID,
                    "data_source_id": TARGET_DS_ID,
                },
            )

        copy_rows(
            src_cur,
            dst_cur,
            "queries",
            "id = %s",
            (query_id,),
            id_map={query_id: new_query_id},
            overrides=lambda _row: {
                "org_id": TARGET_ORG_ID,
                "user_id": TARGET_USER_ID,
                "last_modified_by_id": TARGET_USER_ID,
                "data_source_id": TARGET_DS_ID,
                "latest_query_data_id": qr_id_map.get(query["latest_query_data_id"]),
            },
            skip_columns={"search_vector"},
        )

        for old_viz_id, new_viz_id in viz_id_map.items():
            copy_rows(
                src_cur,
                dst_cur,
                "visualizations",
                "id = %s",
                (old_viz_id,),
                id_map={old_viz_id: new_viz_id},
                overrides=lambda _row: {"query_id": new_query_id},
            )

        copy_rows(
            src_cur,
            dst_cur,
            "ml_models",
            "id = %s",
            (model_id,),
            id_map={model_id: new_model_id},
            overrides=lambda _row: {
                "org_id": TARGET_ORG_ID,
                "user_id": TARGET_USER_ID,
                "query_id": new_query_id,
            },
            skip_columns={"autoencoder_model_blob", "encoder_model_blob"},
        )

        for old_version_id, new_version_id in version_id_map.items():
            copy_rows(
                src_cur,
                dst_cur,
                "ml_model_versions",
                "id = %s",
                (old_version_id,),
                id_map={old_version_id: new_version_id},
                overrides=lambda _row: {
                    "org_id": TARGET_ORG_ID,
                    "user_id": TARGET_USER_ID,
                    "model_id": new_model_id,
                    "query_id": new_query_id,
                },
            )

        if include_predictions:
            for old_pred_id, new_pred_id in pred_id_map.items():
                copy_rows(
                    src_cur,
                    dst_cur,
                    "prediction_results",
                    "id = %s",
                    (old_pred_id,),
                    id_map={old_pred_id: new_pred_id},
                    overrides=lambda row: {
                        "org_id": TARGET_ORG_ID,
                        "user_id": TARGET_USER_ID,
                        "model_id": new_model_id,
                        "query_id": new_query_id,
                        "updated_at": row.get("updated_at") or row["created_at"],
                    },
                )

        dst.commit()
        print("Migration completed successfully.")
        print("New model id: {}".format(new_model_id))
        print("New query id: {}".format(new_query_id))
    except Exception:
        dst.rollback()
        raise
    finally:
        src.close()
        dst.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-id", type=int, required=True)
    parser.add_argument(
        "--source-url",
        default=os.environ.get("SOURCE_DATABASE_URL") or os.environ.get("PROD_DB"),
    )
    parser.add_argument(
        "--target-url",
        default=os.environ.get("TARGET_DATABASE_URL") or os.environ.get("REWATCH_DATABASE_URL"),
    )
    parser.add_argument("--no-predictions", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.source_url or not args.target_url:
        print("SOURCE_DATABASE_URL and REWATCH_DATABASE_URL (or TARGET_DATABASE_URL) are required.", file=sys.stderr)
        sys.exit(1)

    migrate(
        args.model_id,
        args.source_url,
        args.target_url,
        include_predictions=not args.no_predictions,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
