import tempfile
from pathlib import Path

import pytest

from whatsapp_python_bridge.client import WhatsAppCloudClient, compute_appsecret_proof, verify_signature
from whatsapp_python_bridge.config import WhatsAppConfig


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception("HTTP error")

    def json(self):
        return self._payload


class RecordingSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, url, headers=None, json=None, files=None, data=None, timeout=None):
        self.calls.append({"url": url, "headers": headers, "json": json, "files": files, "data": data})
        return self.response

    def get(self, url, headers=None, timeout=None):
        self.calls.append({"url": url, "headers": headers, "timeout": timeout})
        return self.response


def base_config():
    return WhatsAppConfig(phone_number_id="12345", access_token="abc", app_secret="secret")


def test_send_text_builds_payload():
    resp = FakeResponse(payload={"id": "msg-id"})
    session = RecordingSession(resp)
    client = WhatsAppCloudClient(base_config(), session=session)

    response = client.send_text("15551234567", "hello", preview_url=True)

    assert response.json() == {"id": "msg-id"}
    assert session.calls[0]["url"].endswith("/12345/messages")
    assert session.calls[0]["json"]["text"]["body"] == "hello"
    assert session.calls[0]["json"]["text"]["preview_url"] is True
    assert "Idempotency-Key" in session.calls[0]["headers"]


def test_upload_media_uses_file(tmp_path):
    media_file = tmp_path / "hello.txt"
    media_file.write_text("hello")

    resp = FakeResponse(payload={"id": "media-id"})
    session = RecordingSession(resp)
    client = WhatsAppCloudClient(base_config(), session=session)

    meta = client.upload_media(str(media_file), mime_type="text/plain")
    assert meta == {"id": "media-id"}
    assert session.calls[0]["files"]["file"][0] == "hello.txt"


def test_download_media_writes_file(tmp_path):
    resp = FakeResponse(payload=None)
    resp.content = b"data"
    session = RecordingSession(resp)
    client = WhatsAppCloudClient(base_config(), session=session)

    path = client.download_media("https://example.com/file.bin", dest_path=tmp_path / "file.bin")
    assert path.exists()
    assert path.read_bytes() == b"data"


def test_signature_helpers():
    token = "abc"
    secret = "shh"
    proof = compute_appsecret_proof(token, secret)
    assert isinstance(proof, str) and len(proof) == 64

    payload = b'{"test": true}'
    import hmac, hashlib

    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    header = f"sha256={expected}"
    assert verify_signature(secret, payload, header) is True
    assert verify_signature(secret, payload, "sha256=bad") is False
