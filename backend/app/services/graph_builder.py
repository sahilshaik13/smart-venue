"""
Venue Knowledge Graph builder — 1:1 Topology & GPS Sync.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any
from app.models import VenueSnapshot, ZoneStatus

@dataclass
class GraphNode:
    id: str
    label: str
    type: str
    crowd_level: float
    status: str
    current_count: int
    capacity: int
    x_hint: float = 0.5
    y_hint: float = 0.5

@dataclass
class GraphEdge:
    source: str
    target: str
    weight: float
    label: str
    is_congested: bool
    distance_meters: int = 50

@dataclass
class VenueGraph:
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    snapshot_time: str = ""
    match_phase: str = ""
    critical_paths: list[str] = field(default_factory=list)
    recommended_routes: list[dict[str, Any]] = field(default_factory=list)

# ---------------------------------------------------------------------------
# GOLDEN TOPOLOGY MATRIX (1:1 PARITY WITH USER MERMAID)
# ---------------------------------------------------------------------------

# Format: (Source ID, Target ID, Label/Category, Distance Meters)
VENUE_TOPOLOGY: list[tuple[str, str, str, int]] = [
    ("area_security", "gate_main", "Entry Pathway", 76),
    ("gate_main", "area_aeros", "Dining Access", 45),
    ("area_aeros", "area_fairpark", "Lawn Walkway", 83),
    ("gate_main", "gate_g1", "Gate Spine", 88),
    ("gate_g1", "gate_g2", "Gate Spine", 82),
    ("gate_g2", "gate_g3", "Gate Spine", 81),
    ("gate_g3", "gate_g4", "Gate Spine", 55),
    ("gate_g4", "gate_g5", "Gate Spine", 67),
    ("gate_g5", "area_parking_p1", "Parking Access", 100),
    ("area_parking_p1", "area_parking_p2", "Parking Spine", 120),
    ("area_parking_p2", "gate_west", "West Exit Path", 280),
    
    ("area_fairpark", "area_plaza", "Plaza Link", 70),
    ("area_plaza", "area_vpe", "VIP Access", 42),
    ("area_vpe", "area_tradefair", "TFO Link", 80),
    ("area_tradefair", "area_parking_tf", "TFO Parking", 60),
    ("area_parking_tf", "hall_2", "Eastern Gate", 94),
    
    ("gate_g1", "area_service_1", "Service Lane", 40),
    ("gate_g2", "area_service_1", "Service Lane", 55),
    ("gate_g2", "hall_1", "Hall 1 Entry", 90),
    ("gate_g3", "hall_3", "Hall 3 Entry", 84),
    ("gate_g4", "area_service_2", "Service Lane", 138),
    ("gate_g5", "area_parking_open", "Arena Entry", 136),
    
    ("area_service_1", "hall_1", "Backdoor H1", 103),
    ("area_service_2", "area_parking_p1", "Service Loop", 74),
    ("area_service_2", "area_parking_open", "Arena Service", 169),
    
    ("hall_1", "hall_3", "Hall Connector", 77),
    ("hall_1", "hall_2", "Hall Connector", 136),
    ("hall_3", "hall_4", "Hall Connector", 161),
    ("hall_2", "hall_4", "Hall Connector", 104),
    ("hall_4", "area_west_arena", "Arena Access", 100),
    
    ("area_plaza", "hall_1", "Plaza Access", 98),
    ("area_plaza", "hall_2", "Plaza Access", 116),
    ("area_tradefair", "hall_2", "TFO Direct", 72),
    
    ("area_parking_open", "hall_3", "Arena Link", 148),
    ("area_parking_open", "area_lake", "Lakeside Access", 223),
    ("gate_west", "area_lake", "West Lake Link", 140),
    ("gate_west", "area_parking_open", "Arena West Path", 356),
]

def build_venue_graph(snapshot: VenueSnapshot) -> VenueGraph:
    if not snapshot.zones: return VenueGraph()

    lats = [z.lat for z in snapshot.zones]
    lngs = [z.lng for z in snapshot.zones]
    
    min_lat, max_lat = min(lats), max(lats)
    min_lng, max_lng = min(lngs), max(lngs)
    margin = 0.1
    lat_range = max_lat - min_lat if max_lat != min_lat else 1.0
    lng_range = max_lng - min_lng if max_lng != min_lng else 1.0

    nodes = []
    zone_map = {z.zone_id: z for z in snapshot.zones}
    
    for z in snapshot.zones:
        # GPS Projection Mirror
        x = margin + ( (z.lng - min_lng) / lng_range ) * (1 - 2*margin)
        y = (1 - margin) - ( (z.lat - min_lat) / lat_range ) * (1 - 2*margin)

        nodes.append(GraphNode(
            id=z.zone_id, label=z.name, type=z.type,
            crowd_level=z.crowd_level, status=z.status,
            current_count=z.current_count, capacity=z.capacity,
            x_hint=x, y_hint=y
        ))

    edges = []
    for src_id, tgt_id, lbl, dist in VENUE_TOPOLOGY:
        s_z = zone_map.get(src_id)
        t_z = zone_map.get(tgt_id)
        if s_z and t_z:
            weight = (s_z.crowd_level + t_z.crowd_level) / 2.0
            edges.append(GraphEdge(
                source=src_id, target=tgt_id, weight=weight,
                label=lbl, is_congested=weight > 0.7, distance_meters=dist
            ))
            edges.append(GraphEdge(
                source=tgt_id, target=src_id, weight=weight,
                label=lbl, is_congested=weight > 0.7, distance_meters=dist
            ))

    return VenueGraph(
        nodes=nodes, edges=edges,
        snapshot_time=snapshot.snapshot_time.isoformat(),
        match_phase=snapshot.match_phase
    )

def graph_to_text_summary(graph: VenueGraph) -> str:
    name_map = {n.id: n.label for n in graph.nodes}
    node_lines = "\n".join(
        f"- {n.label} (ID: {n.id}): {n.status.upper()} | {int(n.crowd_level*100)}% jam"
        for n in graph.nodes
    )
    
    adj_map = {}
    for e in graph.edges:
        if e.source not in adj_map: adj_map[e.source] = []
        # Human walking speed ~80m/min. Scaling with congestion squared.
        speed_mult = 1.0 + (e.weight ** 2) * 5.0
        est_mins = round((e.distance_meters / 80.0) * speed_mult, 1)
        target_name = name_map.get(e.target, e.target)
        adj_map[e.source].append(f"{target_name}({est_mins}m)")
    
    edge_lines = "\n".join(f"  * {name_map.get(src, src)}: {' | '.join(targets)}" for src, targets in adj_map.items())

    return f"""
VENUE KNOWLEDGE GRAPH LIVE FEED [{graph.match_phase}]
====================================================================
PROJECTED ROSTER (Calibrated Names):
{node_lines}

ADJACENCY MAP (Walking Times):
{edge_lines}

RULES (MANDATORY):
1. USE EXACT NAMES FROM ROSTER. No IDs.
2. Recommend path with LOWEST total minutes.
3. Lead with: **ETA: X.X mins**
====================================================================
""".strip()

def graph_to_dict(graph: VenueGraph) -> dict[str, Any]:
    return {
        "nodes": [asdict(n) for n in graph.nodes],
        "edges": [asdict(e) for e in graph.edges],
        "snapshot_time": graph.snapshot_time,
        "match_phase": graph.match_phase
    }
