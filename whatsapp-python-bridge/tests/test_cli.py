import pytest

from whatsapp_python_bridge import cli


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_cli_help_exits_cleanly():
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--help"])
    assert excinfo.value.code == 0


def test_cli_send_text_invokes_client(monkeypatch):
    calls = {}

    def fake_send_text(self, to, text, preview_url=False):
        calls["to"] = to
        calls["text"] = text
        calls["preview_url"] = preview_url
        return DummyResponse({"ok": True})

    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "12345")
    monkeypatch.setenv("WHATSAPP_TOKEN", "token")
    monkeypatch.setattr("whatsapp_python_bridge.cli.WhatsAppCloudClient.send_text", fake_send_text)

    cli.main(["send-text", "--to", "15551234567", "--text", "hello"])
    assert calls["to"] == "15551234567"
    assert calls["text"] == "hello"
