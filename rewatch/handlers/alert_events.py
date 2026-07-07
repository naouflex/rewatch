from flask import request

from rewatch import models
from rewatch.handlers.base import BaseResource, get_object_or_404, paginate
from rewatch.permissions import (
    require_access,
    require_admin_or_owner,
    view_only,
)
from rewatch.serializers import serialize_alert_event


def _bool_arg(value, default=False):
    if value is None:
        return default
    return str(value).lower() in ("1", "true", "yes")


class AlertEventListResource(BaseResource):
    """List events recorded for a single alert."""

    def get(self, alert_id):
        alert = get_object_or_404(models.Alert.get_by_id_and_org, alert_id, self.current_org)
        require_access(alert, self.current_user, view_only)

        include_archived = _bool_arg(request.args.get("include_archived"))
        events = models.AlertEvent.for_alert(alert.id, include_archived=include_archived)

        page = request.args.get("page", 1, type=int)
        page_size = request.args.get("page_size", 20, type=int)

        return paginate(events, page, page_size, serialize_alert_event)


class AlertEventResource(BaseResource):
    """Inspect / archive / delete a single alert event."""

    def get(self, alert_id, event_id):
        alert = get_object_or_404(models.Alert.get_by_id_and_org, alert_id, self.current_org)
        require_access(alert, self.current_user, view_only)

        event = get_object_or_404(models.AlertEvent.get_by_id_and_org, event_id, self.current_org)
        if event.alert_id != alert.id:
            from werkzeug.exceptions import NotFound

            raise NotFound()
        return serialize_alert_event(event)

    def post(self, alert_id, event_id):
        alert = get_object_or_404(models.Alert.get_by_id_and_org, alert_id, self.current_org)
        require_admin_or_owner(alert.user_id)

        event = get_object_or_404(models.AlertEvent.get_by_id_and_org, event_id, self.current_org)
        if event.alert_id != alert.id:
            from werkzeug.exceptions import NotFound

            raise NotFound()

        event.archive()
        return serialize_alert_event(event)

    def delete(self, alert_id, event_id):
        alert = get_object_or_404(models.Alert.get_by_id_and_org, alert_id, self.current_org)
        require_admin_or_owner(alert.user_id)

        event = get_object_or_404(models.AlertEvent.get_by_id_and_org, event_id, self.current_org)
        if event.alert_id != alert.id:
            from werkzeug.exceptions import NotFound

            raise NotFound()

        models.db.session.delete(event)
        models.db.session.commit()


class MyAlertEventsResource(BaseResource):
    """Cross-alert event feed for the current user's groups."""

    def get(self):
        include_archived = _bool_arg(request.args.get("include_archived"))
        events = models.AlertEvent.for_user(self.current_user, include_archived=include_archived)

        try:
            limit = int(request.args.get("limit", "50"))
        except (TypeError, ValueError):
            limit = 50
        limit = max(1, min(limit, 500))

        return [serialize_alert_event(e) for e in events.limit(limit)]
