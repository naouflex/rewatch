"""
This will eventually replace all the `to_dict` methods of the different model
classes we have. This will ensure cleaner code and better
separation of concerns.
"""

from flask_login import current_user
from funcy import project
from rq.job import JobStatus
from rq.timeouts import JobTimeoutException

from rewatch import models
from rewatch.models.parameterized_query import ParameterizedQuery
from rewatch.permissions import has_access, view_only
from rewatch.serializers.query_result import (
    serialize_query_result,
    serialize_query_result_to_dsv,
    serialize_query_result_to_xlsx,
)


def public_widget(widget):
    res = {
        "id": widget.id,
        "width": widget.width,
        "options": widget.options,
        "text": widget.text,
        "updated_at": widget.updated_at,
        "created_at": widget.created_at,
    }

    v = widget.visualization
    if v and v.id:
        res["visualization"] = {
            "type": v.type,
            "name": v.name,
            "description": v.description,
            "options": v.options,
            "updated_at": v.updated_at,
            "created_at": v.created_at,
            "query": {
                "id": v.query_rel.id,
                "name": v.query_rel.name,
                "description": v.query_rel.description,
                "options": v.query_rel.options,
            },
        }

    return res


def public_dashboard(dashboard):
    dashboard_dict = project(
        serialize_dashboard(dashboard, with_favorite_state=False),
        ("name", "layout", "dashboard_filters_enabled", "updated_at", "created_at", "options"),
    )

    widget_list = (
        models.Widget.query.filter(models.Widget.dashboard_id == dashboard.id)
        .outerjoin(models.Visualization)
        .outerjoin(models.Query)
    )

    dashboard_dict["widgets"] = [public_widget(w) for w in widget_list]
    return dashboard_dict


class Serializer:
    pass


class QuerySerializer(Serializer):
    def __init__(self, object_or_list, **kwargs):
        self.object_or_list = object_or_list
        self.options = kwargs

    def serialize(self):
        if isinstance(self.object_or_list, models.Query):
            result = serialize_query(self.object_or_list, **self.options)
            if self.options.get("with_favorite_state", True) and not current_user.is_api_user():
                result["is_favorite"] = models.Favorite.is_favorite(current_user.id, self.object_or_list)
        else:
            result = [serialize_query(query, **self.options) for query in self.object_or_list]
            if self.options.get("with_favorite_state", True):
                queries = list(self.object_or_list)
                favorites = models.Favorite.query.filter(
                    models.Favorite.object_id.in_([o.id for o in queries]),
                    models.Favorite.object_type == "Query",
                    models.Favorite.user_id == current_user.id,
                )
                favorites_dict = {fav.object_id: fav for fav in favorites}

                for query in result:
                    favorite = favorites_dict.get(query["id"])
                    query["is_favorite"] = favorite is not None
                    if favorite:
                        query["starred_at"] = favorite.created_at

        return result


def serialize_query(
    query,
    with_stats=False,
    with_visualizations=False,
    with_user=True,
    with_last_modified_by=True,
):
    d = {
        "id": query.id,
        "latest_query_data_id": query.latest_query_data_id,
        "name": query.name,
        "description": query.description,
        "query": query.query_text,
        "query_hash": query.query_hash,
        "schedule": query.schedule,
        "api_key": query.api_key,
        "is_archived": query.is_archived,
        "is_draft": query.is_draft,
        "updated_at": query.updated_at,
        "created_at": query.created_at,
        "data_source_id": query.data_source_id,
        "options": query.options,
        "version": query.version,
        "tags": query.tags or [],
        "is_safe": query.parameterized.is_safe,
    }

    if with_user:
        d["user"] = query.user.to_dict()
    else:
        d["user_id"] = query.user_id

    if with_last_modified_by:
        d["last_modified_by"] = query.last_modified_by.to_dict() if query.last_modified_by is not None else None
    else:
        d["last_modified_by_id"] = query.last_modified_by_id

    if with_stats:
        if query.latest_query_data is not None:
            d["retrieved_at"] = query.retrieved_at
            d["runtime"] = query.runtime
        else:
            d["retrieved_at"] = None
            d["runtime"] = None

    if with_visualizations:
        d["visualizations"] = [serialize_visualization(vis, with_query=False) for vis in query.visualizations]

    return d


def serialize_visualization(object, with_query=True):
    d = {
        "id": object.id,
        "type": object.type,
        "name": object.name,
        "description": object.description,
        "options": object.options,
        "updated_at": object.updated_at,
        "created_at": object.created_at,
    }

    if with_query:
        d["query"] = serialize_query(object.query_rel)

    return d


def serialize_widget(object):
    d = {
        "id": object.id,
        "width": object.width,
        "options": object.options,
        "dashboard_id": object.dashboard_id,
        "text": object.text,
        "updated_at": object.updated_at,
        "created_at": object.created_at,
    }

    if object.visualization and object.visualization.id:
        d["visualization"] = serialize_visualization(object.visualization)

    return d


def serialize_alert(alert, full=True, with_favorite_state=True):
    d = {
        "id": alert.id,
        "name": alert.name,
        "options": alert.options,
        "state": alert.state,
        "last_triggered_at": alert.last_triggered_at,
        "updated_at": alert.updated_at,
        "created_at": alert.created_at,
        "rearm": alert.rearm,
        "tags": alert.tags or [],
        "is_archived": bool(alert.is_archived),
    }

    if full:
        d["query"] = serialize_query(alert.query_rel)
        d["user"] = alert.user.to_dict()
    else:
        d["query_id"] = alert.query_id
        d["user_id"] = alert.user_id

    if with_favorite_state:
        try:
            if not current_user.is_api_user():
                d["is_favorite"] = models.Favorite.is_favorite(current_user.id, alert)
        except Exception:
            # ``current_user`` may be unbound when the serializer is invoked outside a
            # request context (e.g. inside a destination ``notify`` running on a worker).
            pass

    return d


def serialize_alert_event(alert_event, include_alert=True, include_destination=True):
    d = {
        "id": alert_event.id,
        "alert_id": alert_event.alert_id,
        "alert_type": alert_event.alert_type,
        "query_id": alert_event.query_id,
        "destination_id": alert_event.destination_id,
        "user_id": alert_event.user_id,
        "state": alert_event.state,
        "status": alert_event.status,
        "content": alert_event.content,
        "additional_properties": alert_event.additional_properties or {},
        "row_index": alert_event.row_index,
        "is_archived": bool(alert_event.is_archived),
        "created_at": alert_event.created_at,
    }

    if include_alert and alert_event.alert is not None:
        d["alert"] = {"id": alert_event.alert.id, "name": alert_event.alert.name}

    if include_destination and alert_event.destination is not None:
        d["destination"] = {
            "id": alert_event.destination.id,
            "name": alert_event.destination.name,
            "type": alert_event.destination.type,
        }

    if alert_event.user is not None:
        d["user"] = {"id": alert_event.user.id, "name": alert_event.user.name}

    return d


def serialize_forum_comment(comment, like_summary=None):
    if like_summary is None:
        user_id = None if current_user.is_api_user() else current_user.id
        like_summary = {
            "like_count": models.ForumLike.count_for("comment", comment.id),
            "is_liked": models.ForumLike.is_liked(user_id, "comment", comment.id),
        }

    return {
        "id": comment.id,
        "post_id": comment.post_id,
        "parent_id": comment.parent_id,
        "body": comment.body,
        "created_at": comment.created_at,
        "updated_at": comment.updated_at,
        "user": comment.user.to_dict(),
        "user_id": comment.user_id,
        "like_count": like_summary["like_count"],
        "is_liked": like_summary["is_liked"],
    }


def _serialize_forum_comments(comments):
    comment_ids = [comment.id for comment in comments]
    user_id = None if current_user.is_api_user() else current_user.id
    like_summaries = models.ForumLike.summaries(user_id, "comment", comment_ids)
    return [serialize_forum_comment(comment, like_summaries.get(comment.id)) for comment in comments]


def serialize_forum_post(post, full=True, like_summary=None, reply_count=None):
    body = post.body or ""
    user_id = None if current_user.is_api_user() else current_user.id

    if like_summary is None:
        like_summary = {
            "like_count": models.ForumLike.count_for("post", post.id),
            "is_liked": models.ForumLike.is_liked(user_id, "post", post.id),
        }

    if reply_count is None:
        reply_count = models.ForumComment.query.filter(models.ForumComment.post_id == post.id).count()

    d = {
        "id": post.id,
        "title": post.title,
        "category": post.category,
        "created_at": post.created_at,
        "updated_at": post.updated_at,
        "user": post.user.to_dict(),
        "user_id": post.user_id,
        "like_count": like_summary["like_count"],
        "is_liked": like_summary["is_liked"],
        "reply_count": reply_count,
    }
    if full:
        d["body"] = body
        comments = models.ForumComment.for_post(post.id).all()
        d["comments"] = _serialize_forum_comments(comments)
    else:
        preview = body.replace("\n", " ").strip()
        d["excerpt"] = preview[:240] + ("..." if len(preview) > 240 else "")
    return d


def serialize_indexer(indexer, full=True, with_favorite_state=True):
    d = {
        "id": indexer.id,
        "name": indexer.name,
        "options": indexer.options or {},
        "tags": indexer.tags or [],
        "is_archived": bool(indexer.is_archived),
        "last_triggered_at": indexer.last_triggered_at,
        "updated_at": indexer.updated_at,
        "created_at": indexer.created_at,
    }

    if full:
        d["query"] = serialize_query(indexer.query_rel)
        d["user"] = indexer.user.to_dict()
        if indexer.data_source is not None:
            d["data_source"] = {
                "id": indexer.data_source.id,
                "name": indexer.data_source.name,
                "type": indexer.data_source.type,
            }
        else:
            d["data_source"] = None
    else:
        d["query_id"] = indexer.query_id
        d["user_id"] = indexer.user_id
        d["data_source_id"] = indexer.data_source_id

    if with_favorite_state:
        try:
            if not current_user.is_api_user():
                d["is_favorite"] = models.Favorite.is_favorite(current_user.id, indexer)
        except Exception:
            pass

    return d


def serialize_dashboard(obj, with_widgets=False, user=None, with_favorite_state=True):
    layout = obj.layout

    widgets = []

    if with_widgets:
        for w in obj.widgets:
            if w.visualization_id is None:
                widgets.append(serialize_widget(w))
            elif user and has_access(w.visualization.query_rel, user, view_only):
                widgets.append(serialize_widget(w))
            else:
                widget = project(
                    serialize_widget(w),
                    (
                        "id",
                        "width",
                        "dashboard_id",
                        "options",
                        "created_at",
                        "updated_at",
                    ),
                )
                widget["restricted"] = True
                widgets.append(widget)
    else:
        widgets = None

    d = {
        "id": obj.id,
        "slug": obj.name_as_slug,
        "name": obj.name,
        "user_id": obj.user_id,
        "user": {
            "id": obj.user.id,
            "name": obj.user.name,
            "email": obj.user.email,
            "profile_image_url": obj.user.profile_image_url,
        },
        "layout": layout,
        "dashboard_filters_enabled": obj.dashboard_filters_enabled,
        "widgets": widgets,
        "options": obj.options,
        "is_archived": obj.is_archived,
        "is_draft": obj.is_draft,
        "tags": obj.tags or [],
        "updated_at": obj.updated_at,
        "created_at": obj.created_at,
        "version": obj.version,
    }

    return d


class DashboardSerializer(Serializer):
    def __init__(self, object_or_list, **kwargs):
        self.object_or_list = object_or_list
        self.options = kwargs

    def serialize(self):
        if isinstance(self.object_or_list, models.Dashboard):
            result = serialize_dashboard(self.object_or_list, **self.options)
            if self.options.get("with_favorite_state", True) and not current_user.is_api_user():
                result["is_favorite"] = models.Favorite.is_favorite(current_user.id, self.object_or_list)
        else:
            result = [serialize_dashboard(obj, **self.options) for obj in self.object_or_list]
            if self.options.get("with_favorite_state", True):
                dashboards = list(self.object_or_list)
                favorites = models.Favorite.query.filter(
                    models.Favorite.object_id.in_([o.id for o in dashboards]),
                    models.Favorite.object_type == "Dashboard",
                    models.Favorite.user_id == current_user.id,
                )
                favorites_dict = {fav.object_id: fav for fav in favorites}

                for query in result:
                    favorite = favorites_dict.get(query["id"])
                    query["is_favorite"] = favorite is not None
                    if favorite:
                        query["starred_at"] = favorite.created_at

        return result


def serialize_ml_model(model, full=True, changes=False, with_favorite_state=True):
    """Serialize an MLModel (or an MLModelVersion when ``changes`` is True)."""
    d = {
        "id": model.id,
        "name": model.name,
        "description": model.description,
        "version": model.version,
        "created_at": model.created_at,
        "updated_at": model.updated_at,
        "user_id": model.user_id,
        "org_id": model.org_id,
        "is_archived": bool(model.is_archived),
        "tags": model.tags or [],
        "metrics": model.metrics,
        "last_triggered_at": model.last_triggered_at,
        "rearm": model.rearm,
        "state": model.state,
        "state_train": model.state_train,
        "state_predict": model.state_predict,
        "options": model.options or {},
    }

    if full:
        if model.query_rel is not None:
            d["query"] = serialize_query(model.query_rel)
        if model.user is not None:
            d["user"] = model.user.to_dict()
        if changes and getattr(model, "model", None) is not None:
            d["model"] = serialize_ml_model(model.model, full=False, changes=False, with_favorite_state=False)
    else:
        d["query_id"] = model.query_id
        d["user_id"] = model.user_id
        if changes:
            d["model_id"] = getattr(model, "model_id", None)

    if changes:
        d["changes"] = getattr(model, "changes", None)

    if with_favorite_state:
        try:
            if not current_user.is_api_user():
                d["is_favorite"] = models.Favorite.is_favorite(current_user.id, model)
        except Exception:
            pass

    return d


class MLModelSerializer(Serializer):
    def __init__(self, object_or_list, **kwargs):
        self.object_or_list = object_or_list
        self.options = kwargs
        self.with_favorites_state = kwargs.get("with_favorite_state", True)

    def serialize(self):
        if isinstance(self.object_or_list, models.MLModel):
            return serialize_ml_model(self.object_or_list, with_favorite_state=self.with_favorites_state)
        objects = list(self.object_or_list)
        result = [serialize_ml_model(obj, with_favorite_state=False) for obj in objects]
        if self.with_favorites_state:
            try:
                favorite_ids = models.Favorite.are_favorites(current_user.id, objects)
                for item in result:
                    item["is_favorite"] = item["id"] in favorite_ids
            except Exception:
                pass
        return result


class MLModelVersionSerializer(Serializer):
    def __init__(self, object_or_list, **kwargs):
        self.object_or_list = object_or_list
        self.options = kwargs
        self.with_favorites_state = kwargs.get("with_favorite_state", True)

    def serialize(self):
        if isinstance(self.object_or_list, (models.MLModel, models.MLModelVersion)):
            return serialize_ml_model(self.object_or_list, changes=True, with_favorite_state=self.with_favorites_state)
        objects = list(self.object_or_list)
        result = [serialize_ml_model(obj, changes=True, with_favorite_state=False) for obj in objects]
        if self.with_favorites_state:
            try:
                favorite_ids = models.Favorite.are_favorites(current_user.id, objects)
                for item in result:
                    item["is_favorite"] = item["id"] in favorite_ids
            except Exception:
                pass
        return result


def serialize_prediction_result(prediction, with_nested_objects=True, include_input_data=False):
    from rewatch.utils import json_loads

    content = None
    if prediction.content:
        try:
            content = serialize_query_result(json_loads(prediction.content), False)
        except Exception:
            content = None

    d = {
        "id": prediction.id,
        "model_id": prediction.model_id,
        "query_id": prediction.query_id,
        "user_id": prediction.user_id,
        "org_id": prediction.org_id,
        "destination_id": prediction.destination_id,
        "content": content,
        "additional_properties": prediction.additional_properties or {},
        "created_at": prediction.created_at,
        "updated_at": prediction.updated_at,
        "tags": prediction.tags or [],
        "is_archived": bool(prediction.is_archived),
        "model_version": prediction.model_version,
    }

    if include_input_data:
        d["input_data"] = prediction.input_data

    if with_nested_objects:
        if prediction.user is not None:
            d["user"] = prediction.user.to_dict()
        if prediction.query_rel is not None:
            d["query"] = serialize_query(prediction.query_rel)
        if prediction.destination is not None:
            d["destination"] = prediction.destination.to_dict(all=True)
        if prediction.model is not None:
            d["model"] = serialize_ml_model(prediction.model, with_favorite_state=False)

    return d


class PredictionResultSerializer(Serializer):
    def __init__(self, object_or_list, **kwargs):
        self.object_or_list = object_or_list
        self.options = kwargs
        self.with_favorites_state = kwargs.get("with_favorite_state", True)
        self.include_input_data = kwargs.get("include_input_data", False)

    def serialize(self):
        if isinstance(self.object_or_list, models.PredictionResult):
            result = serialize_prediction_result(
                self.object_or_list, include_input_data=self.include_input_data
            )
            if self.with_favorites_state:
                try:
                    if not current_user.is_api_user():
                        result["is_favorite"] = models.Favorite.is_favorite(current_user.id, self.object_or_list)
                except Exception:
                    pass
            return result
        objects = list(self.object_or_list)
        result = [serialize_prediction_result(obj, include_input_data=self.include_input_data) for obj in objects]
        if self.with_favorites_state:
            try:
                favorite_ids = models.Favorite.are_favorites(current_user.id, objects)
                for item in result:
                    item["is_favorite"] = item["id"] in favorite_ids
            except Exception:
                pass
        return result


def serialize_job(job):
    # TODO: this is mapping to the old Job class statuses. Need to update the client side and remove this
    STATUSES = {
        JobStatus.QUEUED: 1,
        JobStatus.STARTED: 2,
        JobStatus.FINISHED: 3,
        JobStatus.FAILED: 4,
        JobStatus.CANCELED: 5,
        JobStatus.DEFERRED: 6,
        JobStatus.SCHEDULED: 7,
    }

    job_status = job.get_status()
    if job.is_started:
        updated_at = job.started_at or 0
    else:
        updated_at = 0

    status = STATUSES[job_status]
    result = query_result_id = None

    if job.is_cancelled:
        error = "Query cancelled by user."
        status = 4
    elif isinstance(job.result, Exception):
        error = str(job.result)
        status = 4
    elif isinstance(job.result, dict) and "error" in job.result:
        error = job.result["error"]
        status = 4
    else:
        error = ""
        result = query_result_id = job.result

    return {
        "job": {
            "id": job.id,
            "updated_at": updated_at,
            "status": status,
            "error": error,
            "result": result,
            "query_result_id": query_result_id,
        }
    }
