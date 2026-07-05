from flask import request
from funcy import project
from sqlalchemy.exc import IntegrityError

from rewatch import models
from rewatch.handlers.base import (
    BaseResource,
    get_object_or_404,
    require_fields,
)
from rewatch.permissions import require_admin_or_owner, require_permission


def serialize_query_snippets(current_user, snippets):
    snippets = list(snippets)
    favorite_ids = set(models.Favorite.are_favorites(current_user.id, snippets))
    result = []
    for snippet in snippets:
        d = snippet.to_dict()
        d["is_favorite"] = snippet.id in favorite_ids
        result.append(d)
    return result


class QuerySnippetResource(BaseResource):
    @require_permission("view_query_snippet")
    def get(self, snippet_id):
        snippet = get_object_or_404(models.QuerySnippet.get_by_id_and_org, snippet_id, self.current_org)
        require_admin_or_owner(snippet.user_id)

        self.record_event({"action": "view", "object_id": snippet_id, "object_type": "query_snippet"})

        d = snippet.to_dict()
        d["is_favorite"] = models.Favorite.is_favorite(self.current_user.id, snippet)
        return d

    @require_permission("edit_query_snippet")
    def post(self, snippet_id):
        req = request.get_json(True)
        params = project(req, ("trigger", "description", "snippet", "tags"))
        snippet = get_object_or_404(models.QuerySnippet.get_by_id_and_org, snippet_id, self.current_org)
        require_admin_or_owner(snippet.user_id)

        self.update_model(snippet, params)
        models.db.session.commit()

        self.record_event({"action": "edit", "object_id": snippet.id, "object_type": "query_snippet"})
        return snippet.to_dict()

    @require_permission("edit_query_snippet")
    def delete(self, snippet_id):
        snippet = get_object_or_404(models.QuerySnippet.get_by_id_and_org, snippet_id, self.current_org)
        require_admin_or_owner(snippet.user_id)
        models.db.session.delete(snippet)
        models.db.session.commit()

        self.record_event(
            {
                "action": "delete",
                "object_id": snippet.id,
                "object_type": "query_snippet",
            }
        )


class QuerySnippetListResource(BaseResource):
    @require_permission("create_query_snippet")
    def post(self):
        req = request.get_json(True)
        require_fields(req, ("trigger", "description", "snippet"))

        snippet = models.QuerySnippet(
            trigger=req["trigger"],
            description=req["description"],
            snippet=req["snippet"],
            user=self.current_user,
            org=self.current_org,
            tags=req.get("tags"),
        )

        models.db.session.add(snippet)
        models.db.session.commit()

        self.record_event(
            {
                "action": "create",
                "object_id": snippet.id,
                "object_type": "query_snippet",
            }
        )

        return snippet.to_dict()

    @require_permission("list_query_snippets")
    def get(self):
        self.record_event({"action": "list", "object_type": "query_snippet"})
        if self.current_user.has_permission("admin"):
            snippets = models.QuerySnippet.all(org=self.current_org)
        else:
            snippets = models.QuerySnippet.by_user(self.current_user)
        return serialize_query_snippets(self.current_user, snippets)


class MyQuerySnippetsResource(BaseResource):
    @require_permission("list_query_snippets")
    def get(self):
        snippets = models.QuerySnippet.by_user(self.current_user)
        self.record_event({"action": "list", "object_type": "query_snippet", "filter": "my"})
        return serialize_query_snippets(self.current_user, snippets)


class QuerySnippetFavoriteListResource(BaseResource):
    @require_permission("list_query_snippets")
    def get(self):
        snippets = models.QuerySnippet.favorites(self.current_user)
        self.record_event({"action": "load_favorites", "object_type": "query_snippet"})
        return serialize_query_snippets(self.current_user, snippets)


class QuerySnippetArchiveResource(BaseResource):
    def post(self, snippet_id):
        snippet = get_object_or_404(models.QuerySnippet.get_by_id_and_org, snippet_id, self.current_org)
        require_admin_or_owner(snippet.user_id)

        snippet.archive()
        models.db.session.commit()
        self.record_event({"action": "archive", "object_id": snippet.id, "object_type": "query_snippet"})
        return snippet.to_dict()


class QuerySnippetArchivedListResource(BaseResource):
    @require_permission("list_query_snippets")
    def get(self):
        if self.current_user.has_permission("admin"):
            snippets = models.QuerySnippet.all(org=self.current_org, include_archived=True)
        else:
            snippets = models.QuerySnippet.by_user(self.current_user, include_archived=True)
        snippets = snippets.filter(models.QuerySnippet.is_archived.is_(True))
        self.record_event({"action": "list", "object_type": "query_snippet", "filter": "archived"})
        return serialize_query_snippets(self.current_user, snippets)


class QuerySnippetTagsResource(BaseResource):
    @require_permission("list_query_snippets")
    def get(self):
        tags = models.QuerySnippet.all_tags(self.current_org, self.current_user)
        return {"tags": [{"name": name, "count": count} for name, count in tags]}


class QuerySnippetFavoriteResource(BaseResource):
    def post(self, snippet_id):
        snippet = get_object_or_404(models.QuerySnippet.get_by_id_and_org, snippet_id, self.current_org)
        require_admin_or_owner(snippet.user_id)

        fav = models.Favorite(org_id=self.current_org.id, object=snippet, user=self.current_user)
        models.db.session.add(fav)

        try:
            models.db.session.commit()
        except IntegrityError as e:
            if "unique_favorite" in str(e):
                models.db.session.rollback()
            else:
                raise e

        self.record_event(
            {"action": "favorite", "object_id": snippet.id, "object_type": "query_snippet"}
        )

    def delete(self, snippet_id):
        snippet = get_object_or_404(models.QuerySnippet.get_by_id_and_org, snippet_id, self.current_org)
        require_admin_or_owner(snippet.user_id)

        models.Favorite.query.filter(
            models.Favorite.object_id == snippet_id,
            models.Favorite.object_type == "QuerySnippet",
            models.Favorite.user == self.current_user,
        ).delete()
        models.db.session.commit()

        self.record_event(
            {"action": "unfavorite", "object_id": snippet.id, "object_type": "query_snippet"}
        )
