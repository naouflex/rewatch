from flask import request
from funcy import project
from sqlalchemy.exc import IntegrityError

from redash import models, utils
from redash.handlers.base import (
    BaseResource,
    get_object_or_404,
    require_fields,
)
from redash.permissions import (
    require_access,
    require_admin_or_owner,
    require_permission,
    view_only,
)
from redash.serializers import serialize_alert
from redash.tasks.alerts import (
    notify_subscriptions,
    should_notify,
)


class AlertResource(BaseResource):
    def get(self, alert_id):
        alert = get_object_or_404(models.Alert.get_by_id_and_org, alert_id, self.current_org)
        require_access(alert, self.current_user, view_only)
        self.record_event({"action": "view", "object_id": alert.id, "object_type": "alert"})
        return serialize_alert(alert)

    def post(self, alert_id):
        req = request.get_json(True)
        params = project(req, ("options", "name", "query_id", "rearm", "tags"))
        alert = get_object_or_404(models.Alert.get_by_id_and_org, alert_id, self.current_org)
        require_admin_or_owner(alert.user.id)

        self.update_model(alert, params)
        models.db.session.commit()

        self.record_event({"action": "edit", "object_id": alert.id, "object_type": "alert"})

        return serialize_alert(alert)

    def delete(self, alert_id):
        alert = get_object_or_404(models.Alert.get_by_id_and_org, alert_id, self.current_org)
        require_admin_or_owner(alert.user_id)
        models.db.session.delete(alert)
        models.db.session.commit()


class AlertEvaluateResource(BaseResource):
    def post(self, alert_id):
        alert = get_object_or_404(models.Alert.get_by_id_and_org, alert_id, self.current_org)
        require_admin_or_owner(alert.user.id)

        new_state = alert.evaluate()
        if should_notify(alert, new_state):
            alert.state = new_state
            alert.last_triggered_at = utils.utcnow()
            models.db.session.commit()

        notify_subscriptions(alert, new_state, {})
        self.record_event({"action": "evaluate", "object_id": alert.id, "object_type": "alert"})


class AlertMuteResource(BaseResource):
    def post(self, alert_id):
        alert = get_object_or_404(models.Alert.get_by_id_and_org, alert_id, self.current_org)
        require_admin_or_owner(alert.user.id)

        alert.options["muted"] = True
        models.db.session.commit()

        self.record_event({"action": "mute", "object_id": alert.id, "object_type": "alert"})

    def delete(self, alert_id):
        alert = get_object_or_404(models.Alert.get_by_id_and_org, alert_id, self.current_org)
        require_admin_or_owner(alert.user.id)

        alert.options["muted"] = False
        models.db.session.commit()

        self.record_event({"action": "unmute", "object_id": alert.id, "object_type": "alert"})


class AlertListResource(BaseResource):
    def post(self):
        req = request.get_json(True)
        require_fields(req, ("options", "name", "query_id"))

        query = models.Query.get_by_id_and_org(req["query_id"], self.current_org)
        require_access(query, self.current_user, view_only)

        alert = models.Alert(
            name=req["name"],
            query_rel=query,
            user=self.current_user,
            org=self.current_org,
            rearm=req.get("rearm"),
            options=req["options"],
            tags=req.get("tags"),
        )

        models.db.session.add(alert)
        models.db.session.flush()
        models.db.session.commit()

        self.record_event({"action": "create", "object_id": alert.id, "object_type": "alert"})

        return serialize_alert(alert)

    @require_permission("list_alerts")
    def get(self):
        self.record_event({"action": "list", "object_type": "alert"})
        return [serialize_alert(alert) for alert in models.Alert.all(group_ids=self.current_user.group_ids)]


class AlertArchiveResource(BaseResource):
    def post(self, alert_id):
        alert = get_object_or_404(models.Alert.get_by_id_and_org, alert_id, self.current_org)
        require_admin_or_owner(alert.user_id)

        alert.archive(self.current_user)
        models.db.session.commit()
        self.record_event({"action": "archive", "object_id": alert.id, "object_type": "alert"})

        return serialize_alert(alert)


class AlertFavoriteResource(BaseResource):
    def post(self, alert_id):
        alert = get_object_or_404(models.Alert.get_by_id_and_org, alert_id, self.current_org)
        require_access(alert, self.current_user, view_only)

        fav = models.Favorite(org_id=self.current_org.id, object=alert, user=self.current_user)
        models.db.session.add(fav)

        try:
            models.db.session.commit()
        except IntegrityError as e:
            if "unique_favorite" in str(e):
                models.db.session.rollback()
            else:
                raise e

        self.record_event({"action": "favorite", "object_id": alert.id, "object_type": "alert"})

    def delete(self, alert_id):
        alert = get_object_or_404(models.Alert.get_by_id_and_org, alert_id, self.current_org)
        require_access(alert, self.current_user, view_only)

        models.Favorite.query.filter(
            models.Favorite.object_id == alert_id,
            models.Favorite.object_type == "Alert",
            models.Favorite.user == self.current_user,
        ).delete()
        models.db.session.commit()

        self.record_event({"action": "unfavorite", "object_id": alert.id, "object_type": "alert"})


class AlertFavoriteListResource(BaseResource):
    def get(self):
        favorites = models.Alert.favorites(self.current_user)
        self.record_event({"action": "load_favorites", "object_type": "alert"})
        return [serialize_alert(alert) for alert in favorites]


class AlertTagsResource(BaseResource):
    def get(self):
        tags = models.Alert.all_tags(self.current_org, self.current_user)
        return {"tags": [{"name": name, "count": count} for name, count in tags]}


class MyAlertsResource(BaseResource):
    @require_permission("list_alerts")
    def get(self):
        alerts = models.Alert.by_user(self.current_user)
        self.record_event({"action": "list", "object_type": "alert", "filter": "my"})
        return [serialize_alert(alert) for alert in alerts]


class AlertSubscriptionListResource(BaseResource):
    def post(self, alert_id):
        req = request.get_json(True)

        alert = models.Alert.get_by_id_and_org(alert_id, self.current_org)
        require_access(alert, self.current_user, view_only)
        kwargs = {"alert": alert, "user": self.current_user}

        if "destination_id" in req:
            destination = models.NotificationDestination.get_by_id_and_org(req["destination_id"], self.current_org)
            kwargs["destination"] = destination

        subscription = models.AlertSubscription(**kwargs)
        models.db.session.add(subscription)
        models.db.session.commit()

        self.record_event(
            {
                "action": "subscribe",
                "object_id": alert_id,
                "object_type": "alert",
                "destination": req.get("destination_id"),
            }
        )

        d = subscription.to_dict()
        return d

    def get(self, alert_id):
        alert = models.Alert.get_by_id_and_org(alert_id, self.current_org)
        require_access(alert, self.current_user, view_only)

        subscriptions = models.AlertSubscription.all(alert_id)
        return [s.to_dict() for s in subscriptions]


class AlertSubscriptionResource(BaseResource):
    def delete(self, alert_id, subscriber_id):
        subscription = models.AlertSubscription.query.get_or_404(subscriber_id)
        require_admin_or_owner(subscription.user.id)
        models.db.session.delete(subscription)
        models.db.session.commit()

        self.record_event({"action": "unsubscribe", "object_id": alert_id, "object_type": "alert"})
