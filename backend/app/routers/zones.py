from fastapi import APIRouter, Depends, Body
from app.models import VenueSnapshot
from app.dependencies import get_cache, get_snapshot
from app.services.auth import get_current_user

from app.services.venue_simulator import simulator_engine
from app.cache import AsyncTTLCache

router = APIRouter(tags=["zones"])

@router.get("/api/zones", response_model=VenueSnapshot)
async def get_zones(
    snapshot: VenueSnapshot = Depends(get_snapshot),
    user_id: str = Depends(get_current_user)
):
    return snapshot

@router.post("/api/simulate")
async def update_simulation(
    theme: str = Body(...),
    situation: str = Body(...),
    severity: str = Body(...),
    cache: AsyncTTLCache = Depends(get_cache),
    user_id: str = Depends(get_current_user)
):
    """Overrides the current simulation environment theme, situation, and intensity."""
    # Use the new shared Engine Singleton
    simulator_engine.set_state(theme, situation, severity, auto_rotate=False)
    
    # Manually invalidate caches 
    await cache.invalidate("venue_snapshot")
    await cache.invalidate("venue_graph")
    
    return {"status": "success", "theme": theme, "situation": situation, "severity": severity}
