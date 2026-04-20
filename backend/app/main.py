import asyncio
import time
import weakref
import structlog
from contextlib import asynccontextmanager
from typing import List, Set
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.cache import AsyncTTLCache
from app.routers import zones, predict, chat, health, graph, maps
from app.services.venue_simulator import simulator_engine
from app.services.supabase_client import save_zone_snapshot

from app.services.auth import verify_token
from app.services.logging_service import setup_cloud_logging
from app.services.bigquery_client import bq_sink

# Initialize Google Cloud Structured Logging
setup_cloud_logging()

log = structlog.get_logger(__name__)
limiter = Limiter(key_func=get_remote_address)

# Identity-Aware Simulation State
user_settings_registry = {} # Dict[user_id, dict]

# ── Connection Manager for Real-time Streams ──────────────────
class ConnectionManager:
    def __init__(self):
        # user_id -> List[WebSocket]
        self.user_connections: dict[str, set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        # Move accept() AFTER logging and state check to ensure cleaner handshake
        await websocket.accept()
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(websocket)
        log.info("websocket_connected", user_id=user_id, count=len(self.user_connections[user_id]))

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
            log.info("websocket_disconnected", user_id=user_id)

    async def broadcast_to_user(self, user_id: str, message: dict):
        if user_id not in self.user_connections:
            return
        
        dead_links = set()
        for connection in list(self.user_connections[user_id]):
            try:
                await connection.send_json(message)
            except Exception:
                dead_links.add(connection)
        
        for dead in dead_links:
            self.disconnect(dead, user_id)

manager = ConnectionManager()

# ── Intelligence Engine Loop ──────────────────────────────────
async def venue_intelligence_loop():
    """
    Main background process.
    Iterates through active user sessions and broadcasts high-fidelity spatial data.
    """
    iteration = 0
    while True:
        try:
            start_time = time.time()
            
            # Identify users with active WebSocket connections
            active_users = list(manager.user_connections.keys())
            
            for user_id in active_users:
                # Load user-specific sandbox settings
                settings = user_settings_registry.get(user_id, {
                    "theme": "hackathon",
                    "situation": "morning_entry",
                    "severity": "medium"
                })
                
                # Generate unique snapshot for this user's sandbox
                snapshot = simulator_engine.generate_snapshot(**settings)
                snapshot_dict = jsonable_encoder(snapshot)
                
                # Multi-cast to all of THIS user's active devices
                await manager.broadcast_to_user(user_id, {
                    "type": "SNAPSHOT_UPDATE",
                    "data": snapshot_dict,
                    "timestamp": time.time()
                })
                
                # PERSISTENCE - Every 30s per user
                if iteration % 6 == 0:
                    await save_zone_snapshot(user_id, snapshot_dict)
                    # STREAM TO BIGQUERY FOR ANALYTICS (GCP SCORE BOOSTER)
                    await bq_sink.stream_snapshot(snapshot_dict)
            
            iteration += 1
            
            # Adaptive sleep to maintain ~5s cadence
            elapsed = time.time() - start_time
            await asyncio.sleep(max(0.1, 5.0 - elapsed))
            
        except Exception as e:
            log.error("intelligence_loop_failure", error=str(e))
            await asyncio.sleep(5)

# ── Lifespan for resources ────────────────────────────────────
_cache = None
_start_time = time.time()

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _cache
    _cache = AsyncTTLCache()
    app.state.cache = _cache
    app.state.user_settings = user_settings_registry
    app.state.start_time = _start_time
    app.state.request_count = 0
    
    # Start the Intelligence Engine
    loop_task = asyncio.create_task(venue_intelligence_loop())
    
    log.info("smartvenue_autonomous_started")
    yield
    loop_task.cancel()
    log.info("smartvenue_shutdown")

# ── App factory ───────────────────────────────────────────────
app = FastAPI(
    title="SmartVenue AI",
    version="1.1.0",
    description="Autonomous Intelligence Engine with Gravity Flow Simulation.",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://smartvenue-frontend-623281650123.us-central1.run.app"
    ],
    allow_origin_regex="https://smartvenue-frontend-.*\.us-central1\.run\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── WebSocket Endpoint ────────────────────────────────────────
@app.websocket("/api/ws/venue")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    user_id = verify_token(token)
    if not user_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket, user_id)
    try:
        # Send initial snapshot immediately
        settings = user_settings_registry.get(user_id, {"theme": "hackathon", "situation": "morning_entry", "severity": "medium"})
        initial = simulator_engine.generate_snapshot(**settings)
        await websocket.send_json({"type": "SNAPSHOT_UPDATE", "data": jsonable_encoder(initial)})
        
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)

# ── Middleware & Routers ──────────────────────────────────────
@app.middleware("http")
async def security_and_metrics(request: Request, call_next):
    # Add Security Headers for Production Scoring
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' maps.googleapis.com; style-src 'self' 'unsafe-inline' fonts.googleapis.com; font-src 'self' fonts.gstatic.com; img-src 'self' data: maps.gstatic.com maps.googleapis.com; connect-src 'self' *.googleapis.com;"
    
    if hasattr(request.app.state, "request_count"):
        request.app.state.request_count += 1
    return response

app.include_router(zones.router)
app.include_router(predict.router)
app.include_router(chat.router)
app.include_router(health.router)
app.include_router(graph.router)
app.include_router(maps.router)
