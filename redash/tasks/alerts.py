import datetime

from flask import current_app

from redash import models, utils
from redash.worker import get_job_logger, job

logger = get_job_logger(__name__)


def _query_result_rows(alert):
    query_data = alert.query_rel.latest_query_data
    if query_data is None or not query_data.data:
        return []
    return query_data.data.get("rows") or []


def _record_event(alert, subscription, new_state, metadata, status, error_message=None):
    """Persist an AlertEvent for a subscription dispatch (success or failure)."""
    try:
        destination = subscription.destination
        rendered_body = ""
        try:
            rendered_body = alert.render_custom_body(
                row=(metadata or {}).get("row"),
                row_index=(metadata or {}).get("row_index"),
            )
        except Exception:
            logger.exception("Failed to render alert body for AlertEvent record")

        additional = {"recipient_user_id": getattr(subscription.user, "id", None)}
        if error_message:
            additional["error"] = error_message

        models.AlertEvent.record(
            alert,
            destination=destination,
            status=status,
            state=new_state,
            content=rendered_body,
            additional_properties=additional,
            row_index=(metadata or {}).get("row_index"),
            alert_type=destination.type if destination else "email",
            user=subscription.user,
        )
    except Exception:
        logger.exception("Failed to record AlertEvent for alert %s", alert.id)
        models.db.session.rollback()


def _dispatch_to_subscriptions(alert, new_state, host, metadata):
    for subscription in alert.subscriptions:
        try:
            subscription.notify(alert, alert.query_rel, subscription.user, new_state, current_app, host, metadata)
            _record_event(alert, subscription, new_state, metadata, models.AlertEvent.STATUS_OK)
        except Exception as exc:
            logger.exception("Error with processing destination")
            _record_event(
                alert, subscription, new_state, metadata, models.AlertEvent.STATUS_ERROR, error_message=str(exc)
            )


def notify_subscriptions(alert, new_state, metadata):
    host = utils.base_url(alert.query_rel.org)

    if alert.send_for_each_row and new_state == models.Alert.TRIGGERED_STATE:
        rows = _query_result_rows(alert)
        if rows:
            for row_index, row in enumerate(rows):
                row_metadata = {**(metadata or {}), "row": row, "row_index": row_index}
                _dispatch_to_subscriptions(alert, new_state, host, row_metadata)
            return

    _dispatch_to_subscriptions(alert, new_state, host, metadata)


def should_notify(alert, new_state):
    passed_rearm_threshold = False
    if alert.rearm and alert.last_triggered_at:
        passed_rearm_threshold = alert.last_triggered_at + datetime.timedelta(seconds=alert.rearm) < utils.utcnow()

    return new_state != alert.state or (alert.state == models.Alert.TRIGGERED_STATE and passed_rearm_threshold)


@job("default", timeout=300)
def check_alerts_for_query(query_id, metadata):
    logger.debug("Checking query %d for alerts", query_id)

    query = models.Query.query.get(query_id)

    for alert in query.alerts:
        logger.info("Checking alert (%d) of query %d.", alert.id, query_id)
        new_state = alert.evaluate()

        if should_notify(alert, new_state):
            logger.info("Alert %d new state: %s", alert.id, new_state)
            old_state = alert.state

            alert.state = new_state
            alert.last_triggered_at = utils.utcnow()
            models.db.session.commit()

            if old_state == models.Alert.UNKNOWN_STATE and new_state == models.Alert.OK_STATE:
                logger.debug("Skipping notification (previous state was unknown and now it's ok).")
                continue

            if alert.muted:
                logger.debug("Skipping notification (alert muted).")
                continue

            notify_subscriptions(alert, new_state, metadata)
