"""
Supabase client service for SmartVenue AI.

Handles persistent storage for:
- Chat session history
- Zone crowd snapshots (for trend analysis)
- Wait time prediction logs
"""

from __future__ import annotations

import structlog
from typing import Any
from supabase import create_client, Client
from app.config import settings

log = structlog.get_logger(__name__)

_client: Client | None = None


def get_supabase() -> Client:
    """Return a singleton Supabase client, initialised lazily."""
    global _client
    if _client is None:
        # Fallback logic for various env var names used in different environments
        url = settings.supabase_url
        key = settings.supabase_key or settings.supabase_anon_key or settings.supabase_service_role_key
        
        if not url or not key:
            log.error("supabase_config_missing", url=bool(url), key=bool(key))
            raise RuntimeError("Supabase URL or Key is missing from configuration")

        _client = create_client(url, key)
        log.info("supabase_connected", url=url[:30])
    return _client


# ---------------------------------------------------------------------------
# Chat history
# ---------------------------------------------------------------------------

async def save_chat_message(
    user_id: str,
    session_id: str,
    role: str,
    content: str,
    zones_referenced: list[str] | None = None,
) -> None:
    """Persist a single chat message (user or assistant) to Supabase."""
    try:
        sb = get_supabase()
        sb.table("chat_messages").insert(
            {
                "user_id": user_id,
                "session_id": session_id,
                "role": role,
                "content": content[:2000],            # cap to 2 000 chars
                "zones_referenced": zones_referenced or [],
            }
        ).execute()
        log.info("chat_message_saved", user_id=user_id, session_id=session_id, role=role)
    except Exception as exc:
        # Non-fatal: log and continue — don't break the API on DB failures
        log.warning("chat_save_failed", error=str(exc))


async def get_chat_history(user_id: str, session_id: str, limit: int = 20) -> list[dict[str, Any]]:
    """Fetch recent messages for a session (oldest-first for context window)."""
    try:
        sb = get_supabase()
        result = (
            sb.table("chat_messages")
            .select("role, content, created_at")
            .eq("user_id", user_id)
            .eq("session_id", session_id)
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )
        return result.data or []
    except Exception as exc:
        log.warning("chat_history_fetch_failed", error=str(exc))
        return []


# ---------------------------------------------------------------------------
# Zone snapshots  (written every 30 s by the background refresh)
# ---------------------------------------------------------------------------

async def save_zone_snapshot(snapshot_json: dict[str, Any]) -> None:
    """Store a full venue snapshot for historical trend analysis."""
    try:
        sb = get_supabase()
        sb.table("zone_snapshots").insert(
            {
                "match_minute": snapshot_json.get("match_minute"),
                "match_phase": snapshot_json.get("match_phase"),
                "snapshot_data": snapshot_json,
            }
        ).execute()
    except Exception as exc:
        log.warning("snapshot_save_failed", error=str(exc))


async def get_recent_snapshots(limit: int = 5) -> list[dict[str, Any]]:
    """Return the N most-recent zone snapshots (for trend computation)."""
    try:
        sb = get_supabase()
        result = (
            sb.table("zone_snapshots")
            .select("snapshot_data, created_at")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
    except Exception as exc:
        log.warning("snapshots_fetch_failed", error=str(exc))
        return []


# ---------------------------------------------------------------------------
# Wait prediction logs
# ---------------------------------------------------------------------------

async def log_wait_prediction(
    zone_id: str,
    predicted_wait: int,
    confidence: float,
    trend: str,
) -> None:
    """Append a wait-time prediction record for analytics."""
    try:
        sb = get_supabase()
        sb.table("wait_predictions").insert(
            {
                "zone_id": zone_id,
                "predicted_wait_minutes": predicted_wait,
                "confidence": confidence,
                "trend": trend,
            }
        ).execute()
    except Exception as exc:
        log.warning("prediction_log_failed", error=str(exc))
