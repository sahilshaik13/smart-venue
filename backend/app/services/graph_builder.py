"""
Venue Knowledge Graph builder — 1:1 Topology, GPS Sync & Dijkstra Navigation.
"""

from __future__ import annotations
import heapq
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
# GOLDEN TOPOLOGY MATRIX (1:1 PARITY WITH HITEX BLUEPRINT)
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

# ---------------------------------------------------------------------------
# NATURAL LANGUAGE ALIAS MAP
# Maps user-friendly / fuzzy terms → canonical zone IDs
# This is injected into Gemini's context so it can resolve any phrasing.
# ---------------------------------------------------------------------------
ZONE_ALIASES: dict[str, str] = {
    # Restaurant / Food
    "restaurant": "area_aeros",
    "aeros": "area_aeros",
    "aeros restaurant": "area_aeros",
    "dining": "area_aeros",
    "food court": "area_aeros",
    "cafe": "area_aeros",
    "cafeteria": "area_aeros",
    "eat": "area_aeros",
    "food": "area_aeros",

    # Halls
    "hall 1": "hall_1",
    "hall1": "hall_1",
    "hall a": "hall_1",
    "hall 2": "hall_2",
    "hall2": "hall_2",
    "hall b": "hall_2",
    "hall 3": "hall_3",
    "hall3": "hall_3",
    "hall c": "hall_3",
    "hall 4": "hall_4",
    "hall4": "hall_4",
    "hall d": "hall_4",
    "main expo": "hall_4",
    "main hall": "hall_4",
    "exhibition hall": "hall_4",
    "expo hall": "hall_4",

    # Gates
    "main gate": "gate_main",
    "main entrance": "gate_main",
    "main entry": "gate_main",
    "entrance": "gate_main",
    "gate 1": "gate_g1",
    "gate 2": "gate_g2",
    "gate 3": "gate_g3",
    "gate 4": "gate_g4",
    "gate 5": "gate_g5",
    "g1": "gate_g1",
    "g2": "gate_g2",
    "g3": "gate_g3",
    "g4": "gate_g4",
    "g5": "gate_g5",
    "west gate": "gate_west",
    "west entrance": "gate_west",

    # Parking
    "parking": "area_parking_p1",
    "parking p1": "area_parking_p1",
    "parking 1": "area_parking_p1",
    "lot 1": "area_parking_p1",
    "parking p2": "area_parking_p2",
    "parking 2": "area_parking_p2",
    "lot 2": "area_parking_p2",
    "open parking": "area_parking_open",
    "arena parking": "area_parking_open",
    "trade fair parking": "area_parking_tf",

    # VIP / Special
    "vip": "area_vpe",
    "vip entrance": "area_vpe",
    "vip arrival": "area_vpe",
    "vip lounge": "area_vpe",
    "trade fair": "area_tradefair",
    "tfo": "area_tradefair",

    # Plazas / Outdoors
    "plaza": "area_plaza",
    "fairpark": "area_fairpark",
    "fair park": "area_fairpark",
    "lawn": "area_fairpark",
    "lake": "area_lake",
    "hitex lake": "area_lake",
    "lakeside": "area_lake",

    # Arena
    "arena": "area_west_arena",
    "west arena": "area_west_arena",
    "event arena": "area_west_arena",
    "open arena": "area_parking_open",

    # Security
    "security": "area_security",
    "security check": "area_security",
}


def build_venue_graph(snapshot: VenueSnapshot) -> VenueGraph:
    if not snapshot.zones:
        return VenueGraph()

    lats = [z.lat for z in snapshot.zones]
    lngs = [z.lng for z in snapshot.zones]

    min_lat, max_lat = min(lats), max(lats)
    min_lng, max_lng = min(lngs), max(lngs)
    margin = 0.22
    lat_range = max_lat - min_lat if max_lat != min_lat else 1.0
    lng_range = max_lng - min_lng if max_lng != min_lng else 1.0

    nodes = []
    zone_map = {z.zone_id: z for z in snapshot.zones}

    for z in snapshot.zones:
        x = (margin / 2) + ((z.lng - min_lng) / lng_range) * (1 - margin)
        y = (1 - margin / 2) - ((z.lat - min_lat) / lat_range) * (1 - margin)
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
            # Bidirectional — visitors can walk either direction
            edges.append(GraphEdge(
                source=tgt_id, target=src_id, weight=weight,
                label=lbl, is_congested=weight > 0.7, distance_meters=dist
            ))

    return VenueGraph(
        nodes=nodes, edges=edges,
        snapshot_time=snapshot.snapshot_time.isoformat(),
        match_phase=snapshot.match_phase
    )


# ---------------------------------------------------------------------------
# DIJKSTRA NAVIGATION ENGINE
# ---------------------------------------------------------------------------

def dijkstra(graph: VenueGraph, start_id: str) -> dict[str, tuple[float, list[str]]]:
    """
    Dijkstra's shortest path from start_id to all reachable nodes.

    Edge cost = (distance_meters / 80.0) * (1.0 + crowd_weight^2 * 5.0)
    Models walking speed slowing under congestion — same approach as Google Maps.

    Returns: { node_id: (total_minutes, [path_of_node_ids]) }
    """
    adj: dict[str, list[tuple[float, str]]] = {}
    for e in graph.edges:
        speed_mult = 1.0 + (e.weight ** 2) * 5.0
        cost = (e.distance_meters / 80.0) * speed_mult
        adj.setdefault(e.source, []).append((cost, e.target))

    dist: dict[str, float] = {start_id: 0.0}
    prev: dict[str, str | None] = {start_id: None}
    heap = [(0.0, start_id)]

    while heap:
        d, u = heapq.heappop(heap)
        if d > dist.get(u, float("inf")):
            continue
        for cost, v in adj.get(u, []):
            nd = d + cost
            if nd < dist.get(v, float("inf")):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(heap, (nd, v))

    result: dict[str, tuple[float, list[str]]] = {}
    for node_id, total_cost in dist.items():
        path: list[str] = []
        cur: str | None = node_id
        while cur is not None:
            path.append(cur)
            cur = prev.get(cur)
        path.reverse()
        result[node_id] = (round(total_cost, 1), path)
    return result


# All route origins — every zone a visitor might be starting from
_ROUTE_ORIGINS = [
    # Entry gates
    "gate_main", "gate_g1", "gate_g2", "gate_g3", "gate_g4", "gate_g5", "gate_west",
    # Parking
    "area_parking_p1", "area_parking_p2", "area_parking_open", "area_parking_tf",
    # Halls (visitors inside ask for routes too)
    "hall_1", "hall_2", "hall_3", "hall_4",
    # Special zones
    "area_vpe", "area_plaza", "area_fairpark", "area_west_arena",
    "area_aeros", "area_lake", "area_tradefair", "area_security",
]

# All route destinations — everywhere a visitor might want to go
_ROUTE_DESTINATIONS = [
    # Halls
    "hall_1", "hall_2", "hall_3", "hall_4",
    # Dining
    "area_aeros",
    # Outdoors / amenities
    "area_west_arena", "area_lake", "area_fairpark", "area_plaza",
    # VIP / Special
    "area_vpe", "area_tradefair",
    # Gates (for exits)
    "gate_main", "gate_west", "gate_g1", "gate_g5",
    # Parking
    "area_parking_p1", "area_parking_open",
]


def compute_all_fastest_routes(graph: VenueGraph) -> list[dict]:
    """
    Pre-computes Dijkstra fastest routes from ALL meaningful origin zones to ALL
    destination zones. Returns a list of route dicts sorted by ETA ascending.

    Every chat request calls this so the AI always has live congestion-aware ETAs.
    """
    name_map = {n.id: n.label for n in graph.nodes}
    node_ids = {n.id for n in graph.nodes}

    routes = []
    edge_map = {(e.source, e.target): e for e in graph.edges}

    for origin in _ROUTE_ORIGINS:
        if origin not in node_ids:
            continue
        shortest = dijkstra(graph, origin)

        for dest in _ROUTE_DESTINATIONS:
            if dest not in shortest or dest == origin:
                continue
            minutes, path_ids = shortest[dest]
            if len(path_ids) < 2:
                continue

            path_names = [name_map.get(p, p) for p in path_ids]
            bottlenecks = [
                name_map.get(path_ids[i], path_ids[i])
                for i in range(len(path_ids) - 1)
                if edge_map.get((path_ids[i], path_ids[i + 1]),
                                GraphEdge("", "", 0, "", False)).is_congested
            ]
            routes.append({
                "from": name_map.get(origin, origin),
                "from_id": origin,
                "to": name_map.get(dest, dest),
                "to_id": dest,
                "eta_minutes": minutes,
                "path": " → ".join(path_names),
                "bottlenecks": bottlenecks,
                "is_clear": len(bottlenecks) == 0,
            })

    routes.sort(key=lambda r: r["eta_minutes"])
    return routes


def build_alias_context() -> str:
    """
    Returns the alias map as a formatted string for Gemini's context.
    Gemini uses this to resolve informal user queries to canonical zone names
    BEFORE looking up the pre-computed route table.
    """
    lines = ["NATURAL LANGUAGE ALIAS MAP (resolve user terms → canonical zone names):"]
    # Group by destination for readability
    dest_to_aliases: dict[str, list[str]] = {}
    for alias, zone_id in ZONE_ALIASES.items():
        dest_to_aliases.setdefault(zone_id, []).append(f'"{alias}"')
    for zone_id, aliases in dest_to_aliases.items():
        lines.append(f"  {zone_id}: {', '.join(aliases)}")
    return "\n".join(lines)


def graph_to_text_summary(graph: VenueGraph) -> str:
    name_map = {n.id: n.label for n in graph.nodes}
    node_lines = "\n".join(
        f"- {n.label} (ID: {n.id}): {n.status.upper()} | {int(n.crowd_level*100)}% crowd"
        for n in graph.nodes
    )

    adj_map: dict[str, list[str]] = {}
    for e in graph.edges:
        if e.source not in adj_map:
            adj_map[e.source] = []
        speed_mult = 1.0 + (e.weight ** 2) * 5.0
        est_mins = round((e.distance_meters / 80.0) * speed_mult, 1)
        target_name = name_map.get(e.target, e.target)
        adj_map[e.source].append(f"{target_name}({est_mins}m)")

    edge_lines = "\n".join(
        f"  * {name_map.get(src, src)}: {' | '.join(targets)}"
        for src, targets in adj_map.items()
    )

    return f"""
VENUE KNOWLEDGE GRAPH LIVE FEED [{graph.match_phase}]
====================================================================
ZONE ROSTER (Calibrated Names):
{node_lines}

ADJACENCY MAP (Walking Times, congestion-adjusted):
{edge_lines}

RULES (MANDATORY):
1. Use EXACT NAMES from the ZONE ROSTER. Never use IDs.
2. Recommend path with LOWEST total ETA from the PRE-COMPUTED ROUTES TABLE.
3. Lead with: **🧭 ETA: X.X mins**
====================================================================
""".strip()


def graph_to_dict(graph: VenueGraph) -> dict[str, Any]:
    return {
        "nodes": [asdict(n) for n in graph.nodes],
        "edges": [asdict(e) for e in graph.edges],
        "snapshot_time": graph.snapshot_time,
        "match_phase": graph.match_phase
    }
