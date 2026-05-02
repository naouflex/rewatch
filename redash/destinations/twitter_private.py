import logging

from redash.destinations import BaseDestination, register

try:
    import tweepy
except ImportError:
    tweepy = None

DEFAULT_BODY_TEMPLATE = "Alert: {{ALERT_NAME}} is {{ALERT_STATUS}}."

# Twitter DMs cap at 10000 chars but tweepy can fragment longer; cut defensively for safety.
DM_MAX_LENGTH = 10000


class TwitterPrivate(BaseDestination):
    """Send a Twitter Direct Message to the authenticated account."""

    @classmethod
    def name(cls):
        return "Twitter Private"

    @classmethod
    def type(cls):
        return "twitter_private"

    @classmethod
    def configuration_schema(cls):
        return {
            "type": "object",
            "properties": {
                "account_handle": {"type": "string", "title": "Account Handle"},
                "consumer_key": {"type": "string", "title": "Consumer Key"},
                "consumer_secret": {"type": "string", "title": "Consumer Secret"},
                "access_token": {"type": "string", "title": "Access Token"},
                "access_token_secret": {"type": "string", "title": "Access Token Secret"},
                "bearer_token": {"type": "string", "title": "Bearer Token"},
                "recipient_id": {
                    "type": "string",
                    "title": "Recipient ID",
                    "info": "Numeric Twitter user ID. Leave empty to send to the authenticated account itself.",
                },
            },
            "secret": ["consumer_secret", "access_token_secret", "bearer_token"],
            "required": [
                "account_handle",
                "consumer_key",
                "consumer_secret",
                "access_token",
                "access_token_secret",
                "bearer_token",
            ],
        }

    @classmethod
    def icon(cls):
        return "fa-twitter"

    @classmethod
    def enabled(cls):
        return tweepy is not None

    def notify(self, alert, query, user, new_state, app, host, metadata, options):
        row = (metadata or {}).get("row")
        row_index = (metadata or {}).get("row_index")

        try:
            text = alert.render_custom_body(row=row, row_index=row_index)
            if not text:
                text = alert.render_template(DEFAULT_BODY_TEMPLATE, row=row, row_index=row_index)
            text = text[:DM_MAX_LENGTH]

            client = tweepy.Client(
                bearer_token=options["bearer_token"],
                consumer_key=options["consumer_key"],
                consumer_secret=options["consumer_secret"],
                access_token=options["access_token"],
                access_token_secret=options["access_token_secret"],
                wait_on_rate_limit=True,
            )

            recipient_id = options.get("recipient_id")
            if not recipient_id:
                me = client.get_me(user_auth=True)
                recipient_id = me.data.id

            client.create_direct_message(
                participant_id=recipient_id,
                text=text,
                user_auth=True,
            )
            logging.info("TwitterPrivate DM send OK (alert=%s recipient=%s).", alert.id, recipient_id)

        except Exception:
            logging.exception("TwitterPrivate DM send ERROR.")


register(TwitterPrivate)
