from flask import request
from funcy import project
from sqlalchemy.exc import IntegrityError

from rewatch import models
from rewatch.handlers.base import (
    BaseResource,
    get_object_or_404,
    require_fields,
)
from rewatch.permissions import (
    require_access,
    require_admin_or_owner,
    require_permission,
    view_only,
)
from rewatch.serializers import serialize_indexer
from rewatch.indexers.preview import fetch_indexer_table_preview


class IndexerResource(BaseResource):
    @require_permission("view_indexer")
    def get(self, indexer_id):
        indexer = get_object_or_404(models.Indexer.get_by_id_and_org, indexer_id, self.current_org)
        require_access(indexer, self.current_user, view_only)
        self.record_event({"action": "view", "object_id": indexer.id, "object_type": "indexer"})
        return serialize_indexer(indexer)

    @require_permission("edit_indexer")
    def post(self, indexer_id):
        req = request.get_json(True)
        params = project(req, ("options", "name", "query_id", "data_source_id", "tags"))

        indexer = get_object_or_404(models.Indexer.get_by_id_and_org, indexer_id, self.current_org)
        require_admin_or_owner(indexer.user_id)

        if "data_source_id" in params:
            data_source = get_object_or_404(
                models.DataSource.get_by_id_and_org, params["data_source_id"], self.current_org
            )
            require_access(data_source, self.current_user, view_only)
            params["data_source"] = data_source
            del params["data_source_id"]

        if "query_id" in params:
            query = get_object_or_404(models.Query.get_by_id_and_org, params["query_id"], self.current_org)
            require_access(query, self.current_user, view_only)
            params["query_rel"] = query
            del params["query_id"]

        self.update_model(indexer, params)
        models.db.session.commit()

        self.record_event({"action": "edit", "object_id": indexer.id, "object_type": "indexer"})

        return serialize_indexer(indexer)

    @require_permission("edit_indexer")
    def delete(self, indexer_id):
        indexer = get_object_or_404(models.Indexer.get_by_id_and_org, indexer_id, self.current_org)
        require_admin_or_owner(indexer.user_id)
        models.db.session.delete(indexer)
        models.db.session.commit()

        self.record_event({"action": "delete", "object_id": indexer.id, "object_type": "indexer"})


class IndexerListResource(BaseResource):
    @require_permission("create_indexer")
    def post(self):
        req = request.get_json(True)
        require_fields(req, ("name", "query_id", "data_source_id"))

        query = get_object_or_404(models.Query.get_by_id_and_org, req["query_id"], self.current_org)
        require_access(query, self.current_user, view_only)

        data_source = get_object_or_404(
            models.DataSource.get_by_id_and_org, req["data_source_id"], self.current_org
        )
        require_access(data_source, self.current_user, view_only)

        indexer = models.Indexer(
            name=req["name"],
            query_rel=query,
            data_source=data_source,
            user=self.current_user,
            org=self.current_org,
            options=req.get("options") or {},
            tags=req.get("tags"),
        )

        models.db.session.add(indexer)
        models.db.session.flush()
        models.db.session.commit()

        self.record_event({"action": "create", "object_id": indexer.id, "object_type": "indexer"})
        return serialize_indexer(indexer)

    @require_permission("list_indexers")
    def get(self):
        self.record_event({"action": "list", "object_type": "indexer"})
        indexers = models.Indexer.all(group_ids=self.current_user.group_ids)
        return [serialize_indexer(indexer) for indexer in indexers]


class IndexerArchiveResource(BaseResource):
    """Archive a single indexer (POST) or list archived indexers (GET)."""

    def post(self, indexer_id):
        indexer = get_object_or_404(models.Indexer.get_by_id_and_org, indexer_id, self.current_org)
        require_admin_or_owner(indexer.user_id)

        indexer.archive()
        models.db.session.commit()
        self.record_event({"action": "archive", "object_id": indexer.id, "object_type": "indexer"})

        return serialize_indexer(indexer)


class IndexerArchivedListResource(BaseResource):
    @require_permission("list_indexers")
    def get(self):
        indexers = models.Indexer.all_indexers(self.current_user.group_ids, include_archived=True)
        self.record_event({"action": "list", "object_type": "indexer", "filter": "archived"})
        return [serialize_indexer(indexer) for indexer in indexers]


class MyIndexersResource(BaseResource):
    @require_permission("list_indexers")
    def get(self):
        indexers = models.Indexer.by_user(self.current_user)
        self.record_event({"action": "list", "object_type": "indexer", "filter": "my"})
        return [serialize_indexer(indexer) for indexer in indexers]


class IndexerFavoriteResource(BaseResource):
    def post(self, indexer_id):
        indexer = get_object_or_404(models.Indexer.get_by_id_and_org, indexer_id, self.current_org)
        require_access(indexer, self.current_user, view_only)

        fav = models.Favorite(org_id=self.current_org.id, object=indexer, user=self.current_user)
        models.db.session.add(fav)

        try:
            models.db.session.commit()
        except IntegrityError as e:
            if "unique_favorite" in str(e):
                models.db.session.rollback()
            else:
                raise e

        self.record_event({"action": "favorite", "object_id": indexer.id, "object_type": "indexer"})

    def delete(self, indexer_id):
        indexer = get_object_or_404(models.Indexer.get_by_id_and_org, indexer_id, self.current_org)
        require_access(indexer, self.current_user, view_only)

        models.Favorite.query.filter(
            models.Favorite.object_id == indexer_id,
            models.Favorite.object_type == "Indexer",
            models.Favorite.user == self.current_user,
        ).delete()
        models.db.session.commit()

        self.record_event({"action": "unfavorite", "object_id": indexer.id, "object_type": "indexer"})


class IndexerFavoriteListResource(BaseResource):
    @require_permission("list_indexers")
    def get(self):
        favorites = models.Indexer.favorites(self.current_user)
        self.record_event({"action": "load_favorites", "object_type": "indexer"})
        return [serialize_indexer(indexer) for indexer in favorites]


class IndexerTagsResource(BaseResource):
    @require_permission("list_indexers")
    def get(self):
        tags = models.Indexer.all_tags(self.current_org, self.current_user)
        return {"tags": [{"name": name, "count": count} for name, count in tags]}


class IndexerPreviewResource(BaseResource):
    @require_permission("view_indexer")
    def get(self, indexer_id):
        indexer = get_object_or_404(models.Indexer.get_by_id_and_org, indexer_id, self.current_org)
        require_access(indexer, self.current_user, view_only)

        limit = request.args.get("limit", type=int)
        preview = fetch_indexer_table_preview(indexer, limit=limit)

        self.record_event({"action": "preview", "object_id": indexer.id, "object_type": "indexer"})
        return preview
