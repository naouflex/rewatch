from flask import request
from funcy import project

from rewatch import models
from rewatch.handlers.base import BaseResource, get_object_or_404, paginate, require_fields
from rewatch.models.community import FORUM_CATEGORIES
from rewatch.permissions import require_admin_or_owner, require_permission
from rewatch.serializers import serialize_forum_post


def _parse_list_params():
    category = (request.args.get("category") or "").strip() or None
    if category and category not in FORUM_CATEGORIES:
        from flask_restful import abort

        abort(400, message="Invalid category.")

    q = (request.args.get("q") or "").strip() or None
    page = request.args.get("page", type=int)
    page_size = request.args.get("page_size", type=int)

    return category, q, page, page_size


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
        return [serialize_forum_post(post, full=False) for post in posts.limit(limit)]

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
        post = get_object_or_404(models.ForumPost.get_by_id_and_org, post_id, self.current_org)
        self.record_event({"action": "view", "object_id": post.id, "object_type": "forum_post"})
        return serialize_forum_post(post)

    @require_permission("edit_community_post")
    def post(self, post_id):
        req = request.get_json(True)
        params = project(req, ("title", "body", "category"))

        post = get_object_or_404(models.ForumPost.get_by_id_and_org, post_id, self.current_org)
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
        post = get_object_or_404(models.ForumPost.get_by_id_and_org, post_id, self.current_org)
        require_admin_or_owner(post.user_id)
        models.db.session.delete(post)
        models.db.session.commit()

        self.record_event({"action": "delete", "object_id": post.id, "object_type": "forum_post"})
