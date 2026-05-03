"""HTTP handlers for ML model versions (training snapshots).

Endpoints (all under ``/api``):

- ``GET    /ml_models_versions``                     paginated version list
- ``GET    /ml_models_versions/my``                  versions owned by current user
- ``GET    /ml_models_versions/recent``              recent versions
- ``GET    /ml_models_versions/archive``             archived versions
- ``GET    /ml_models_versions/favorites``           favourited versions
- ``GET    /ml_models_versions/tags``                tag cloud
- ``GET    /ml_models_versions/search``              redirect to ``/ml_models_versions?q=...``
- ``GET/POST/DELETE /ml_models_versions/<id>``       read/update/delete a version
- ``GET    /ml_models/<model_id>/versions``          versions for a single model
"""

import json
import logging

from flask import jsonify, make_response, request, url_for
from flask_restful import abort
from funcy import partial
from sqlalchemy.orm.exc import StaleDataError

from redash import models
from redash.authentication.org_resolving import current_org
from redash.handlers.base import (
    BaseResource,
    filter_by_tags,
    get_object_or_404,
    order_results as _order_results,
    paginate,
)
from redash.permissions import (
    can_modify,
    require_access,
    require_admin_or_owner,
    require_object_modify_permission,
    require_permission,
    view_only,
)
from redash.serializers import MLModelVersionSerializer

logger = logging.getLogger(__name__)


order_map = {
    "created_at": "created_at",
    "-created_at": "-created_at",
    "updated_at": "updated_at",
    "-updated_at": "-updated_at",
    "version": "version",
    "-version": "-version",
}
order_results = partial(_order_results, default_order="-created_at", allowed_orders=order_map)


class MLModelVersionSearchResource(BaseResource):
    @require_permission("view_model")
    def get(self):
        term = request.args.get("q", "")
        if not term:
            return []
        self.record_event({"action": "search", "object_type": "ml_model_version", "term": term})
        return {}, 301, {"Location": url_for("ml_models_versions", q=term, org_slug=current_org.slug)}


class MLModelVersionRecentResource(BaseResource):
    @require_permission("list_models")
    def get(self):
        results = (
            models.MLModelVersion.by_user(self.current_user)
            .order_by(models.MLModelVersion.updated_at.desc())
            .limit(10)
        )
        return MLModelVersionSerializer(results).serialize()


class BaseMLModelVersionListResource(BaseResource):
    def get_models(self, search_term):
        if search_term:
            return models.MLModelVersion.search(
                search_term,
                self.current_user.group_ids,
                self.current_user.id,
                limit=None,
            )
        return models.MLModelVersion.all_models(self.current_user.group_ids, self.current_user.id)

    @require_permission("list_models")
    def get(self):
        search_term = request.args.get("q", "")
        models_list = self.get_models(search_term)
        results = filter_by_tags(models_list, models.MLModelVersion.tags)
        ordered = order_results(results, fallback=not bool(search_term))
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 25, type=int)
        return paginate(ordered, page=page, page_size=page_size, serializer=MLModelVersionSerializer)


class MLModelVersionListResource(BaseMLModelVersionListResource):
    """Versions are created by ``MLModel.train`` automatically; the public POST
    endpoint exists only as a convenience for ad-hoc snapshots from scripts.
    """

    @require_permission("edit_model")
    def post(self):
        try:
            req = request.get_json(True) or {}
            model_id = req.get("model_id")
            if not model_id:
                abort(400, message="model_id is required.")
            model = get_object_or_404(models.MLModel.get_by_id_and_org, model_id, self.current_org)
            require_access(model, self.current_user, view_only)
            version = model.save_new_version(req.get("changes") or "Manual snapshot")
            return MLModelVersionSerializer(version).serialize()
        except Exception:
            logger.exception("Failed to create MLModelVersion")
            abort(500, message="Failed to create version.")


class MLModelVersionArchiveResource(BaseMLModelVersionListResource):
    def get_models(self, search_term):
        if search_term:
            return models.MLModelVersion.search(
                search_term,
                self.current_user.group_ids,
                self.current_user.id,
                limit=None,
                include_archived=True,
            )
        return models.MLModelVersion.all_models(
            self.current_user.group_ids, self.current_user.id, include_archived=True
        )


class MyMLModelVersionsResource(BaseResource):
    @require_permission("list_models")
    def get(self):
        search_term = request.args.get("q", "")
        if search_term:
            results = models.MLModelVersion.search_by_user(search_term, self.current_user)
        else:
            results = models.MLModelVersion.by_user(self.current_user)
        results = filter_by_tags(results, models.MLModelVersion.tags)
        ordered = order_results(results, fallback=not bool(search_term))
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 25, type=int)
        return paginate(ordered, page, page_size, MLModelVersionSerializer)


class MLModelVersionResource(BaseResource):
    @require_permission("edit_model")
    def post(self, model_version_id):
        version = get_object_or_404(
            models.MLModelVersion.get_by_id_and_org, model_version_id, self.current_org
        )
        version_def = request.get_json(force=True) or {}
        require_object_modify_permission(version, self.current_user)

        if "tags" in version_def:
            version_def["tags"] = [t for t in (version_def["tags"] or []) if t]
        if "options" in version_def and isinstance(version_def["options"], str):
            try:
                version_def["options"] = json.loads(version_def["options"])
            except ValueError:
                abort(400, message="Invalid options JSON")

        for nested in ("user", "query", "model"):
            value = version_def.pop(nested, None)
            if isinstance(value, dict) and "id" in value:
                version_def["{0}_id".format(nested if nested != "query" else "query")] = value["id"]

        for read_only in ("metrics", "state", "state_train", "state_predict", "model_blob"):
            version_def.pop(read_only, None)

        try:
            self.update_model(version, version_def)
            models.db.session.commit()
        except StaleDataError:
            abort(409)
        return MLModelVersionSerializer(version).serialize()

    @require_permission("view_model")
    def get(self, model_version_id):
        version = get_object_or_404(
            models.MLModelVersion.get_by_id_and_org, model_version_id, self.current_org
        )
        require_access(version, self.current_user, view_only)
        result = MLModelVersionSerializer(version).serialize()
        result["can_edit"] = can_modify(version, self.current_user)
        self.record_event(
            {"action": "view", "object_id": model_version_id, "object_type": "ml_model_version"}
        )
        return result

    @require_permission("edit_model")
    def delete(self, model_version_id):
        version = get_object_or_404(
            models.MLModelVersion.get_by_id_and_org, model_version_id, self.current_org
        )
        require_admin_or_owner(version.user_id)
        models.db.session.delete(version)
        models.db.session.commit()
        return make_response("", 204)


class MLModelVersionTagsResource(BaseResource):
    @require_permission("list_models")
    def get(self):
        tags = models.MLModelVersion.all_tags(self.current_org, self.current_user)
        return {"tags": [{"name": name, "count": count} for name, count in tags]}


class MLModelVersionFavoriteListResource(BaseResource):
    @require_permission("list_models")
    def get(self):
        search_term = request.args.get("q")
        if search_term:
            base = models.MLModelVersion.search(search_term, self.current_user.group_ids, limit=None)
            favorites = models.MLModelVersion.favorites(self.current_user, base_query=base)
        else:
            favorites = models.MLModelVersion.favorites(self.current_user)
        favorites = filter_by_tags(favorites, models.MLModelVersion.tags)
        ordered = order_results(favorites, fallback=not bool(search_term))
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 25, type=int)
        return paginate(ordered, page, page_size, MLModelVersionSerializer)


class ModelVersionsResource(BaseResource):
    @require_permission("list_models")
    def get(self, model_id):
        get_object_or_404(models.MLModel.get_by_id_and_org, model_id, self.current_org)
        versions = models.MLModelVersion.get_by_model_id_and_org(model_id, self.current_org)
        if not versions:
            return make_response(jsonify([]), 200)
        return MLModelVersionSerializer(versions).serialize()
