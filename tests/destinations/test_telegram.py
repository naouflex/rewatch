from unittest import mock

from rewatch.destinations.telegram import Telegram
from rewatch.models import Alert


def _make_alert(custom_body=None):
    alert = mock.Mock()
    alert.id = 1
    alert.name = "Test Alert"
    alert.options = {}
    alert.render_custom_body = mock.Mock(return_value=custom_body or "")
    alert.render_template = mock.Mock(return_value="rendered default")
    return alert


def test_telegram_registered():
    from rewatch.destinations import destinations

    assert destinations.get("telegram") is Telegram


def test_telegram_notify_uses_default_template_when_no_custom_body():
    options = {"bot_token": "abc", "chat_id": "42"}
    alert = _make_alert(custom_body=None)

    destination = Telegram(options)
    with mock.patch("rewatch.destinations.telegram.requests.post") as mock_post:
        mock_post.return_value = mock.Mock(status_code=200, text="ok")
        destination.notify(alert, mock.Mock(), mock.Mock(), Alert.TRIGGERED_STATE, mock.Mock(), "http://h", {}, options)

    alert.render_template.assert_called_once()
    call_args, call_kwargs = mock_post.call_args
    assert "https://api.telegram.org/botabc/sendMessage" in call_args[0]
    assert call_kwargs["data"]["chat_id"] == "42"
    assert call_kwargs["data"]["text"] == "rendered default"


def test_telegram_notify_passes_row_metadata_for_per_row():
    options = {"bot_token": "abc", "chat_id": "42"}
    alert = _make_alert(custom_body="Row {{QUERY_RESULT_ROW_INDEX}}")
    alert.render_custom_body = mock.Mock(return_value="Row 1")

    destination = Telegram(options)
    with mock.patch("rewatch.destinations.telegram.requests.post") as mock_post:
        mock_post.return_value = mock.Mock(status_code=200, text="ok")
        destination.notify(
            alert,
            mock.Mock(),
            mock.Mock(),
            Alert.TRIGGERED_STATE,
            mock.Mock(),
            "http://h",
            {"row": {"foo": 7}, "row_index": 1},
            options,
        )

    alert.render_custom_body.assert_called_with(row={"foo": 7}, row_index=1)
    assert mock_post.call_args.kwargs["data"]["text"] == "Row 1"
