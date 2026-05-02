import json
import logging

import requests

from redash.destinations import BaseDestination, register
from redash.models import Alert
from redash.utils import json_dumps

# Brand colors (decimal as required by Discord embeds).
DISCORD_COLOR = {
    Alert.OK_STATE: int("0x2ecc71", 16),
    Alert.TRIGGERED_STATE: int("0xe74c3c", 16),
    Alert.UNKNOWN_STATE: int("0xf1c40f", 16),
}

DEFAULT_EMBED_TITLE = "Alert: {{ALERT_NAME}} is {{ALERT_STATUS}}"


class DiscordWebhook(BaseDestination):
    """Send alerts to a Discord channel through an incoming webhook.

    Two modes:

    - Default: a structured embed with status-colored title, condition summary, and direct
      links to the alert and query.
    - Custom: when ``alert.options['custom_body']`` is set, it is interpreted as a Mustache
      template that must render to a valid Discord webhook JSON payload (``content``,
      ``embeds``, ...). All standard alert/query Mustache variables are available, plus
      ``QUERY_RESULT_ROW`` / ``QUERY_RESULT_ROW_INDEX`` when the alert sends a notification
      per row.
    """

    @classmethod
    def name(cls):
        return "Discord Webhook"

    @classmethod
    def type(cls):
        return "discord_webhook"

    @classmethod
    def configuration_schema(cls):
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "title": "Discord Webhook URL"},
                "username": {"type": "string", "title": "Override username"},
                "avatar_url": {"type": "string", "title": "Override avatar URL"},
            },
            "secret": ["url"],
            "required": ["url"],
        }

    @classmethod
    def icon(cls):
        return "fa-bolt"

    def _build_default_payload(self, alert, query, host, new_state, row, row_index):
        title = alert.render_template(DEFAULT_EMBED_TITLE, row=row, row_index=row_index)
        description = alert.render_custom_body(row=row, row_index=row_index)

        fields = [
            {"name": "Query", "value": "{host}/queries/{qid}".format(host=host, qid=query.id), "inline": True},
            {"name": "Alert", "value": "{host}/alerts/{aid}".format(host=host, aid=alert.id), "inline": True},
        ]
        try:
            fields.append(
                {
                    "name": "Condition",
                    "value": "`{column} {op} {value}`".format(
                        column=alert.options.get("column", ""),
                        op=alert.options.get("op", ""),
                        value=alert.options.get("value", ""),
                    ),
                    "inline": False,
                }
            )
        except Exception:
            logging.debug("Discord webhook: couldn't build condition field", exc_info=True)

        if row is not None:
            preview = ", ".join("{k}={v}".format(k=k, v=v) for k, v in list(row.items())[:10])
            fields.append({"name": "Row #{idx}".format(idx=row_index), "value": preview or "(empty)", "inline": False})

        embed = {
            "title": title,
            "color": DISCORD_COLOR.get(new_state, DISCORD_COLOR[Alert.UNKNOWN_STATE]),
            "fields": fields,
        }
        if description:
            embed["description"] = description

        return {"embeds": [embed]}

    def notify(self, alert, query, user, new_state, app, host, metadata, options):
        row = (metadata or {}).get("row")
        row_index = (metadata or {}).get("row_index")

        custom_body = alert.options.get("custom_body") or alert.options.get("template")
        if custom_body:
            rendered = alert.render_template(custom_body, row=row, row_index=row_index)
            try:
                payload = json.loads(rendered)
            except (ValueError, TypeError):
                logging.warning("Discord webhook: custom_body did not render to valid JSON, sending as content.")
                payload = {"content": rendered}
        else:
            payload = self._build_default_payload(alert, query, host, new_state, row, row_index)

        if options.get("username"):
            payload["username"] = options["username"]
        if options.get("avatar_url"):
            payload["avatar_url"] = options["avatar_url"]

        headers = {"Content-Type": "application/json"}
        try:
            resp = requests.post(
                options["url"],
                data=json_dumps(payload).encode("utf-8"),
                headers=headers,
                timeout=5.0,
            )
            if resp.status_code not in (200, 204):
                logging.error(
                    "Discord webhook send ERROR. status_code => %s body => %s",
                    resp.status_code,
                    resp.text,
                )
            else:
                logging.info("Discord webhook send OK (alert=%s state=%s).", alert.id, new_state)
        except Exception:
            logging.exception("Discord webhook send ERROR.")


register(DiscordWebhook)
