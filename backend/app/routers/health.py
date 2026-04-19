from fastapi import APIRouter, Response
import time
from app.services.venue_simulator import simulator_engine
from app.services.supabase_client import get_supabase

router = APIRouter(tags=["health"])
_startup_time = time.time()

@router.get("/health")
async def health_check(response: Response):
    # Check Subsystems
    db_status = "ok"
    try:
        client = get_supabase()
        if not client:
            db_status = "error"
    except Exception:
        db_status = "error"
        
    sim_status = "ok" if simulator_engine and simulator_engine.graph else "error"
    
    # Check Prediction Service (Model Status)
    from app.services.prediction_service import prediction_service
    model_status = "ok" if prediction_service.model else "error"

    health = {
        "status": "ok",
        "uptime_seconds": int(time.time() - _startup_time),
        "subsystems": {
            "database": db_status,
            "simulator": sim_status,
            "prediction_model": model_status
        }
    }
    
    # If any subsystem is down, we still return 200 but with status: error
    if any(v == "error" for v in health["subsystems"].values()):
        health["status"] = "degraded"
        
    return health

@router.get("/api/metrics")
async def metrics():
    return {"uptime_seconds": int(time.time() - _startup_time)}
