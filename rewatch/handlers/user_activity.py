from flask import request

from rewatch.handlers.base import BaseResource
from rewatch.services.user_activity import get_user_activity_summary


class UserActivityResource(BaseResource):
    def get(self):
        days = request.args.get("days", default=365, type=int)
        summary = get_user_activity_summary(self.current_user, self.current_org, days=days)
        self.record_event({"action": "view", "object_type": "user_activity"})
        return summary
