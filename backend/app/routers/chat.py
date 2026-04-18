"""
/api/chat  — Gemini-powered venue assistant with Graph RAG.

Pulls live venue graph as context, fetches Supabase chat history for
multi-turn memory, calls Gemini, then persists the exchange.
"""

import re
import structlog
from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.cache import AsyncTTLCache
from app.dependencies import get_cache, get_snapshot
from app.services.auth import get_current_user
from app.services.graph_builder import build_venue_graph
from app.services.gemini_client import ask_gemini
from app.services.supabase_client import save_chat_message, get_chat_history

log = structlog.get_logger(__name__)
router = APIRouter(tags=["chat"])

_HTML_RE = re.compile(r"<[^>]+>")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500, description="Attendee question")
    session_id: str = Field(..., min_length=4, max_length=64, description="Client session ID")

    @field_validator("message")
    @classmethod
    def sanitise_message(cls, v: str) -> str:
        """Strip HTML tags to prevent prompt injection via markup."""
        return _HTML_RE.sub("", v).strip()

    @field_validator("session_id")
    @classmethod
    def validate_session(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_\-]+$", v):
            raise ValueError("session_id must be alphanumeric")
        return v


class ChatResponse(BaseModel):
    reply: str
    zones_referenced: list[str] = []
    response_time_ms: int = 0


@router.post(
    "/api/chat",
    response_model=ChatResponse,
    summary="Ask the Gemini venue assistant",
    description=(
        "Send a natural-language question to the Gemini-powered venue assistant. "
        "The assistant has full access to the live venue knowledge graph (Graph RAG). "
        "Rate limited to 10 requests per minute per IP."
    ),
)
# Note: Use the limiter from the app state
async def chat(
    request: Request,
    body: ChatRequest,
    cache: AsyncTTLCache = Depends(get_cache),
    user_id: str = Depends(get_current_user),
) -> ChatResponse:
    """
    Graph RAG chat endpoint.
    """
    # Rate limit check using the global app limiter
    limiter = request.app.state.limiter
    with limiter.limit("10/minute", key_func=get_remote_address, request=request):
        import time
        t0 = time.time()

    # Build graph context
    snapshot = await get_snapshot(cache)
    venue_graph = build_venue_graph(snapshot)

    # Fetch multi-turn history from Supabase (Filtering by current user)
    history = await get_chat_history(user_id, body.session_id, limit=6)

    # Call Gemini
    try:
        reply = await ask_gemini(
            message=body.message,
            venue_graph=venue_graph,
            chat_history=history,
        )
    except RuntimeError as exc:
        log.error("gemini_failed", session_id=body.session_id, user_id=user_id, error=str(exc))
        raise HTTPException(status_code=503, detail="AI assistant temporarily unavailable")

    latency = int((time.time() - t0) * 1000)

    # Detect which zones are mentioned in the reply
    zones_referenced = [
        z.zone_id for z in snapshot.zones
        if z.name.lower() in reply.lower() or z.zone_id in reply.lower()
    ]

    # Persist to Supabase (fire-and-forget, non-blocking)
    import asyncio
    asyncio.create_task(save_chat_message(user_id, body.session_id, "user", body.message))
    asyncio.create_task(
        save_chat_message(user_id, body.session_id, "assistant", reply, zones_referenced)
    )

    log.info(
        "chat_served",
        session_id=body.session_id,
        latency_ms=latency,
        zones_referenced=len(zones_referenced),
    )

    return ChatResponse(
        reply=reply,
        zones_referenced=zones_referenced,
        response_time_ms=latency,
    )
