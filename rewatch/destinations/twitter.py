import logging

from rewatch.destinations import BaseDestination, register

try:
    import tweepy
except ImportError:
    tweepy = None

DEFAULT_BODY_TEMPLATE = "Alert: {{ALERT_NAME}} is {{ALERT_STATUS}}."

# Twitter rejects tweets > 280 chars; trim defensively to avoid losing the whole alert.
TWEET_MAX_LENGTH = 280


class Twitter(BaseDestination):
    @classmethod
    def name(cls):
        return "Twitter"

    @classmethod
    def type(cls):
        return "twitter"

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
            text = text[:TWEET_MAX_LENGTH]

            client = tweepy.Client(
                consumer_key=options["consumer_key"],
                consumer_secret=options["consumer_secret"],
                access_token=options["access_token"],
                access_token_secret=options["access_token_secret"],
                bearer_token=options["bearer_token"],
            )

            tweet = client.create_tweet(text=text)
            tweet_id = getattr(tweet, "data", {}) and tweet.data.get("id")
            logging.info("Twitter send OK (alert=%s tweet=%s).", alert.id, tweet_id)

        except Exception:
            logging.exception("Twitter send ERROR.")


register(Twitter)
