"""OpenAPI / API-docs integration.

Two pieces here:

1. **Spec generation** (custom). We walk Flask's URL map and emit an
   OpenAPI 2.0 document covering every route under ``/api/*``. Each handler
   contributes:

   * **Summary** — the first paragraph of its method docstring.
   * **Tag** — derived from the URL prefix (``/api/queries/...`` -> ``Queries``).
   * **Path parameters** — extracted from the Flask URL converter syntax.
   * **Optional override** — if the docstring contains a ``---``-separated
     YAML block (Flasgger-style), keys in that block override the auto-
     generated values for fine-grained control. Existing ML model
     docstrings keep their detailed swagger annotations this way.

   Auto-generation means new endpoints are documented the moment they're
   registered with Flask — no manual swagger annotation required.

2. **Docs UI** (Scalar). The rendered spec is consumed by a vendored
   Scalar bundle (see ``api_docs_static/``) served at ``/api/docs/``. Scalar
   fetches the spec from ``/api/spec`` at runtime — same origin, so no CSP
   relaxation is required.

Routes added by this module
---------------------------

* ``GET /api/spec``   — OpenAPI 2.0 JSON, generated on demand.
* ``GET /api/docs/``  — Scalar UI (HTML shell, no inline scripts).
* ``GET /api/docs/scalar.standalone.js`` — vendored Scalar runtime.
"""

from __future__ import annotations

import inspect
import logging
import os
import re
from collections import OrderedDict
from typing import Any, Dict, Iterable, List, Optional, Tuple

import yaml
from flask import Blueprint, current_app, jsonify, render_template_string, send_from_directory

logger = logging.getLogger(__name__)

# Where the vendored Scalar bundle lives. Travels with this Python package
# so it gets baked into the docker image alongside the rest of the source
# tree without any webpack involvement.
_API_DOCS_STATIC_DIR = os.path.join(os.path.dirname(__file__), "api_docs_static")

# OpenAPI 2.0 ``operationId`` must be unique. We deduplicate by appending a
# counter if collisions happen (rare; Flask endpoint names are usually
# unique on their own).
_OPERATION_ID_SUFFIX = re.compile(r"_(\d+)$")

# ``<int:widget_id>``, ``<string:token>``, ``<token>``, ``<filetype>`` ...
_FLASK_PARAM_RE = re.compile(r"<(?:(?P<conv>[^:>]+):)?(?P<name>[^>]+)>")

# Sphinx-style fields used liberally throughout the existing handler
# docstrings. We translate them into proper OpenAPI artefacts so they show
# up as structured rows in the docs UI rather than as raw markup text.
#
# Examples that get matched:
#   :qparam string q: Search term
#   :qparam number page: Page number
#   :<json string name: Query name
#   :>json number id: Query ID
#   :param query_id: ID of query to fetch
_SPHINX_FIELD_RE = re.compile(
    r"^\s*:(?P<role>qparam|<json|>json|param)\s+"
    r"(?:(?P<type>\w+)\s+)?(?P<name>[\w.\-]+)\s*:\s*(?P<desc>.*?)\s*$",
    re.MULTILINE,
)

# Sphinx ``:ref:`label <target>``` -> we just keep the label text.
_SPHINX_REF_RE = re.compile(r":ref:`([^`<]+?)\s*(?:<[^`>]+>)?`")
# Generic ``:role:`text``` cleanup once the structured fields are gone.
_SPHINX_INLINE_ROLE_RE = re.compile(r":(?:doc|class|func|mod|attr):`([^`]+)`")
# Sphinx anchor lines like ``.. _query-response-label:`` add no value here.
_SPHINX_ANCHOR_RE = re.compile(r"^\s*\.\.\s*_[\w-]+:\s*$", re.MULTILINE)

# Maps Flask URL converter names to OpenAPI 2.0 parameter types.
_CONVERTER_TYPES = {
    "int": "integer",
    "float": "number",
    "string": "string",
    "path": "string",
    "uuid": "string",
    None: "string",
}

# Tag definitions: order here drives the order in the rendered docs UI.
# A path is bucketed into the FIRST entry whose ``prefix`` matches.
_TAG_TABLE: List[Tuple[str, str, str]] = [
    # (prefix, tag name, description)
    ("/api/ml_models_versions", "MLModelVersions", "Snapshots produced by training runs of an MLModel."),
    ("/api/ml_models", "MLModels", "Train and run predictions with scikit-learn models bound to a Rewatch query."),
    ("/api/predictions", "Predictions", "Stored prediction results emitted by trained MLModel runs."),
    ("/api/indexers", "Indexers", "Long-running ingestion jobs that materialize external data into Rewatch."),
    ("/api/alerts", "Alerts", "Alerts evaluated against query results and the destinations they notify."),
    ("/api/alert_events", "AlertEvents", "History of alert evaluations and state transitions."),
    ("/api/dashboards", "Dashboards", "Dashboards, their widgets, sharing and favorites."),
    ("/api/widgets", "Widgets", "Individual widgets on a dashboard."),
    ("/api/visualizations", "Visualizations", "Visualizations attached to a query (chart, table, counter, ...)."),
    ("/api/queries", "Queries", "Queries against connected data sources."),
    ("/api/query_results", "QueryResults", "Cached query result rows and async result jobs."),
    ("/api/query_snippets", "QuerySnippets", "Private, per-user reusable SQL snippets."),
    ("/api/jobs", "Jobs", "Background job status (refreshes, exports, etc.)."),
    ("/api/data_sources", "DataSources", "Connections to external data warehouses, databases and APIs."),
    ("/api/databricks", "Databricks", "Databricks-specific data source helpers."),
    ("/api/destinations", "Destinations", "Private, per-user alert notification destinations (Slack, email, webhooks, ...)."),
    ("/api/users", "Users", "User accounts, invites, password resets and API keys."),
    ("/api/groups", "Groups", "User groups and the data sources they may access."),
    ("/api/events", "Events", "Audit log of user-facing actions."),
    ("/api/settings", "Settings", "Org-wide application settings."),
    ("/api/", "Misc", "Permission checks and other endpoints that don't fit a dedicated tag."),
]


def _classify(path: str) -> Tuple[str, str]:
    """Return ``(tag, tag_description)`` for the given path."""
    for prefix, name, desc in _TAG_TABLE:
        if path.startswith(prefix):
            return name, desc
    return "Misc", "Uncategorized."


def _extract_path_params(rule_path: str) -> Tuple[str, List[Dict[str, Any]]]:
    """Convert a Flask URL pattern to OpenAPI's ``{name}`` syntax.

    Returns ``(openapi_path, [parameter_objects])``.
    """
    parameters: List[Dict[str, Any]] = []
    seen = set()

    def _replace(match: re.Match) -> str:
        name = match.group("name")
        conv = match.group("conv")
        if name not in seen:
            seen.add(name)
            parameters.append(
                {
                    "name": name,
                    "in": "path",
                    "required": True,
                    "type": _CONVERTER_TYPES.get(conv, "string"),
                }
            )
        return "{" + name + "}"

    openapi_path = _FLASK_PARAM_RE.sub(_replace, rule_path)
    return openapi_path, parameters


_SPHINX_TYPE_TO_OPENAPI = {
    "string": "string",
    "str": "string",
    "number": "number",
    "int": "integer",
    "integer": "integer",
    "bool": "boolean",
    "boolean": "boolean",
    "object": "object",
    "array": "array",
    "list": "array",
}


def _parse_sphinx_fields(text: str) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
    """Extract Sphinx fields from a docstring body.

    Returns ``(cleaned_text, query_params, body_schema)``:

    * ``query_params`` — list of OpenAPI 2.0 query parameter objects built
      from ``:qparam <type> <name>: <desc>`` lines.
    * ``body_schema`` — a JSON schema (object) collected from
      ``:<json <type> <name>: <desc>`` lines, ready to be wrapped as a
      ``{"in": "body"}`` parameter. Empty dict if no body fields were found.
    * ``cleaned_text`` — the docstring body with all field markers and
      Sphinx anchor lines removed.
    """
    query_params: List[Dict[str, Any]] = []
    body_props: Dict[str, Dict[str, Any]] = {}
    response_props: Dict[str, Dict[str, Any]] = {}

    def _consume(match: re.Match) -> str:
        role = match.group("role")
        ftype = match.group("type") or ""
        name = match.group("name")
        desc = match.group("desc") or ""
        oapi_type = _SPHINX_TYPE_TO_OPENAPI.get(ftype.lower(), "string") if ftype else "string"
        if role == "qparam":
            query_params.append(
                {"name": name, "in": "query", "required": False, "type": oapi_type, "description": desc}
            )
        elif role == "<json":
            body_props[name] = {"type": oapi_type, "description": desc}
        elif role == ">json":
            response_props[name] = {"type": oapi_type, "description": desc}
        # ``:param`` (path param hint) is already covered by the URL parser;
        # we just drop it from the visible text.
        return ""

    cleaned = _SPHINX_FIELD_RE.sub(_consume, text)
    cleaned = _SPHINX_ANCHOR_RE.sub("", cleaned)
    cleaned = _SPHINX_REF_RE.sub(r"\1", cleaned)
    cleaned = _SPHINX_INLINE_ROLE_RE.sub(r"\1", cleaned)
    # Collapse 3+ consecutive blank lines (left behind by the substitutions)
    # into the standard paragraph separator.
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()

    body_schema: Dict[str, Any] = {}
    if body_props:
        body_schema = {
            "in": "body",
            "name": "body",
            "required": True,
            "schema": {"type": "object", "properties": body_props},
        }

    extras: Dict[str, Any] = {}
    if response_props:
        extras["__response_schema__"] = {"type": "object", "properties": response_props}

    return cleaned, query_params + ([body_schema] if body_schema else []), extras


def _split_docstring(doc: Optional[str]) -> Tuple[str, str, List[Dict[str, Any]], Dict[str, Any], Dict[str, Any]]:
    """Pull structured information out of a handler docstring.

    Returns ``(summary, description, sphinx_params, sphinx_extras, override_yaml)``:

    * ``summary`` — first non-empty line.
    * ``description`` — everything after the first paragraph and before any
      ``---`` separator, with Sphinx markup cleaned up.
    * ``sphinx_params`` — query/body parameters parsed from ``:qparam`` /
      ``:<json`` Sphinx fields.
    * ``sphinx_extras`` — extras we auto-extract (currently only the
      ``__response_schema__`` synthesised from ``:>json`` fields).
    * ``override_yaml`` — anything after ``---`` parsed as YAML; used to
      override or augment the auto-generated operation entry.
    """
    if not doc:
        return "", "", [], {}, {}
    cleaned = inspect.cleandoc(doc)
    yaml_overrides: Dict[str, Any] = {}
    if "\n---" in cleaned or cleaned.startswith("---"):
        body, _, yaml_block = cleaned.partition("\n---")
        if not body:
            body, _, yaml_block = "", "", cleaned[3:]
        try:
            parsed = yaml.safe_load(yaml_block) or {}
            if isinstance(parsed, dict):
                yaml_overrides = parsed
        except yaml.YAMLError as exc:
            logger.debug("Could not parse swagger YAML in docstring: %s", exc)
        cleaned = body

    cleaned, sphinx_params, sphinx_extras = _parse_sphinx_fields(cleaned)

    parts = [p.strip() for p in cleaned.split("\n\n", 1)]
    summary = parts[0].split("\n", 1)[0].strip() if parts else ""
    description = parts[1].strip() if len(parts) > 1 else ""
    rest_of_first_para = parts[0].split("\n", 1)[1].strip() if parts and "\n" in parts[0] else ""
    if rest_of_first_para:
        description = (rest_of_first_para + ("\n\n" + description if description else "")).strip()
    return summary, description, sphinx_params, sphinx_extras, yaml_overrides


def _resource_view_handlers(view_func) -> Iterable[Tuple[str, Any]]:
    """Yield ``(http_method, handler_func)`` tuples for a Flask view.

    Works for both Flask-RESTful resources (``view_class.get/post/...``) and
    plain ``@app.route``-style functions.
    """
    view_class = getattr(view_func, "view_class", None)
    if view_class is not None:
        for http_method in ("get", "post", "put", "patch", "delete", "options", "head"):
            handler = getattr(view_class, http_method, None)
            if callable(handler):
                yield http_method, handler
        return
    # Plain function: yield it for every method declared on the rule.
    yield "_function", view_func


def _build_operation(
    *,
    handler: Any,
    method: str,
    path_parameters: List[Dict[str, Any]],
    tag_name: str,
    operation_id: str,
) -> Dict[str, Any]:
    """Generate one OpenAPI operation object from a handler callable."""
    summary, description, sphinx_params, sphinx_extras, overrides = _split_docstring(handler.__doc__)
    operation: Dict[str, Any] = {
        "operationId": operation_id,
        "tags": [tag_name],
        "summary": summary or _humanize(operation_id),
        "responses": {
            "200": {"description": "Successful response."},
            "401": {"description": "Authentication required or invalid API key."},
        },
    }
    if description:
        operation["description"] = description
    parameters: List[Dict[str, Any]] = list(path_parameters) + list(sphinx_params)
    if parameters:
        operation["parameters"] = [dict(p) for p in parameters]
    if path_parameters:
        operation["responses"].setdefault(
            "404", {"description": "Object not found or you do not have access to it."}
        )
    if method in ("post", "put", "patch", "delete"):
        operation["responses"].setdefault(
            "400", {"description": "Invalid request payload or parameters."}
        )
    # Sphinx ``:>json`` fields aggregated into a 200 response schema.
    response_schema = sphinx_extras.get("__response_schema__")
    if response_schema:
        operation["responses"]["200"] = {
            "description": "Successful response.",
            "schema": response_schema,
        }

    # Apply user-supplied YAML overrides from the docstring.
    if overrides:
        if "parameters" in overrides:
            # Replace any existing parameter that shares the same
            # ``(name, in)`` pair so overrides win cleanly. Order: original
            # path params first, then anything new from the override.
            existing = OrderedDict(
                ((p["name"], p.get("in", "path")), p) for p in operation.get("parameters", [])
            )
            for extra in overrides["parameters"]:
                # Some hand-written YAML blocks use OpenAPI 3.0 style
                # ``schema: {type: integer}`` for path/query params even
                # though we emit OpenAPI 2.0 (where ``type`` is top-level).
                # Normalize so the parameter still renders properly.
                if "schema" in extra and "type" not in extra:
                    schema = extra.get("schema") or {}
                    if isinstance(schema, dict) and "type" in schema:
                        extra = {**extra, "type": schema["type"]}
                key = (extra.get("name"), extra.get("in", "path"))
                existing[key] = extra
            operation["parameters"] = list(existing.values())
            overrides = {k: v for k, v in overrides.items() if k != "parameters"}
        if "responses" in overrides:
            merged_responses = dict(operation["responses"])
            # YAML parses ``200:`` as an int; OpenAPI requires string keys
            # (and json.dumps with sort_keys breaks on mixed key types).
            for status, payload in overrides["responses"].items():
                merged_responses[str(status)] = payload
            operation["responses"] = merged_responses
            overrides = {k: v for k, v in overrides.items() if k != "responses"}
        operation.update(overrides)

    return operation


def _humanize(operation_id: str) -> str:
    """Best-effort fallback summary when no docstring is available."""
    return operation_id.replace("_", " ").strip().capitalize()


def _build_spec(app) -> Dict[str, Any]:
    """Walk ``app.url_map`` and assemble a complete OpenAPI 2.0 spec."""
    paths: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
    used_tags: Dict[str, str] = {}
    used_operation_ids: Dict[str, int] = {}

    rules = sorted(app.url_map.iter_rules(), key=lambda r: r.rule)
    for rule in rules:
        # Ignore everything that isn't part of the JSON API — static assets,
        # the React shell, OAuth callbacks, the Scalar UI itself, etc.
        if not rule.rule.startswith("/api/"):
            continue
        if rule.rule.startswith("/api/docs"):
            continue
        if rule.rule.startswith("/api/spec"):
            continue
        if rule.rule.startswith("/api/_flasgger"):
            continue

        view_func = app.view_functions.get(rule.endpoint)
        if view_func is None:
            continue

        openapi_path, path_parameters = _extract_path_params(rule.rule)
        tag_name, tag_description = _classify(rule.rule)
        used_tags.setdefault(tag_name, tag_description)

        path_entry = paths.setdefault(openapi_path, {})

        for http_method, handler in _resource_view_handlers(view_func):
            if http_method == "_function":
                # Plain @routes.route function: emit one operation per HTTP
                # method declared on the rule, skipping the noisy defaults.
                methods = (rule.methods or set()) - {"OPTIONS", "HEAD"}
                for verb in sorted(methods):
                    op_method = verb.lower()
                    op_id = _make_operation_id(used_operation_ids, rule.endpoint, op_method)
                    path_entry[op_method] = _build_operation(
                        handler=handler,
                        method=op_method,
                        path_parameters=path_parameters,
                        tag_name=tag_name,
                        operation_id=op_id,
                    )
            else:
                # Flask-RESTful resource: only include verbs the resource
                # actually implements (``getattr`` returned a callable).
                if rule.methods and http_method.upper() not in rule.methods:
                    continue
                op_id = _make_operation_id(used_operation_ids, rule.endpoint, http_method)
                path_entry[http_method] = _build_operation(
                    handler=handler,
                    method=http_method,
                    path_parameters=path_parameters,
                    tag_name=tag_name,
                    operation_id=op_id,
                )

    spec: Dict[str, Any] = {
        "swagger": "2.0",
        "info": {
            "title": "Rewatch API",
            "description": (
                "The Rewatch REST API exposes everything the web UI uses: queries, "
                "dashboards, alerts, ML models, predictions, indexers and more.\n\n"
                "**Authentication.** Pass your personal API key as the ``api_key`` "
                "query parameter, or via the ``Authorization: Key <key>`` header. "
                "Per-object API keys (e.g. a query's API key) are also accepted on "
                "their respective endpoints.\n\n"
                "This document is generated on demand from Flask's URL map, so it "
                "always reflects the routes registered on the live server."
            ),
            "termsOfService": "https://naoufel.io/help/",
            "contact": {"email": "maintainers@naoufel.io"},
            "version": "1.0.0",
        },
        "schemes": ["http", "https"],
        "consumes": ["application/json"],
        "produces": ["application/json"],
        "securityDefinitions": {
            "ApiKeyAuth": {"type": "apiKey", "name": "api_key", "in": "query"},
            "ApiKeyHeader": {"type": "apiKey", "name": "Authorization", "in": "header"},
        },
        "security": [{"ApiKeyAuth": []}, {"ApiKeyHeader": []}],
        # Order tags by ``_TAG_TABLE``.
        "tags": [
            {"name": name, "description": desc}
            for _, name, desc in _TAG_TABLE
            if name in used_tags
        ],
        "paths": paths,
    }
    return spec


def _make_operation_id(used: Dict[str, int], endpoint: str, http_method: str) -> str:
    base = f"{http_method}_{endpoint.replace('.', '_')}"
    candidate = base
    n = used.get(base, 0)
    if n:
        candidate = f"{base}_{n + 1}"
    used[base] = n + 1
    return candidate


# ---------------------------------------------------------------------------
# Docs UI (Scalar)
# ---------------------------------------------------------------------------

# CSP-safe HTML shell for Scalar. Notes on the design:
#   * The ``<script id="api-reference">`` mounting element is declared with
#     ``type="application/json"`` so the browser doesn't treat it as inline
#     code — Scalar reads its attributes (``data-url``, ``data-configuration``)
#     to discover the spec.
#   * The Scalar runtime is loaded from the same origin, so a strict
#     ``script-src 'self'`` CSP is enough — no relaxation needed.
#   * Scalar attempts to fetch its own webfonts from ``fonts.scalar.com``;
#     CSP blocks them and Scalar gracefully falls back to the system font
#     stack.
_SCALAR_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Rewatch API</title>
  <link rel="icon" type="image/png" href="/static/images/favicon-32x32.png">
</head>
<body>
  <script
    id="api-reference"
    type="application/json"
    data-url="/api/spec"
    data-configuration='{"theme":"default","layout":"modern","defaultOpenAllTags":false,"hideClientButton":false,"hideDownloadButton":false,"hideSearch":false,"metaData":{"title":"Rewatch API"}}'></script>
  <script src="/api/docs/scalar.standalone.js"></script>
</body>
</html>
"""


def _build_blueprint() -> Blueprint:
    bp = Blueprint("api_docs", __name__)

    @bp.route("/api/spec", methods=["GET"])
    def api_spec():
        return jsonify(_build_spec(current_app))

    @bp.route("/api/docs/scalar.standalone.js")
    def scalar_bundle():
        # Cached for a day so the 3.6 MB bundle isn't refetched on every
        # docs visit.
        return send_from_directory(
            _API_DOCS_STATIC_DIR,
            "scalar.standalone.js",
            max_age=86400,
            mimetype="application/javascript",
        )

    @bp.route("/api/docs/", methods=["GET"])
    @bp.route("/api/docs", methods=["GET"])
    def docs_ui():
        return render_template_string(_SCALAR_TEMPLATE)

    return bp


def setup_swagger(app):
    """Mount the OpenAPI spec endpoint and the Scalar UI on ``app``."""
    app.register_blueprint(_build_blueprint())
