"""Platform catalog: alerts, notification destinations, and webhook templates for the assistant."""

from __future__ import annotations

from typing import Any, Optional

ALERT_OPERATORS = [">", ">=", "<", "<=", "==", "!="]

ALERT_SELECTORS = ["first", "min", "max"]

MUSTACHE_VARIABLES: list[dict[str, str]] = [
    {"name": "ALERT_NAME", "description": "Alert display name"},
    {"name": "ALERT_URL", "description": "Link to the alert in Rewatch (use {{{ALERT_URL}}} for unescaped URL)"},
    {"name": "ALERT_STATUS", "description": "Current state: OK, TRIGGERED, or UNKNOWN"},
    {"name": "ALERT_SELECTOR", "description": "Value selector: first, min, or max"},
    {"name": "ALERT_CONDITION", "description": "Comparison operator (>, ==, etc.)"},
    {"name": "ALERT_THRESHOLD", "description": "Threshold configured on the alert"},
    {"name": "QUERY_NAME", "description": "Linked query name"},
    {"name": "QUERY_URL", "description": "Link to the query (use {{{QUERY_URL}}} for unescaped URL)"},
    {"name": "QUERY_RESULT_VALUE", "description": "Value in the alert column (current row when send_for_each_row)"},
    {"name": "QUERY_RESULT_ROW", "description": "Current row object when send_for_each_row is enabled"},
    {"name": "QUERY_RESULT_ROW_INDEX", "description": "0-based row index in per-row notifications"},
    {"name": "QUERY_RESULT_ROWS", "description": "All result rows (JSON array)"},
    {"name": "QUERY_RESULT_COLS", "description": "Column metadata from the query result"},
    {"name": "QUERY_RESULT_TABLE", "description": "2D array for Mustache table sections"},
    {"name": "QUERY_RESULT_BY_COLUMN", "description": "Cross-row access namespace (e.g. {{QUERY_RESULT_BY_COLUMN.ethereum.0}})"},
    {"name": "<column_name>", "description": "Shortcut to current row value (per-row) or indexed dict ({{col.0}})"},
]

DESTINATION_TYPE_NOTES: dict[str, dict[str, Any]] = {
    "webhook": {
        "name": "Webhook",
        "summary": "POST a JSON payload to any HTTP URL. Supports optional HTTP basic auth.",
        "required_options": ["url"],
        "optional_options": ["username", "password"],
        "template_location": "alert",
        "template_notes": [
            "Set alert.options.custom_subject and alert.options.custom_body (Mustache templates).",
            "Rendered values appear in the JSON payload as alert.title and alert.description.",
            "The webhook body also includes event, alert metadata, url_base, and metadata.",
        ],
        "example_destination_options": {
            "url": "https://example.com/hooks/rewatch",
        },
        "example_alert_templates": {
            "custom_subject": "{{ALERT_NAME}} is {{ALERT_STATUS}}",
            "custom_body": "Value {{QUERY_RESULT_VALUE}} crossed threshold {{ALERT_THRESHOLD}}. See {{{QUERY_URL}}}",
        },
    },
    "discord_webhook": {
        "name": "Discord Webhook",
        "summary": "Discord incoming webhook. Default embed, or full custom JSON payload via alert template.",
        "required_options": ["url"],
        "optional_options": ["username", "avatar_url"],
        "template_location": "alert",
        "template_notes": [
            "Default: structured embed with status color, condition, and links.",
            "Custom: set alert.options.custom_body (or template) to a Mustache template that renders to valid Discord webhook JSON.",
            "If custom_body does not render to JSON, it is sent as plain content.",
            "Use send_for_each_row + {{QUERY_RESULT_ROW}} / column shortcuts for per-row Discord messages.",
        ],
        "example_destination_options": {
            "url": "https://discord.com/api/webhooks/...",
        },
        "example_alert_templates": {
            "custom_body": (
                '{"content": "{{ALERT_NAME}} triggered", "embeds": [{"title": "Value: {{QUERY_RESULT_VALUE}}", '
                '"description": "Threshold: {{ALERT_THRESHOLD}}", "color": 15158332}]}'
            ),
        },
    },
    "slack": {
        "name": "Slack",
        "summary": "Slack incoming webhook with attachment fields.",
        "required_options": ["url"],
        "template_location": "alert",
        "template_notes": [
            "custom_subject becomes the attachment text when triggered.",
            "custom_body is added as a Description field.",
        ],
        "example_alert_templates": {
            "custom_subject": ":rotating_light: {{ALERT_NAME}} — value is {{QUERY_RESULT_VALUE}}",
            "custom_body": "Condition: {{ALERT_CONDITION}} {{ALERT_THRESHOLD}}. Query: {{{QUERY_URL}}}",
        },
    },
    "microsoft_teams_webhook": {
        "name": "Microsoft Teams Webhook",
        "summary": "Teams MessageCard via incoming webhook.",
        "required_options": ["url"],
        "optional_options": ["message_template"],
        "template_location": "destination",
        "template_notes": [
            "Destination options.message_template is a JSON string with Python-style placeholders: "
            "{alert_name}, {alert_url}, {query_text}, {query_url}.",
            "NOT Mustache — use alert custom_body only for destinations that document Mustache support.",
            "Default template is used when message_template is omitted.",
        ],
        "example_destination_options": {
            "url": "https://outlook.office.com/webhook/...",
            "message_template": (
                '{"@type":"MessageCard","summary":"{alert_name}","sections":[{"activityTitle":"{alert_name}",'
                '"facts":[{"name":"Query","value":"{query_url}"}],"markdown":true}]}'
            ),
        },
    },
    "email": {
        "name": "Email",
        "summary": "SMTP email to configured recipients (org-level email settings required).",
        "template_location": "alert",
        "template_notes": [
            "custom_subject and custom_body (Mustache) override the default HTML email.",
            "custom_body may contain HTML; QUERY_RESULT_TABLE supports Mustache table sections.",
        ],
        "example_alert_templates": {
            "custom_subject": "[Rewatch] {{ALERT_NAME}} — {{ALERT_STATUS}}",
            "custom_body": "<p>Current value: <b>{{QUERY_RESULT_VALUE}}</b></p><p><a href=\"{{{ALERT_URL}}}\">View alert</a></p>",
        },
    },
    "telegram": {
        "name": "Telegram",
        "summary": "Telegram bot message.",
        "template_location": "alert",
        "template_notes": ["custom_body (Mustache) overrides the default message text."],
    },
    "mattermost": {
        "name": "Mattermost",
        "summary": "Mattermost incoming webhook.",
        "template_location": "alert",
        "template_notes": ["Uses alert custom_subject / custom_body when set."],
    },
    "pagerduty": {
        "name": "PagerDuty",
        "summary": "PagerDuty Events API v2 integration.",
        "required_options": ["integration_key"],
        "template_location": "none",
        "template_notes": ["Uses built-in incident payload; alert templates do not customize the PagerDuty body."],
    },
}


def _match_filter(text: str, query: str) -> bool:
    q = (query or "").strip().lower()
    if not q:
        return True
    return q in text.lower()


def alert_workflow() -> dict[str, Any]:
    return {
        "steps": [
            "run_query(query_id=...) — confirm columns and sample values for the threshold column",
            "list_destination_types or get_destination_type — pick destination type and option schema",
            "create_destination(name, type, options) — or reuse an existing destination from list_destinations",
            "create_alert(..., destination_ids=[...]) — threshold + optional Mustache templates; auto-subscribes destinations",
            "evaluate_alert(alert_id) — optional manual test after query has fresh results",
        ],
        "operators": ALERT_OPERATORS,
        "selectors": {
            "first": "Compare using the first result row (default)",
            "min": "Compare the minimum value of the column across all rows",
            "max": "Compare the maximum value of the column across all rows",
        },
        "send_for_each_row": (
            "When true, notifications fire once per result row (use QUERY_RESULT_ROW and column shortcuts in templates)."
        ),
        "mustache_variables": MUSTACHE_VARIABLES,
        "assistant_note": (
            "Always validate the alert column against run_query columns before create_alert. "
            "Call get_destination_type before custom webhook/Discord templates."
        ),
    }


def list_destination_types_catalog(
    api_types: Optional[list[dict[str, Any]]] = None,
    query: Optional[str] = None,
) -> dict[str, Any]:
    """Merge live API destination types with static catalog notes."""
    api_types = api_types or []
    api_by_type = {t.get("type"): t for t in api_types if t.get("type")}
    all_types = sorted(set(api_by_type) | set(DESTINATION_TYPE_NOTES))

    items: list[dict[str, Any]] = []
    for dest_type in all_types:
        api_entry = api_by_type.get(dest_type, {})
        notes = DESTINATION_TYPE_NOTES.get(dest_type, {})
        haystack = f"{dest_type} {api_entry.get('name', '')} {notes.get('summary', '')}"
        if not _match_filter(haystack, query or ""):
            continue
        items.append(
            {
                "type": dest_type,
                "name": api_entry.get("name") or notes.get("name") or dest_type,
                "summary": notes.get("summary"),
                "configuration_schema": api_entry.get("configuration_schema"),
                "required_options": notes.get("required_options"),
                "template_location": notes.get("template_location"),
            }
        )

    return {
        "destination_types": items,
        "count": len(items),
        "assistant_note": "Call get_destination_type(type) for template examples and webhook JSON samples.",
    }


def get_destination_type(
    dest_type: str,
    api_entry: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Full catalog entry for one destination type."""
    dest_type = (dest_type or "").strip().lower()
    notes = DESTINATION_TYPE_NOTES.get(dest_type)
    if notes is None and not api_entry:
        return {
            "error": f"Unknown destination type {dest_type!r}.",
            "known_types": sorted(DESTINATION_TYPE_NOTES.keys()),
            "hint": "Call list_destination_types to browse types returned by the API.",
        }

    result: dict[str, Any] = {
        "type": dest_type,
        "name": (api_entry or {}).get("name") or (notes or {}).get("name") or dest_type,
        "configuration_schema": (api_entry or {}).get("configuration_schema"),
        "workflow": alert_workflow()["steps"],
    }
    if notes:
        result.update({k: v for k, v in notes.items() if k != "name"})
    if not result.get("summary"):
        result["summary"] = f"Notification destination type `{dest_type}`."
    result["mustache_variables"] = MUSTACHE_VARIABLES
    return result


def validate_alert_column(column: str, columns: list[str]) -> dict[str, Any]:
    """Check that an alert threshold column exists in query results."""
    column = (column or "").strip()
    if not columns:
        return {
            "valid": False,
            "message": "Query returned no columns — run the query and ensure it produces results.",
            "available_columns": [],
        }
    if column in columns:
        return {"valid": True, "column": column, "available_columns": columns}
    lower_map = {c.lower(): c for c in columns}
    if column.lower() in lower_map:
        corrected = lower_map[column.lower()]
        return {
            "valid": True,
            "column": corrected,
            "corrected_from": column,
            "available_columns": columns,
            "note": f"Column name corrected to exact match: {corrected!r}",
        }
    return {
        "valid": False,
        "message": f"Column {column!r} not found in query results.",
        "available_columns": columns,
        "hint": "Pick a column from available_columns (case-sensitive, dots allowed).",
    }


def validate_alert_operator(op: str) -> str:
    op = (op or "").strip()
    if op not in ALERT_OPERATORS:
        raise ValueError(f"Invalid alert operator {op!r}. Use one of: {', '.join(ALERT_OPERATORS)}")
    return op


def validate_alert_selector_value(selector: str) -> str:
    selector = (selector or "first").strip().lower()
    if selector not in ALERT_SELECTORS:
        raise ValueError(f"Invalid alert selector {selector!r}. Use one of: {', '.join(ALERT_SELECTORS)}")
    return selector


def build_alert_options(
    *,
    column: str,
    op: str,
    value: Any,
    selector: str = "first",
    custom_subject: Optional[str] = None,
    custom_body: Optional[str] = None,
    send_for_each_row: bool = False,
    muted: bool = False,
) -> dict[str, Any]:
    """Build alert.options dict for API create/update."""
    op = validate_alert_operator(op)
    selector = validate_alert_selector_value(selector)
    options: dict[str, Any] = {
        "column": column,
        "op": op,
        "value": value,
        "selector": selector,
    }
    if custom_subject is not None:
        options["custom_subject"] = custom_subject
    if custom_body is not None:
        options["custom_body"] = custom_body
    if send_for_each_row:
        options["send_for_each_row"] = True
    if muted:
        options["muted"] = True
    return options
