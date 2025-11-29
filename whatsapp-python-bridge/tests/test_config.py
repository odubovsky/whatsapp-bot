import os

import pytest

from whatsapp_python_bridge.config import WhatsAppConfig


def test_config_from_env(monkeypatch):
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "12345")
    monkeypatch.setenv("WHATSAPP_TOKEN", "abc-token")
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "secret")
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "verifyme")

    cfg = WhatsAppConfig.from_env()
    assert cfg.phone_number_id == "12345"
    assert cfg.access_token == "abc-token"
    assert cfg.app_secret == "secret"
    assert cfg.verify_token == "verifyme"


def test_config_requires_env(monkeypatch):
    monkeypatch.delenv("WHATSAPP_PHONE_NUMBER_ID", raising=False)
    monkeypatch.delenv("WHATSAPP_TOKEN", raising=False)
    with pytest.raises(ValueError):
        WhatsAppConfig.from_env()
