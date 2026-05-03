"""HTTP handlers for the MLModels feature.

Endpoints exposed (all under ``/api``):

- ``GET/POST    /ml_models``                        list + create
- ``GET         /ml_models/my``                     models owned by current user
- ``GET         /ml_models/recent``                 recent models for current user
- ``GET         /ml_models/archive``                archived models
- ``GET         /ml_models/favorites``              favourited models
- ``GET         /ml_models/tags``                   tag cloud
- ``GET         /ml_models/search``                 redirect to ``/ml_models?q=...``
- ``GET/POST/DELETE /ml_models/<id>``               read/update/delete a model
- ``POST/DELETE /ml_models/<id>/mute``              mute / unmute notifications
- ``POST        /ml_models/<id>/train``             enqueue a training job
- ``POST        /ml_models/<id>/predict``           enqueue a prediction job
- ``POST        /ml_models/<id>/stop``              cancel an in-flight training job
- ``POST        /ml_models/<id>/stop_predict``      cancel an in-flight prediction job
- ``POST        /ml_models/<id>/revert``            revert to a stored version
- ``POST        /ml_models/<id>/create_from_version`` fork a version into a new model
- ``POST        /ml_models/<id>/copy``              clone a model
- ``GET/POST    /ml_models/<id>/subscriptions``     list/add subscriptions
- ``DELETE      /ml_models/<id>/subscriptions/<sub_id>`` remove a subscription
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
    require_fields,
)
from redash.permissions import (
    can_modify,
    not_view_only,
    require_access,
    require_admin_or_owner,
    require_object_modify_permission,
    require_permission,
    view_only,
)
from redash.serializers import MLModelSerializer
from redash.tasks import (
    enqueue_predict_model,
    enqueue_train_model,
    kill_model_predicting,
    kill_model_training,
)

logger = logging.getLogger(__name__)


order_map = {
    "created_at": "created_at",
    "-created_at": "-created_at",
    "updated_at": "updated_at",
    "-updated_at": "-updated_at",
    "name": "name",
    "-name": "-name",
    "created_by": "users-name",
    "-created_by": "-users-name",
}
order_results = partial(_order_results, default_order="-created_at", allowed_orders=order_map)


class MLModelSearchResource(BaseResource):
    @require_permission("view_model")
    def get(self):
        """Search ML models by name (redirects to the list endpoint).

        ---
        tags:
          - MLModels
        security:
          - ApiKeyAuth: []
        parameters:
          - in: query
            name: q
            required: true
            schema:
              type: string
            description: Free-text search term matching the model name.
        responses:
          301:
            description: Redirect to ``/api/ml_models?q=<term>``.
          200:
            description: Empty list when no search term is provided.
        """
        term = request.args.get("q", "")
        if not term:
            return []
        self.record_event({"action": "search", "object_type": "ml_model", "term": term})
        new_location = url_for("ml_models", q=term, org_slug=current_org.slug)
        return {}, 301, {"Location": new_location}


class MLModelRecentResource(BaseResource):
    @require_permission("list_models")
    def get(self):
        """List the 10 most recently updated ML models for the current user.

        ---
        tags:
          - MLModels
        security:
          - ApiKeyAuth: []
        responses:
          200:
            description: Array of ML model objects ordered by ``updated_at`` desc.
        """
        results = (
            models.MLModel.by_user(self.current_user)
            .order_by(models.MLModel.updated_at.desc())
            .limit(10)
        )
        return MLModelSerializer(results).serialize()


class BaseMLModelListResource(BaseResource):
    def get_models(self, search_term):
        if search_term:
            return models.MLModel.search(
                search_term,
                self.current_user.group_ids,
                self.current_user.id,
                limit=None,
            )
        return models.MLModel.all_models(self.current_user.group_ids, self.current_user.id)

    @require_permission("list_models")
    def get(self):
        """List ML models visible to the current user.

        ---
        tags:
          - MLModels
        security:
          - ApiKeyAuth: []
        parameters:
          - in: query
            name: q
            schema:
              type: string
            description: Optional search term (matches model and creator name).
          - in: query
            name: tags
            schema:
              type: array
              items:
                type: string
            description: Filter by one or more tags.
          - in: query
            name: page
            schema:
              type: integer
              default: 1
          - in: query
            name: page_size
            schema:
              type: integer
              default: 25
        responses:
          200:
            description: Paginated list of ML models.
        """
        search_term = request.args.get("q", "")
        models_list = self.get_models(search_term)
        results = filter_by_tags(models_list, models.MLModel.tags)
        ordered_results = order_results(results, fallback=not bool(search_term))
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 25, type=int)
        return paginate(ordered_results, page=page, page_size=page_size, serializer=MLModelSerializer)


class MLModelListResource(BaseMLModelListResource):
    @require_permission("view_model")
    def post(self):
        """Create a new ML model bound to a Redash query.

        ---
        tags:
          - MLModels
        security:
          - ApiKeyAuth: []
        parameters:
          - in: body
            name: body
            required: true
            schema:
              type: object
              required: [name, query_id, options]
              properties:
                name:
                  type: string
                description:
                  type: string
                query_id:
                  type: integer
                  description: Redash query whose latest result feeds the model.
                options:
                  type: object
                  description: |
                    Model configuration: ``regressor``, ``features``, ``targets``,
                    ``train_size``, ``random_state``, etc.
                tags:
                  type: array
                  items:
                    type: string
                rearm:
                  type: integer
                  description: Cooldown (seconds) between auto-train runs.
        responses:
          200:
            description: The created MLModel.
          404:
            description: Query has no cached result yet.
          500:
            description: Internal error while persisting the model.
        """
        try:
            req = request.get_json(True)
            require_fields(req, ("options", "name", "query_id"))

            query = models.Query.get_by_id_and_org(req["query_id"], self.current_org)
            require_access(query, self.current_user, view_only)
            query_data = query.latest_query_data.data if query.latest_query_data else None
            if not query_data:
                abort(404, message="Query has no cached result; refresh the query first.")

            model = models.MLModel(
                name=req["name"],
                query_rel=query,
                user=self.current_user,
                options=req.get("options") or {},
                org=self.current_org,
                version=req.get("version") or 1,
                input_data=json.dumps(query_data),
                description=req.get("description"),
                rearm=req.get("rearm"),
                tags=req.get("tags") or [],
            )
            models.db.session.add(model)
            models.db.session.commit()

            self.record_event({"action": "create", "object_id": model.id, "object_type": "ml_model"})
            return MLModelSerializer(model).serialize()
        except Exception:
            logger.exception("Failed to create MLModel")
            abort(500, message="Failed to create model.")


class MLModelArchiveResource(BaseMLModelListResource):
    def get_models(self, search_term):
        if search_term:
            return models.MLModel.search(
                search_term,
                self.current_user.group_ids,
                self.current_user.id,
                limit=None,
                include_archived=True,
            )
        return models.MLModel.all_models(
            self.current_user.group_ids, self.current_user.id, include_archived=True
        )


class MyMLModelsResource(BaseResource):
    @require_permission("list_models")
    def get(self):
        search_term = request.args.get("q", "")
        if search_term:
            results = models.MLModel.search_by_user(search_term, self.current_user)
        else:
            results = models.MLModel.by_user(self.current_user)
        results = filter_by_tags(results, models.MLModel.tags)
        ordered_results = order_results(results, fallback=not bool(search_term))
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 25, type=int)
        return paginate(ordered_results, page, page_size, MLModelSerializer)


class MLModelResource(BaseResource):
    @require_permission("edit_model")
    def post(self, model_id):
        """Update an existing ML model definition.

        ---
        tags:
          - MLModels
        security:
          - ApiKeyAuth: []
        parameters:
          - in: path
            name: model_id
            required: true
            schema:
              type: integer
          - in: body
            name: body
            required: true
            schema:
              type: object
              description: |
                Partial model update. Read-only fields (``metrics``, ``state``,
                ``state_train``, ``state_predict``, ``model_blob``) are silently
                stripped.
        responses:
          200:
            description: The updated MLModel.
          400:
            description: Invalid options JSON.
          409:
            description: Stale data — the model was modified concurrently.
        """
        model = get_object_or_404(models.MLModel.get_by_id_and_org, model_id, self.current_org)
        model_def = request.get_json(force=True) or {}
        require_object_modify_permission(model, self.current_user)

        if "tags" in model_def:
            model_def["tags"] = [t for t in (model_def["tags"] or []) if t]

        if "options" in model_def and isinstance(model_def["options"], str):
            try:
                model_def["options"] = json.loads(model_def["options"])
            except ValueError:
                abort(400, message="Invalid options JSON")

        if "user" in model_def:
            user_dict = model_def.pop("user") or {}
            if "id" in user_dict:
                model_def["user_id"] = user_dict["id"]

        if "query" in model_def:
            query_dict = model_def.pop("query") or {}
            if "id" in query_dict:
                model_def["query_id"] = query_dict["id"]

        if "input_data" in model_def and model.query_rel and model.query_rel.latest_query_data:
            # Refresh cached data from the latest query result.
            model_def["input_data"] = json.dumps(model.query_rel.latest_query_data.data)

        # Strip read-only / nested fields the model doesn't accept
        for read_only in ("metrics", "state", "state_train", "state_predict", "model_blob"):
            model_def.pop(read_only, None)

        try:
            self.update_model(model, model_def)
            models.db.session.commit()
        except StaleDataError:
            abort(409)

        return MLModelSerializer(model).serialize()

    @require_permission("view_model")
    def get(self, model_id):
        """Retrieve a single ML model.

        ---
        tags:
          - MLModels
        security:
          - ApiKeyAuth: []
        parameters:
          - in: path
            name: model_id
            required: true
            schema:
              type: integer
        responses:
          200:
            description: The MLModel object, augmented with ``can_edit``.
          404:
            description: Model not found.
        """
        model = get_object_or_404(models.MLModel.get_by_id_and_org, model_id, self.current_org)
        require_access(model, self.current_user, view_only)
        result = MLModelSerializer(model).serialize()
        result["can_edit"] = can_modify(model, self.current_user)
        self.record_event({"action": "view", "object_id": model_id, "object_type": "ml_model"})
        return result

    @require_permission("edit_model")
    def delete(self, model_id):
        """Delete an ML model and all its versions / predictions / subscriptions.

        ---
        tags:
          - MLModels
        security:
          - ApiKeyAuth: []
        parameters:
          - in: path
            name: model_id
            required: true
            schema:
              type: integer
        responses:
          204:
            description: Model deleted.
          403:
            description: Caller is not the owner or an admin.
        """
        model = get_object_or_404(models.MLModel.get_by_id_and_org, model_id, self.current_org)
        require_admin_or_owner(model.user_id)
        models.MLModel.delete_model(model_id, self.current_org.id)
        return make_response("", 204)


class MLModelStopResource(BaseResource):
    @require_permission("edit_model")
    def post(self, model_id):
        """Cancel the in-flight training job for a model.

        ---
        tags:
          - MLModels
        security:
          - ApiKeyAuth: []
        parameters:
          - in: path
            name: model_id
            required: true
            schema:
              type: integer
        responses:
          204:
            description: Cancellation enqueued; model state set to ``error``.
          500:
            description: Internal error while signalling the worker.
        """
        model = get_object_or_404(models.MLModel.get_by_id_and_org, model_id, self.current_org)
        require_access(model, self.current_user, view_only)
        try:
            kill_model_training.delay(model_id)
            self.record_event({"action": "stop_train", "object_id": model.id, "object_type": "ml_model"})
            model.state = models.MLModel.ERROR_STATE
            model.state_train = models.MLModel.ERROR_STATE
            models.db.session.commit()
            return make_response("", 204)
        except Exception:
            logger.exception("Failed to stop training for model %s", model_id)
            return {"message": "Failed to stop training."}, 500


class MLModelStopPredictResource(BaseResource):
    @require_permission("edit_model")
    def post(self, model_id):
        """Cancel the in-flight prediction job for a model.

        ---
        tags:
          - MLModels
        security:
          - ApiKeyAuth: []
        parameters:
          - in: path
            name: model_id
            required: true
            schema:
              type: integer
        responses:
          204:
            description: Cancellation enqueued; model state set to ``error``.
          500:
            description: Internal error while signalling the worker.
        """
        model = get_object_or_404(models.MLModel.get_by_id_and_org, model_id, self.current_org)
        require_access(model, self.current_user, view_only)
        try:
            kill_model_predicting.delay(model_id)
            self.record_event({"action": "stop_predict", "object_id": model.id, "object_type": "ml_model"})
            model.state = models.MLModel.ERROR_STATE
            model.state_predict = models.MLModel.ERROR_STATE
            models.db.session.commit()
            return make_response("", 204)
        except Exception:
            logger.exception("Failed to stop prediction for model %s", model_id)
            return {"message": "Failed to stop prediction."}, 500


class MLModelTagsResource(BaseResource):
    @require_permission("list_models")
    def get(self):
        tags = models.MLModel.all_tags(self.current_org, self.current_user)
        return {"tags": [{"name": name, "count": count} for name, count in tags]}


class MLModelFavoriteListResource(BaseResource):
    @require_permission("list_models")
    def get(self):
        search_term = request.args.get("q")
        if search_term:
            base = models.MLModel.search(search_term, self.current_user.group_ids, limit=None)
            favorites = models.MLModel.favorites(self.current_user, base_query=base)
        else:
            favorites = models.MLModel.favorites(self.current_user)
        favorites = filter_by_tags(favorites, models.MLModel.tags)
        ordered = order_results(favorites, fallback=not bool(search_term))
        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 25, type=int)
        return paginate(ordered, page, page_size, MLModelSerializer)


class MLModelMuteResource(BaseResource):
    @require_permission("edit_model")
    def post(self, model_id):
        model = get_object_or_404(models.MLModel.get_by_id_and_org, model_id, self.current_org)
        require_admin_or_owner(model.user.id)
        model.options["muted"] = True
        models.db.session.commit()
        self.record_event({"action": "mute", "object_id": model.id, "object_type": "ml_model"})
        return MLModelSerializer(model).serialize()

    @require_permission("edit_model")
    def delete(self, model_id):
        model = get_object_or_404(models.MLModel.get_by_id_and_org, model_id, self.current_org)
        require_admin_or_owner(model.user.id)
        model.options["muted"] = False
        models.db.session.commit()
        self.record_event({"action": "unmute", "object_id": model.id, "object_type": "ml_model"})
        return MLModelSerializer(model).serialize()


class MLModelSubscriptionListResource(BaseResource):
    @require_permission("edit_model")
    def post(self, model_id):
        req = request.get_json(True) or {}
        model = get_object_or_404(models.MLModel.get_by_id_and_org, model_id, self.current_org)
        require_access(model, self.current_user, view_only)
        kwargs = {"ml_model": model, "user": self.current_user}
        if "destination_id" in req:
            destination = models.NotificationDestination.get_by_id_and_org(
                req["destination_id"], self.current_org
            )
            kwargs["destination"] = destination
        subscription = models.MLModelSubscription(**kwargs)
        models.db.session.add(subscription)
        models.db.session.commit()
        self.record_event(
            {
                "action": "subscribe",
                "object_id": model_id,
                "object_type": "ml_model",
                "destination": req.get("destination_id"),
            }
        )
        return subscription.to_dict()

    @require_permission("list_models")
    def get(self, model_id):
        model = get_object_or_404(models.MLModel.get_by_id_and_org, model_id, self.current_org)
        require_access(model, self.current_user, view_only)
        return [s.to_dict() for s in models.MLModelSubscription.all(model_id)]


class MLModelSubscriptionResource(BaseResource):
    @require_permission("edit_model")
    def delete(self, model_id, subscriber_id):
        subscription = models.MLModelSubscription.query.get_or_404(subscriber_id)
        require_admin_or_owner(subscription.user.id)
        models.db.session.delete(subscription)
        models.db.session.commit()
        self.record_event({"action": "unsubscribe", "object_id": model_id, "object_type": "ml_model"})
        return make_response("", 204)


class MLModelTrainResource(BaseResource):
    @require_permission("edit_model")
    def post(self, model_id):
        """Enqueue a training job for the model on the ``training`` RQ queue.

        The actual training runs in a dedicated ``ml-worker`` container with the
        scikit-learn stack installed. Use ``/api/ml_models/<id>/stop`` to cancel
        an in-flight job.

        ---
        tags:
          - MLModels
        security:
          - ApiKeyAuth: []
        parameters:
          - in: path
            name: model_id
            required: true
            schema:
              type: integer
        responses:
          200:
            description: Training job enqueued.
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Training started."
          400:
            description: Failed to enqueue (e.g. no cached query data).
        """
        model = get_object_or_404(models.MLModel.get_by_id_and_org, model_id, self.current_org)
        require_access(model, self.current_user, not_view_only)
        try:
            self.record_event({"action": "train", "object_id": model.id, "object_type": "ml_model"})
            enqueue_train_model(model_id, self.current_user.id)
            return make_response(jsonify({"message": "Training started."}), 200)
        except Exception:
            logger.exception("Failed to enqueue training for model %s", model_id)
            abort(400, message="Failed to start training.")


class MLModelPredictResource(BaseResource):
    @require_permission("view_model")
    def post(self, model_id):
        """Enqueue a prediction job that writes a new ``PredictionResult`` row.

        ---
        tags:
          - MLModels
        security:
          - ApiKeyAuth: []
        parameters:
          - in: path
            name: model_id
            required: true
            schema:
              type: integer
        responses:
          200:
            description: Prediction job enqueued.
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Prediction queued."
          400:
            description: Failed to enqueue (e.g. model has not been trained).
        """
        model = get_object_or_404(models.MLModel.get_by_id_and_org, model_id, self.current_org)
        require_access(model, self.current_user, not_view_only)
        try:
            self.record_event({"action": "predict", "object_id": model.id, "object_type": "ml_model"})
            enqueue_predict_model(model_id, self.current_user.id)
            return make_response(jsonify({"message": "Prediction queued."}), 200)
        except Exception:
            logger.exception("Failed to enqueue prediction for model %s", model_id)
            abort(400, message="Failed to start prediction.")


class MLModelVersionRevertResource(BaseResource):
    @require_permission("edit_model")
    def post(self, model_id):
        model = get_object_or_404(models.MLModel.get_by_id_and_org, model_id, self.current_org)
        require_object_modify_permission(model, self.current_user)
        version_number = (request.get_json(force=True) or {}).get("version")
        if not version_number:
            abort(400, message="Version number is required.")
        try:
            reverted = model.revert_to_version(version_number)
            return MLModelSerializer(reverted).serialize()
        except Exception as exc:
            logger.exception("Revert failed for model %s -> v%s", model_id, version_number)
            abort(400, message=str(exc))


class MLModelCreateFromVersionResource(BaseResource):
    @require_permission("edit_model")
    def post(self, model_id):
        model = get_object_or_404(models.MLModel.get_by_id_and_org, model_id, self.current_org)
        require_object_modify_permission(model, self.current_user)
        version_number = (request.get_json(force=True) or {}).get("version")
        if not version_number:
            abort(400, message="Version number is required.")
        try:
            new_model = model.create_from_version(version_number)
            return MLModelSerializer(new_model).serialize()
        except Exception as exc:
            logger.exception("Create-from-version failed for model %s -> v%s", model_id, version_number)
            abort(400, message=str(exc))


class MLModelCopyResource(BaseResource):
    @require_permission("edit_model")
    def post(self, model_id):
        model = get_object_or_404(models.MLModel.get_by_id_and_org, model_id, self.current_org)
        require_object_modify_permission(model, self.current_user)
        new_model = model.copy_model()
        return MLModelSerializer(new_model).serialize()
