import uvicorn

from .client import WhatsAppCloudClient
from .config import WhatsAppConfig
from .webhook import create_app
import json


def app_factory() -> object:
    """Factory for uvicorn to create the FastAPI app."""
    cfg = WhatsAppConfig.from_env()
    client = WhatsAppCloudClient(cfg)
    # Log incoming webhook payloads for visibility during setup/debug
    return create_app(
        cfg,
        client,
        on_message=lambda payload: print("[webhook] received:", json.dumps(payload)),
    )


def run_server(host: str = "0.0.0.0", port: int = 8080, reload: bool = False) -> None:
    """Run uvicorn serving the webhook."""
    uvicorn.run("whatsapp_python_bridge.server:app_factory", host=host, port=port, reload=reload, factory=True)
