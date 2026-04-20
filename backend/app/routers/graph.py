"""
/api/graph  — Venue Knowledge Graph endpoint.

Returns the full node-edge graph of the venue, cached with the same
30-second TTL as the zone snapshot. Frontend uses this to render a
D3 force-directed graph.  Gemini uses the text summary for Graph RAG.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, Request
from typing import Any

from app.cache import AsyncTTLCache
from app.dependencies import get_cache, get_snapshot
from app.models import VenueSnapshot
from app.services.graph_builder import build_venue_graph, graph_to_dict

log = structlog.get_logger(__name__)
router = APIRouter(tags=["graph"])

CACHE_KEY_BASE = "venue_graph"

@router.get(
    "/api/graph",
    response_model=dict,
    summary="Venue Knowledge Graph",
)
async def get_venue_graph(
    request: Request,
    snapshot: VenueSnapshot = Depends(get_snapshot),
    cache: AsyncTTLCache = Depends(get_cache),
) -> dict[str, Any]:
    """
    Build and return the venue knowledge graph.
    Scoped by user_id to ensure private sandbox data.
    """
    # Use user-specific cache key
    user_id = getattr(request.state, "user_id", "anonymous")
    cache_key = f"{CACHE_KEY_BASE}_{user_id}"
    
    cached = await cache.get(cache_key)
    if cached:
        log.info("graph_cache_hit", user_id=user_id)
        return cached

    graph = build_venue_graph(snapshot)
    result = graph_to_dict(graph)

    await cache.set(cache_key, result)
    log.info(
        "graph_built",
        user_id=user_id,
        nodes=len(graph.nodes),
        edges=len(graph.edges),
    )
    return result
