"""
/api/maps-key & Heatmap Data — GeoJSON Provider for Frontend Overlays.
"""

from fastapi import APIRouter, Depends, Request
from app.config import settings
from app.dependencies import get_cache, get_snapshot
from app.cache import AsyncTTLCache

router = APIRouter(tags=["maps"])


@router.get(
    "/api/maps-key",
    summary="Google Maps API key (public, browser-restricted)",
    description=(
        "Returns the Google Maps JavaScript API key for use in the frontend. "
        "Key should be restricted to your Cloud Run URL in GCP Console."
    ),
)
async def get_maps_key() -> dict[str, str]:
    """Return the Maps API key for dynamic script injection."""
    return {"key": settings.google_maps_api_key}


@router.get(
    "/api/maps/heatmap",
    summary="GeoJSON Heatmap Data",
    description=(
        "Returns a standard GeoJSON FeatureCollection of all 25 venue nodes. "
        "Each feature includes a 'weight' property representing its live congestion (0.0 to 1.0). "
        "Designed to be consumed directly by Google Maps HeatmapLayer."
    ),
)
async def get_heatmap_geojson(
    cache: AsyncTTLCache = Depends(get_cache)
) -> dict:
    """Provides a GeoJSON feed for real-time traffic heatmaps."""
    snapshot = await get_snapshot(cache)
    
    features = []
    for zone in snapshot.zones:
        features.append({
            "type": "Feature",
            "properties": {
                "id": zone.zone_id,
                "name": zone.name,
                "weight": zone.crowd_level, # Fast normalization for HeatmapLayer
                "status": zone.status
            },
            "geometry": {
                "type": "Point",
                "coordinates": [zone.lng, zone.lat]
            }
        })
        
    return {
        "type": "FeatureCollection",
        "features": features
    }
