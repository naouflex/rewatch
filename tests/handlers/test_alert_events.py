"""Tests for the AlertEvent HTTP handlers and the dispatch-time hook that
records an AlertEvent for every notification fired."""
from unittest.mock import MagicMock, patch

from rewatch.models import Alert, AlertEvent, db
from rewatch.tasks.alerts import notify_subscriptions
from tests import BaseTestCase


def _make_query_with_rows(factory, rows):
    """Helper that creates a query with a latest_query_data set to ``rows``."""
    result = factory.create_query_result(
        data={"rows": rows, "columns": [{"name": "foo", "type": "INTEGER"}]}
    )
    return factory.create_query(latest_query_data_id=result.id)


class TestAlertEventRecordingOnDispatch(BaseTestCase):
    def test_successful_dispatch_records_an_event(self):
        subscription = self.factory.create_alert_subscription()
        subscription.notify = MagicMock()

        notify_subscriptions(subscription.alert, Alert.TRIGGERED_STATE, metadata={})

        events = AlertEvent.query.filter_by(alert_id=subscription.alert.id).all()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].status, AlertEvent.STATUS_OK)
        self.assertEqual(events[0].state, Alert.TRIGGERED_STATE)
        self.assertEqual(events[0].destination_id, subscription.destination.id)

    def test_failed_dispatch_records_error_event(self):
        subscription = self.factory.create_alert_subscription()
        subscription.notify = MagicMock(side_effect=RuntimeError("boom"))

        notify_subscriptions(subscription.alert, Alert.TRIGGERED_STATE, metadata={})

        events = AlertEvent.query.filter_by(alert_id=subscription.alert.id).all()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].status, AlertEvent.STATUS_ERROR)
        self.assertIn("boom", events[0].additional_properties.get("error", ""))

    def test_per_row_dispatch_records_one_event_per_row(self):
        rows = [{"foo": 1}, {"foo": 2}, {"foo": 3}]
        query = _make_query_with_rows(self.factory, rows)
        alert = self.factory.create_alert(
            query_rel=query,
            options={
                "send_for_each_row": True,
                "selector": "first",
                "op": "equals",
                "column": "foo",
                "value": "1",
            },
        )
        subscription = self.factory.create_alert_subscription(alert=alert)
        subscription.notify = MagicMock()

        notify_subscriptions(alert, Alert.TRIGGERED_STATE, metadata={})

        events = AlertEvent.query.filter_by(alert_id=alert.id).order_by(AlertEvent.row_index).all()
        self.assertEqual(len(events), 3)
        self.assertEqual([e.row_index for e in events], [0, 1, 2])


class TestAlertEventListResource(BaseTestCase):
    def test_lists_events_for_an_alert(self):
        alert = self.factory.create_alert()
        for i in range(3):
            self.factory.create_alert_event(alert=alert, content="row {}".format(i))
        db.session.commit()

        rv = self.make_request("get", "/api/alerts/{}/events".format(alert.id))
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(len(rv.json), 3)

    def test_excludes_archived_events_by_default(self):
        alert = self.factory.create_alert()
        e1 = self.factory.create_alert_event(alert=alert)
        e2 = self.factory.create_alert_event(alert=alert)
        e2.is_archived = True
        db.session.commit()

        rv = self.make_request("get", "/api/alerts/{}/events".format(alert.id))
        ids = [e["id"] for e in rv.json]
        self.assertIn(e1.id, ids)
        self.assertNotIn(e2.id, ids)

    def test_returns_403_when_user_has_no_access_to_alert(self):
        data_source = self.factory.create_data_source(group=self.factory.create_group())
        query = self.factory.create_query(data_source=data_source)
        alert = self.factory.create_alert(query_rel=query)
        db.session.commit()

        rv = self.make_request("get", "/api/alerts/{}/events".format(alert.id))
        self.assertEqual(rv.status_code, 403)


class TestAlertEventResource(BaseTestCase):
    def test_get_returns_event_payload(self):
        event = self.factory.create_alert_event(content="hello")
        db.session.commit()

        rv = self.make_request(
            "get", "/api/alerts/{}/events/{}".format(event.alert_id, event.id)
        )
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.json["id"], event.id)
        self.assertEqual(rv.json["content"], "hello")

    def test_post_archives_event(self):
        event = self.factory.create_alert_event()
        db.session.commit()

        rv = self.make_request(
            "post", "/api/alerts/{}/events/{}".format(event.alert_id, event.id)
        )
        self.assertEqual(rv.status_code, 200)
        self.assertTrue(rv.json["is_archived"])

    def test_delete_removes_event(self):
        event = self.factory.create_alert_event()
        event_id = event.id
        alert_id = event.alert_id
        db.session.commit()

        rv = self.make_request("delete", "/api/alerts/{}/events/{}".format(alert_id, event_id))
        self.assertEqual(rv.status_code, 200)
        self.assertIsNone(AlertEvent.query.get(event_id))

    def test_404_when_event_does_not_belong_to_alert(self):
        e1 = self.factory.create_alert_event()
        e2 = self.factory.create_alert_event()
        db.session.commit()

        rv = self.make_request("get", "/api/alerts/{}/events/{}".format(e1.alert_id, e2.id))
        self.assertEqual(rv.status_code, 404)


class TestMyAlertEvents(BaseTestCase):
    def test_returns_events_across_alerts_for_current_user(self):
        a1 = self.factory.create_alert()
        a2 = self.factory.create_alert()
        self.factory.create_alert_event(alert=a1)
        self.factory.create_alert_event(alert=a2)
        db.session.commit()

        rv = self.make_request("get", "/api/alert_events")
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(len(rv.json), 2)
