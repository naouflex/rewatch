"""Machine learning models, versions, predictions and subscriptions.

This module is the sklearn-only port of the MLModels feature originally
implemented in inverse-watch. The original codebase mixed scikit-learn with
TensorFlow/Keras (custom NN regressors, Keras tuner, autoencoders for feature
reduction). All TF/Keras code paths have been removed: training and prediction
go through scikit-learn's regression/classification estimators only.

Database schema
---------------
- ``ml_models``               - root model definition + serialized weights
- ``ml_model_versions``       - per-train snapshots used for revert / fork
- ``prediction_results``      - inference outputs (one row per prediction run)
- ``ml_model_subscriptions``  - notification destinations for train/predict events

Storage
-------
Trained estimators are pickled with ``joblib`` and zlib-compressed before
being stored in ``ml_models.model_blob`` (Postgres ``BYTEA``). A hard cap on
the compressed size (``settings.ML_MODEL_MAX_BLOB_MB``, 100 MB by default)
protects the database from runaway pickles.
"""

from __future__ import annotations

import datetime
import hashlib
import io
import json
import logging
import traceback
import zlib

from sqlalchemy import UniqueConstraint, and_, or_
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import backref, defer, joinedload, load_only
from sqlalchemy.sql import func

# Heavy ML deps (numpy / pandas / sklearn / joblib) are only required at
# runtime (training, prediction, feature engineering). Importing them lazily
# keeps the model-class import side effect-free so the rest of the server can
# still boot when scikit-learn isn't installed (e.g. in a slim CI image).
try:
    import joblib  # noqa: F401
    import numpy as np  # noqa: F401
    import pandas as pd  # noqa: F401

    _ML_DEPS_AVAILABLE = True
    _ML_DEPS_ERROR = None
except Exception as _exc:  # pragma: no cover - exercised in slim images only
    joblib = None  # type: ignore
    np = None  # type: ignore
    pd = None  # type: ignore
    _ML_DEPS_AVAILABLE = False
    _ML_DEPS_ERROR = _exc


def _require_ml_deps():
    """Raise a friendly error when training/prediction code paths fire without sklearn."""
    if _ML_DEPS_AVAILABLE:
        return
    raise RuntimeError(
        "MLModel training/prediction requires scikit-learn / numpy / pandas / joblib. "
        "Install the `all_ds` poetry group or use the redash-ml-worker image. "
        "Original import error: {0!r}".format(_ML_DEPS_ERROR)
    )


def _sklearn():
    """Return the sklearn submodules we need (imported on demand)."""
    _require_ml_deps()
    from sklearn.ensemble import (
        AdaBoostClassifier,
        AdaBoostRegressor,
        GradientBoostingClassifier,
        GradientBoostingRegressor,
        RandomForestClassifier,
        RandomForestRegressor,
    )
    from sklearn.linear_model import LinearRegression, LogisticRegression
    from sklearn.metrics import (
        accuracy_score,
        f1_score,
        mean_absolute_error,
        mean_squared_error,
        precision_score,
        r2_score,
        recall_score,
    )
    from sklearn.model_selection import RandomizedSearchCV, train_test_split
    from sklearn.multiclass import OneVsRestClassifier
    from sklearn.multioutput import MultiOutputClassifier, MultiOutputRegressor
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    return {
        "AdaBoostClassifier": AdaBoostClassifier,
        "AdaBoostRegressor": AdaBoostRegressor,
        "GradientBoostingClassifier": GradientBoostingClassifier,
        "GradientBoostingRegressor": GradientBoostingRegressor,
        "RandomForestClassifier": RandomForestClassifier,
        "RandomForestRegressor": RandomForestRegressor,
        "LinearRegression": LinearRegression,
        "LogisticRegression": LogisticRegression,
        "accuracy_score": accuracy_score,
        "f1_score": f1_score,
        "mean_absolute_error": mean_absolute_error,
        "mean_squared_error": mean_squared_error,
        "precision_score": precision_score,
        "r2_score": r2_score,
        "recall_score": recall_score,
        "RandomizedSearchCV": RandomizedSearchCV,
        "train_test_split": train_test_split,
        "OneVsRestClassifier": OneVsRestClassifier,
        "MultiOutputClassifier": MultiOutputClassifier,
        "MultiOutputRegressor": MultiOutputRegressor,
        "OneHotEncoder": OneHotEncoder,
        "StandardScaler": StandardScaler,
    }


from redash import settings
from redash.destinations import (
    get_configuration_schema_for_destination_type,
    get_destination,
)
from redash.models.base import Column, db, key_type, primary_key
from redash.models.changes import ChangeTrackingMixin
from redash.models.mixins import BelongsToOrgMixin, TimestampMixin
from redash.models.organizations import Organization
from redash.models.types import MutableDict, MutableList
from redash.models.users import User
from redash.utils import json_dumps
from redash.utils.configuration import ConfigurationContainer

logger = logging.getLogger(__name__)


# Operators recognised by ``MLModel.evaluate`` for the train/predict criteria.
OPERATORS = {
    ">": lambda v, t: v > t,
    ">=": lambda v, t: v >= t,
    "<": lambda v, t: v < t,
    "<=": lambda v, t: v <= t,
    "==": lambda v, t: v == t,
    "!=": lambda v, t: v != t,
}


def _to_serializable(value):
    """Convert numpy scalars/arrays into native Python types."""
    if _ML_DEPS_AVAILABLE:
        if isinstance(value, np.generic):
            return value.item()
        if isinstance(value, np.ndarray):
            return value.tolist()
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    return value


def _is_nan_like(value):
    if value is None:
        return True
    if isinstance(value, float):
        try:
            return value != value  # NaN test that doesn't require numpy
        except Exception:
            return False
    if isinstance(value, str) and value.strip().lower() in ("", "nan", "none", "null"):
        return True
    return False


class MLModel(TimestampMixin, BelongsToOrgMixin, db.Model):
    """A trainable machine learning model bound to a Redash query.

    The query produces the input data (``query.latest_query_data``) which is
    cleaned, encoded, split into train/validation, then fed to the configured
    sklearn regressor or classifier. The fitted estimator is joblib-pickled,
    zlib-compressed and stored in ``model_blob``; an immutable snapshot is
    written to ``ml_model_versions`` so the user can revert later.
    """

    UNKNOWN_STATE = "unknown"
    OK_STATE = "ok"
    TRIGGERED_STATE = "triggered"
    TRAINING_STATE = "training"
    TRAINED_STATE = "trained"
    PREDICTING_STATE = "predicting"
    PREDICTED_STATE = "predicted"
    ERROR_STATE = "error"

    __tablename__ = "ml_models"
    __table_args__ = (db.Index("ml_models_org_id_name", "org_id", "name"),)

    id = primary_key("MLModel")
    name = Column(db.String(255), nullable=False)
    description = Column(db.String(1024), nullable=True)
    version = Column(db.Integer, nullable=False, default=1)
    query_id = Column(key_type("Query"), db.ForeignKey("queries.id"), nullable=False)
    user_id = Column(key_type("User"), db.ForeignKey("users.id"), nullable=False)
    org_id = Column(key_type("Organization"), db.ForeignKey("organizations.id"), nullable=False)

    tags = Column("tags", MutableList.as_mutable(postgresql.ARRAY(db.Unicode)), nullable=True)
    is_archived = Column(db.Boolean, default=False, index=True, nullable=False)
    last_triggered_at = Column(db.DateTime(True), nullable=True)
    rearm = Column(db.Integer, nullable=True)

    state = Column(db.String(255), default=UNKNOWN_STATE)
    state_train = Column(db.String(255), default=UNKNOWN_STATE)
    state_predict = Column(db.String(255), default=UNKNOWN_STATE)

    options = Column(MutableDict.as_mutable(postgresql.JSON), server_default="{}", default={})
    input_data = Column(db.Text, nullable=True, default="")
    model_blob = Column(db.LargeBinary, nullable=False, default=b"")

    metrics = Column(MutableDict.as_mutable(postgresql.JSON), nullable=True)

    train_data_hash = Column(db.String(64), nullable=True)
    test_data_hash = Column(db.String(64), nullable=True)

    user = db.relationship(User, backref="ml_models")
    org = db.relationship(Organization, backref="ml_models")
    query_rel = db.relationship("Query", backref=backref("ml_models", cascade="all"))
    subscriptions = db.relationship("MLModelSubscription", cascade="all, delete-orphan")

    # Class-level configuration helpers ---------------------------------

    @classmethod
    def all(cls, group_ids):
        from redash.models import DataSourceGroup, Query

        return (
            cls.query.options(joinedload(cls.user), joinedload(cls.query_rel))
            .join(Query, Query.id == cls.query_id)
            .join(DataSourceGroup, DataSourceGroup.data_source_id == Query.data_source_id)
            .filter(DataSourceGroup.group_id.in_(group_ids))
        )

    @classmethod
    def get_by_id(cls, _id):
        return cls.query.filter(cls.id == _id).one()

    @classmethod
    def all_models(cls, group_ids, user_id=None, include_archived=False):
        from redash.models import DataSourceGroup, Query

        models = (
            cls.query.options(
                joinedload(cls.user),
                joinedload(cls.query_rel),
                defer(cls.model_blob),
            )
            .join(Query, Query.id == cls.query_id)
            .join(DataSourceGroup, DataSourceGroup.data_source_id == Query.data_source_id)
            .filter(DataSourceGroup.group_id.in_(group_ids))
        )
        if include_archived:
            models = models.filter(cls.is_archived.is_(True))
        else:
            models = models.filter(cls.is_archived.is_(False))
        return models

    @classmethod
    def search(cls, term, group_ids, user_id=None, limit=None, include_archived=False):
        like = "%{0}%".format(term)
        results = (
            cls.all_models(group_ids, user_id=user_id, include_archived=include_archived)
            .outerjoin(User, User.id == cls.user_id)
            .filter(or_(cls.name.ilike(like), User.name.ilike(like)))
        )
        if limit:
            results = results.limit(limit)
        return results

    @classmethod
    def by_user(cls, user):
        return cls.all_models(user.group_ids, user.id).filter(cls.user == user)

    @classmethod
    def search_by_user(cls, term, user, limit=None):
        like = "%{0}%".format(term)
        results = cls.by_user(user).filter(cls.name.ilike(like))
        if limit:
            results = results.limit(limit)
        return results

    @classmethod
    def all_tags(cls, org, user):
        models = cls.all(user.group_ids)
        tag_column = func.unnest(cls.tags).label("tag")
        usage_count = func.count(1).label("usage_count")
        return (
            db.session.query(tag_column, usage_count)
            .group_by(tag_column)
            .filter(cls.id.in_(models.options(load_only("id"))))
            .order_by(usage_count.desc())
        )

    @classmethod
    def favorites(cls, user, base_query=None):
        from redash.models import Favorite

        if base_query is None:
            base_query = cls.all_models(user.group_ids, user.id)
        return base_query.join(
            (
                Favorite,
                and_(Favorite.object_type == "MLModel", Favorite.object_id == cls.id),
            )
        ).filter(Favorite.user_id == user.id)

    @classmethod
    def get_by_id_and_org(cls, object_id, org):
        from redash.models import Query

        return super(MLModel, cls).get_by_id_and_org(object_id, org, Query)

    @classmethod
    def delete_model(cls, model_id, org_id):
        """Cascade-delete a model and all its versions / predictions / subscriptions."""
        model = cls.query.filter_by(id=model_id, org_id=org_id).first()
        if not model:
            return
        try:
            for v in MLModelVersion.get_by_model_id(model_id):
                db.session.delete(v)
            for sub in MLModelSubscription.get_by_model_id(model_id):
                db.session.delete(sub)
            for pred in PredictionResult.get_by_model_id(model_id):
                db.session.delete(pred)
            db.session.delete(model)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    # Instance helpers ---------------------------------------------------

    @property
    def groups(self):
        return self.query_rel.groups

    @property
    def muted(self):
        return bool(self.options.get("muted", False))

    @property
    def regressor(self):
        return self.options.get("regressor", "Regression")

    @property
    def train_size(self):
        return float(self.options.get("train_size", 0.8))

    @property
    def test_size(self):
        return float(self.options.get("test_size", 0.2))

    @property
    def random_state(self):
        return int(self.options.get("random_state", 42))

    @property
    def features(self):
        return list(self.options.get("features", []))

    @features.setter
    def features(self, feature_list):
        self.options["features"] = list(feature_list)

    @property
    def targets(self):
        return list(self.options.get("targets", []))

    @targets.setter
    def targets(self, target_list):
        self.options["targets"] = list(target_list)

    @property
    def regressor_options(self):
        return self.options.get("regressor_options", {})

    @regressor_options.setter
    def regressor_options(self, value):
        self.options["regressor_options"] = value

    def archive(self, user=None):
        db.session.add(self)
        self.is_archived = True
        if user:
            self.record_changes(user)

    def unarchive(self, user=None):
        db.session.add(self)
        self.is_archived = False
        if user:
            self.record_changes(user)

    def stop(self):
        """Set the cooperative stop flag picked up by training/predicting loops."""
        self.options["stop"] = True
        db.session.commit()
        return self

    def evaluate(self):
        """Compare the latest query result against the train/predict thresholds."""
        if not self.query_rel or not self.query_rel.latest_query_data:
            return self.UNKNOWN_STATE
        data = self.query_rel.latest_query_data.data
        rows = (data or {}).get("rows") or []
        if not rows or "column" not in self.options:
            return self.UNKNOWN_STATE
        column = self.options.get("column")
        if column not in rows[0]:
            return self.UNKNOWN_STATE
        op = OPERATORS.get(self.options.get("op"), lambda v, t: False)
        return self.TRIGGERED_STATE if op(rows[0][column], self.options.get("value")) else self.OK_STATE

    # Training -----------------------------------------------------------

    def _clean_data(self, rows):
        """Drop rows with missing values and normalise types in-place."""
        if not rows:
            return []
        cleaned = []
        for row in rows:
            if any(v is None or (isinstance(v, float) and pd.isna(v)) for v in row.values()):
                continue
            cleaned.append({k: (float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v) for k, v in row.items()})
        return cleaned

    def _hash_rows(self, rows):
        try:
            payload = [{k: _to_serializable(v) for k, v in row.items()} for row in rows]
            return hashlib.sha256(json_dumps(payload).encode()).hexdigest()
        except Exception:
            return None

    def _engineer_features(self, df, mode):
        """Build feature matrix X (numpy 2-D float array).

        Numeric columns get a ``StandardScaler``, categorical columns get a
        ``OneHotEncoder``. Encoders are pickled into ``options`` so that
        ``predict`` can apply the exact same transformations.
        """
        sk = _sklearn()
        OneHotEncoder = sk["OneHotEncoder"]
        StandardScaler = sk["StandardScaler"]
        if mode == "train":
            self.options["feature_types"] = {}
            self.options["feature_encoders"] = {}
            self.options["feature_scalers"] = {}

        feature_types = dict(self.options.get("feature_types", {}))
        feature_encoders = dict(self.options.get("feature_encoders", {}))
        feature_scalers_blob = self.options.get("feature_scalers", "")
        feature_scalers = {}
        if mode == "predict" and feature_scalers_blob:
            try:
                feature_scalers = joblib.load(io.BytesIO(zlib.decompress(bytes(feature_scalers_blob, "latin1"))))
            except Exception:
                logger.exception("Failed to restore feature scalers; refitting from current data")
                feature_scalers = {}

        cols = []
        new_columns = {}

        for feature in self.features:
            if feature not in df.columns:
                raise ValueError("Feature column %r is missing from the input data" % feature)

            if mode == "train":
                series = df[feature]
                if pd.api.types.is_numeric_dtype(series) and series.notna().any():
                    feature_types[feature] = "numeric"
                else:
                    feature_types[feature] = "categorical"

            ftype = feature_types.get(feature, "categorical")
            series = df[feature]

            if ftype == "numeric":
                values = pd.to_numeric(series, errors="coerce").fillna(0.0).values.reshape(-1, 1)
                if mode == "train":
                    scaler = StandardScaler()
                    new_columns[feature] = scaler.fit_transform(values).ravel()
                    feature_scalers[feature] = scaler
                else:
                    scaler = feature_scalers.get(feature)
                    if scaler is None:
                        scaler = StandardScaler().fit(values)
                    new_columns[feature] = scaler.transform(values).ravel()
                cols.append(feature)
            else:  # categorical
                str_values = series.astype(str).values.reshape(-1, 1)
                if mode == "train":
                    encoder = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
                    encoded = encoder.fit_transform(str_values)
                    feature_encoders[feature] = {"categories": encoder.categories_[0].tolist()}
                else:
                    categories = feature_encoders.get(feature, {}).get("categories")
                    if categories is None:
                        encoder = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
                        encoded = encoder.fit_transform(str_values)
                    else:
                        encoder = OneHotEncoder(sparse_output=False, handle_unknown="ignore", categories=[categories])
                        encoded = encoder.fit_transform(str_values)
                for i in range(encoded.shape[1]):
                    name = "{0}_{1}".format(feature, i)
                    new_columns[name] = encoded[:, i]
                    cols.append(name)

        if mode == "train":
            self.options["feature_types"] = feature_types
            self.options["feature_encoders"] = feature_encoders
            buf = io.BytesIO()
            joblib.dump(feature_scalers, buf)
            self.options["feature_scalers"] = zlib.compress(buf.getvalue()).decode("latin1")

        if not cols:
            raise ValueError("Feature engineering produced no columns")

        return np.column_stack([new_columns[c] for c in cols]).astype(np.float64)

    def _extract_targets(self, df, mode):
        """Build target matrix y and remember the encoders for later decoding."""
        sk = _sklearn()
        OneHotEncoder = sk["OneHotEncoder"]
        StandardScaler = sk["StandardScaler"]
        if mode == "train":
            target_types = {}
            target_encoders = {}
        else:
            target_types = dict(self.options.get("target_types", {}))
            target_encoders = dict(self.options.get("target_encoders", {}))

        y_columns = []
        for target in self.targets:
            if target not in df.columns:
                raise ValueError("Target column %r is missing from the input data" % target)
            series = df[target]
            if mode == "train":
                if pd.api.types.is_numeric_dtype(series) and series.notna().any():
                    target_types[target] = "numeric"
                else:
                    target_types[target] = "categorical"

            ttype = target_types.get(target, "categorical")
            if ttype == "numeric":
                values = pd.to_numeric(series, errors="coerce").fillna(0.0).values.reshape(-1, 1)
                if mode == "train":
                    scaler = StandardScaler()
                    scaled = scaler.fit_transform(values)
                    target_encoders[target] = {
                        "type": "StandardScaler",
                        "mean": scaler.mean_.tolist(),
                        "scale": scaler.scale_.tolist(),
                    }
                else:
                    enc = target_encoders.get(target, {})
                    mean = np.array(enc.get("mean", [0.0]))
                    scale = np.array(enc.get("scale", [1.0]))
                    scale = np.where(scale == 0, 1.0, scale)
                    scaled = (values - mean) / scale
                y_columns.append(scaled)
            else:
                str_values = series.astype(str).values.reshape(-1, 1)
                if mode == "train":
                    encoder = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
                    encoded = encoder.fit_transform(str_values)
                    target_encoders[target] = {
                        "type": "OneHotEncoder",
                        "categories": encoder.categories_[0].tolist(),
                    }
                else:
                    categories = target_encoders.get(target, {}).get("categories", [])
                    if categories:
                        encoder = OneHotEncoder(sparse_output=False, handle_unknown="ignore", categories=[categories])
                    else:
                        encoder = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
                    encoded = encoder.fit_transform(str_values)
                y_columns.append(encoded)

        if mode == "train":
            self.options["target_types"] = target_types
            self.options["target_encoders"] = target_encoders

        if not y_columns:
            raise ValueError("No targets specified")

        return np.hstack(y_columns), target_types, target_encoders

    def _build_estimator(self):
        """Return an unfitted sklearn estimator based on ``self.regressor``."""
        sk = _sklearn()
        target_types = dict(self.options.get("target_types", {}))
        is_classification = bool(target_types) and all(t == "categorical" for t in target_types.values())
        regressor_name = self.regressor
        opts = dict(self.regressor_options)
        auto_mode = bool(opts.pop("auto_mode", False))

        builders = {
            "RandomForest": (sk["RandomForestClassifier"], sk["RandomForestRegressor"]),
            "GradientBoosting": (sk["GradientBoostingClassifier"], sk["GradientBoostingRegressor"]),
            "AdaBoost": (sk["AdaBoostClassifier"], sk["AdaBoostRegressor"]),
        }

        if regressor_name in builders:
            cls = builders[regressor_name][0 if is_classification else 1]
            base = cls()
            param_dist = self._param_distribution(regressor_name, is_classification)
        elif regressor_name == "Regression":
            if is_classification:
                base = sk["OneVsRestClassifier"](sk["LogisticRegression"](max_iter=1000))
                param_dist = {"estimator__C": [0.01, 0.1, 1.0, 10.0]}
            else:
                base = sk["LinearRegression"]()
                param_dist = {}
        else:
            raise ValueError("Regressor %r is not supported" % regressor_name)

        if len(self.targets) > 1 and not isinstance(base, sk["OneVsRestClassifier"]):
            base = sk["MultiOutputClassifier"](base) if is_classification else sk["MultiOutputRegressor"](base)
            param_dist = {"estimator__" + k: v for k, v in param_dist.items()}

        if auto_mode and param_dist:
            return sk["RandomizedSearchCV"](
                base,
                param_distributions=param_dist,
                n_iter=10,
                cv=3,
                random_state=self.random_state,
                n_jobs=-1,
            )
        return base

    def _param_distribution(self, regressor_name, is_classification):
        if regressor_name == "RandomForest":
            return {
                "n_estimators": [50, 100, 200],
                "max_depth": [None, 5, 10, 20],
                "min_samples_split": [2, 5, 10],
                "min_samples_leaf": [1, 2, 4],
            }
        if regressor_name == "GradientBoosting":
            return {
                "n_estimators": [50, 100, 200],
                "learning_rate": [0.01, 0.1, 0.5],
                "max_depth": [3, 5, 10],
            }
        if regressor_name == "AdaBoost":
            return {
                "n_estimators": [50, 100, 200],
                "learning_rate": [0.01, 0.1, 1.0],
            }
        return {}

    def train(self):
        """Run a full train cycle: clean -> engineer -> split -> fit -> evaluate -> save."""
        _require_ml_deps()
        if self.state_train == self.TRAINING_STATE:
            return self
        self.state = self.TRAINING_STATE
        self.state_train = self.TRAINING_STATE
        self.options["train_last_triggered_at"] = datetime.datetime.utcnow().isoformat()
        self.options["stop"] = False
        db.session.commit()

        try:
            data = (self.query_rel.latest_query_data.data or {}).get("rows", [])
            data = self._clean_data(data)
            if not data:
                raise ValueError("No usable rows in the latest query result")

            self.train_data_hash = self._hash_rows(data)

            df = pd.DataFrame(data)
            if not self.features:
                self.features = [c for c in df.columns if c not in self.targets]

            X = self._engineer_features(df, mode="train")
            y, target_types, target_encoders = self._extract_targets(df, mode="train")

            sk = _sklearn()
            X_train, X_val, y_train, y_val = sk["train_test_split"](
                X, y, test_size=self.test_size, random_state=self.random_state
            )

            estimator = self._build_estimator()

            # Single-output sklearn estimators expect y as a 1-D array; multi-output
            # estimators want a 2-D array.
            multi_output_types = (sk["MultiOutputRegressor"], sk["MultiOutputClassifier"])
            if y_train.shape[1] == 1 and not isinstance(estimator, multi_output_types):
                estimator.fit(X_train, y_train.ravel())
                y_train_pred = estimator.predict(X_train).reshape(-1, 1)
                y_val_pred = estimator.predict(X_val).reshape(-1, 1)
            else:
                estimator.fit(X_train, y_train)
                y_train_pred = np.asarray(estimator.predict(X_train))
                y_val_pred = np.asarray(estimator.predict(X_val))
                if y_train_pred.ndim == 1:
                    y_train_pred = y_train_pred.reshape(-1, 1)
                if y_val_pred.ndim == 1:
                    y_val_pred = y_val_pred.reshape(-1, 1)

            self._calculate_metrics(y_val, y_val_pred, y_train, y_train_pred, target_encoders)
            self._save_estimator(estimator)
            self.save_new_version("Model trained")

            self.state = self.OK_STATE
            self.state_train = self.TRAINED_STATE
            db.session.commit()
            return self
        except Exception:
            logger.exception("Training failed for model %s", self.id)
            db.session.rollback()
            self.state = self.ERROR_STATE
            self.state_train = self.ERROR_STATE
            db.session.commit()
            raise

    def predict(self):
        """Run inference using the stored estimator and persist a PredictionResult."""
        _require_ml_deps()
        if self.state_predict == self.PREDICTING_STATE or self.state_train == self.TRAINING_STATE:
            return None
        if not self.model_blob:
            raise ValueError("Model has not been trained yet")

        self.state_predict = self.PREDICTING_STATE
        self.state = self.OK_STATE
        db.session.commit()

        try:
            estimator = self._load_estimator()
            data = (self.query_rel.latest_query_data.data or {}).get("rows", [])
            if not data:
                raise ValueError("No data available for prediction")

            df = pd.DataFrame(data)
            X = self._engineer_features(df, mode="predict")
            target_types = dict(self.options.get("target_types", {}))
            target_encoders = dict(self.options.get("target_encoders", {}))

            predictions = np.asarray(estimator.predict(X))
            if predictions.ndim == 1:
                predictions = predictions.reshape(-1, 1)

            decoded = self._decode_predictions(predictions, target_types, target_encoders)
            prediction_row = self._save_prediction_results(df, decoded)

            self.options["predict_last_triggered_at"] = datetime.datetime.utcnow().isoformat()
            self.state_predict = self.PREDICTED_STATE
            self.state = self.OK_STATE
            db.session.commit()
            return prediction_row
        except Exception:
            logger.exception("Prediction failed for model %s", self.id)
            db.session.rollback()
            self.state = self.ERROR_STATE
            self.state_predict = self.ERROR_STATE
            db.session.commit()
            raise

    # Versioning ---------------------------------------------------------

    def save_new_version(self, change_description="Model updated"):
        highest = (
            db.session.query(func.max(MLModelVersion.version))
            .filter(MLModelVersion.model_id == self.id)
            .scalar()
            or 0
        )
        new_version = MLModelVersion(
            model_id=self.id,
            name=self.name,
            description=self.description,
            user_id=self.user_id,
            org_id=self.org_id,
            query_id=self.query_id,
            version=highest + 1,
            changes=change_description,
            model_blob=self.model_blob,
            metrics=self.metrics,
            options=dict(self.options or {}),
            last_triggered_at=self.last_triggered_at,
            rearm=self.rearm,
            state=self.state,
            state_train=self.state_train,
            state_predict=self.state_predict,
            input_data=self.input_data,
        )
        self.version = highest + 1
        db.session.add(new_version)
        db.session.commit()
        return new_version

    def revert_to_version(self, version_number):
        version = MLModelVersion.query.filter_by(model_id=self.id, version=version_number).first()
        if not version:
            raise ValueError("Version %s not found" % version_number)
        self.model_blob = version.model_blob
        self.metrics = version.metrics
        self.options = dict(version.options or {})
        self.name = version.name
        self.description = version.description
        self.query_id = version.query_id
        self.last_triggered_at = version.last_triggered_at
        self.rearm = version.rearm
        self.input_data = version.input_data
        self.state = self.UNKNOWN_STATE
        self.state_train = self.UNKNOWN_STATE
        self.state_predict = self.UNKNOWN_STATE
        db.session.commit()
        return self

    def create_from_version(self, version_number):
        version = MLModelVersion.query.filter_by(model_id=self.id, version=version_number).first()
        if not version:
            raise ValueError("Version %s not found" % version_number)
        new_model = MLModel(
            name="{0} (Copy from v{1})".format(version.name, version_number),
            description=version.description,
            user_id=self.user_id,
            org_id=self.org_id,
            query_id=version.query_id,
            version=1,
            model_blob=version.model_blob,
            metrics=version.metrics,
            options=dict(version.options or {}),
            state=self.UNKNOWN_STATE,
            state_train=self.UNKNOWN_STATE,
            state_predict=self.UNKNOWN_STATE,
            rearm=version.rearm,
            input_data=version.input_data,
        )
        db.session.add(new_model)
        db.session.commit()
        return new_model

    def copy_model(self):
        new_model = MLModel(
            name="{0} (Copy)".format(self.name),
            description=self.description,
            user_id=self.user_id,
            org_id=self.org_id,
            query_id=self.query_id,
            version=1,
            model_blob=self.model_blob,
            metrics=self.metrics,
            options=dict(self.options or {}),
            state=self.state,
            state_train=self.state_train,
            state_predict=self.state_predict,
            rearm=self.rearm,
            input_data=self.input_data,
        )
        db.session.add(new_model)
        db.session.commit()
        return new_model

    # Persistence helpers ------------------------------------------------

    def _save_estimator(self, estimator):
        _require_ml_deps()
        buf = io.BytesIO()
        joblib.dump(estimator, buf)
        compressed = zlib.compress(buf.getvalue(), level=9)
        size_mb = len(compressed) / (1024 * 1024)
        max_mb = settings.ML_MODEL_MAX_BLOB_MB
        if size_mb > max_mb:
            raise ValueError(
                "Serialized model size ({0:.1f} MB) exceeds the configured cap of {1} MB".format(size_mb, max_mb)
            )
        self.model_blob = compressed
        logger.info("Saved estimator for model %s (%.2f MB compressed)", self.id, size_mb)

    def _load_estimator(self):
        _require_ml_deps()
        blob = self.model_blob
        try:
            blob = zlib.decompress(blob)
        except (zlib.error, TypeError):
            # Legacy/uncompressed blob — keep the raw bytes.
            pass
        return joblib.load(io.BytesIO(blob))

    # Decoding / metrics -------------------------------------------------

    def _decode_predictions(self, predictions, target_types, target_encoders):
        decoded_columns = {}
        start = 0
        for target in self.targets:
            ttype = target_types.get(target, "categorical")
            encoder_info = target_encoders.get(target, {})
            if ttype == "numeric":
                column = predictions[:, start]
                mean = np.array(encoder_info.get("mean", [0.0]))
                scale = np.array(encoder_info.get("scale", [1.0]))
                scale = np.where(scale == 0, 1.0, scale)
                decoded_columns["pred_{0}".format(target)] = (column * scale + mean).flatten().tolist()
                start += 1
            else:
                categories = encoder_info.get("categories", [])
                num_categories = len(categories) or 1
                # Predictions might be class indices (single column) or probabilities (one-hot).
                if predictions.shape[1] - start >= num_categories and num_categories > 1:
                    block = predictions[:, start : start + num_categories]
                    indices = np.argmax(block, axis=1)
                    start += num_categories
                else:
                    indices = predictions[:, start].astype(int)
                    start += 1
                decoded_columns["pred_{0}".format(target)] = [
                    categories[i] if 0 <= i < len(categories) else "Unknown" for i in indices
                ]
        return pd.DataFrame(decoded_columns)

    def _calculate_metrics(self, y_true, y_pred, y_train, y_train_pred, target_encoders):
        metrics = {}
        target_types = dict(self.options.get("target_types", {}))
        start = 0
        for target in self.targets:
            ttype = target_types.get(target, "categorical")
            if ttype == "numeric":
                yt = y_true[:, start]
                yp = y_pred[:, start]
                ytt = y_train[:, start]
                ytp = y_train_pred[:, start]
                metrics[target] = self._regression_metrics(yt, yp, ytt, ytp)
                start += 1
            else:
                categories = target_encoders.get(target, {}).get("categories", [])
                n = max(len(categories), 1)
                yt = np.argmax(y_true[:, start : start + n], axis=1) if n > 1 else y_true[:, start].astype(int)
                yp = np.argmax(y_pred[:, start : start + n], axis=1) if n > 1 else y_pred[:, start].astype(int)
                ytt = np.argmax(y_train[:, start : start + n], axis=1) if n > 1 else y_train[:, start].astype(int)
                ytp = np.argmax(y_train_pred[:, start : start + n], axis=1) if n > 1 else y_train_pred[:, start].astype(int)
                metrics[target] = self._classification_metrics(yt, yp, ytt, ytp)
                start += n if n > 1 else 1

        overall = {}
        for key in ("mean_absolute_error", "mean_squared_error", "r2_score", "accuracy", "precision", "recall", "f1_score"):
            values = [m[key] for m in metrics.values() if key in m]
            if values:
                overall[key] = float(np.mean(values))
        overfit_scores = [m.get("overfitting_score", 0) for m in metrics.values()]
        if overfit_scores:
            overall["overfitting_score"] = float(np.mean(overfit_scores))
            overall["max_overfitting_score"] = float(max(overfit_scores))
            overall["is_overfitted"] = any(s > 0.4 for s in overfit_scores) or overall["overfitting_score"] > 0.25
        metrics["overall"] = overall
        self.metrics = self._numpy_to_python(metrics)

    @staticmethod
    def _classification_metrics(y_true, y_pred, y_train, y_train_pred):
        sk = _sklearn()
        try:
            val_acc = float(sk["accuracy_score"](y_true, y_pred))
            train_acc = float(sk["accuracy_score"](y_train, y_train_pred))
        except Exception:
            val_acc = train_acc = 0.0
        return {
            "accuracy": val_acc,
            "precision": float(sk["precision_score"](y_true, y_pred, average="weighted", zero_division=0)),
            "recall": float(sk["recall_score"](y_true, y_pred, average="weighted", zero_division=0)),
            "f1_score": float(sk["f1_score"](y_true, y_pred, average="weighted", zero_division=0)),
            "train_performance": train_acc,
            "val_performance": val_acc,
            "overfitting_score": max(train_acc - val_acc, 0.0),
            "is_overfitted": (train_acc - val_acc) > 0.25,
        }

    @staticmethod
    def _regression_metrics(y_true, y_pred, y_train, y_train_pred):
        sk = _sklearn()
        try:
            val_r2 = float(sk["r2_score"](y_true, y_pred))
            train_r2 = float(sk["r2_score"](y_train, y_train_pred))
        except Exception:
            val_r2 = train_r2 = 0.0
        return {
            "mean_absolute_error": float(sk["mean_absolute_error"](y_true, y_pred)),
            "mean_squared_error": float(sk["mean_squared_error"](y_true, y_pred)),
            "r2_score": val_r2,
            "train_performance": train_r2,
            "val_performance": val_r2,
            "overfitting_score": max(train_r2 - val_r2, 0.0),
            "is_overfitted": (train_r2 - val_r2) > 0.25,
        }

    @classmethod
    def _numpy_to_python(cls, obj):
        if isinstance(obj, np.generic):
            return obj.item()
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, dict):
            return {k: cls._numpy_to_python(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [cls._numpy_to_python(v) for v in obj]
        return obj

    def _save_prediction_results(self, data_df, predictions_df):
        original_columns = list(data_df.columns)
        prediction_columns = list(predictions_df.columns)

        rows = []
        for i, original in enumerate(data_df.to_dict(orient="records")):
            row = {k: _to_serializable(v) for k, v in original.items()}
            for col in prediction_columns:
                row[col] = _to_serializable(predictions_df.iloc[i][col])
            rows.append(row)

        columns_meta = []
        for col in original_columns:
            sample = data_df.iloc[0][col] if len(data_df) else None
            columns_meta.append({"name": col, "friendly_name": col.replace("_", " ").title(), "type": _column_type(sample)})
        for col in prediction_columns:
            sample = predictions_df.iloc[0][col] if len(predictions_df) else None
            columns_meta.append({"name": col, "friendly_name": col.replace("_", " ").title(), "type": _column_type(sample)})

        bundle = json_dumps({"rows": rows, "columns": columns_meta})
        prediction = PredictionResult(
            model_id=self.id,
            model_version=self.version,
            user_id=self.user_id,
            org_id=self.org_id,
            query_id=self.query_id,
            destination_id=None,
            input_data=self.input_data,
            content=bundle,
            additional_properties=self.metrics,
        )
        db.session.add(prediction)
        db.session.commit()
        return prediction


def _column_type(value):
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "float"
    if isinstance(value, datetime.datetime):
        return "datetime"
    return "string"


class MLModelVersion(BelongsToOrgMixin, db.Model):
    """Immutable snapshot of an MLModel taken on every successful train."""

    __tablename__ = "ml_model_versions"
    __table_args__ = (UniqueConstraint("model_id", "version", name="unique_model_version"),)

    id = primary_key("MLModelVersion")
    model_id = Column(key_type("MLModel"), db.ForeignKey("ml_models.id"), nullable=False)
    name = Column(db.String(255))
    description = Column(db.String(1024), nullable=True)
    version = Column(db.Integer, nullable=False)
    created_at = Column(db.DateTime(True), default=db.func.now())
    updated_at = Column(db.DateTime(True), default=db.func.now(), onupdate=db.func.now())

    user_id = Column(key_type("User"), db.ForeignKey("users.id"))
    org_id = Column(key_type("Organization"), db.ForeignKey("organizations.id"))
    query_id = Column(key_type("Query"), db.ForeignKey("queries.id"))

    changes = Column(db.String(255), nullable=True)
    model_blob = Column(db.LargeBinary, nullable=False, default=b"")
    metrics = Column(MutableDict.as_mutable(postgresql.JSON), nullable=True)
    options = Column(MutableDict.as_mutable(postgresql.JSON), server_default="{}", default={})
    is_archived = Column(db.Boolean, default=False, index=True, nullable=False)
    tags = Column("tags", MutableList.as_mutable(postgresql.ARRAY(db.Unicode)), nullable=True)
    rearm = Column(db.Integer, nullable=True)
    last_triggered_at = Column(db.DateTime(True), nullable=True)
    state = Column(db.String(255), default=MLModel.UNKNOWN_STATE)
    state_train = Column(db.String(255), default=MLModel.UNKNOWN_STATE)
    state_predict = Column(db.String(255), default=MLModel.UNKNOWN_STATE)
    input_data = Column(db.Text, nullable=True, default="")

    model = db.relationship(MLModel, backref="versions")
    user = db.relationship(User, backref="ml_model_versions")
    org = db.relationship(Organization, backref="ml_model_versions")
    query_rel = db.relationship("Query", backref="ml_model_versions")

    def to_dict(self):
        return {
            "id": self.id,
            "model_id": self.model_id,
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "user_id": self.user_id,
            "org_id": self.org_id,
            "query_id": self.query_id,
            "changes": self.changes,
            "metrics": self.metrics,
            "options": self.options,
            "is_archived": self.is_archived,
            "tags": self.tags,
        }

    @classmethod
    def get_by_id(cls, _id):
        return cls.query.filter(cls.id == _id).one()

    @classmethod
    def get_by_model_id(cls, model_id):
        return cls.query.filter(cls.model_id == model_id).all()

    @classmethod
    def get_by_model_id_and_org(cls, model_id, org):
        return (
            cls.query.options(defer(cls.model_blob))
            .filter_by(model_id=model_id, org_id=org.id)
            .order_by(cls.version.desc())
            .all()
        )

    @classmethod
    def all(cls, group_ids):
        from redash.models import DataSourceGroup, Query

        return (
            cls.query.options(joinedload(cls.user), joinedload(cls.model), defer(cls.model_blob))
            .join(MLModel, MLModel.id == cls.model_id)
            .join(Query, Query.id == cls.query_id)
            .join(DataSourceGroup, DataSourceGroup.data_source_id == Query.data_source_id)
            .filter(DataSourceGroup.group_id.in_(group_ids))
        )

    @classmethod
    def all_models(cls, group_ids, user_id=None, include_archived=False):
        results = cls.all(group_ids)
        if include_archived:
            results = results.filter(cls.is_archived.is_(True))
        else:
            results = results.filter(cls.is_archived.is_(False))
        return results

    @classmethod
    def search(cls, term, group_ids, user_id=None, limit=None, include_archived=False):
        like = "%{0}%".format(term)
        results = (
            cls.all_models(group_ids, user_id=user_id, include_archived=include_archived)
            .outerjoin(User, User.id == cls.user_id)
            .filter(or_(cls.name.ilike(like), User.name.ilike(like)))
        )
        if limit:
            results = results.limit(limit)
        return results

    @classmethod
    def by_user(cls, user):
        return cls.all_models(user.group_ids, user.id).filter(cls.user == user)

    @classmethod
    def search_by_user(cls, term, user, limit=None):
        like = "%{0}%".format(term)
        results = cls.by_user(user).filter(cls.name.ilike(like))
        if limit:
            results = results.limit(limit)
        return results

    @classmethod
    def all_tags(cls, org, user):
        models = cls.all(user.group_ids)
        tag_column = func.unnest(cls.tags).label("tag")
        usage_count = func.count(1).label("usage_count")
        return (
            db.session.query(tag_column, usage_count)
            .group_by(tag_column)
            .filter(cls.id.in_(models.options(load_only("id"))))
            .order_by(usage_count.desc())
        )

    @classmethod
    def favorites(cls, user, base_query=None):
        from redash.models import Favorite

        if base_query is None:
            base_query = cls.all_models(user.group_ids, user.id)
        return base_query.join(
            (
                Favorite,
                and_(Favorite.object_type == "MLModelVersion", Favorite.object_id == cls.id),
            )
        ).filter(Favorite.user_id == user.id)

    @classmethod
    def get_by_id_and_org(cls, object_id, org):
        from redash.models import Query

        return super(MLModelVersion, cls).get_by_id_and_org(object_id, org, Query)

    def archive(self, user=None):
        db.session.add(self)
        self.is_archived = True

    def unarchive(self, user=None):
        db.session.add(self)
        self.is_archived = False


class PredictionResult(BelongsToOrgMixin, db.Model):
    """One row per ``MLModel.predict`` invocation."""

    __tablename__ = "prediction_results"

    id = primary_key("PredictionResult")
    org_id = Column(key_type("Organization"), db.ForeignKey("organizations.id"), nullable=True)
    user_id = Column(key_type("User"), db.ForeignKey("users.id"), nullable=True)
    model_id = Column(key_type("MLModel"), db.ForeignKey("ml_models.id"), nullable=True)
    query_id = Column(key_type("Query"), db.ForeignKey("queries.id"), nullable=True)
    destination_id = Column(
        key_type("NotificationDestination"),
        db.ForeignKey("notification_destinations.id"),
        nullable=True,
    )

    additional_properties = Column(MutableDict.as_mutable(postgresql.JSONB), nullable=True, default={})
    is_archived = Column(db.Boolean, default=False, index=True, nullable=False)
    tags = Column("tags", MutableList.as_mutable(postgresql.ARRAY(db.Unicode)), nullable=True)
    model_version = Column(db.Integer, nullable=True)
    content = Column(db.Text, nullable=True)
    created_at = Column(db.DateTime(True), default=db.func.now())
    updated_at = Column(db.DateTime(True), default=db.func.now(), onupdate=db.func.now())
    input_data = Column(db.Text, nullable=True, default="")

    org = db.relationship(Organization, backref="prediction_results")
    user = db.relationship(User, backref="prediction_results")
    model = db.relationship(MLModel, backref="prediction_results")
    query_rel = db.relationship("Query", backref="prediction_results")
    destination = db.relationship("NotificationDestination", backref="prediction_results")

    def to_dict(self):
        return {
            "id": self.id,
            "model_id": self.model_id,
            "query_id": self.query_id,
            "destination_id": self.destination_id,
            "content": self.content,
            "created_at": self.created_at,
            "additional_properties": self.additional_properties,
        }

    def get_content_data(self):
        try:
            return json.loads(self.content) if self.content else None
        except json.JSONDecodeError:
            logger.exception("Failed to decode prediction content for id=%s", self.id)
            return None

    @classmethod
    def get_by_id(cls, _id):
        return cls.query.filter(cls.id == _id).one()

    @classmethod
    def get_by_model_id(cls, model_id):
        return cls.query.filter(cls.model_id == model_id).all()

    @classmethod
    def get_by_model_id_and_org(cls, model_id, org):
        return (
            cls.query.filter_by(model_id=model_id, org_id=org.id)
            .order_by(cls.created_at.desc())
            .all()
        )

    @classmethod
    def all(cls, group_ids):
        from redash.models import DataSourceGroup, Query

        return (
            cls.query.options(joinedload(cls.user), joinedload(cls.query_rel))
            .join(Query, Query.id == cls.query_id)
            .join(DataSourceGroup, DataSourceGroup.data_source_id == Query.data_source_id)
            .filter(DataSourceGroup.group_id.in_(group_ids))
        )

    @classmethod
    def all_predictions(cls, group_ids, user_id=None, include_archived=False):
        results = cls.all(group_ids)
        if include_archived:
            results = results.filter(cls.is_archived.is_(True))
        else:
            results = results.filter(cls.is_archived.is_(False))
        return results

    @classmethod
    def search(cls, term, group_ids, user_id=None, limit=None, include_archived=False):
        like = "%{0}%".format(term)
        results = (
            cls.all_predictions(group_ids, user_id=user_id, include_archived=include_archived)
            .outerjoin(MLModel, MLModel.id == cls.model_id)
            .outerjoin(User, User.id == cls.user_id)
            .filter(or_(MLModel.name.ilike(like), User.name.ilike(like)))
        )
        if limit:
            results = results.limit(limit)
        return results

    @classmethod
    def by_user(cls, user):
        return cls.all_predictions(user.group_ids, user.id).filter(cls.user == user)

    @classmethod
    def search_by_user(cls, term, user, limit=None):
        like = "%{0}%".format(term)
        results = (
            cls.by_user(user)
            .outerjoin(MLModel, MLModel.id == cls.model_id)
            .filter(MLModel.name.ilike(like))
        )
        if limit:
            results = results.limit(limit)
        return results

    @classmethod
    def all_tags(cls, org, user):
        predictions = cls.all(user.group_ids)
        tag_column = func.unnest(cls.tags).label("tag")
        usage_count = func.count(1).label("usage_count")
        return (
            db.session.query(tag_column, usage_count)
            .group_by(tag_column)
            .filter(cls.id.in_(predictions.options(load_only("id"))))
            .order_by(usage_count.desc())
        )

    @classmethod
    def favorites(cls, user, base_query=None):
        from redash.models import Favorite

        if base_query is None:
            base_query = cls.all_predictions(user.group_ids, user.id)
        return base_query.join(
            (
                Favorite,
                and_(Favorite.object_type == "PredictionResult", Favorite.object_id == cls.id),
            )
        ).filter(Favorite.user_id == user.id)

    @classmethod
    def get_by_id_and_org(cls, object_id, org):
        from redash.models import Query

        return super(PredictionResult, cls).get_by_id_and_org(object_id, org, Query)

    def archive(self, user=None):
        db.session.add(self)
        self.is_archived = True

    def unarchive(self, user=None):
        db.session.add(self)
        self.is_archived = False


class MLModelSubscription(TimestampMixin, db.Model):
    """A user/destination pair that should be notified when a model trains/predicts."""

    __tablename__ = "ml_model_subscriptions"
    __table_args__ = (
        db.Index(
            "ml_model_subscriptions_destination_id_model_id",
            "destination_id",
            "model_id",
            unique=True,
        ),
    )

    id = primary_key("MLModelSubscription")
    user_id = Column(key_type("User"), db.ForeignKey("users.id"))
    destination_id = Column(
        key_type("NotificationDestination"),
        db.ForeignKey("notification_destinations.id"),
        nullable=True,
    )
    model_id = Column(key_type("MLModel"), db.ForeignKey("ml_models.id"))

    user = db.relationship(User)
    destination = db.relationship("NotificationDestination")
    ml_model = db.relationship(MLModel, back_populates="subscriptions")

    def to_dict(self):
        d = {"id": self.id, "user": self.user.to_dict(), "model_id": self.model_id}
        if self.destination:
            d["destination"] = self.destination.to_dict()
        return d

    @classmethod
    def all(cls, model_id):
        return cls.query.join(User).filter(cls.model_id == model_id)

    @classmethod
    def get_by_model_id(cls, model_id):
        return cls.query.filter(cls.model_id == model_id).all()

    def _notify(self, model, query, user, new_state, app, host, notification_type):
        if self.destination:
            return self.destination.notify(
                model, query, user, new_state, app, host, self.destination.id, type=notification_type
            )
        # Email-fallback for user subscriptions without a destination.
        config = {"addresses": self.user.email}
        schema = get_configuration_schema_for_destination_type("email")
        options = ConfigurationContainer(config, schema)
        destination = get_destination("email", options)
        return destination.notify(model, query, user, new_state, app, host, None, options, type=notification_type)

    def notify_train(self, model, query, user, new_state, app, host):
        return self._notify(model, query, user, new_state, app, host, "model_train")

    def notify_predict(self, model, query, user, new_state, app, host):
        return self._notify(model, query, user, new_state, app, host, "model_predict")
