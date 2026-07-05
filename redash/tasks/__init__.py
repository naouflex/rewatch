from rq.connections import pop_connection, push_connection

from rewatch import rq_redis_connection
from rewatch.tasks.alerts import check_alerts_for_query
from rewatch.tasks.failure_report import send_aggregated_errors
from rewatch.tasks.indexers import check_indexers_for_query, index_query_results
from rewatch.tasks.ml_models import (
    check_models_for_query_predict,
    check_models_for_query_train,
    enqueue_predict_model,
    enqueue_train_model,
    kill_model_predicting,
    kill_model_training,
    notify_subscriptions as notify_model_subscriptions,
    predict_model,
    train_model,
)
from rewatch.tasks.general import (
    record_event,
    send_mail,
    sync_user_details,
    version_check,
)
from rewatch.tasks.queries import (
    cleanup_query_results,
    empty_schedules,
    enqueue_query,
    execute_query,
    refresh_queries,
    refresh_schemas,
    remove_ghost_locks,
)
from rewatch.tasks.schedule import (
    periodic_job_definitions,
    rq_scheduler,
    schedule_periodic_jobs,
)
from rewatch.tasks.worker import Job, Queue, Worker


def init_app(app):
    app.before_request(lambda: push_connection(rq_redis_connection))
    app.teardown_request(lambda _: pop_connection())
