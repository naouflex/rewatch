import logging

import requests

from redash.destinations import BaseDestination, register

DEFAULT_BODY_TEMPLATE = "Alert: {{ALERT_NAME}} is {{ALERT_STATUS}}.\n{{{ALERT_URL}}}"


class Telegram(BaseDestination):
    @classmethod
    def name(cls):
        return "Telegram"

    @classmethod
    def type(cls):
        return "telegram"

    @classmethod
    def configuration_schema(cls):
        return {
            "type": "object",
            "properties": {
                "bot_token": {"type": "string", "title": "Bot Token"},
                "chat_id": {"type": "string", "title": "Chat ID"},
            },
            "secret": ["bot_token"],
            "required": ["bot_token", "chat_id"],
        }

    @classmethod
    def icon(cls):
        return "fa-telegram"

    def notify(self, alert, query, user, new_state, app, host, metadata, options):
        row = (metadata or {}).get("row")
        row_index = (metadata or {}).get("row_index")

        try:
            text = alert.render_custom_body(row=row, row_index=row_index)
            if not text:
                text = alert.render_template(DEFAULT_BODY_TEMPLATE, row=row, row_index=row_index)

            response = requests.post(
                "https://api.telegram.org/bot{token}/sendMessage".format(token=options["bot_token"]),
                data={"chat_id": options["chat_id"], "text": text},
                timeout=5.0,
            )

            if response.status_code != 200:
                logging.error(
                    "Telegram send ERROR. status_code => %s body => %s",
                    response.status_code,
                    response.text,
                )
            else:
                logging.info("Telegram send OK (alert=%s state=%s).", alert.id, new_state)

        except Exception:
            logging.exception("Telegram send ERROR.")


register(Telegram)
