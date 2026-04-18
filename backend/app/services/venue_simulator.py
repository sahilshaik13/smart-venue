import json
import os
import math
import random
import time
import structlog
from datetime import datetime
from typing import Dict, List, Tuple, Any
from app.models import VenueSnapshot, ZoneStatus, ZoneType
from app.services.webhook_manager import webhook_manager
from app.services.prediction_service import prediction_service

log = structlog.get_logger(__name__)

# THEME_MATRICES remains as the procedural logic layer
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
    "startup_summit": {
        "gate_main": 80, "gate_g1": 60, "gate_g2": 44, "gate_g3": 24, "gate_g4": 16, "gate_g5": 44, "gate_west": 20,
        "hall_1": 68, "hall_2": 92, "hall_3": 72, "hall_4": 84,
        "area_fairpark": 20, "area_vpe": 68, "area_tradefair": 52, "area_parking_tf": 60, "area_plaza": 56,
        "area_lake": 16, "area_parking_open": 52, "area_parking_p1": 60, "area_parking_p2": 44, "area_aeros": 80,
        "area_west_arena": 28, "area_security": 44, "area_service_1": 32, "area_service_2": 24
    }
}

class SimulatorEngine:
    def __init__(self):
        self.theme = "hackathon"
        self.situation = "morning_entry"
        self.severity = "medium"
        self.auto_rotate = False
        self.last_rotation_time = time.time()
        self._load_zone_data()
        self._load_patterns()

    def _load_zone_data(self):
        # 1:1 PARITY WITH CALIBRATION JSON
        self.zone_data = [
            ("gate_main",    "Main Gate Entrance (MG)",  ZoneType.gate, 5000, 17.469243, 78.376628),
            ("gate_g1",      "Gate G1 (Entrance)",       ZoneType.gate, 2000, 17.469435, 78.375820),
            ("gate_g2",      "Gate G2 (Hall 1 Entry)",   ZoneType.gate, 2000, 17.469518, 78.375055),
            ("gate_g3",      "Gate G3 (Hall 3 Entry)",   ZoneType.gate, 2000, 17.469668, 78.374310),
            ("gate_g4",      "Gate G4 (Service)",        ZoneType.gate, 1000, 17.469800, 78.373813),
            ("gate_g5",      "Gate G5 (Parking Entry)",  ZoneType.gate, 1000, 17.469952, 78.373204),
            ("gate_west",    "West Gate (Back Entry)",   ZoneType.gate, 1500, 17.471400, 78.370370),
            
            ("hall_1",       "Hall 1 (Trade Center)",    ZoneType.seating, 10000, 17.470181, 78.375540),
            ("hall_2",       "Hall 2 (Convention)",      ZoneType.seating, 8000,  17.471328, 78.375980),
            ("hall_3",       "Hall 3 (Exhibition)",      ZoneType.seating, 12000, 17.470254, 78.374815),
            ("hall_4",       "Hall 4 (Main Expo)",       ZoneType.seating, 15000, 17.471683, 78.375076),
            
            ("area_fairpark",     "Fair Park (FP)",            ZoneType.seating, 2000, 17.4697737818, 78.376266795),
            ("area_vpe",          "VIP Entrance (VPE)",        ZoneType.gate,    1500, 17.470310, 78.376832),
            ("area_tradefair",    "Trade Fair Office (TF)",    ZoneType.seating, 500,  17.470975, 78.376551),
            ("area_parking_tf",   "TF North Parking",          ZoneType.seating, 1000, 17.471421, 78.376864),
            ("area_plaza",        "Exhibition Plaza",          ZoneType.seating, 4000, 17.470378, 78.376445),
            ("area_lake",         "Hitex Lake (HL)",           ZoneType.seating, 1000, 17.470960, 78.371611),
            ("area_west_arena",   "Parking/Open Expo/Arena",   ZoneType.seating, 8000, 17.472458147, 78.375549434),
            ("area_parking_open", "Open West Event Arena",     ZoneType.seating, 8000, 17.471076, 78.373716),
            ("area_parking_p1",   "Parking P1",                ZoneType.seating, 5000, 17.469392, 78.372466),
            ("area_parking_p2",   "Parking P2",                ZoneType.seating, 5000, 17.469068, 78.371384),
            ("area_aeros",        "Aeros Restaurant",          ZoneType.concession, 800, 17.469023, 78.376276),
            ("area_security",     "Hitex Security Room",       ZoneType.gate,    5000, 17.468674905, 78.376220884),
            ("area_service_1",    "Service Provider Off 1",    ZoneType.gate,    500,  17.469249828, 78.375494804),
            ("area_service_2",    "Service Provider Off 2",    ZoneType.gate,    500,  17.470052115, 78.372534496),
        ]

    def _load_patterns(self):
        self.patterns = {}
        path = os.path.join(os.path.dirname(__file__), "../resources/hero_patterns.json")
        if os.path.exists(path):
            with open(path, "r") as f:
                self.patterns = json.load(f)

    def set_state(self, theme: str, situation: str, severity: str, auto_rotate: bool = True):
        log.info("simulator_state_update", theme=theme, situation=situation, severity=severity)
        self.theme = theme.lower()
        self.situation = situation.lower()
        self.severity = severity.lower()
        self.auto_rotate = auto_rotate
        self.last_rotation_time = time.time()

    def generate_snapshot(self) -> VenueSnapshot:
        matrix = THEME_MATRICES.get(self.theme, {})
        sev_mult = {"low": 0.4, "medium": 0.7, "high": 1.0}.get(self.severity, 0.7)
        
        zones = []
        for zid, zname, ztype, cap, lat, lng in self.zone_data:
            base_perc = matrix.get(zid, 8)
            if self.situation == "morning_entry":
                if "gate" in zid or "parking" in zid: base_perc = min(99, base_perc * 1.2)
                else: base_perc *= 0.6
            elif self.situation == "closing":
                if "gate" in zid or "parking" in zid: base_perc = min(99, base_perc * 1.3)
                else: base_perc *= 0.4
            
            crowd_lvl = (base_perc / 100.0) * sev_mult
            jitter = random.uniform(-0.02, 0.02)
            crowd_lvl = min(0.99, max(0.01, crowd_lvl + jitter))
            
            pred_wait = prediction_service.predict_wait_time(self.theme, self.situation, ztype, crowd_lvl)
            zones.append(ZoneStatus(
                zone_id=zid, name=zname, type=ztype, capacity=cap,
                current_count=int(cap * crowd_lvl), crowd_level=crowd_lvl,
                status="critical" if crowd_lvl > 0.8 else "high" if crowd_lvl > 0.6 else "medium" if crowd_lvl > 0.35 else "low",
                predicted_wait_time=pred_wait, lat=lat, lng=lng
            ))

        particles = []
        # Radius mapping
        SCATTER_CONFIG = {
            "hall_1": 0.0007, "hall_2": 0.0007, "hall_3": 0.0008, "hall_4": 0.0009,
            "area_west_arena": 0.0012, "area_parking_open": 0.0010, "area_lake": 0.0012,
            "area_parking_p1": 0.0009, "area_parking_p2": 0.0009, "area_plaza": 0.0008, "area_fairpark": 0.0007,
            "gate_main": 0.0004, "gate_west": 0.0003, "area_security": 0.0004, "area_aeros": 0.0003,
            "area_vpe": 0.0003, "area_tradefair": 0.0003, "area_parking_tf": 0.0005
        }
        HERO_HUBS = {
            "area_plaza": "plaza", "hall_1": "arena", "hall_2": "arena", 
            "hall_3": "arena", "hall_4": "arena", "area_west_arena": "arena",
            "area_fairpark": "plaza", "gate_main": "plaza"
        }
        
        elapsed = int((time.time() - self.last_rotation_time) * 10)
        for zone in zones:
            dot_count = math.floor((zone.crowd_level * 100) / 4)
            if dot_count <= 0: continue
            
            scatter_radius = SCATTER_CONFIG.get(zone.zone_id, 0.0005)
            hero_key = HERO_HUBS.get(zone.zone_id)
            hero_scene = self.patterns.get(hero_key, {}) if hero_key else None

            if hero_scene and len(hero_scene) >= dot_count:
                tids = list(hero_scene.keys())[:dot_count]
                for tid in tids:
                    path = hero_scene[tid]
                    point = path[elapsed % len(path)]
                    particles.append({
                        "id": f"{zone.zone_id}_{tid}",
                        "x": zone.lng + (((point["x"]/1607)-0.5) * scatter_radius),
                        "y": zone.lat + (((point["y"]/1899)-0.5) * scatter_radius),
                        "type": point["t"]
                    })
            else:
                for i in range(dot_count):
                    random.seed(hash(f"{zone.zone_id}_{i}"))
                    dx = random.gauss(0, scatter_radius * 0.5)
                    dy = random.gauss(0, scatter_radius * 0.5)
                    particles.append({
                        "id": f"{zone.zone_id}_fall_{i}",
                        "x": zone.lng + dx, "y": zone.lat + dy, "type": "visitor"
                    })
                random.seed()

        return VenueSnapshot(
            snapshot_time=datetime.utcnow(),
            match_minute=0,
            match_phase=f"{self.theme.upper()} - {self.situation.replace('_',' ').upper()} ({self.severity.upper()})",
            zones=zones,
            particles=particles
        )

simulator_engine = SimulatorEngine()
