# SmartVenue Intelligence Engine: System Manual

This document provides a 360-degree technical overview of the **SmartVenue Intelligence Engine**, a high-fidelity "Digital Twin" of the HITEX Exhibition Center. 

---

## 🏗️ 1. System Overview
The SmartVenue engine is a real-time autonomous simulation and navigation platform. It synchronizes a physical simulation engine (modeling crowd flow) with a Graph-based AI Assistant (reasoning over venue topology).

### Core Workflow:
1.  **Simulation Loop**: The `SimulatorEngine` generates a state frame every 5 seconds.
2.  **Broadcast**: New frames are pushed to all clients via WebSockets (`/api/ws/venue`).
3.  **Knowledge Mapping**: The `GraphBuilder` transforms the live frame into a structured text-based knowledge graph.
4.  **AI Reasoning**: The `GeminiClient` uses the live knowledge graph to calculate the fastest path based on real-time congestion.

---

## 🛠️ 2. File & Function Registry

### A. Intelligence & Navigation
*   **[`gemini_client.py`](file:///d:/promptwars/backend/app/services/gemini_client.py)**:
    *   `ask_gemini(...)`: Initializes a **Native Chat Session** with `gemini-2.5-flash`.
    *   **Async Stability**: Uses non-blocking `asyncio.sleep` for retries.
    *   **Deterministic Thinking**: Set to `temperature=0.0` for clinical pathfinding.
*   **[`graph_builder.py`](file:///d:/promptwars/backend/app/services/graph_builder.py)**:
    *   `build_venue_graph(...)`: Maps nodes to a 32-edge adjacency matrix based on the Aug 2025 blueprint.
    *   **GPS Projection**: Performs Lat/Lng to 2D Canvas mapping with zero offset.

### B. Physical Simulation
*   **[`venue_simulator.py`](file:///d:/promptwars/backend/app/services/venue_simulator.py)**:
    *   `SimulatorEngine`: Singleton managing the 25-node roster.
    *   **Gaussian Scattering**: Implements the "4% = 1 Dot" rule with stable jitter to prevent visual jumping.
*   **[`main.py`](file:///d:/promptwars/backend/app/main.py)**:
    *   **Concurrency**: Uses `weakref.WeakSet` for WebSocket management to prevent memory leaks.
    *   **Persistence Throttle**: Broadcasts every 5s, but persists to Supabase every **30s** to optimize database IO.

### C. Data & Infrastructure
*   **[`maps.py`](file:///d:/promptwars/backend/app/routers/maps.py)**:
    *   `/api/maps/heatmap`: Returns a GeoJSON FeatureCollection with live congestion weights for mapping overlays.

---

## 🧪 3. Technical Hardening (Audit)

### ✅ The Good (Strengths)
1.  **Memory Efficiency**: The WeakSet connection manager ensures dead sockets are cleaned instantly.
2.  **Security Boundaries**: Hardened middleware injects HSTS, CSP, and X-Frame headers.
3.  **Topology locking**: The 32-edge manual matrix eliminates all AI pathfinding hallucinations.

### ⚠️ The Risks (Future Dev)
1.  **Vertex AI Latency**: Cold-start spikes (2-3s) remain a risk during low-traffic periods.
2.  **Global Limiter**: The `slowapi` limiter is memory-backed; for multi-instance deployment, this must move to Redis.
