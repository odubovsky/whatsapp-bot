import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from whatsapp_python_bridge.client import verify_signature
from whatsapp_python_bridge.config import WhatsAppConfig
from whatsapp_python_bridge.webhook import create_app


def make_signature(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def test_webhook_verification_success():
    cfg = WhatsAppConfig(
        phone_number_id="123",
        access_token="token",
        app_secret="secret",
        verify_token="verifyme",
    )
    from whatsapp_python_bridge.client import WhatsAppCloudClient

    app = create_app(cfg, WhatsAppCloudClient(cfg))
    client = TestClient(app)

    # GET challenge
    resp = client.get("/webhook", params={"mode": "subscribe", "challenge": "42", "token": "verifyme"})
    assert resp.status_code == 200
    assert resp.json() == 42

    body = b'{"entry":[]}'
    signature = make_signature(cfg.app_secret, body)
    resp = client.post("/webhook", content=body, headers={"X-Hub-Signature-256": signature})
    assert resp.status_code == 200
    assert resp.json()["status"] == "received"


def test_webhook_rejects_bad_signature():
    cfg = WhatsAppConfig(
        phone_number_id="123",
        access_token="token",
        app_secret="secret",
        verify_token="verifyme",
    )
    from whatsapp_python_bridge.client import WhatsAppCloudClient

    app = create_app(cfg, WhatsAppCloudClient(cfg))
    client = TestClient(app)

    body = b'{"entry":[]}'
    resp = client.post("/webhook", content=body, headers={"X-Hub-Signature-256": "sha256=bad"})
    assert resp.status_code == 401
