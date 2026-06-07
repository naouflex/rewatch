from redash.models import QuerySnippet, db
from tests import BaseTestCase


class TestQuerySnippetResource(BaseTestCase):
    def test_get_snippet(self):
        snippet = self.factory.create_query_snippet(user=self.factory.user)

        rv = self.make_request("get", "/api/query_snippets/{}".format(snippet.id), user=self.factory.user)

        for field in ("snippet", "description", "trigger"):
            self.assertEqual(rv.json[field], getattr(snippet, field))

    def test_get_forbidden_for_non_owner(self):
        snippet = self.factory.create_query_snippet(user=self.factory.create_user())

        rv = self.make_request("get", "/api/query_snippets/{}".format(snippet.id), user=self.factory.user)
        self.assertEqual(rv.status_code, 403)

    def test_get_allowed_for_admin(self):
        snippet = self.factory.create_query_snippet(user=self.factory.create_user())

        rv = self.make_request(
            "get", "/api/query_snippets/{}".format(snippet.id), user=self.factory.create_admin()
        )
        self.assertEqual(rv.status_code, 200)

    def test_update_snippet(self):
        snippet = self.factory.create_query_snippet(user=self.factory.user)

        data = {
            "snippet": "updated",
            "trigger": "updated trigger",
            "description": "updated description",
        }

        rv = self.make_request(
            "post", "/api/query_snippets/{}".format(snippet.id), data=data, user=self.factory.user
        )

        for field in ("snippet", "description", "trigger"):
            self.assertEqual(rv.json[field], data[field])

    def test_update_forbidden_for_non_owner(self):
        snippet = self.factory.create_query_snippet(user=self.factory.create_user())

        data = {
            "snippet": "updated",
            "trigger": "updated trigger",
            "description": "updated description",
        }

        rv = self.make_request(
            "post", "/api/query_snippets/{}".format(snippet.id), data=data, user=self.factory.user
        )
        self.assertEqual(rv.status_code, 403)

    def test_delete_snippet(self):
        snippet = self.factory.create_query_snippet(user=self.factory.user)
        self.make_request("delete", "/api/query_snippets/{}".format(snippet.id), user=self.factory.user)

        self.assertIsNone(QuerySnippet.query.get(snippet.id))

    def test_delete_forbidden_for_non_owner(self):
        snippet = self.factory.create_query_snippet(user=self.factory.create_user())
        rv = self.make_request(
            "delete", "/api/query_snippets/{}".format(snippet.id), user=self.factory.user
        )
        self.assertEqual(rv.status_code, 403)
        self.assertIsNotNone(QuerySnippet.query.get(snippet.id))


class TestQuerySnippetListResource(BaseTestCase):
    def test_create_snippet(self):
        data = {
            "snippet": "updated",
            "trigger": "updated trigger",
            "description": "updated description",
        }

        rv = self.make_request("post", "/api/query_snippets", data=data, user=self.factory.user)
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.json["user_id"], self.factory.user.id)

    def test_list_returns_only_users_own_snippets(self):
        snippet1 = self.factory.create_query_snippet(user=self.factory.user)
        snippet2 = self.factory.create_query_snippet(user=self.factory.user)
        snippet_other_user = self.factory.create_query_snippet(user=self.factory.create_user())
        snippet_diff_org = self.factory.create_query_snippet(org=self.factory.create_org())

        rv = self.make_request("get", "/api/query_snippets", user=self.factory.user)
        ids = [s["id"] for s in rv.json]

        self.assertIn(snippet1.id, ids)
        self.assertIn(snippet2.id, ids)
        self.assertNotIn(snippet_other_user.id, ids)
        self.assertNotIn(snippet_diff_org.id, ids)

    def test_admin_lists_all_snippets_in_org(self):
        snippet1 = self.factory.create_query_snippet(user=self.factory.user)
        snippet2 = self.factory.create_query_snippet(user=self.factory.create_user())

        rv = self.make_request("get", "/api/query_snippets", user=self.factory.create_admin())
        ids = [s["id"] for s in rv.json]

        self.assertIn(snippet1.id, ids)
        self.assertIn(snippet2.id, ids)


class TestMyQuerySnippetsResource(BaseTestCase):
    def test_returns_only_current_users_snippets(self):
        mine = self.factory.create_query_snippet(user=self.factory.user)
        self.factory.create_query_snippet(user=self.factory.create_user())

        rv = self.make_request("get", "/api/query_snippets/my", user=self.factory.user)
        ids = [s["id"] for s in rv.json]
        self.assertEqual(ids, [mine.id])


class TestQuerySnippetFavoriteResource(BaseTestCase):
    def test_list_includes_is_favorite(self):
        self.factory.create_query_snippet(user=self.factory.user)
        rv = self.make_request("get", "/api/query_snippets", user=self.factory.user)
        self.assertIn("is_favorite", rv.json[0])
        self.assertFalse(rv.json[0]["is_favorite"])

    def test_favorite_then_appears_in_favorites(self):
        snippet = self.factory.create_query_snippet(user=self.factory.user)
        self.make_request("post", "/api/query_snippets/{}/favorite".format(snippet.id), user=self.factory.user)

        rv = self.make_request("get", "/api/query_snippets/favorites", user=self.factory.user)
        ids = [item["id"] for item in rv.json]
        self.assertEqual(ids, [snippet.id])
        self.assertTrue(rv.json[0]["is_favorite"])

    def test_unfavorite_removes_from_favorites(self):
        snippet = self.factory.create_query_snippet(user=self.factory.user)
        self.make_request("post", "/api/query_snippets/{}/favorite".format(snippet.id), user=self.factory.user)
        self.make_request("delete", "/api/query_snippets/{}/favorite".format(snippet.id), user=self.factory.user)

        rv = self.make_request("get", "/api/query_snippets/favorites", user=self.factory.user)
        self.assertEqual(rv.json, [])

    def test_favorite_forbidden_for_non_owner(self):
        snippet = self.factory.create_query_snippet(user=self.factory.create_user())
        rv = self.make_request(
            "post", "/api/query_snippets/{}/favorite".format(snippet.id), user=self.factory.user
        )
        self.assertEqual(rv.status_code, 403)


class TestQuerySnippetArchiveResource(BaseTestCase):
    def test_archive_hides_from_default_list(self):
        snippet = self.factory.create_query_snippet(user=self.factory.user)
        self.make_request("post", "/api/query_snippets/{}/archive".format(snippet.id), user=self.factory.user)

        rv = self.make_request("get", "/api/query_snippets", user=self.factory.user)
        self.assertEqual([item["id"] for item in rv.json], [])

    def test_archived_appears_in_archive_list(self):
        snippet = self.factory.create_query_snippet(user=self.factory.user)
        self.make_request("post", "/api/query_snippets/{}/archive".format(snippet.id), user=self.factory.user)

        rv = self.make_request("get", "/api/query_snippets/archive", user=self.factory.user)
        ids = [item["id"] for item in rv.json]
        self.assertEqual(ids, [snippet.id])
        self.assertTrue(rv.json[0]["is_archived"])

    def test_archive_forbidden_for_non_owner(self):
        snippet = self.factory.create_query_snippet(user=self.factory.create_user())
        rv = self.make_request(
            "post", "/api/query_snippets/{}/archive".format(snippet.id), user=self.factory.user
        )
        self.assertEqual(rv.status_code, 403)


class TestQuerySnippetTagsResource(BaseTestCase):
    def test_returns_tags_with_usage_count(self):
        self.factory.create_query_snippet(user=self.factory.user, tags=["sql", "join"])
        self.factory.create_query_snippet(user=self.factory.user, tags=["sql"])

        rv = self.make_request("get", "/api/query_snippets/tags", user=self.factory.user)
        tags = {t["name"]: t["count"] for t in rv.json["tags"]}
        self.assertEqual(tags, {"sql": 2, "join": 1})

    def test_update_tags_via_post(self):
        snippet = self.factory.create_query_snippet(user=self.factory.user)
        self.make_request(
            "post",
            "/api/query_snippets/{}".format(snippet.id),
            data={"tags": ["x", "y"]},
            user=self.factory.user,
        )
        db.session.refresh(snippet)
        self.assertEqual(snippet.tags, ["x", "y"])
