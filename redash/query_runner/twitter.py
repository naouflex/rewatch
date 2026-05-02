"""Twitter query runner.

Reads from the Twitter / X API via tweepy. Queries are written as YAML, e.g.

    user_id: "44196397"      # numeric Twitter user id, or
    username: "elonmusk"     # screen-name (will be resolved to id)
    max_results: 25

Returns the most recent tweets in that user's timeline. Ported from
inverse-watch with modernised v2 API support (the v1 ``user_timeline``
endpoint was decommissioned for the free tier; we keep it as an opt-in
fallback).
"""
import logging

import yaml

from redash.query_runner import (
    TYPE_INTEGER,
    TYPE_STRING,
    BaseQueryRunner,
    register,
)
from redash.utils import json_dumps

logger = logging.getLogger(__name__)

try:
    import tweepy

    enabled = True
except ImportError:
    tweepy = None
    enabled = False


class Twitter(BaseQueryRunner):
    should_annotate_query = False

    @classmethod
    def name(cls):
        return "Twitter"

    @classmethod
    def type(cls):
        return "twitter"

    @classmethod
    def enabled(cls):
        return enabled

    @classmethod
    def configuration_schema(cls):
        return {
            "type": "object",
            "properties": {
                "bearer_token": {
                    "type": "string",
                    "title": "Bearer Token (v2 API)",
                    "description": "Required for the v2 endpoints. App-only auth from the Twitter developer portal.",
                },
                "consumer_key": {"type": "string", "title": "API Key (v1 / OAuth1)"},
                "consumer_secret": {"type": "string", "title": "API Key Secret (v1 / OAuth1)"},
                "access_token": {"type": "string", "title": "Access Token (v1 / OAuth1)"},
                "access_token_secret": {"type": "string", "title": "Access Token Secret (v1 / OAuth1)"},
                "use_v1": {
                    "type": "boolean",
                    "title": "Use legacy v1.1 API",
                    "default": False,
                    "description": "Tick if your account still has access to the v1.1 user_timeline endpoint.",
                },
            },
            "secret": [
                "bearer_token",
                "consumer_secret",
                "access_token_secret",
            ],
            "order": [
                "bearer_token",
                "consumer_key",
                "consumer_secret",
                "access_token",
                "access_token_secret",
                "use_v1",
            ],
        }

    def __init__(self, configuration):
        super(Twitter, self).__init__(configuration)
        self.syntax = "yaml"

    def test_connection(self):
        if not enabled:
            raise Exception("tweepy is not installed.")
        client = self._get_client()
        # Cheap call: resolve our own credentials/user.
        if isinstance(client, tweepy.Client):
            client.get_me(user_auth=False)
        else:
            client.verify_credentials()

    def run_query(self, query, user):
        if not enabled:
            return None, "tweepy is not installed."

        try:
            params = yaml.safe_load(query) or {}
        except yaml.YAMLError as e:
            return None, "Invalid YAML: {0}".format(e)
        if not isinstance(params, dict):
            return None, "Query must be a YAML object."

        user_id = params.get("user_id")
        username = params.get("username")
        max_results = int(params.get("max_results", 10))

        if not user_id and not username:
            return None, "Either 'user_id' or 'username' is required."

        try:
            if self._use_v1():
                rows = self._fetch_tweets_v1(user_id or username, max_results)
            else:
                rows = self._fetch_tweets_v2(user_id, username, max_results)
        except Exception as e:
            logger.exception("Twitter query failed")
            return None, str(e)

        return json_dumps({"columns": self._columns(), "rows": rows}), None

    # ------------------------------------------------------------- internals

    def _use_v1(self):
        return bool(self.configuration.get("use_v1"))

    def _get_client(self):
        if self._use_v1():
            auth = tweepy.OAuth1UserHandler(
                self.configuration["consumer_key"],
                self.configuration["consumer_secret"],
                self.configuration["access_token"],
                self.configuration["access_token_secret"],
            )
            return tweepy.API(auth, wait_on_rate_limit=True)

        bearer_token = self.configuration.get("bearer_token")
        if not bearer_token:
            raise Exception("bearer_token is required for the v2 API (or enable 'Use legacy v1.1 API').")

        return tweepy.Client(
            bearer_token=bearer_token,
            consumer_key=self.configuration.get("consumer_key"),
            consumer_secret=self.configuration.get("consumer_secret"),
            access_token=self.configuration.get("access_token"),
            access_token_secret=self.configuration.get("access_token_secret"),
            wait_on_rate_limit=True,
        )

    def _fetch_tweets_v1(self, user_ref, max_results):
        api = self._get_client()
        kwargs = {"count": max_results, "tweet_mode": "extended"}
        if str(user_ref).isdigit():
            kwargs["user_id"] = user_ref
        else:
            kwargs["screen_name"] = user_ref
        tweets = api.user_timeline(**kwargs)
        return [
            {
                "id": tweet.id_str,
                "text": getattr(tweet, "full_text", getattr(tweet, "text", "")),
                "created_at": str(tweet.created_at),
                "lang": getattr(tweet, "lang", None),
                "retweet_count": getattr(tweet, "retweet_count", None),
                "favorite_count": getattr(tweet, "favorite_count", None),
            }
            for tweet in tweets
        ]

    def _fetch_tweets_v2(self, user_id, username, max_results):
        client = self._get_client()
        if not user_id:
            user_response = client.get_user(username=username, user_auth=False)
            if not user_response or not user_response.data:
                raise Exception("Twitter user '{0}' not found.".format(username))
            user_id = user_response.data.id

        # Twitter caps `max_results` at 100 per request for this endpoint.
        max_results = max(5, min(int(max_results), 100))
        response = client.get_users_tweets(
            id=user_id,
            max_results=max_results,
            tweet_fields=["created_at", "lang", "public_metrics"],
            user_auth=False,
        )

        rows = []
        for tweet in response.data or []:
            metrics = getattr(tweet, "public_metrics", None) or {}
            rows.append(
                {
                    "id": str(tweet.id),
                    "text": tweet.text,
                    "created_at": str(getattr(tweet, "created_at", "")),
                    "lang": getattr(tweet, "lang", None),
                    "retweet_count": metrics.get("retweet_count"),
                    "favorite_count": metrics.get("like_count"),
                }
            )
        return rows

    @staticmethod
    def _columns():
        return [
            {"name": "id", "type": TYPE_STRING, "friendly_name": "ID"},
            {"name": "text", "type": TYPE_STRING, "friendly_name": "Text"},
            {"name": "created_at", "type": TYPE_STRING, "friendly_name": "Created At"},
            {"name": "lang", "type": TYPE_STRING, "friendly_name": "Language"},
            {"name": "retweet_count", "type": TYPE_INTEGER, "friendly_name": "Retweets"},
            {"name": "favorite_count", "type": TYPE_INTEGER, "friendly_name": "Likes"},
        ]


register(Twitter)
