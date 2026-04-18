import asyncio
from fastapi import Request, Depends
from app.cache import AsyncTTLCache
from app.services.venue_simulator import simulator_engine
from app.models import VenueSnapshot

# Global lock to synchronize snapshot generation
_snapshot_lock = asyncio.Lock()

async def get_cache(request: Request) -> AsyncTTLCache:
    return request.app.state.cache

async def get_snapshot(cache: AsyncTTLCache = Depends(get_cache)) -> VenueSnapshot:
    async with _snapshot_lock:
        cached = await cache.get("venue_snapshot")
        if cached:
            return cached
        # Generate from the shared Singleton Engine
        snapshot = simulator_engine.generate_snapshot()
        await cache.set("venue_snapshot", snapshot)
        return snapshot
