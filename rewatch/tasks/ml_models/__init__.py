"""Worker tasks for the MLModels feature.

The :mod:`rewatch.tasks.ml_models.execution` submodule exposes RQ jobs that
train, predict and notify on machine learning models. This package's
``__init__`` re-exports the public symbols so callers can do
``from rewatch.tasks import enqueue_train_model`` once it's wired up in the
top-level ``rewatch.tasks.__init__``.
"""

from rewatch.tasks.ml_models.execution import (  # noqa: F401
    REDIS_ML_MODEL_JOB_KEY,
    check_models_for_query_predict,
    check_models_for_query_train,
    enqueue_predict_model,
    enqueue_train_model,
    kill_model_predicting,
    kill_model_training,
    notify_subscriptions,
    predict_model,
    should_notify_predict,
    should_notify_train,
    train_model,
)
