from mock import ANY, MagicMock

import rewatch.tasks.alerts
from rewatch.models import Alert
from rewatch.tasks.alerts import check_alerts_for_query, notify_subscriptions
from tests import BaseTestCase


class TestCheckAlertsForQuery(BaseTestCase):
    def test_notifies_subscribers_when_should(self):
        rewatch.tasks.alerts.notify_subscriptions = MagicMock()
        Alert.evaluate = MagicMock(return_value=Alert.TRIGGERED_STATE)

        alert = self.factory.create_alert()
        check_alerts_for_query(alert.query_id, metadata={"Scheduled": False})

        self.assertTrue(rewatch.tasks.alerts.notify_subscriptions.called)

    def test_doesnt_notify_when_nothing_changed(self):
        rewatch.tasks.alerts.notify_subscriptions = MagicMock()
        Alert.evaluate = MagicMock(return_value=Alert.OK_STATE)

        alert = self.factory.create_alert()
        check_alerts_for_query(alert.query_id, metadata={"Scheduled": False})

        self.assertFalse(rewatch.tasks.alerts.notify_subscriptions.called)

    def test_doesnt_notify_when_muted(self):
        rewatch.tasks.alerts.notify_subscriptions = MagicMock()
        Alert.evaluate = MagicMock(return_value=Alert.TRIGGERED_STATE)

        alert = self.factory.create_alert(options={"muted": True})
        check_alerts_for_query(alert.query_id, metadata={"Scheduled": False})

        self.assertFalse(rewatch.tasks.alerts.notify_subscriptions.called)


class TestNotifySubscriptions(BaseTestCase):
    def test_calls_notify_for_subscribers(self):
        subscription = self.factory.create_alert_subscription()
        subscription.notify = MagicMock()
        notify_subscriptions(subscription.alert, Alert.OK_STATE, metadata={"Scheduled": False})
        subscription.notify.assert_called_with(
            subscription.alert,
            subscription.alert.query_rel,
            subscription.user,
            Alert.OK_STATE,
            ANY,
            ANY,
            ANY,
        )

    def _create_alert_with_rows(self, rows, options=None):
        result = self.factory.create_query_result(
            data={"rows": rows, "columns": [{"name": "foo", "type": "INTEGER"}]}
        )
        query = self.factory.create_query(latest_query_data_id=result.id)
        merged_options = {"selector": "first", "op": "equals", "column": "foo", "value": "1"}
        if options:
            merged_options.update(options)
        alert = self.factory.create_alert(query_rel=query, options=merged_options)
        return self.factory.create_alert_subscription(alert=alert)

    def test_send_for_each_row_dispatches_per_row_when_triggered(self):
        rows = [{"foo": 1}, {"foo": 2}, {"foo": 3}]
        subscription = self._create_alert_with_rows(rows, options={"send_for_each_row": True})
        subscription.notify = MagicMock()

        notify_subscriptions(subscription.alert, Alert.TRIGGERED_STATE, metadata={"Scheduled": False})

        self.assertEqual(subscription.notify.call_count, len(rows))
        for index, call_args in enumerate(subscription.notify.call_args_list):
            metadata = call_args[0][6]
            self.assertEqual(metadata["row"], rows[index])
            self.assertEqual(metadata["row_index"], index)
            self.assertEqual(metadata["Scheduled"], False)

    def test_send_for_each_row_falls_back_to_single_dispatch_when_not_triggered(self):
        rows = [{"foo": 1}, {"foo": 2}]
        subscription = self._create_alert_with_rows(rows, options={"send_for_each_row": True})
        subscription.notify = MagicMock()

        notify_subscriptions(subscription.alert, Alert.OK_STATE, metadata={"Scheduled": False})

        self.assertEqual(subscription.notify.call_count, 1)
        metadata = subscription.notify.call_args[0][6]
        self.assertNotIn("row", metadata)
        self.assertNotIn("row_index", metadata)

    def test_send_for_each_row_with_no_rows_falls_back_to_single_dispatch(self):
        subscription = self._create_alert_with_rows([], options={"send_for_each_row": True})
        subscription.notify = MagicMock()

        notify_subscriptions(subscription.alert, Alert.TRIGGERED_STATE, metadata={"Scheduled": False})

        self.assertEqual(subscription.notify.call_count, 1)
