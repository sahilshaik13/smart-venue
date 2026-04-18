import asyncio
import time
import weakref
import structlog
from contextlib import asynccontextmanager
from typing import List, Set
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
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

log = structlog.get_logger(__name__)
limiter = Limiter(key_func=get_remote_address)

# ── Connection Manager for Real-time Streams ──────────────────
class ConnectionManager:
    def __init__(self):
        # Use WeakSet so dead connections are auto-garbage-collected
        self.active_connections: Set[WebSocket] = weakref.WeakSet()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        log.info("websocket_connected", count=len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            log.info("websocket_disconnected", count=len(self.active_connections))

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                # Broken pipe or connection lost
                self.active_connections.discard(connection)

manager = ConnectionManager()

# ── Background Intelligence Task ──────────────────────────────
async def venue_intelligence_loop():
    """ Periodic data generation, broadcast, and persistence. """
    iteration = 0
    while True:
        try:
            # Generate new frame using the shared Singleton Engine
            snapshot = simulator_engine.generate_snapshot()
            snapshot_dict = jsonable_encoder(snapshot)
            
            if _cache:
                await _cache.set("venue_snapshot", snapshot)
            
            # LIVE BROADCAST - Always every 5s
            await manager.broadcast({
                "type": "SNAPSHOT_UPDATE",
                "data": snapshot_dict
            })
            
            # PERSISTENCE THROTTLE - Every 30s (iteration % 6 == 0)
            if iteration % 6 == 0:
                await save_zone_snapshot(snapshot_dict)
                log.info("supabase_persistence_synced", timestamp=snapshot.snapshot_time)
            
            iteration += 1
            
        except Exception as e:
            log.error("intelligence_loop_error", error=str(e))
            
        await asyncio.sleep(5)  # 5-second interval for live broadcast

# ── Startup/Shutdown ──────────────────────────────────────────
_start_time = time.time()
_cache: AsyncTTLCache | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _cache
    _cache = AsyncTTLCache()
    app.state.cache = _cache
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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── WebSocket Endpoint ────────────────────────────────────────
@app.websocket("/api/ws/venue")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # 1. Send the current ground-truth as initial state
        initial = simulator_engine.generate_snapshot()
        await websocket.send_json({"type": "SNAPSHOT_UPDATE", "data": jsonable_encoder(initial)})
        
        while True:
            # Keep connection open
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

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
