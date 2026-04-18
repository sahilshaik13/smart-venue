import random
from datetime import datetime
from app.models import ZoneStatus, WaitTimePrediction, ZoneType

def predict_wait(zone: ZoneStatus) -> WaitTimePrediction:
    base_waits = {
        ZoneType.gate: 5,
        ZoneType.concession: 8,
        ZoneType.restroom: 3,
        ZoneType.seating: 0
    }
    
    base = base_waits.get(zone.type, 5)
    wait_minutes = int(base * (zone.crowd_level ** 2) * 1.5 + random.uniform(0, 3))
    
    trend = "stable"
    if zone.crowd_level > 0.8:
        trend = "rising"
    elif zone.crowd_level < 0.4:
        trend = "falling"
        
    return WaitTimePrediction(
        zone_id=zone.zone_id,
        predicted_wait_minutes=max(1, wait_minutes) if zone.type != ZoneType.seating else 0,
        confidence=round(random.uniform(0.7, 0.95), 2),
        trend=trend,
        recommendation=f"Current crowd level is {int(zone.crowd_level * 100)}%.",
        predicted_at=datetime.utcnow()
    )
