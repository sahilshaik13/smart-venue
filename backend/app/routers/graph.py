"""
/api/graph  — Venue Knowledge Graph endpoint.

Returns the full node-edge graph of the venue, cached with the same
30-second TTL as the zone snapshot. Frontend uses this to render a
D3 force-directed graph.  Gemini uses the text summary for Graph RAG.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends
from typing import Any

from app.cache import AsyncTTLCache
from app.dependencies import get_cache, get_snapshot
from app.services.graph_builder import build_venue_graph, graph_to_dict

log = structlog.get_logger(__name__)
router = APIRouter(tags=["graph"])

CACHE_KEY = "venue_graph"


@router.get(
    "/api/graph",
    response_model=dict,
    summary="Venue Knowledge Graph",
    description=(
        "Returns a node-edge knowledge graph of all venue zones and physical "
        "walkway connections. Edge weights represent live crowd-flow volume. "
        "Inspired by GitNexus — Graph RAG for physical spaces."
    ),
)
async def get_venue_graph(
    cache: AsyncTTLCache = Depends(get_cache),
) -> dict[str, Any]:
    """
    Build and return the venue knowledge graph.

    Nodes  = venue zones (gates, concessions, restrooms, seating)
    Edges  = physical walkways weighted by live crowd-flow volume
    """
    cached = await cache.get(CACHE_KEY)
    if cached:
        log.info("graph_cache_hit")
        return cached

    snapshot = await get_snapshot(cache)
    graph = build_venue_graph(snapshot)
    result = graph_to_dict(graph)

    await cache.set(CACHE_KEY, result)
    log.info(
        "graph_built",
        nodes=len(graph.nodes),
        edges=len(graph.edges),
        critical_zones=len(graph.critical_paths),
    )
    return result
