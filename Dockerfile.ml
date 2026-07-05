# Dockerfile.ml — heavyweight worker image with the full ML stack pre-installed.
#
# This image is intentionally separate from the regular `rewatch-server` /
# `rewatch-worker` image so that:
#   * the small/fast HTTP image does not have to ship gigabytes of scikit-learn
#     / scipy / statsmodels wheels,
#   * production deployments that don't use MLModels can simply skip building
#     this image,
#   * deploying a new MLModels feature only requires rebuilding `rewatch-ml-worker`.
#
# It is built FROM the existing rewatch image (so it shares the entrypoint,
# Poetry layout, working directory, and `rewatch` user). On top of that we install
# the `all_ds` Poetry group which already includes scikit-learn / joblib /
# scipy / statsmodels (added when the MLModels feature was ported), plus a
# couple of extra system libraries that some sklearn wheels need at runtime.
#
# Usage in compose.yaml:
#   ml-worker:
#     build:
#       context: .
#       dockerfile: Dockerfile.ml
#     command: dev_worker
#     environment:
#       QUEUES: "training,predicting"
#
# QUEUES can be overridden to add the regular default/queries queues if you want
# the same container to act as a generic worker as well.

ARG BASE_IMAGE=rewatch-worker:latest
FROM ${BASE_IMAGE}

USER root

# OpenMP runtime is needed by scikit-learn / scipy wheels for parallel
# fit/predict; libgomp1 is the minimal package that provides it on Debian.
RUN apt-get update && \
  apt-get install -y --no-install-recommends \
    libgomp1 \
    libatlas3-base \
    libopenblas0 && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*

# Install the heavy ML stack via pip rather than poetry: scikit-learn /
# scipy / statsmodels would force a `poetry.lock` regeneration, which today
# conflicts with the pinned jsonschema 3.1.1 / web3 6.20.3 combination.
# Keeping these in `requirements.ml.txt` lets us upgrade them independently
# without touching the rest of the dependency graph.
COPY requirements.ml.txt /tmp/requirements.ml.txt
RUN pip install --no-cache-dir -r /tmp/requirements.ml.txt && \
    rm /tmp/requirements.ml.txt

# Default this container to the ML queues. Can be overridden in compose.
ENV QUEUES="training,predicting" \
    WORKERS_COUNT=2 \
    REDASH_ML_MODEL_TRAINING_TIME_LIMIT=36000 \
    REDASH_ML_MODEL_PREDICTING_TIME_LIMIT=360

USER rewatch

ENTRYPOINT ["/app/bin/docker-entrypoint"]
CMD ["worker"]
