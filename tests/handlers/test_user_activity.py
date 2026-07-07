"""Tests for user activity summary API."""
from datetime import datetime, timedelta

from rewatch.models import Event, db
from tests import BaseTestCase


class TestUserActivityResource(BaseTestCase):
    def _record_event(self, action, object_type="query", days_ago=0):
        event = Event(
            org_id=self.factory.org.id,
            user_id=self.factory.user.id,
            action=action,
            object_type=object_type,
            object_id="1",
            created_at=datetime.utcnow() - timedelta(days=days_ago),
        )
        db.session.add(event)

    def test_activity_summary_returns_daily_counts(self):
        self._record_event("execute", days_ago=0)
        self._record_event("execute", days_ago=0)
        self._record_event("edit", object_type="dashboard", days_ago=1)
        db.session.commit()

        rv = self.make_request("get", "/api/users/me/activity?days=7")
        self.assertEqual(rv.status_code, 200)
        self.assertGreaterEqual(rv.json["total"], 3)
        self.assertEqual(len(rv.json["daily"]), 7)
        self.assertEqual(len(rv.json["week"]), 7)
        self.assertTrue(any(item["count"] > 0 for item in rv.json["daily"]))
        self.assertTrue(rv.json["by_action"])
        self.assertTrue(rv.json["by_object_type"])

    def test_activity_ignores_passive_view_events(self):
        self._record_event("view", days_ago=0)
        self._record_event("list", object_type="dashboard", days_ago=0)
        db.session.commit()

        rv = self.make_request("get", "/api/users/me/activity?days=7")
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.json["total"], 0)

    def test_activity_clamps_days_parameter(self):
        rv = self.make_request("get", "/api/users/me/activity?days=999")
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(len(rv.json["daily"]), 366)
