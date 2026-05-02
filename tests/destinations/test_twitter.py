from unittest import mock

import pytest

tweepy = pytest.importorskip("tweepy")

from redash.destinations.twitter import Twitter  # noqa: E402
from redash.destinations.twitter_private import TwitterPrivate  # noqa: E402
from redash.models import Alert  # noqa: E402


def _alert(custom_body=""):
    alert = mock.Mock()
    alert.id = 1
    alert.name = "Test"
    alert.options = {}
    alert.render_custom_body = mock.Mock(return_value=custom_body)
    alert.render_template = mock.Mock(return_value="default tweet")
    return alert


def _twitter_options():
    return {
        "account_handle": "redash",
        "consumer_key": "ck",
        "consumer_secret": "cs",
        "access_token": "at",
        "access_token_secret": "ats",
        "bearer_token": "bt",
    }


def test_twitter_registered_and_enabled():
    from redash.destinations import destinations

    assert destinations.get("twitter") is Twitter
    assert destinations.get("twitter_private") is TwitterPrivate


def test_twitter_notify_creates_tweet():
    options = _twitter_options()
    alert = _alert()

    fake_tweet = mock.Mock(data={"id": 999})
    fake_client = mock.Mock()
    fake_client.create_tweet.return_value = fake_tweet

    with mock.patch("redash.destinations.twitter.tweepy.Client", return_value=fake_client) as mock_client_cls:
        Twitter(options).notify(alert, mock.Mock(), mock.Mock(), Alert.TRIGGERED_STATE, mock.Mock(), "http://h", {}, options)

    mock_client_cls.assert_called_once()
    fake_client.create_tweet.assert_called_once_with(text="default tweet")


def test_twitter_truncates_long_tweets():
    options = _twitter_options()
    long_text = "a" * 500
    alert = _alert(custom_body=long_text)

    fake_client = mock.Mock()
    fake_client.create_tweet.return_value = mock.Mock(data={"id": 1})

    with mock.patch("redash.destinations.twitter.tweepy.Client", return_value=fake_client):
        Twitter(options).notify(alert, mock.Mock(), mock.Mock(), Alert.TRIGGERED_STATE, mock.Mock(), "http://h", {}, options)

    sent = fake_client.create_tweet.call_args.kwargs["text"]
    assert len(sent) == 280


def test_twitter_private_dm_uses_explicit_recipient():
    options = _twitter_options()
    options["recipient_id"] = "12345"
    alert = _alert(custom_body="hello")

    fake_client = mock.Mock()
    fake_client.create_direct_message.return_value = mock.Mock()

    with mock.patch("redash.destinations.twitter_private.tweepy.Client", return_value=fake_client):
        TwitterPrivate(options).notify(
            alert, mock.Mock(), mock.Mock(), Alert.TRIGGERED_STATE, mock.Mock(), "http://h", {}, options
        )

    fake_client.get_me.assert_not_called()
    fake_client.create_direct_message.assert_called_once_with(
        participant_id="12345", text="hello", user_auth=True
    )


def test_twitter_private_dm_falls_back_to_authenticated_user():
    options = _twitter_options()
    alert = _alert(custom_body="hi")

    fake_client = mock.Mock()
    fake_client.get_me.return_value = mock.Mock(data=mock.Mock(id="55"))
    fake_client.create_direct_message.return_value = mock.Mock()

    with mock.patch("redash.destinations.twitter_private.tweepy.Client", return_value=fake_client):
        TwitterPrivate(options).notify(
            alert, mock.Mock(), mock.Mock(), Alert.TRIGGERED_STATE, mock.Mock(), "http://h", {}, options
        )

    fake_client.get_me.assert_called_once_with(user_auth=True)
    fake_client.create_direct_message.assert_called_once_with(
        participant_id="55", text="hi", user_auth=True
    )
