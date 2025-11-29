import contextlib
import hashlib
import hmac
import json
import mimetypes
import os
import uuid
from pathlib import Path
from typing import Dict, Optional

import requests

from .config import WhatsAppConfig


class WhatsAppCloudClient:
    """Thin wrapper around the WhatsApp Cloud API (Graph)."""

    def __init__(self, config: WhatsAppConfig, session: Optional[requests.Session] = None):
        self.config = config
        self.session = session or requests.Session()

    def _headers(self, idempotency_key: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.config.access_token}",
            "Content-Type": "application/json",
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        return headers

    def _url(self, path: str) -> str:
        return f"{self.config.graph_api_base.rstrip('/')}/{path.lstrip('/')}"

    def send_text(
        self,
        to: str,
        text: str,
        preview_url: bool = False,
        idempotency_key: Optional[str] = None,
    ) -> requests.Response:
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text, "preview_url": preview_url},
        }
        return self._post_message(payload, idempotency_key)

    def send_media(
        self,
        to: str,
        media_id: str,
        media_type: str = "image",
        caption: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> requests.Response:
        message = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": media_type,
            media_type: {"id": media_id},
        }
        if caption:
            message[media_type]["caption"] = caption
        return self._post_message(message, idempotency_key)

    def _post_message(self, payload: Dict, idempotency_key: Optional[str]) -> requests.Response:
        key = idempotency_key or str(uuid.uuid4())
        url = self._url(f"{self.config.phone_number_id}/messages")
        response = self.session.post(url, headers=self._headers(key), json=payload, timeout=15)
        response.raise_for_status()
        return response

    def upload_media(self, file_path: str, mime_type: Optional[str] = None) -> Dict:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Media file not found: {file_path}")

        mime = mime_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        url = self._url(f"{self.config.phone_number_id}/media")
        with path.open("rb") as fh:
            files = {"file": (path.name, fh, mime)}
            data = {"messaging_product": "whatsapp"}
            response = self.session.post(
                url,
                headers={"Authorization": f"Bearer {self.config.access_token}"},
                files=files,
                data=data,
                timeout=30,
            )
        response.raise_for_status()
        return response.json()

    def download_media(self, media_url: str, dest_path: Optional[str] = None) -> Path:
        headers = {"Authorization": f"Bearer {self.config.access_token}"}
        response = self.session.get(media_url, headers=headers, timeout=30)
        response.raise_for_status()
        filename = dest_path or self._filename_from_url(media_url)
        path = Path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(response.content)
        return path

    def _filename_from_url(self, media_url: str) -> str:
        basename = media_url.split("?")[0].rstrip("/").split("/")[-1]
        return basename or f"media_{uuid.uuid4().hex}"


def compute_appsecret_proof(token: str, app_secret: str) -> str:
    """Generate appsecret_proof for Graph API calls when required."""
    digest = hmac.new(app_secret.encode("utf-8"), msg=token.encode("utf-8"), digestmod=hashlib.sha256)
    return digest.hexdigest()


def verify_signature(app_secret: str, payload: bytes, signature_header: str) -> bool:
    """Validate X-Hub-Signature-256 from a webhook POST."""
    if not signature_header:
        return False
    try:
        scheme, received = signature_header.split("=", 1)
    except ValueError:
        return False
    if scheme.lower() != "sha256":
        return False
    expected = hmac.new(app_secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    # constant time compare
    return hmac.compare_digest(expected, received)


def load_json_env(var: str) -> Optional[Dict]:
    """Helper to parse optional JSON from an environment variable."""
    raw = os.getenv(var, "").strip()
    if not raw:
        return None
    with contextlib.suppress(json.JSONDecodeError):
        return json.loads(raw)
    raise ValueError(f"{var} contains invalid JSON")
