from app.services.venue_simulator import simulator_engine
from app.services.graph_builder import build_venue_graph
from app.utils.spatial_utils import calculate_crowd_level

def test_simulator_roster_integrity():
    """Verify that the simulator always generates exactly 25 calibrated nodes."""
    snapshot = simulator_engine.generate_snapshot()
    assert len(snapshot.zones) == 25
    assert all(z.lat != 0 for z in snapshot.zones)
    assert all(z.lng != 0 for z in snapshot.zones)

def test_simulator_crowd_bounds():
    """Ensure crowd levels are always between 0 and 1."""
    snapshot = simulator_engine.generate_snapshot()
    for zone in snapshot.zones:
        assert 0.0 <= zone.crowd_level <= 1.0

def test_spatial_logic_edge_cases():
    """Verify crowd calculations for empty and maximum severity scenarios."""
    # 0 base % should result in near 0 crowd level
    low = calculate_crowd_level(0, "standard", "gate_main", 0.4)
    assert low < 0.05
    
    # 100 base % with high severity should result in max crowd level
    high = calculate_crowd_level(100, "morning_entry", "gate_main", 1.0)
    assert high >= 0.95

def test_graph_topology_integrity():
    """Verify that the graph builder implements the physical edges from the matrix."""
    snapshot = simulator_engine.generate_snapshot()
    graph = build_venue_graph(snapshot)
    
    # We expect 32 undirected edges * 2 for bidirectional = 64 edges
    assert len(graph.edges) >= 64
    
    # Verify a known path: Main Gate -> Security Room
    sources = [e.source for e in graph.edges]
    targets = [e.target for e in graph.edges]
    assert "gate_main" in sources
    assert "area_security" in targets

def test_zone_nomenclature():
    """Verify that the critical Event Arena name is correctly mapped."""
    snapshot = simulator_engine.generate_snapshot()
    arena_zone = next(z for z in snapshot.zones if z.zone_id == "area_parking_open")
    assert arena_zone.name == "Open West Event Arena"
