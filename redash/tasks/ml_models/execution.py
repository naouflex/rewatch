"""RQ jobs and helpers for ML model training, prediction and notification.

These mirror the inverse-watch ``rewatch/tasks/queries/maintenance.py`` and
``rewatch/tasks/ml_models/execution.py`` modules. Two dedicated RQ queues are
used so heavy ML workloads don't starve the normal query workers:

- ``training``    - long-running ``train_model`` jobs
- ``predicting``  - shorter ``predict_model`` jobs

A Redis key (``REDIS_ML_MODEL_JOB_KEY``) tracks the currently in-flight RQ job
id per model, so we can:
- avoid double-enqueueing the same model
- support a "stop training/prediction" UI button by canceling the tracked job
"""

import datetime
import logging

from flask import current_app
from rq.job import JobStatus

from rewatch import models, redis_connection, settings, utils
from rewatch.tasks.worker import Queue as RewatchQueue
from rewatch.worker import get_job_logger, job

try:  # rq.get_current_job is not always importable from a single path
    from rq import get_current_job
except ImportError:  # pragma: no cover
    from rq.job import get_current_job  # type: ignore

logger = get_job_logger(__name__)

REDIS_ML_MODEL_JOB_KEY = "ml_model:{model_id}:job_id"


# ---------------------------------------------------------------------------
# RQ entry points
# ---------------------------------------------------------------------------


@job("training", timeout=-1)
def train_model(model_id):
    """Train ``model_id`` synchronously inside an RQ ``training`` worker."""
    try:
        model = models.MLModel.get_by_id(model_id)
        current_job = get_current_job()
        if current_job is not None:
            redis_connection.set(REDIS_ML_MODEL_JOB_KEY.format(model_id=model_id), current_job.id)
        model.train()

        # After training, fan out subscriptions in the same job so the user
        # gets notified without an extra hop.
        if should_notify_train(model, model.state_train):
            notify_subscriptions(model, model.state_train, "model_train")
    except Exception:
        logger.exception("Failed to train model %s", model_id)
    finally:
        redis_connection.delete(REDIS_ML_MODEL_JOB_KEY.format(model_id=model_id))


@job("predicting", timeout=-1)
def predict_model(model_id):
    """Run inference for ``model_id`` and persist a PredictionResult."""
    try:
        model = models.MLModel.get_by_id(model_id)
        current_job = get_current_job()
        if current_job is not None:
            redis_connection.set(REDIS_ML_MODEL_JOB_KEY.format(model_id=model_id), current_job.id)
        model.predict()

        if should_notify_predict(model, model.state_predict):
            notify_subscriptions(model, model.state_predict, "model_predict")
    except Exception:
        logger.exception("Failed to predict using model %s", model_id)
    finally:
        redis_connection.delete(REDIS_ML_MODEL_JOB_KEY.format(model_id=model_id))


# ---------------------------------------------------------------------------
# Cancellation
# ---------------------------------------------------------------------------


def _cancel_job_for_model(model_id, queue_name, label):
    """Cancel the in-flight RQ job tracked for ``model_id``."""
    raw = redis_connection.get(REDIS_ML_MODEL_JOB_KEY.format(model_id=model_id))
    if not raw:
        logger.warning("No %s job tracked for model %s", label, model_id)
        return

    job_id = raw.decode("utf-8", errors="ignore") if isinstance(raw, bytes) else str(raw)
    job_key = "rq:job:{0}".format(job_id)

    try:
        status = redis_connection.hget(job_key, "status")
        if status:
            if isinstance(status, bytes):
                status = status.decode("utf-8", errors="ignore")
            if status == JobStatus.STARTED:
                redis_connection.hset(job_key, "status", JobStatus.FAILED)
                redis_connection.hset(job_key, "exc_info", "Job cancelled by user")
            elif status == JobStatus.QUEUED:
                queue = RewatchQueue(queue_name, connection=redis_connection)
                queue.remove(job_id)
                redis_connection.hset(job_key, "status", JobStatus.FAILED)
                redis_connection.hset(job_key, "exc_info", "Job cancelled by user")
        redis_connection.delete(job_key)
    except Exception:
        logger.exception("Failed to cancel %s job %s for model %s", label, job_id, model_id)
    finally:
        redis_connection.delete(REDIS_ML_MODEL_JOB_KEY.format(model_id=model_id))


@job("training", timeout=-1)
def kill_model_training(model_id):
    _cancel_job_for_model(model_id, "training", "training")


@job("predicting", timeout=-1)
def kill_model_predicting(model_id):
    _cancel_job_for_model(model_id, "predicting", "predicting")


# ---------------------------------------------------------------------------
# Enqueueing helpers (called from Flask handlers)
# ---------------------------------------------------------------------------


def _existing_job_running(model_id):
    raw = redis_connection.get(REDIS_ML_MODEL_JOB_KEY.format(model_id=model_id))
    if not raw:
        return None
    job_id = raw.decode("utf-8", errors="ignore") if isinstance(raw, bytes) else str(raw)
    job_key = "rq:job:{0}".format(job_id)
    status = redis_connection.hget(job_key, "status")
    if not status:
        return None
    if isinstance(status, bytes):
        status = status.decode("utf-8", errors="ignore")
    if status in (JobStatus.QUEUED, JobStatus.STARTED):
        return job_id
    return None


def _enqueue(model_id, user_id, queue_name, target, time_limit):
    queue = RewatchQueue(queue_name, connection=redis_connection)
    existing = _existing_job_running(model_id)
    if existing:
        logger.info("Model %s already has a running %s job: %s", model_id, queue_name, existing)
        return queue.fetch_job(existing)

    enqueue_kwargs = {
        "job_timeout": time_limit,
        "failure_ttl": settings.JOB_DEFAULT_FAILURE_TTL,
        "result_ttl": settings.JOB_EXPIRY_TIME,
        "meta": {"model_id": model_id, "user_id": user_id},
    }
    enqueued = queue.enqueue(target, model_id, **enqueue_kwargs)
    redis_connection.set(REDIS_ML_MODEL_JOB_KEY.format(model_id=model_id), enqueued.id, ex=time_limit)
    logger.info("Enqueued %s job for model %s: %s", queue_name, model_id, enqueued.id)
    return enqueued


def enqueue_train_model(model_id, user_id):
    if not models.MLModel.query.filter_by(id=model_id).first():
        logger.warning("Cannot enqueue training: model %s not found", model_id)
        return None
    return _enqueue(model_id, user_id, "training", train_model, settings.ML_MODEL_TRAINING_TIME_LIMIT)


def enqueue_predict_model(model_id, user_id):
    if not models.MLModel.query.filter_by(id=model_id).first():
        logger.warning("Cannot enqueue prediction: model %s not found", model_id)
        return None
    return _enqueue(model_id, user_id, "predicting", predict_model, settings.ML_MODEL_PREDICTING_TIME_LIMIT)


# ---------------------------------------------------------------------------
# Subscription notifications
# ---------------------------------------------------------------------------


def should_notify_train(model, new_state):
    """Decide whether a state transition warrants a train notification."""
    if model.muted:
        return False
    if new_state in (models.MLModel.UNKNOWN_STATE, None):
        return False
    last = model.options.get("train_last_triggered_at")
    rearm = model.rearm or 0
    if last and rearm:
        try:
            last_dt = datetime.datetime.fromisoformat(last)
            if last_dt + datetime.timedelta(seconds=rearm) > datetime.datetime.utcnow():
                return False
        except ValueError:
            pass
    return True


def should_notify_predict(model, new_state):
    """Decide whether a state transition warrants a prediction notification."""
    if model.muted:
        return False
    if new_state in (models.MLModel.UNKNOWN_STATE, None):
        return False
    return True


def notify_subscriptions(model, new_state, notification_type):
    host = utils.base_url(model.org)
    for subscription in model.subscriptions:
        try:
            if notification_type == "model_train":
                subscription.notify_train(model, model.query_rel, subscription.user, new_state, current_app, host)
            else:
                subscription.notify_predict(model, model.query_rel, subscription.user, new_state, current_app, host)
        except Exception:
            logger.exception("Failed to notify subscription %s for model %s", subscription.id, model.id)


# ---------------------------------------------------------------------------
# Hooks invoked from query execution
# ---------------------------------------------------------------------------


@job("training", timeout=-1)
def check_models_for_query_train(query_id):
    """Triggered after a query refresh when at least one model wants to retrain."""
    logger.debug("Checking query %d for ml model retraining", query_id)
    model_list = models.MLModel.query.filter_by(query_id=query_id, is_archived=False).all()
    for model in model_list:
        criteria = (model.options or {}).get("train_criteria", "do_nothing")
        if criteria == "do_nothing":
            continue
        try:
            model.train()
            if should_notify_train(model, model.state_train):
                notify_subscriptions(model, model.state_train, "model_train")
        except Exception:
            logger.exception("Auto-train failed for model %s on query %s", model.id, query_id)


@job("predicting", timeout=-1)
def check_models_for_query_predict(query_id):
    """Triggered after a query refresh when at least one model wants to re-predict."""
    logger.debug("Checking query %d for ml model re-prediction", query_id)
    model_list = models.MLModel.query.filter_by(query_id=query_id, is_archived=False).all()
    for model in model_list:
        criteria = (model.options or {}).get("predict_criteria", "do_nothing")
        if criteria == "do_nothing":
            continue
        try:
            model.predict()
            if should_notify_predict(model, model.state_predict):
                notify_subscriptions(model, model.state_predict, "model_predict")
        except Exception:
            logger.exception("Auto-predict failed for model %s on query %s", model.id, query_id)
