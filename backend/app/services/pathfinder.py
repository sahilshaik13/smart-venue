import math
import heapq
from typing import Dict, List, Tuple
from app.models import ZoneStatus

def calculate_edge_cost(src: ZoneStatus, tgt: ZoneStatus, distance_meters: int) -> float:
    """
    Calculates dynamic traversal cost taking physical distance and crowd penalties into account.
    Base time assumes walking speed of ~1.4 m/s (approx 84m/min).
    Queue time: Add exponential delay based on crowd level if target is gate/concession.
    """
    base_time_mins = distance_meters / 84.0
    
    # Average crowd density over the path
    crowd_penalty_factor = (src.crowd_level + tgt.crowd_level) / 2.0
    
    # Exponential slowdown if crowded
    # 0% crowd -> multiplier 1x. 100% crowd -> multiplier (1 + 5) = 6x slower
    movement_multiplier = 1.0 + (crowd_penalty_factor ** 2) * 5.0
    
    traversal_time = base_time_mins * movement_multiplier
    
    # Add static queue delays for specific chokepoint types
    queue_delay = 0.0
    if tgt.type in ("gate", "concession"):
        queue_delay = tgt.crowd_level * 15.0 # Max 15 minutes queue delay
        
    return round(traversal_time + queue_delay, 2)

def find_fastest_route(
    topology: list[tuple[str, str, str, int]], 
    zone_map: Dict[str, ZoneStatus],
    start_id: str,
    target_id: str,
    avoid_congested: bool = False
) -> Dict:
    """
    Dijkstra's shortest path algorithm.
    Returns path of node IDs, human readable directions, and total estimated minutes.
    If `avoid_congested` is True, absolutely avoids node edges where crowd_level > 0.60
    """
    # Build adjacency list
    # Graph is bidirectional
    graph = {uid: [] for uid in zone_map.keys()}
    
    for src_id, tgt_id, label, dist in topology:
        if src_id not in zone_map or tgt_id not in zone_map:
            continue
            
        src_zone = zone_map[src_id]
        tgt_zone = zone_map[tgt_id]
        
        # Calculate cost in both directions
        cost_forward = calculate_edge_cost(src_zone, tgt_zone, dist)
        cost_backward = calculate_edge_cost(tgt_zone, src_zone, dist)
        
        if avoid_congested:
            if src_zone.crowd_level > 0.60 or tgt_zone.crowd_level > 0.60:
                cost_forward += 9999.0
                cost_backward += 9999.0

        graph[src_id].append((tgt_id, cost_forward))
        graph[tgt_id].append((src_id, cost_backward))
        
    # Dijkstra
    distances = {node: float('inf') for node in zone_map}
    distances[start_id] = 0
    previous_nodes = {node: None for node in zone_map}
    
    pq = [(0, start_id)]
    
    while pq:
        current_cost, current_node = heapq.heappop(pq)
        
        if current_node == target_id:
            break
            
        if current_cost > distances[current_node]:
            continue
            
        for neighbor, weight in graph[current_node]:
            distance = current_cost + weight
            if distance < distances[neighbor]:
                distances[neighbor] = distance
                previous_nodes[neighbor] = current_node
                heapq.heappush(pq, (distance, neighbor))
                
    # Reconstruct path
    path = []
    current = target_id
    while current is not None:
        path.append(current)
        current = previous_nodes[current]
        if current == start_id:
            path.append(start_id)
            break
            
    if start_id not in path:
        return {"path": [], "readable": "No available route.", "eta_mins": -1}
        
    path.reverse()
    
    # Generate human string
    readable_steps = " -> ".join([zone_map[nid].name for nid in path])
    eta_mins = round(distances[target_id])
    
    if avoid_congested and distances[target_id] > 5000:
        return {"path": [], "readable": "Could not find a route avoiding severe crowds.", "eta_mins": -1}
        
    return {
        "path": path,
        "readable": readable_steps,
        "eta_mins": eta_mins
    }

def generate_strategic_routes(topology: list, zone_map: Dict[str, ZoneStatus], destinations: List[str]) -> str:
    """Pre-calculates possibilities from Main Entrances to Destinations for the AI"""
    starts = ["gate_main", "gate_west"]
    
    report = []
    report.append("--- ALGORITHMIC NAVIGATION LOGIC ---")
    
    for end in destinations:
        if end not in zone_map: continue
        tgt_name = zone_map[end].name
        
        report.append(f"\\nDESTINATION: {tgt_name}")
        
        best_fastest = {"eta_mins": 9999, "readable": ""}
        best_clear = {"eta_mins": 9999, "readable": ""}
        
        for start in starts:
            if start not in zone_map: continue
            if start == end: continue
            
            fastest = find_fastest_route(topology, zone_map, start, end, avoid_congested=False)
            clear = find_fastest_route(topology, zone_map, start, end, avoid_congested=True)
            
            if fastest["eta_mins"] != -1 and fastest["eta_mins"] < best_fastest["eta_mins"]:
                best_fastest = fastest
            if clear["eta_mins"] != -1 and clear["eta_mins"] < best_clear["eta_mins"]:
                best_clear = clear
                
        report.append(f"1. Fastest Route (Regardless of Crowd): {best_fastest['readable']} (ETA: {best_fastest['eta_mins']} mins)")
        
        if best_clear['eta_mins'] != 9999:
            report.append(f"2. Least Crowded Route (Avoids bottlenecks): {best_clear['readable']} (ETA: {best_clear['eta_mins']} mins)")
        else:
            report.append("2. Least Crowded Route: Not physically possible (all access paths are currently jammed).")
            
    return "\\n".join(report)
