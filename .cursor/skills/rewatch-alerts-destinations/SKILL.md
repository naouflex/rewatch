---
name: rewatch-alerts-destinations
description: Creates Rewatch alerts, notification destinations (webhooks, Slack, Discord, email), custom Mustache templates, and alert subscriptions via MCP/API. Use when setting up monitoring, thresholds, webhook payloads, or notification routing.
---

# Rewatch Alerts & Destinations

## Quick start

End-to-end flow:

```
run_query(query_id=...) → get_destination_type(type) → create_destination → create_alert(..., destination_ids=[...])
```

Use the **user-rewatch** MCP server. Prefer dedicated tools over `call_api`.

## Core workflow

### 1. Validate query data first

Always confirm the threshold column exists in query results.

```text
run_query(query_id=...)   # read columns + sample rows
```

Pick `column` from the exact `columns` list (case-sensitive, dots allowed). `create_alert` validates automatically unless `validate_column=false`.

### 2. Choose a destination type

```text
list_destination_types
get_destination_type(type="webhook")          # or discord_webhook, slack, email, microsoft_teams_webhook
get_alert_template_guide                      # Mustache variables for custom_subject / custom_body
```

| Type | Config on | Custom template |
|------|-----------|-----------------|
| `webhook` | destination: `url` | alert `custom_subject` / `custom_body` (Mustache) → JSON `title` / `description` |
| `discord_webhook` | destination: `url` | alert `custom_body` = Discord webhook JSON (Mustache) or default embed |
| `slack` | destination: `url` | alert `custom_subject` (message text), `custom_body` (description field) |
| `email` | org SMTP settings | alert `custom_subject` / `custom_body` (HTML Mustache) |
| `microsoft_teams_webhook` | destination: `url`, `message_template` | destination template with `{alert_name}`, `{alert_url}` — **not** Mustache |

### 3. Create the destination

```text
create_destination(name, type, options)
list_destinations                    # reuse existing if appropriate
get_destination(destination_id)      # verify config
```

Webhook example:

```json
{
  "name": "Ops webhook",
  "type": "webhook",
  "options": { "url": "https://example.com/hooks/rewatch" }
}
```

Discord custom JSON example (set on the **alert**, not the destination):

```json
{
  "custom_body": "{\"content\": \"{{ALERT_NAME}} triggered\", \"embeds\": [{\"title\": \"Value: {{QUERY_RESULT_VALUE}}\"}]}"
}
```

### 4. Create the alert

```text
create_alert(
  name, query_id, column, op, value,
  selector="first",                  # or min, max
  custom_subject="...",
  custom_body="...",
  send_for_each_row=false,
  destination_ids=[1, 2]
)
```

Operators: `>`, `>=`, `<`, `<=`, `==`, `!=`.

`rearm` (seconds) prevents repeat notifications. `muted: true` in options suppresses notifications.

### 5. Subscribe or test

```text
subscribe_alert(alert_id, destination_id)     # add another destination later
list_alert_subscriptions(alert_id)
evaluate_alert(alert_id)                      # manual test with latest query results
```

Share alert URL: `/alerts/{id}`.

## Mustache template variables

Call `get_alert_template_guide` for the full list. Common variables:

| Variable | Meaning |
|----------|---------|
| `{{ALERT_NAME}}` | Alert name |
| `{{ALERT_STATUS}}` | OK, TRIGGERED, UNKNOWN |
| `{{QUERY_RESULT_VALUE}}` | Value in the alert column |
| `{{QUERY_RESULT_ROW}}` | Current row object (with `send_for_each_row`) |
| `{{QUERY_RESULT_ROW_INDEX}}` | Row index in per-row mode |
| `{{{QUERY_URL}}}` | Unescaped query link (triple braces) |
| `{{column_name}}` | Shortcut to current row's column value |

Cross-row access: `{{ethereum.0}}` for row 0's `ethereum` column.

## Per-row notifications

Set `send_for_each_row: true` when the query returns multiple rows and each should trigger its own notification. Use column shortcuts in templates:

```
{{timestamp}} — {{symbol}} price {{price}} exceeded {{ALERT_THRESHOLD}}
```

## Pitfalls

- **Wrong column name**: always read `run_query` columns first; placeholders like `value` fail unless literal.
- **Teams vs Mustache**: `microsoft_teams_webhook` uses `{alert_name}` in destination `message_template`, not `{{ALERT_NAME}}`.
- **Discord JSON**: `custom_body` must render to valid JSON after Mustache substitution; otherwise sent as plain `content`.
- **No subscribers**: creating an alert does not notify anyone unless `destination_ids` is set or you call `subscribe_alert`.
- **Stale query data**: alerts evaluate against the query's latest cached result — refresh the query schedule or run it before `evaluate_alert`.
- **Empty query**: selector `min`/`max` on empty results yields UNKNOWN state.

## Checklist

```text
Task Progress:
- [ ] run_query — confirm columns + pick threshold column
- [ ] get_destination_type — read config schema + template examples
- [ ] create_destination (or reuse from list_destinations)
- [ ] get_alert_template_guide — if using custom_subject/custom_body
- [ ] create_alert with destination_ids
- [ ] evaluate_alert — optional smoke test
- [ ] Share /alerts/{id} link
```

## Additional resources

- Visualization/dashboard workflow: `rewatch-visualizations-dashboards` skill
- User docs topic: `get_docs_topic(topic_id="alert_setup")`
