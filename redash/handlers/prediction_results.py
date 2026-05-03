"""HTTP handlers for prediction results.

Endpoints (all under ``/api``):

- ``GET    /predictions``                          paginated list
- ``GET    /predictions/my``                       predictions owned by current user
- ``GET    /predictions/recent``                   recent predictions
- ``GET    /predictions/archive``                  archived predictions
- ``GET    /predictions/favorites``                favourited predictions
- ``GET    /predictions/tags``                     tag cloud
- ``GET    /predictions/search``                   redirect to ``/predictions?q=...``
- ``GET/POST/DELETE /predictions/<id>``            read/update/delete one prediction
- ``GET    /ml_models/<model_id>/predictions``     predictions for a single model
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
from redash.serializers import PredictionResultSerializer

logger = logging.getLogger(__name__)


order_map = {
    "created_at": "created_at",
    "-created_at": "-created_at",
    "updated_at": "updated_at",
    "-updated_at": "-updated_at",
}
order_results = partial(_order_results, default_order="-created_at", allowed_orders=order_map)


class PredictionResultSearchResource(BaseResource):
    @require_permission("view_model")
    def get(self):
        term = request.args.get("q", "")
        if not term:
            return []
        self.record_event({"action": "search", "object_type": "prediction_result", "term": term})
        return {}, 301, {"Location": url_for("prediction_results", q=term, org_slug=current_org.slug)}


class PredictionResultRecentResource(BaseResource):
    @require_permission("list_models")
    def get(self):
        results = (
            models.PredictionResult.by_user(self.current_user)
            .order_by(models.PredictionResult.created_at.desc())
            .limit(10)
        )
        return PredictionResultSerializer(results).serialize()


class BasePredictionResultListResource(BaseResource):
    def get_predictions(self, search_term):
        if search_term:
            return models.PredictionResult.search(
                search_term,
                self.current_user.group_ids,
                self.current_user.id,
                limit=None,
            )
        return models.PredictionResult.all_predictions(
            self.current_user.group_ids, self.current_user.id
        )

    @require_permission("list_models")
    def get(self):
        search_term = request.args.get("q", "")
        predictions_list = self.get_predictions(search_term)
        results = filter_by_tags(predictions_list, models.PredictionResult.tags)
        ordered = order_results(results, fallback=not bool(search_term))
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 25, type=int)
        return paginate(
            ordered, page=page, page_size=page_size, serializer=PredictionResultSerializer
        )


class PredictionResultListResource(BasePredictionResultListResource):
    """The POST endpoint is intentionally read-only (PredictionResults are
    produced by ``MLModel.predict``); we only accept GET on this resource.
    """


class PredictionResultArchiveResource(BasePredictionResultListResource):
    def get_predictions(self, search_term):
        if search_term:
            return models.PredictionResult.search(
                search_term,
                self.current_user.group_ids,
                self.current_user.id,
                limit=None,
                include_archived=True,
            )
        return models.PredictionResult.all_predictions(
            self.current_user.group_ids, self.current_user.id, include_archived=True
        )


class MyPredictionResultsResource(BaseResource):
    @require_permission("list_models")
    def get(self):
        search_term = request.args.get("q", "")
        if search_term:
            results = models.PredictionResult.search_by_user(search_term, self.current_user)
        else:
            results = models.PredictionResult.by_user(self.current_user)
        results = filter_by_tags(results, models.PredictionResult.tags)
        ordered = order_results(results, fallback=not bool(search_term))
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 25, type=int)
        return paginate(ordered, page, page_size, PredictionResultSerializer)


class PredictionResultResource(BaseResource):
    @require_permission("edit_model")
    def post(self, prediction_result_id):
        prediction = get_object_or_404(
            models.PredictionResult.get_by_id_and_org, prediction_result_id, self.current_org
        )
        prediction_def = request.get_json(force=True) or {}
        require_object_modify_permission(prediction, self.current_user)

        if "tags" in prediction_def:
            prediction_def["tags"] = [t for t in (prediction_def["tags"] or []) if t]

        for nested in ("user", "query", "model", "destination"):
            value = prediction_def.pop(nested, None)
            if isinstance(value, dict) and "id" in value:
                prediction_def["{0}_id".format(nested)] = value["id"]

        prediction_def.pop("destinations", None)

        if "additional_properties" in prediction_def and isinstance(
            prediction_def["additional_properties"], str
        ):
            try:
                prediction_def["additional_properties"] = json.loads(
                    prediction_def["additional_properties"]
                )
            except ValueError:
                abort(400, message="Invalid additional_properties JSON")

        prediction_def.pop("content", None)

        try:
            self.update_model(prediction, prediction_def)
            models.db.session.commit()
        except StaleDataError:
            abort(409)
        return PredictionResultSerializer(prediction).serialize()

    @require_permission("view_model")
    def get(self, prediction_result_id):
        prediction = get_object_or_404(
            models.PredictionResult.get_by_id_and_org, prediction_result_id, self.current_org
        )
        require_access(prediction, self.current_user, view_only)
        result = PredictionResultSerializer(prediction, include_input_data=True).serialize()
        result["can_edit"] = can_modify(prediction, self.current_user)
        self.record_event(
            {"action": "view", "object_id": prediction_result_id, "object_type": "prediction_result"}
        )
        return result

    @require_permission("edit_model")
    def delete(self, prediction_result_id):
        prediction = get_object_or_404(
            models.PredictionResult.get_by_id_and_org, prediction_result_id, self.current_org
        )
        require_admin_or_owner(prediction.user_id)
        models.db.session.delete(prediction)
        models.db.session.commit()
        return make_response("", 204)


class PredictionResultTagsResource(BaseResource):
    @require_permission("list_models")
    def get(self):
        tags = models.PredictionResult.all_tags(self.current_org, self.current_user)
        return {"tags": [{"name": name, "count": count} for name, count in tags]}


class PredictionResultFavoriteListResource(BaseResource):
    @require_permission("list_models")
    def get(self):
        search_term = request.args.get("q")
        if search_term:
            base = models.PredictionResult.search(search_term, self.current_user.group_ids, limit=None)
            favorites = models.PredictionResult.favorites(self.current_user, base_query=base)
        else:
            favorites = models.PredictionResult.favorites(self.current_user)
        favorites = filter_by_tags(favorites, models.PredictionResult.tags)
        ordered = order_results(favorites, fallback=not bool(search_term))
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 25, type=int)
        return paginate(ordered, page, page_size, PredictionResultSerializer)


class ModelPredictionsResource(BaseResource):
    @require_permission("list_models")
    def get(self, model_id):
        get_object_or_404(models.MLModel.get_by_id_and_org, model_id, self.current_org)
        predictions = models.PredictionResult.get_by_model_id_and_org(model_id, self.current_org)
        if not predictions:
            return make_response(jsonify([]), 200)
        return PredictionResultSerializer(predictions).serialize()
