# SmartVenue Intelligence Engine: System Manual
**Deep Technical Reference — v3.0 (Dijkstra Navigation + CORS Fix)**

This document is the authoritative technical reference for the SmartVenue platform — a production-grade Digital Twin of the HITEX Exhibition Center running on Google Cloud Run.

---

## 🏗️ 1. System Overview

SmartVenue is a real-time, AI-powered crowd intelligence platform. It integrates:
- A **physics-based crowd simulator** modeling 25 HITEX zones in real-time
- A **Dijkstra navigation engine** computing fastest walking routes using live congestion
- A **Gemini 2.5 Flash AI assistant** grounded in pre-computed route tables (not hallucinations)
- A **React frontend** showing live maps, D3 graphs, and an AI chatbot

### Core Data Flow:
```
SimulatorEngine (every 5s)
    │
    ├─→ WebSocket Broadcast (/api/ws/venue) → React Frontend
    │       └─→ Google Maps heatmap update
    │       └─→ D3 topology graph update
    │       └─→ WaitTimesSection sidebar update
    │
    ├─→ GraphBuilder → VenueGraph (nodes + edges + crowd weights)
    │       └─→ Dijkstra Engine → Pre-computed route table
    │               └─→ Gemini 2.5 Flash (temperature=0) → AI navigation
    │
    └─→ Supabase Persistence (every 30s, throttled)
```

---

## 🛠️ 2. File & Function Registry

### A. Navigation Intelligence

#### [`gemini_client.py`](./backend/app/services/gemini_client.py)
| Function | Description |
|---|---|
| `ask_gemini(message, venue_graph, fastest_routes, chat_history)` | Vertex AI Gemini 2.5 Flash chat session. Injects pre-computed Dijkstra route table into context. `temperature=0` for deterministic navigation. |
| `_build_routes_table(fastest_routes)` | Formats the Dijkstra output as a structured ASCII table for the AI prompt: From/To/ETA/Path/Bottlenecks |

#### [`graph_builder.py`](./backend/app/services/graph_builder.py)
| Function | Description |
|---|---|
| `build_venue_graph(snapshot)` | Transforms `VenueSnapshot` into `VenueGraph` with GPS-projected nodes and congestion-weighted edges |
| `dijkstra(graph, start_id)` | Dijkstra's shortest path from `start_id` to all reachable nodes. Cost = `(dist_m / 80.0) × (1 + weight² × 5.0)`. Mirrors Google Maps walking speed model. |
| `compute_all_fastest_routes(graph)` | Pre-computes Dijkstra from all 10 entry/parking nodes to all 10 destination halls. Returns sorted list of route dicts. |
| `graph_to_text_summary(graph)` | Converts VenueGraph to LLM-readable text: zone roster + adjacency map with walking times |

**Topology**: 32 directed edges across 25 nodes — calibrated to the Aug 2025 HITEX Blueprint.  
**Edge cost formula**: Walking speed degrades under congestion:
```python
speed_mult = 1.0 + (crowd_level ** 2) * 5.0
cost_minutes = (distance_meters / 80.0) * speed_mult
# At 0% crowd: 1x speed. At 100% crowd: 6x slower.
```

### B. Physical Simulation

#### [`venue_simulator.py`](./backend/app/services/venue_simulator.py)
| Component | Description |
|---|---|
| `SimulatorEngine` | Singleton. Manages 25-zone crowd state with Gravity Flow model. |
| `set_state(theme, situation, severity)` | Overrides simulation parameters (from `/api/simulate`). |
| `generate_snapshot()` | Produces a full `VenueSnapshot` including: crowd levels, particles (Gaussian scatter), zone status, trend (rising/falling/stable) |
| `THEME_MATRICES` | Dict of crowd density multipliers per zone for each event type (`hackathon`, `expo`, `marathon`, etc.) |

**Trend calculation**:
- `rising` → during `morning_entry`, `program_init`, `vip_entry`
- `falling` → during `closing`  
- `stable` → otherwise

#### [`main.py`](./backend/app/main.py)
| Component | Description |
|---|---|
| `lifespan()` | Background intelligence loop — runs `SimulatorEngine` every 5s, persists to Supabase every 30s |
| `venue_ws()` | WebSocket handler at `/api/ws/venue`. Uses `weakref.WeakSet` for zero-leak connection management |
| CORS | `allow_origins=["*"]` — permissive for hackathon; restrict to production URLs in prod |

### C. API Routers

#### [`chat.py`](./backend/app/routers/chat.py) — `/api/chat`
| Behavior | Notes |
|---|---|
| Auth | JWT-verified via `get_current_user` (Supabase JWKS) |
| Context | Builds VenueGraph + runs Dijkstra on every request — AI always has live route data |
| History | Fetches last 6 turns from Supabase for multi-turn memory |
| Persistence | Saves both user + assistant turns to Supabase asynchronously (non-blocking `create_task`) |

> **Previous CORS Bug (Fixed)**: The old chat.py used `with limiter.limit()` as a context manager — which is not a valid `slowapi` API (it's decorator-only). This crashed the endpoint before CORS headers were written, causing browser-side CORS errors. Fixed by removing the broken context manager.

#### [`zones.py`](./backend/app/routers/zones.py) — `/api/zones`, `/api/simulate`
| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/api/zones` | GET | ✅ | Returns full `VenueSnapshot` from cache |
| `/api/simulate` | POST | ✅ | Overrides simulation theme/situation/severity |

#### [`predict.py`](./backend/app/routers/predict.py) — `/api/predict`
- Runs ML inference (scikit-learn RandomForest) on a zone request
- Falls back to rule-based heuristic if model unavailable

#### [`maps.py`](./backend/app/routers/maps.py) — `/api/maps/*`
- `/api/maps/heatmap` — Returns GeoJSON FeatureCollection for Google Maps overlay
- `/api/maps/key` — Returns Maps API key for frontend initialization

### D. Authentication

#### [`auth.py`](./backend/app/services/auth.py)
| Feature | Details |
|---|---|
| JWKS | `PyJWKClient` with `cache_keys=True, lifespan=600` — fetches Supabase public signing keys |
| Algorithms | Supports both `ES256` (Supabase default) and `HS256` (legacy fallback) |
| Error Handling | `PyJWKClientConnectionError` → 401 (not 500). Network failure degrades gracefully. |

---

## 🧠 3. ML Prediction Engine

### Model
- **Algorithm**: RandomForest (scikit-learn)
- **File**: `backend/app/resources/wait_time_model.pkl` (434MB — **not in git**)
- **Download**: `gs://prompt-wars-493709-models/wait_time_model.pkl`
- **Features**: Zone type, theme, situation, crowd density, capacity ratio
- **Fallback**: Rule-based heuristic (`crowd_level × 15 minutes`) if model file absent

### Pipeline
```python
features = {
    "theme": theme,           # One-hot encoded
    "situation": situation,   # One-hot encoded
    "zone_type": zone_type,   # hall / gate / parking / etc.
    "crowd_level": 0.0–1.0,   # Live from simulator
    "current_count": int,
    "capacity": int,
}
→ pd.DataFrame → model.predict() → wait_time_minutes
```

---

## 🗺️ 4. Frontend Architecture

### Real-Time Data Flow
```
WebSocket onmessage → setSnapshot(data)
    │
    ├─→ MapSection     → Updates heatmap + zone popups
    ├─→ GraphSection   → D3 General Update Pattern (keyed nodes/edges)
    ├─→ WaitTimesSection → Sidebar cards (zero extra HTTP calls)
    └─→ SimulatorConsole → Theme/Severity selector → POST /api/simulate
```

### Key Components

| Component | File | Role |
|---|---|---|
| `App.tsx` | `src/App.tsx` | Root: WebSocket manager + auth guard |
| `MapSection` | `components/MapSection.tsx` | Google Maps 3D + heatmap + zone InfoWindows |
| `GraphSection` | `components/GraphSection.tsx` | D3 force graph — live topology animation |
| `WaitTimesSection` | `components/WaitTimesSection.tsx` | Sidebar analytics — props-driven, no HTTP calls |
| `SimulatorConsole` | `components/SimulatorConsole.tsx` | Theme/situation/severity control bar |
| `ChatWidget` | `components/ChatWidget.tsx` | Gemini navigation assistant chat UI |

### ⚠️ Security Note: Anon Key vs Service Role Key
The frontend **must** use the `anon` Supabase key, never `service_role`.  
- `anon` key: respects Row Level Security (RLS) — safe for browsers
- `service_role` key: bypasses ALL RLS — would give any user full database access

---

## ☁️ 5. Production Infrastructure

### Cloud Run Services
| Service | Revision | Region | RAM | vCPU |
|---|---|---|---|---|
| `smartvenue-backend` | `00008-xj6` | us-central1 | 4GiB | 4 |
| `smartvenue-frontend` | `00014-cmh` | us-central1 | 512MiB | 1 |

### Backend Configuration
- **Session Affinity**: Client IP — prevents WebSocket handshake failures during reconnects
- **Timeout**: 3600s — enables persistent "forever connections" for telemetry streaming
- **WebSocket Heartbeat**: 20s ping — keeps idle connections alive through Cloud Run's 60s idle limit
- **Min Instances**: 1 — keeps the 434MB model warm, avoids 5s cold start

### Secrets Management
Secrets are injected as **Cloud Run environment variables** at deploy time:
```powershell
gcloud run deploy smartvenue-backend \
  --set-env-vars="SUPABASE_URL=...,SUPABASE_KEY=...,SUPABASE_JWT_SECRET=...,GOOGLE_CLOUD_PROJECT=..."
```
**Never** commit secrets to git. Use `.env.example` as templates.

---

## 🔒 6. Security Audit

### ✅ Fixes Applied (v3.0)
| Issue | Status | Fix |
|---|---|---|
| CORS error on `/api/chat` | ✅ Fixed | Removed broken `with limiter.limit()` context manager + fixed `NameError` for `t0` |
| `service_role` key in frontend `.env.development` | ✅ Fixed | Replaced with `anon` key |
| 434MB model in git history | ✅ Fixed | `git filter-repo --invert-paths` + `*.pkl` in `.gitignore` |
| JWT JWKS failure → 500 | ✅ Fixed | `PyJWKClientConnectionError` now returns 401 |
| `auto_expo` theme mismatch | ✅ Fixed | Removed duplicate, uses valid `expo` ID |

### ✅ Ongoing Protections
- `.gitignore` excludes all `.env*`, `*.pkl`, `*.json` data files
- HSTS, CSP, X-Frame-Options on all responses
- Rate limiting: 20 req/min on `/api/chat` (per IP)
- JWT verification with JWKS key rotation support

---

## 🧪 7. Verification

```bash
# Health check all subsystems
curl https://smartvenue-backend-623281650123.us-central1.run.app/health

# Expected response:
# {"status":"ok","subsystems":{"database":"ok","simulator":"ok","prediction_model":"ok"}}
```

```bash
# Test WebSocket (wsscat or websocat)
websocat wss://smartvenue-backend-623281650123.us-central1.run.app/api/ws/venue
# Should receive JSON snapshots every ~5 seconds
```

---

*SmartVenue Intelligence Engine — HITEX Digital Twin | Gemini Prompt Wars 2025 🦾🏁*
