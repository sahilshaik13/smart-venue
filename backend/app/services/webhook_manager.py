import httpx
import asyncio
import structlog
from typing import Any, Dict
from app.config import settings

log = structlog.get_logger(__name__)

class WebhookManager:
    def __init__(self):
        self.url = settings.webhook_url # We'll add this to settings
        self.client = httpx.AsyncClient(timeout=5.0)

    async def emit(self, event_type: str, data: Dict[str, Any]):
        """Asynchronously send a webhook event to the configured endpoint."""
        if not self.url:
            log.debug("webhook_skipped_no_url", event_type=event_type)
            return

        payload = {
            "event": event_type,
            "timestamp": str(asyncio.get_event_loop().time()),
            "data": data
        }

        try:
            log.info("webhook_emitting", event_type=event_type, url=self.url)
            response = await self.client.post(self.url, json=payload)
            response.raise_for_status()
            log.info("webhook_delivered", event_type=event_type, status=response.status_code)
        except Exception as e:
            log.warning("webhook_failed", event_type=event_type, error=str(e))

# Singleton instance
webhook_manager = WebhookManager()
