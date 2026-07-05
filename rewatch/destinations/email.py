import logging

from flask_mail import Message

from rewatch import mail, settings
from rewatch.destinations import BaseDestination, register


class Email(BaseDestination):
    @classmethod
    def configuration_schema(cls):
        return {
            "type": "object",
            "properties": {
                "addresses": {"type": "string"},
                "subject_template": {
                    "type": "string",
                    "default": settings.ALERTS_DEFAULT_MAIL_SUBJECT_TEMPLATE,
                    "title": "Subject Template",
                },
            },
            "required": ["addresses"],
            "extra_options": ["subject_template"],
        }

    @classmethod
    def icon(cls):
        return "fa-envelope"

    def notify(self, alert, query, user, new_state, app, host, metadata, options):
        recipients = [email for email in options.get("addresses", "").split(",") if email]

        if not recipients:
            logging.warning("No emails given. Skipping send.")

        row = (metadata or {}).get("row")
        row_index = (metadata or {}).get("row_index")

        custom_body = alert.render_custom_body(row=row, row_index=row_index)
        if custom_body:
            html = custom_body
        else:
            with open(settings.REDASH_ALERTS_DEFAULT_MAIL_BODY_TEMPLATE_FILE, "r") as f:
                html = alert.render_template(f.read(), row=row, row_index=row_index)
        logging.debug("Notifying: %s", recipients)

        try:
            state = new_state.upper()
            custom_subject = alert.render_custom_subject(row=row, row_index=row_index)
            if custom_subject:
                subject = custom_subject
            else:
                subject_template = options.get("subject_template", settings.ALERTS_DEFAULT_MAIL_SUBJECT_TEMPLATE)
                subject = subject_template.format(alert_name=alert.name, state=state)

            message = Message(recipients=recipients, subject=subject, html=html)
            mail.send(message)
        except Exception:
            logging.exception("Mail send error.")


register(Email)
