from pydantic import BaseModel, ConfigDict
from enum import Enum
from datetime import datetime
from typing import List

class ZoneType(str, Enum):
    gate = "gate"
    concession = "concession"
    restroom = "restroom"
    seating = "seating"

class ZoneStatus(BaseModel):
    zone_id: str
    name: str
    type: ZoneType
    capacity: int
    current_count: int
    crowd_level: float
    status: str
    predicted_wait_time: float = 0.0 # From ML model
    lat: float | None = None
    lng: float | None = None

class Particle(BaseModel):
    id: str
    x: float
    y: float
    type: str

class VenueSnapshot(BaseModel):
    snapshot_time: datetime
    match_minute: int
    match_phase: str
    zones: List[ZoneStatus]
    particles: List[Particle] = []

class WaitTimePrediction(BaseModel):
    zone_id: str
    predicted_wait_minutes: int
    confidence: float
    trend: str
    recommendation: str
    predicted_at: datetime
