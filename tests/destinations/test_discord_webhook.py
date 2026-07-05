import json
from unittest import mock

from rewatch.destinations.discord_webhook import DEFAULT_EMBED_TITLE, DiscordWebhook
from rewatch.models import Alert


def _alert(custom_body=None, custom_template=None):
    alert = mock.Mock()
    alert.id = 7
    alert.name = "RAM usage"
    alert.options = {"column": "value", "op": ">", "value": 80}
    if custom_body:
        alert.options["custom_body"] = custom_body
    if custom_template:
        alert.options["template"] = custom_template

    def render_template(template, row=None, row_index=None):
        if template == DEFAULT_EMBED_TITLE:
            return "Alert: RAM usage is {}".format(row.get("foo") if row else "TRIGGERED")
        # Mustache-like substitution for {{ALERT_NAME}} only, leave everything else intact.
        return template.replace("{{ALERT_NAME}}", "RAM usage")

    alert.render_template = mock.Mock(side_effect=render_template)
    alert.render_custom_body = mock.Mock(return_value="rendered desc")
    return alert


def test_discord_webhook_registered():
    from rewatch.destinations import destinations

    assert destinations.get("discord_webhook") is DiscordWebhook


def test_discord_webhook_sends_default_embed():
    options = {"url": "https://discord/webhook"}
    alert = _alert()
    query = mock.Mock(id=11)

    with mock.patch("rewatch.destinations.discord_webhook.requests.post") as mock_post:
        mock_post.return_value = mock.Mock(status_code=204, text="")
        DiscordWebhook(options).notify(
            alert, query, mock.Mock(), Alert.TRIGGERED_STATE, mock.Mock(), "http://h", {}, options
        )

    sent = json.loads(mock_post.call_args.kwargs["data"].decode("utf-8"))
    embed = sent["embeds"][0]
    assert embed["title"].startswith("Alert: RAM usage")
    assert embed["description"] == "rendered desc"
    fields = {f["name"]: f["value"] for f in embed["fields"]}
    assert fields["Query"] == "http://h/queries/11"
    assert fields["Alert"] == "http://h/alerts/7"
    assert "value > 80" in fields["Condition"]


def test_discord_webhook_uses_custom_body_as_json_payload():
    custom = '{"content": "{{ALERT_NAME}} fired", "username": "bot"}'
    options = {"url": "https://discord/webhook"}
    alert = _alert(custom_body=custom)

    with mock.patch("rewatch.destinations.discord_webhook.requests.post") as mock_post:
        mock_post.return_value = mock.Mock(status_code=204, text="")
        DiscordWebhook(options).notify(
            alert, mock.Mock(id=11), mock.Mock(), Alert.TRIGGERED_STATE, mock.Mock(), "http://h", {}, options
        )

    sent = json.loads(mock_post.call_args.kwargs["data"].decode("utf-8"))
    assert sent == {"content": "RAM usage fired", "username": "bot"}


def test_discord_webhook_falls_back_when_custom_body_not_json():
    custom = "Plain text alert {{ALERT_NAME}}"
    options = {"url": "https://discord/webhook", "username": "rewatch-bot", "avatar_url": "http://img"}
    alert = _alert(custom_body=custom)

    with mock.patch("rewatch.destinations.discord_webhook.requests.post") as mock_post:
        mock_post.return_value = mock.Mock(status_code=204, text="")
        DiscordWebhook(options).notify(
            alert, mock.Mock(id=11), mock.Mock(), Alert.TRIGGERED_STATE, mock.Mock(), "http://h", {}, options
        )

    sent = json.loads(mock_post.call_args.kwargs["data"].decode("utf-8"))
    assert sent["content"] == "Plain text alert RAM usage"
    assert sent["username"] == "rewatch-bot"
    assert sent["avatar_url"] == "http://img"


def test_discord_webhook_includes_row_field_in_per_row_mode():
    options = {"url": "https://discord/webhook"}
    alert = _alert()

    with mock.patch("rewatch.destinations.discord_webhook.requests.post") as mock_post:
        mock_post.return_value = mock.Mock(status_code=204, text="")
        DiscordWebhook(options).notify(
            alert,
            mock.Mock(id=11),
            mock.Mock(),
            Alert.TRIGGERED_STATE,
            mock.Mock(),
            "http://h",
            {"row": {"foo": 9}, "row_index": 2},
            options,
        )

    sent = json.loads(mock_post.call_args.kwargs["data"].decode("utf-8"))
    fields = {f["name"]: f["value"] for f in sent["embeds"][0]["fields"]}
    assert "Row #2" in fields
    assert "foo=9" in fields["Row #2"]
