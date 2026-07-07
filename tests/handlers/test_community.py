"""Tests for community forum handlers."""
from rewatch.models import ForumPost, db
from tests import BaseTestCase


class TestCommunityPosts(BaseTestCase):
    def test_create_and_list_posts(self):
        rv = self.make_request(
            "post",
            "/api/community/posts",
            data={
                "title": "Sharing a cohort query",
                "body": "Here is how we track weekly retention.",
                "category": "queries",
            },
        )
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.json["title"], "Sharing a cohort query")
        self.assertEqual(rv.json["category"], "queries")
        self.assertIn("body", rv.json)

        list_rv = self.make_request("get", "/api/community/posts")
        self.assertEqual(list_rv.status_code, 200)
        titles = [item["title"] for item in list_rv.json]
        self.assertIn("Sharing a cohort query", titles)
        self.assertTrue(all("excerpt" in item for item in list_rv.json))

    def test_get_update_and_delete_post(self):
        post = ForumPost(
            title="Dashboard tips",
            body="Keep KPIs in the first row.",
            category="dashboards",
            user=self.factory.user,
            org=self.factory.org,
        )
        db.session.add(post)
        db.session.commit()

        rv = self.make_request("get", f"/api/community/posts/{post.id}")
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.json["body"], "Keep KPIs in the first row.")

        update_rv = self.make_request(
            "post",
            f"/api/community/posts/{post.id}",
            data={"title": "Updated dashboard tips"},
        )
        self.assertEqual(update_rv.status_code, 200)
        self.assertEqual(update_rv.json["title"], "Updated dashboard tips")

        delete_rv = self.make_request("delete", f"/api/community/posts/{post.id}")
        self.assertEqual(delete_rv.status_code, 200)
        self.assertIsNone(ForumPost.query.get(post.id))

    def test_only_owner_or_admin_can_edit(self):
        post = ForumPost(
            title="Locked post",
            body="Original body",
            category="general",
            user=self.factory.user,
            org=self.factory.org,
        )
        db.session.add(post)
        db.session.commit()

        other = self.factory.create_user()
        rv = self.make_request(
            "post",
            f"/api/community/posts/{post.id}",
            user=other,
            data={"title": "Hijacked"},
        )
        self.assertEqual(rv.status_code, 403)

    def test_invalid_category_rejected(self):
        rv = self.make_request(
            "post",
            "/api/community/posts",
            data={"title": "Bad", "body": "Bad", "category": "unknown"},
        )
        self.assertEqual(rv.status_code, 400)
