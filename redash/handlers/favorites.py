from sqlalchemy.exc import IntegrityError

from redash import models
from redash.handlers.base import BaseResource, get_object_or_404
from redash.permissions import require_access, view_only


class QueryFavoriteResource(BaseResource):
    def post(self, query_id):
        query = get_object_or_404(models.Query.get_by_id_and_org, query_id, self.current_org)
        require_access(query, self.current_user, view_only)

        fav = models.Favorite(org_id=self.current_org.id, object=query, user=self.current_user)
        models.db.session.add(fav)

        try:
            models.db.session.commit()
        except IntegrityError as e:
            if "unique_favorite" in str(e):
                models.db.session.rollback()
            else:
                raise e

        self.record_event({"action": "favorite", "object_id": query.id, "object_type": "query"})

    def delete(self, query_id):
        query = get_object_or_404(models.Query.get_by_id_and_org, query_id, self.current_org)
        require_access(query, self.current_user, view_only)

        models.Favorite.query.filter(
            models.Favorite.object_id == query_id,
            models.Favorite.object_type == "Query",
            models.Favorite.user == self.current_user,
        ).delete()
        models.db.session.commit()

        self.record_event({"action": "favorite", "object_id": query.id, "object_type": "query"})


class DashboardFavoriteResource(BaseResource):
    def post(self, object_id):
        dashboard = get_object_or_404(models.Dashboard.get_by_id_and_org, object_id, self.current_org)
        fav = models.Favorite(org_id=self.current_org.id, object=dashboard, user=self.current_user)
        models.db.session.add(fav)

        try:
            models.db.session.commit()
        except IntegrityError as e:
            if "unique_favorite" in str(e):
                models.db.session.rollback()
            else:
                raise e

        self.record_event(
            {
                "action": "favorite",
                "object_id": dashboard.id,
                "object_type": "dashboard",
            }
        )

    def delete(self, object_id):
        dashboard = get_object_or_404(models.Dashboard.get_by_id_and_org, object_id, self.current_org)
        models.Favorite.query.filter(
            models.Favorite.object == dashboard,
            models.Favorite.user == self.current_user,
        ).delete()
        models.db.session.commit()
        self.record_event(
            {
                "action": "unfavorite",
                "object_id": dashboard.id,
                "object_type": "dashboard",
            }
        )


def _toggle_favorite(get_by_id, object_id, current_org, current_user, object_type, action_record):
    """Shared favorite/unfavorite implementation for ML model resources."""
    obj = get_object_or_404(get_by_id, object_id, current_org)
    fav = models.Favorite(org_id=current_org.id, object=obj, user=current_user)
    models.db.session.add(fav)
    try:
        models.db.session.commit()
    except IntegrityError as exc:
        if "unique_favorite" in str(exc):
            models.db.session.rollback()
        else:
            raise
    action_record({"action": "favorite", "object_id": obj.id, "object_type": object_type})


class MLModelFavoriteResource(BaseResource):
    def post(self, model_id):
        model = get_object_or_404(models.MLModel.get_by_id_and_org, model_id, self.current_org)
        require_access(model, self.current_user, view_only)
        _toggle_favorite(
            models.MLModel.get_by_id_and_org,
            model_id,
            self.current_org,
            self.current_user,
            "ml_model",
            self.record_event,
        )

    def delete(self, model_id):
        model = get_object_or_404(models.MLModel.get_by_id_and_org, model_id, self.current_org)
        models.Favorite.query.filter(
            models.Favorite.object_id == model.id,
            models.Favorite.object_type == "MLModel",
            models.Favorite.user == self.current_user,
        ).delete()
        models.db.session.commit()
        self.record_event(
            {"action": "unfavorite", "object_id": model.id, "object_type": "ml_model"}
        )


class MLModelVersionFavoriteResource(BaseResource):
    def post(self, model_version_id):
        version = get_object_or_404(
            models.MLModelVersion.get_by_id_and_org, model_version_id, self.current_org
        )
        fav = models.Favorite(org_id=self.current_org.id, object=version, user=self.current_user)
        models.db.session.add(fav)
        try:
            models.db.session.commit()
        except IntegrityError as exc:
            if "unique_favorite" in str(exc):
                models.db.session.rollback()
            else:
                raise
        self.record_event(
            {"action": "favorite", "object_id": version.id, "object_type": "ml_model_version"}
        )

    def delete(self, model_version_id):
        version = get_object_or_404(
            models.MLModelVersion.get_by_id_and_org, model_version_id, self.current_org
        )
        models.Favorite.query.filter(
            models.Favorite.object_id == version.id,
            models.Favorite.object_type == "MLModelVersion",
            models.Favorite.user == self.current_user,
        ).delete()
        models.db.session.commit()
        self.record_event(
            {"action": "unfavorite", "object_id": version.id, "object_type": "ml_model_version"}
        )


class PredictionResultFavoriteResource(BaseResource):
    def post(self, prediction_result_id):
        prediction = get_object_or_404(
            models.PredictionResult.get_by_id_and_org, prediction_result_id, self.current_org
        )
        fav = models.Favorite(org_id=self.current_org.id, object=prediction, user=self.current_user)
        models.db.session.add(fav)
        try:
            models.db.session.commit()
        except IntegrityError as exc:
            if "unique_favorite" in str(exc):
                models.db.session.rollback()
            else:
                raise
        self.record_event(
            {
                "action": "favorite",
                "object_id": prediction.id,
                "object_type": "prediction_result",
            }
        )

    def delete(self, prediction_result_id):
        prediction = get_object_or_404(
            models.PredictionResult.get_by_id_and_org, prediction_result_id, self.current_org
        )
        models.Favorite.query.filter(
            models.Favorite.object_id == prediction.id,
            models.Favorite.object_type == "PredictionResult",
            models.Favorite.user == self.current_user,
        ).delete()
        models.db.session.commit()
        self.record_event(
            {
                "action": "unfavorite",
                "object_id": prediction.id,
                "object_type": "prediction_result",
            }
        )
