"""Tests for community forum handlers."""
from rewatch.models import ForumComment, ForumLike, ForumPost, db
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
        self.assertIn("reply_count", rv.json)

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
        self.assertIn("comments", rv.json)

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


class TestCommunityCommentsAndLikes(BaseTestCase):
    def _create_post(self):
        post = ForumPost(
            title="Thread",
            body="Original post body",
            category="general",
            user=self.factory.user,
            org=self.factory.org,
        )
        db.session.add(post)
        db.session.commit()
        return post

    def test_create_reply_and_like_post(self):
        post = self._create_post()

        reply_rv = self.make_request(
            "post",
            f"/api/community/posts/{post.id}/comments",
            data={"body": "Great idea, thanks!"},
        )
        self.assertEqual(reply_rv.status_code, 200)
        self.assertEqual(reply_rv.json["reply_count"], 1)
        self.assertEqual(len(reply_rv.json["comments"]), 1)

        like_rv = self.make_request("post", f"/api/community/posts/{post.id}/like")
        self.assertEqual(like_rv.status_code, 200)
        self.assertTrue(like_rv.json["is_liked"])
        self.assertEqual(like_rv.json["like_count"], 1)

        unlike_rv = self.make_request("post", f"/api/community/posts/{post.id}/like")
        self.assertEqual(unlike_rv.status_code, 200)
        self.assertFalse(unlike_rv.json["is_liked"])
        self.assertEqual(unlike_rv.json["like_count"], 0)

    def test_nested_reply_and_comment_like(self):
        post = self._create_post()
        comment = ForumComment(
            post_id=post.id,
            org_id=self.factory.org.id,
            user_id=self.factory.user.id,
            body="Top-level reply",
        )
        db.session.add(comment)
        db.session.commit()

        nested_rv = self.make_request(
            "post",
            f"/api/community/posts/{post.id}/comments",
            data={"body": "Nested reply", "parent_id": comment.id},
        )
        self.assertEqual(nested_rv.status_code, 200)
        self.assertEqual(nested_rv.json["reply_count"], 2)

        nested_id = [item for item in nested_rv.json["comments"] if item["parent_id"] == comment.id][0]["id"]
        like_rv = self.make_request(
            "post",
            f"/api/community/posts/{post.id}/comments/{nested_id}/like",
        )
        self.assertEqual(like_rv.status_code, 200)
        self.assertTrue(like_rv.json["is_liked"])

    def test_edit_and_delete_comment(self):
        post = self._create_post()
        comment = ForumComment(
            post_id=post.id,
            org_id=self.factory.org.id,
            user_id=self.factory.user.id,
            body="Draft reply",
        )
        db.session.add(comment)
        db.session.commit()

        edit_rv = self.make_request(
            "post",
            f"/api/community/posts/{post.id}/comments/{comment.id}",
            data={"body": "Updated reply"},
        )
        self.assertEqual(edit_rv.status_code, 200)
        self.assertEqual(
            [item for item in edit_rv.json["comments"] if item["id"] == comment.id][0]["body"],
            "Updated reply",
        )

        delete_rv = self.make_request(
            "delete",
            f"/api/community/posts/{post.id}/comments/{comment.id}",
        )
        self.assertEqual(delete_rv.status_code, 200)
        self.assertEqual(delete_rv.json["reply_count"], 0)
        self.assertIsNone(ForumComment.query.get(comment.id))
        self.assertEqual(ForumLike.query.filter_by(target_type="comment", target_id=comment.id).count(), 0)
