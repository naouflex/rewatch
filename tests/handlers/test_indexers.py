"""Tests for the Indexer feature: model, handlers, and worker task."""
from unittest import mock

from rewatch.models import Favorite, Indexer, db
from tests import BaseTestCase


class TestIndexerListResource(BaseTestCase):
    def test_post_creates_indexer(self):
        query = self.factory.create_query()
        target = self.factory.create_data_source(group=self.factory.default_group)

        rv = self.make_request(
            "post",
            "/api/indexers",
            data={
                "name": "Daily blocks",
                "query_id": query.id,
                "data_source_id": target.id,
                "options": {"target_table": "blocks_idx", "insert_strategy": "append"},
                "tags": ["chains"],
            },
        )

        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.json["name"], "Daily blocks")
        self.assertEqual(rv.json["options"]["target_table"], "blocks_idx")
        self.assertEqual(rv.json["tags"], ["chains"])
        self.assertEqual(rv.json["data_source"]["id"], target.id)
        # Backed by a real row
        self.assertIsNotNone(Indexer.query.get(rv.json["id"]))

    def test_post_rejects_missing_required_fields(self):
        query = self.factory.create_query()
        rv = self.make_request("post", "/api/indexers", data={"name": "x", "query_id": query.id})
        # No data_source_id → 400 from require_fields
        self.assertEqual(rv.status_code, 400)

    def test_get_lists_only_visible_indexers(self):
        self.factory.create_indexer(name="A")
        self.factory.create_indexer(name="B")
        rv = self.make_request("get", "/api/indexers")
        self.assertEqual(rv.status_code, 200)
        names = sorted(item["name"] for item in rv.json)
        self.assertIn("A", names)
        self.assertIn("B", names)


class TestIndexerResource(BaseTestCase):
    def test_get_returns_indexer(self):
        indexer = self.factory.create_indexer(name="Indexer 7")
        rv = self.make_request("get", "/api/indexers/{}".format(indexer.id))
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.json["id"], indexer.id)
        self.assertEqual(rv.json["name"], "Indexer 7")

    def test_post_updates_options_and_tags(self):
        indexer = self.factory.create_indexer()
        rv = self.make_request(
            "post",
            "/api/indexers/{}".format(indexer.id),
            data={"options": {"target_table": "renamed"}, "tags": ["prod"]},
        )
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.json["options"]["target_table"], "renamed")
        self.assertEqual(rv.json["tags"], ["prod"])

    def test_only_owner_or_admin_can_edit(self):
        indexer = self.factory.create_indexer()
        other = self.factory.create_user()
        rv = self.make_request(
            "post",
            "/api/indexers/{}".format(indexer.id),
            user=other,
            data={"name": "hijack"},
        )
        self.assertEqual(rv.status_code, 403)

    def test_delete_removes_indexer(self):
        indexer = self.factory.create_indexer()
        indexer_id = indexer.id
        rv = self.make_request("delete", "/api/indexers/{}".format(indexer_id))
        self.assertEqual(rv.status_code, 200)
        self.assertIsNone(Indexer.query.get(indexer_id))


class TestIndexerArchive(BaseTestCase):
    def test_archive_excludes_from_default_listing(self):
        indexer = self.factory.create_indexer()
        rv = self.make_request("post", "/api/indexers/{}/archive".format(indexer.id))
        self.assertEqual(rv.status_code, 200)
        self.assertTrue(rv.json["is_archived"])

        rv = self.make_request("get", "/api/indexers")
        self.assertEqual([item for item in rv.json if item["id"] == indexer.id], [])

        rv = self.make_request("get", "/api/indexers/archive")
        self.assertEqual(rv.status_code, 200)
        self.assertIn(indexer.id, [item["id"] for item in rv.json])


class TestIndexerFavorite(BaseTestCase):
    def test_favorite_unfavorite_round_trip(self):
        indexer = self.factory.create_indexer()
        rv = self.make_request("post", "/api/indexers/{}/favorite".format(indexer.id))
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(
            Favorite.query.filter(
                Favorite.object_id == indexer.id, Favorite.object_type == "Indexer"
            ).count(),
            1,
        )

        rv = self.make_request("get", "/api/indexers/favorites")
        self.assertEqual(rv.status_code, 200)
        self.assertIn(indexer.id, [item["id"] for item in rv.json])

        rv = self.make_request("delete", "/api/indexers/{}/favorite".format(indexer.id))
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(
            Favorite.query.filter(
                Favorite.object_id == indexer.id, Favorite.object_type == "Indexer"
            ).count(),
            0,
        )


class TestIndexerTagsAndMy(BaseTestCase):
    def test_tags_endpoint_aggregates(self):
        self.factory.create_indexer(tags=["prod", "blocks"])
        self.factory.create_indexer(tags=["prod"])
        db.session.commit()

        rv = self.make_request("get", "/api/indexers/tags")
        names = [t["name"] for t in rv.json["tags"]]
        self.assertIn("prod", names)
        self.assertIn("blocks", names)

    def test_my_endpoint_returns_only_owned_indexers(self):
        mine = self.factory.create_indexer(name="mine")
        other_user = self.factory.create_user()
        self.factory.create_indexer(name="theirs", user=other_user)
        db.session.commit()

        rv = self.make_request("get", "/api/indexers/my")
        self.assertEqual(rv.status_code, 200)
        names = [item["name"] for item in rv.json]
        self.assertIn("mine", names)
        self.assertNotIn("theirs", names)
        # Sanity: ours is in the list
        self.assertIn(mine.id, [item["id"] for item in rv.json])


class TestIndexQueryResultsTask(BaseTestCase):
    def test_index_query_results_runs_runner_with_create_and_inserts(self):
        from rewatch.tasks.indexers import index_query_results

        indexer = self.factory.create_indexer(
            options={"target_table": "demo_idx", "insert_strategy": "append"}
        )
        query_result = self.factory.create_query_result(
            data={
                "columns": [{"name": "ethereum"}, {"name": "fantom"}],
                "rows": [
                    {"ethereum": 1, "fantom": 2},
                    {"ethereum": 3, "fantom": 4},
                ],
            }
        )

        runner = mock.Mock()
        runner.run_query.return_value = (None, None)
        with mock.patch("rewatch.tasks.indexers.get_query_runner", return_value=runner):
            ok = index_query_results(indexer, query_result)

        self.assertTrue(ok)
        # 1 CREATE + 2 INSERT = 3 calls
        self.assertEqual(runner.run_query.call_count, 3)
        first_call = runner.run_query.call_args_list[0][0][0]
        self.assertIn("CREATE TABLE IF NOT EXISTS demo_idx", first_call)
        self.assertIn('"ethereum"', first_call)
        # last_triggered_at gets updated
        self.assertIsNotNone(Indexer.query.get(indexer.id).last_triggered_at)

    def test_index_query_results_overwrite_strategy_truncates(self):
        from rewatch.tasks.indexers import index_query_results

        indexer = self.factory.create_indexer(options={"insert_strategy": "overwrite"})
        query_result = self.factory.create_query_result(
            data={"columns": [{"name": "x"}], "rows": [{"x": 1}]}
        )
        runner = mock.Mock()
        runner.run_query.return_value = (None, None)
        with mock.patch("rewatch.tasks.indexers.get_query_runner", return_value=runner):
            self.assertTrue(index_query_results(indexer, query_result))

        sqls = [call[0][0] for call in runner.run_query.call_args_list]
        self.assertTrue(any(s.startswith("DELETE FROM ") for s in sqls))

    def test_index_query_results_handles_empty_rows(self):
        from rewatch.tasks.indexers import index_query_results

        indexer = self.factory.create_indexer()
        query_result = self.factory.create_query_result(
            data={"columns": [{"name": "x"}], "rows": []}
        )
        runner = mock.Mock()
        with mock.patch("rewatch.tasks.indexers.get_query_runner", return_value=runner):
            self.assertTrue(index_query_results(indexer, query_result))
        runner.run_query.assert_not_called()


class TestIndexerPreviewResource(BaseTestCase):
    def test_preview_returns_table_rows(self):
        indexer = self.factory.create_indexer(
            options={"target_table": "demo_idx", "insert_strategy": "append"}
        )
        runner = mock.Mock()
        runner.supports_auto_limit = False
        runner.run_query.return_value = (
            {
                "columns": [{"name": "ethereum", "friendly_name": "ethereum", "type": "integer"}],
                "rows": [{"ethereum": 1}, {"ethereum": 2}],
            },
            None,
        )
        with mock.patch("rewatch.indexers.preview.get_query_runner", return_value=runner):
            rv = self.make_request("get", "/api/indexers/{}/preview".format(indexer.id))

        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.json["target_table"], "demo_idx")
        self.assertEqual(len(rv.json["rows"]), 2)
        runner.run_query.assert_called_once()
        self.assertIn("SELECT * FROM demo_idx", runner.run_query.call_args[0][0])

    def test_preview_rejects_invalid_table_name(self):
        indexer = self.factory.create_indexer(options={"target_table": "bad;drop"})
        rv = self.make_request("get", "/api/indexers/{}/preview".format(indexer.id))
        self.assertEqual(rv.status_code, 400)
