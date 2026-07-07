from flask import request
from funcy import project
from sqlalchemy import func

from rewatch import models
from rewatch.handlers.base import BaseResource, get_object_or_404, paginate, require_fields
from rewatch.models.community import FORUM_CATEGORIES, FORUM_LIKE_COMMENT, FORUM_LIKE_POST
from rewatch.permissions import require_admin_or_owner, require_permission
from rewatch.serializers import serialize_forum_comment, serialize_forum_post


def _parse_list_params():
    category = (request.args.get("category") or "").strip() or None
    if category and category not in FORUM_CATEGORIES:
        from flask_restful import abort

        abort(400, message="Invalid category.")

    q = (request.args.get("q") or "").strip() or None
    page = request.args.get("page", type=int)
    page_size = request.args.get("page_size", type=int)

    return category, q, page, page_size


def _get_post(post_id, org):
    return get_object_or_404(models.ForumPost.get_by_id_and_org, post_id, org)


def _get_comment(post_id, comment_id, org):
    comment = get_object_or_404(models.ForumComment.get_by_id_and_org, comment_id, org)
    if comment.post_id != int(post_id):
        from flask_restful import abort

        abort(404)
    return comment


def _serialize_post_list(posts):
    posts = list(posts)
    if not posts:
        return []

    post_ids = [post.id for post in posts]
    from flask_login import current_user

    user_id = None if current_user.is_api_user() else current_user.id

    like_summaries = models.ForumLike.summaries(user_id, FORUM_LIKE_POST, post_ids)
    reply_counts = dict(
        models.db.session.query(models.ForumComment.post_id, func.count(models.ForumComment.id))
        .filter(models.ForumComment.post_id.in_(post_ids))
        .group_by(models.ForumComment.post_id)
        .all()
    )

    return [
        serialize_forum_post(
            post,
            full=False,
            like_summary=like_summaries.get(post.id),
            reply_count=reply_counts.get(post.id, 0),
        )
        for post in posts
    ]


class ForumPostListResource(BaseResource):
    @require_permission("list_community_posts")
    def get(self):
        category, q, page, page_size = _parse_list_params()
        posts = models.ForumPost.all_for_org(self.current_org, category=category, q=q)
        self.record_event({"action": "list", "object_type": "forum_post"})

        if page is not None:
            page_size = page_size or 25
            return paginate(posts, page, page_size, lambda post: serialize_forum_post(post, full=False))

        limit = min(request.args.get("limit", type=int) or 100, 250)
        return _serialize_post_list(posts.limit(limit))

    @require_permission("create_community_post")
    def post(self):
        req = request.get_json(True)
        require_fields(req, ("title", "body", "category"))

        category = req["category"]
        if category not in FORUM_CATEGORIES:
            from flask_restful import abort

            abort(400, message="Invalid category.")

        title = (req["title"] or "").strip()
        body = (req["body"] or "").strip()
        if not title or not body:
            from flask_restful import abort

            abort(400, message="Title and body are required.")

        post = models.ForumPost(
            title=title[:255],
            body=body,
            category=category,
            user=self.current_user,
            org=self.current_org,
        )
        models.db.session.add(post)
        models.db.session.commit()

        self.record_event({"action": "create", "object_id": post.id, "object_type": "forum_post"})
        return serialize_forum_post(post)


class ForumPostResource(BaseResource):
    @require_permission("view_community_post")
    def get(self, post_id):
        post = _get_post(post_id, self.current_org)
        self.record_event({"action": "view", "object_id": post.id, "object_type": "forum_post"})
        return serialize_forum_post(post)

    @require_permission("edit_community_post")
    def post(self, post_id):
        req = request.get_json(True)
        params = project(req, ("title", "body", "category"))

        post = _get_post(post_id, self.current_org)
        require_admin_or_owner(post.user_id)

        if "category" in params:
            if params["category"] not in FORUM_CATEGORIES:
                from flask_restful import abort

                abort(400, message="Invalid category.")

        if "title" in params:
            title = (params["title"] or "").strip()
            if not title:
                from flask_restful import abort

                abort(400, message="Title is required.")
            params["title"] = title[:255]

        if "body" in params:
            body = (params["body"] or "").strip()
            if not body:
                from flask_restful import abort

                abort(400, message="Body is required.")
            params["body"] = body

        self.update_model(post, params)
        models.db.session.commit()

        self.record_event({"action": "edit", "object_id": post.id, "object_type": "forum_post"})
        return serialize_forum_post(post)

    @require_permission("edit_community_post")
    def delete(self, post_id):
        post = _get_post(post_id, self.current_org)
        require_admin_or_owner(post.user_id)
        models.db.session.delete(post)
        models.db.session.commit()

        self.record_event({"action": "delete", "object_id": post.id, "object_type": "forum_post"})


class ForumCommentListResource(BaseResource):
    @require_permission("view_community_post")
    def get(self, post_id):
        _get_post(post_id, self.current_org)
        comments = models.ForumComment.for_post(post_id).all()
        from rewatch.serializers import _serialize_forum_comments

        return _serialize_forum_comments(comments)

    @require_permission("create_community_post")
    def post(self, post_id):
        req = request.get_json(True)
        require_fields(req, ("body",))

        post = _get_post(post_id, self.current_org)
        body = (req["body"] or "").strip()
        if not body:
            from flask_restful import abort

            abort(400, message="Reply body is required.")

        parent_id = req.get("parent_id")
        if parent_id is not None:
            parent = _get_comment(post_id, parent_id, self.current_org)
            if parent.parent_id is not None:
                from flask_restful import abort

                abort(400, message="Only one level of replies is supported.")

        comment = models.ForumComment(
            post=post,
            org=self.current_org,
            user=self.current_user,
            body=body,
            parent_id=parent_id,
        )
        models.db.session.add(comment)
        post.updated_at = models.db.func.now()
        models.db.session.commit()

        self.record_event(
            {
                "action": "create",
                "object_id": comment.id,
                "object_type": "forum_comment",
                "post_id": post.id,
            }
        )
        return serialize_forum_post(post)


class ForumCommentResource(BaseResource):
    @require_permission("edit_community_post")
    def post(self, post_id, comment_id):
        req = request.get_json(True)
        require_fields(req, ("body",))

        comment = _get_comment(post_id, comment_id, self.current_org)
        require_admin_or_owner(comment.user_id)

        body = (req["body"] or "").strip()
        if not body:
            from flask_restful import abort

            abort(400, message="Reply body is required.")

        comment.body = body
        comment.post.updated_at = models.db.func.now()
        models.db.session.commit()

        self.record_event({"action": "edit", "object_id": comment.id, "object_type": "forum_comment"})
        return serialize_forum_post(comment.post)

    @require_permission("edit_community_post")
    def delete(self, post_id, comment_id):
        comment = _get_comment(post_id, comment_id, self.current_org)
        require_admin_or_owner(comment.user_id)
        post = comment.post
        models.db.session.delete(comment)
        post.updated_at = models.db.func.now()
        models.db.session.commit()

        self.record_event({"action": "delete", "object_id": comment.id, "object_type": "forum_comment"})
        return serialize_forum_post(post)


class ForumPostLikeResource(BaseResource):
    @require_permission("view_community_post")
    def post(self, post_id):
        post = _get_post(post_id, self.current_org)
        result = models.ForumLike.toggle(self.current_user, self.current_org, FORUM_LIKE_POST, post.id)
        self.record_event({"action": "like", "object_id": post.id, "object_type": "forum_post"})
        return result


class ForumCommentLikeResource(BaseResource):
    @require_permission("view_community_post")
    def post(self, post_id, comment_id):
        comment = _get_comment(post_id, comment_id, self.current_org)
        result = models.ForumLike.toggle(
            self.current_user, self.current_org, FORUM_LIKE_COMMENT, comment.id
        )
        self.record_event({"action": "like", "object_id": comment.id, "object_type": "forum_comment"})
        return result
