# backend/app/utils/spatial_utils.py

import math
import random
from typing import Dict, Any

# THEME_MATRICES: Procedural logic layer for venue congestion profiles
THEME_MATRICES = {
    "marathon": {
        "gate_main": 88, "gate_g1": 72, "gate_g2": 40, "gate_g3": 36, "gate_g4": 20, "gate_g5": 80, "gate_west": 28,
        "hall_1": 8, "hall_2": 4, "hall_3": 12, "hall_4": 8,
        "area_fairpark": 76, "area_vpe": 44, "area_tradefair": 16, "area_parking_tf": 60, "area_plaza": 68,
        "area_lake": 32, "area_parking_open": 72, "area_parking_p1": 80, "area_parking_p2": 64, "area_aeros": 52,
        "area_west_arena": 56, "area_security": 48, "area_service_1": 24, "area_service_2": 20
    },
    "hackathon": {
        "gate_main": 76, "gate_g1": 48, "gate_g2": 32, "gate_g3": 20, "gate_g4": 8, "gate_g5": 28, "gate_west": 8,
        "hall_1": 88, "hall_2": 72, "hall_3": 56, "hall_4": 80,
        "area_fairpark": 16, "area_vpe": 52, "area_tradefair": 36, "area_parking_tf": 40, "area_plaza": 44,
        "area_lake": 12, "area_parking_open": 36, "area_parking_p1": 48, "area_parking_p2": 28, "area_aeros": 84,
        "area_west_arena": 20, "area_security": 32, "area_service_1": 20, "area_service_2": 16
    },
    "expo": {
        "gate_main": 92, "gate_g1": 84, "gate_g2": 76, "gate_g3": 68, "gate_g4": 40, "gate_g5": 72, "gate_west": 32,
        "hall_1": 96, "hall_2": 88, "hall_3": 84, "hall_4": 92,
        "area_fairpark": 60, "area_vpe": 72, "area_tradefair": 80, "area_parking_tf": 76, "area_plaza": 88,
        "area_lake": 24, "area_parking_open": 80, "area_parking_p1": 84, "area_parking_p2": 72, "area_aeros": 76,
        "area_west_arena": 68, "area_security": 56, "area_service_1": 60, "area_service_2": 52
    },
    "music_festival": {
        "gate_main": 96, "gate_g1": 88, "gate_g2": 64, "gate_g3": 48, "gate_g4": 24, "gate_g5": 84, "gate_west": 40,
        "hall_1": 20, "hall_2": 32, "hall_3": 44, "hall_4": 24,
        "area_fairpark": 52, "area_vpe": 80, "area_tradefair": 20, "area_parking_tf": 68, "area_plaza": 72,
        "area_lake": 36, "area_parking_open": 92, "area_parking_p1": 88, "area_parking_p2": 80, "area_aeros": 68,
        "area_west_arena": 96, "area_security": 80, "area_service_1": 36, "area_service_2": 28
    },
    "awards": { 
        "gate_main": 84, "gate_g1": 72, "gate_g2": 56, "gate_g3": 32, "gate_g4": 12, "gate_g5": 52, "gate_west": 16,
        "hall_1": 92, "hall_2": 88, "hall_3": 72, "hall_4": 76,
        "area_fairpark": 44, "area_vpe": 36, "area_tradefair": 48, "area_parking_tf": 52, "area_plaza": 64,
        "area_lake": 16, "area_parking_open": 60, "area_parking_p1": 68, "area_parking_p2": 52, "area_aeros": 72,
        "area_west_arena": 24, "area_security": 40, "area_service_1": 28, "area_service_2": 20
    },
    "football_match": {
        "gate_main": 80, "gate_g1": 96, "gate_g2": 92, "gate_g3": 84, "gate_g4": 40, "gate_g5": 88, "gate_west": 72,
        "hall_1": 12, "hall_2": 8, "hall_3": 16, "hall_4": 10,
        "area_fairpark": 20, "area_vpe": 68, "area_tradefair": 52, "area_parking_tf": 60, "area_plaza": 56,
        "area_lake": 16, "area_parking_open": 52, "area_parking_p1": 60, "area_parking_p2": 44, "area_aeros": 80,
        "area_west_arena": 28, "area_security": 44, "area_service_1": 32, "area_service_2": 24
    }
}

def calculate_crowd_level(
    base_perc: float, 
    situation: str, 
    zone_id: str, 
    severity_multiplier: float
) -> float:
    """Computes the final crowd density level based on situation and severity."""
    if situation == "morning_entry":
        if "gate" in zone_id or "parking" in zone_id:
            base_perc = min(99, base_perc * 1.2)
        else:
            base_perc *= 0.6
    elif situation == "closing":
        if "gate" in zone_id or "parking" in zone_id:
            base_perc = min(99, base_perc * 1.3)
        else:
            base_perc *= 0.4
    
    crowd_lvl = (base_perc / 100.0) * severity_multiplier
    jitter = random.uniform(-0.02, 0.02)
    return min(0.99, max(0.01, crowd_lvl + jitter))

def generate_random_particles(lat: float, lng: float, count: int) -> list[dict]:
    """Generates particle coordinates around a zone center, matching the Particle model schema."""
    particles = []
    for i in range(count):
        particles.append({
            "id": f"p_{i}_{random.randint(1000, 9999)}",
            "x": lat + (random.random() - 0.5) * 0.0005,
            "y": lng + (random.random() - 0.5) * 0.0005,
            "type": random.choice(["fan", "security", "staff"])
        })
    return particles
