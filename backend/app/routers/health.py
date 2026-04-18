from fastapi import APIRouter
import time

router = APIRouter(tags=["health"])

_startup_time = time.time()

@router.get("/health")
async def health_check():
    return {"status": "ok", "uptime_seconds": int(time.time() - _startup_time)}

@router.get("/api/metrics")
async def metrics():
    return {"uptime_seconds": int(time.time() - _startup_time)}
