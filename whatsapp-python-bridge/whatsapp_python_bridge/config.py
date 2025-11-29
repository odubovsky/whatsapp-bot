from dataclasses import dataclass
from typing import Optional
import os

from dotenv import load_dotenv


@dataclass
class WhatsAppConfig:
    phone_number_id: str
    access_token: str
    app_secret: Optional[str] = None
    verify_token: Optional[str] = None
    graph_api_base: str = "https://graph.facebook.com/v19.0"

    @classmethod
    def from_env(cls) -> "WhatsAppConfig":
        # Load .env automatically so CLI/server pick up values without manual export
        load_dotenv()
        phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "").strip()
        access_token = os.getenv("WHATSAPP_TOKEN", "").strip()
        app_secret = os.getenv("WHATSAPP_APP_SECRET", "").strip() or None
        verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "").strip() or None
        if not phone_number_id:
            raise ValueError("WHATSAPP_PHONE_NUMBER_ID is required")
        if not access_token:
            raise ValueError("WHATSAPP_TOKEN is required")
        return cls(
            phone_number_id=phone_number_id,
            access_token=access_token,
            app_secret=app_secret,
            verify_token=verify_token,
        )

    def with_override(
        self,
        phone_number_id: Optional[str] = None,
        access_token: Optional[str] = None,
        app_secret: Optional[str] = None,
        verify_token: Optional[str] = None,
    ) -> "WhatsAppConfig":
        return WhatsAppConfig(
            phone_number_id=phone_number_id or self.phone_number_id,
            access_token=access_token or self.access_token,
            app_secret=app_secret if app_secret is not None else self.app_secret,
            verify_token=verify_token if verify_token is not None else self.verify_token,
            graph_api_base=self.graph_api_base,
        )
