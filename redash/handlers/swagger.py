"""Flasgger / Swagger UI integration.

Mirrors the inverse-watch ``setup_api`` swagger configuration so the Redash
REST API is browseable at ``/api/docs/``. Each handler can document its own
endpoints by including a YAML block separated by ``---`` inside its docstring;
flasgger picks up those blocks automatically and merges them into the spec.

Example handler docstring::

    def post(self, alert_id):
        \"\"\"Mute an alert.

        ---
        tags:
          - Alerts
        security:
          - ApiKeyAuth: []
        parameters:
          - in: path
            name: alert_id
            required: true
            schema:
              type: integer
        responses:
          200:
            description: Alert muted successfully
        \"\"\"

The Swagger UI is exposed at ``/api/docs/`` and the raw OpenAPI 2.0 spec at
``/api/spec``. API key auth is the default security scheme: clients pass their
key as the ``api_key`` query parameter (Redash's standard convention).
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def default_swagger_config():
    """Return the base swagger 2.0 spec (matches inverse-watch's layout)."""
    return {
        "swagger": "2.0",
        "info": {
            "title": "Redash API",
            "description": (
                "The Redash REST API exposes everything the web UI uses: queries, "
                "dashboards, alerts, ML models, predictions, indexers and more. "
                "Authenticate by passing your personal API key as the ``api_key`` "
                "query parameter, or via the ``Authorization: Key <key>`` header."
            ),
            "termsOfService": "https://redash.io/help/",
            "contact": {"email": "maintainers@redash.io"},
            "version": "1.0.0",
        },
        "securityDefinitions": {
            "ApiKeyAuth": {
                "type": "apiKey",
                "name": "api_key",
                "in": "query",
            }
        },
        "security": [{"ApiKeyAuth": []}],
    }


def setup_swagger(app):
    """Initialise Flasgger on ``app`` and expose Swagger UI at ``/api/docs/``.

    Safe to call from production: if ``flasgger`` is not installed (e.g. on a
    slim image that skipped the extra ``pip install`` step) we log a warning and
    continue silently rather than crashing the whole server.
    """
    try:
        from flasgger import Swagger
    except ImportError:
        logger.warning(
            "flasgger is not installed; /api/docs/ will not be available. "
            "Install with `pip install flasgger==0.9.7.1` to enable the Swagger UI."
        )
        return None

    base_config = {
        "uiversion": 3,
        "specs_route": "/api/docs/",
        # Keep the OpenAPI spec endpoint stable so external consumers can fetch
        # it without going through the UI.
        "specs": [
            {
                "endpoint": "apispec_1",
                "route": "/api/spec",
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
    }

    existing = app.config.get("SWAGGER", {}) or {}
    app.config["SWAGGER"] = {
        **default_swagger_config(),
        **base_config,
        **existing,
    }
    app.config["SWAGGER"].setdefault("title", "Redash API")

    return Swagger(app)
