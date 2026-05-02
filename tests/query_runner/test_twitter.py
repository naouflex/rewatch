"""Unit tests for the Twitter query runner.

Tweepy's network calls are mocked so the tests don't need API credentials.
If ``tweepy`` isn't installed in the environment we still verify the
module's metadata (it's `enabled()` flag is then False).
"""
import json
from unittest import TestCase
from unittest import mock

from redash.query_runner.twitter import Twitter, enabled as twitter_enabled


CONFIG_V2 = {"bearer_token": "test-bearer"}
CONFIG_V1 = {
    "consumer_key": "ck",
    "consumer_secret": "cs",
    "access_token": "at",
    "access_token_secret": "ats",
    "use_v1": True,
}


class TestTwitterMetadata(TestCase):
    def test_type_and_name(self):
        self.assertEqual(Twitter.type(), "twitter")
        self.assertEqual(Twitter.name(), "Twitter")

    def test_required_secrets(self):
        schema = Twitter.configuration_schema()
        self.assertIn("bearer_token", schema["secret"])
        self.assertIn("consumer_secret", schema["secret"])
        self.assertIn("access_token_secret", schema["secret"])


class TestTwitterRunner(TestCase):
    def setUp(self):
        if not twitter_enabled:
            self.skipTest("tweepy not installed")

    def test_run_query_requires_user(self):
        runner = Twitter(CONFIG_V2)
        data, error = runner.run_query("max_results: 5", None)
        self.assertIsNone(data)
        self.assertIn("user_id", error)

    def test_run_query_rejects_non_dict_yaml(self):
        runner = Twitter(CONFIG_V2)
        data, error = runner.run_query("just a string", None)
        self.assertIsNone(data)
        self.assertIn("YAML object", error)

    def test_v2_resolves_username_then_fetches_tweets(self):
        runner = Twitter(CONFIG_V2)

        user_response = mock.Mock()
        user_response.data = mock.Mock(id=12345)

        tweet1 = mock.Mock(id=1, text="hello", created_at="2026-01-01", lang="en", public_metrics={"retweet_count": 1, "like_count": 2})
        tweet2 = mock.Mock(id=2, text="world", created_at="2026-01-02", lang="en", public_metrics={"retweet_count": 3, "like_count": 4})
        tweets_response = mock.Mock(data=[tweet1, tweet2])

        client = mock.Mock()
        client.get_user.return_value = user_response
        client.get_users_tweets.return_value = tweets_response

        with mock.patch.object(runner, "_get_client", return_value=client):
            data, error = runner.run_query("username: someone\nmax_results: 5", None)

        self.assertIsNone(error)
        client.get_user.assert_called_once()
        client.get_users_tweets.assert_called_once()
        payload = json.loads(data)
        self.assertEqual(len(payload["rows"]), 2)
        self.assertEqual(payload["rows"][0]["id"], "1")
        self.assertEqual(payload["rows"][0]["favorite_count"], 2)

    def test_v2_uses_user_id_directly(self):
        runner = Twitter(CONFIG_V2)
        client = mock.Mock()
        client.get_users_tweets.return_value = mock.Mock(data=[])

        with mock.patch.object(runner, "_get_client", return_value=client):
            data, error = runner.run_query("user_id: '99'\nmax_results: 5", None)

        self.assertIsNone(error)
        client.get_user.assert_not_called()
        client.get_users_tweets.assert_called_once()
        kwargs = client.get_users_tweets.call_args.kwargs
        self.assertEqual(kwargs["id"], "99")
        self.assertEqual(kwargs["max_results"], 5)

    def test_v2_clamps_max_results_to_api_limit(self):
        runner = Twitter(CONFIG_V2)
        client = mock.Mock()
        client.get_users_tweets.return_value = mock.Mock(data=[])

        with mock.patch.object(runner, "_get_client", return_value=client):
            runner.run_query("user_id: '1'\nmax_results: 500", None)

        kwargs = client.get_users_tweets.call_args.kwargs
        self.assertEqual(kwargs["max_results"], 100)

    def test_v1_path_calls_user_timeline(self):
        runner = Twitter(CONFIG_V1)
        api = mock.Mock()
        api.user_timeline.return_value = [
            mock.Mock(id_str="1", full_text="hi", created_at="2026-01-01", lang="en", retweet_count=0, favorite_count=1),
        ]
        with mock.patch.object(runner, "_get_client", return_value=api):
            data, error = runner.run_query("username: someone\nmax_results: 3", None)
        self.assertIsNone(error)
        api.user_timeline.assert_called_once()
        payload = json.loads(data)
        self.assertEqual(payload["rows"][0]["text"], "hi")
