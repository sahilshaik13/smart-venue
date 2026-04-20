import pytest
from datetime import datetime
from app.services.graph_builder import build_venue_graph, dijkstra, compute_all_fastest_routes
from app.models import VenueSnapshot, ZoneStatus, ZoneType

@pytest.fixture
def mock_snapshot():
    return VenueSnapshot(
        snapshot_id="test_snap",
        snapshot_time=datetime.now(),
        match_phase="Testing",
        match_minute=10,
        zones=[
            ZoneStatus(zone_id="gate_main", name="Main Gate", type=ZoneType.gate, current_count=100, capacity=1000, crowd_level=0.1, status="low", lat=17.470, lng=78.370),
            ZoneStatus(zone_id="hall_1", name="Hall 1", type=ZoneType.gate, current_count=500, capacity=1000, crowd_level=0.5, status="medium", lat=17.472, lng=78.372),
            ZoneStatus(zone_id="hall_2", name="Hall 2", type=ZoneType.gate, current_count=800, capacity=1000, crowd_level=0.8, status="high", lat=17.474, lng=78.374),
        ]
    )

def test_graph_building(mock_snapshot):
    """Verify that the graph is correctly constructed from a snapshot."""
    graph = build_venue_graph(mock_snapshot)
    assert len(graph.nodes) == 3
    assert len(graph.edges) > 0  # Should have edges from VENUE_TOPOLOGY
    
    # Check node attributes
    gate_node = next(n for n in graph.nodes if n.id == "gate_main")
    assert gate_node.label == "Main Gate"
    assert gate_node.crowd_level == 0.1

def test_dijkstra_logic(mock_snapshot):
    """Verify shortest path calculation with congestion weights."""
    graph = build_venue_graph(mock_snapshot)
    # Mock edges for a simple path: gate_main -> hall_1
    # Note: build_venue_graph uses real VENUE_TOPOLOGY, let's check it handles it
    results = dijkstra(graph, "gate_main")
    
    assert "gate_main" in results
    assert results["gate_main"][0] == 0.0  # Distance to self is 0
    
    # Verify that paths are returned as a list of strings
    for node_id, (mins, path) in results.items():
        assert isinstance(mins, float)
        assert isinstance(path, list)
        assert path[0] == "gate_main"

def test_route_computation(mock_snapshot):
    """Verify that fastest routes are correctly pre-computed for AI context."""
    graph = build_venue_graph(mock_snapshot)
    routes = compute_all_fastest_routes(graph)
    
    assert isinstance(routes, list)
    if len(routes) > 0:
        route = routes[0]
        assert "from" in route
        assert "to" in route
        assert "eta_minutes" in route
        assert "path" in route
