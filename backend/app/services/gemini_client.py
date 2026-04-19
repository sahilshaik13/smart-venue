"""
Gemini Intelligence Engine — Two-Phase Navigation with Alias Resolution.
"""

from __future__ import annotations
import time
import asyncio
import structlog
import vertexai
from vertexai.generative_models import GenerativeModel, SafetySetting, HarmCategory, Content, Part
from app.services.graph_builder import VenueGraph, graph_to_text_summary, build_alias_context

log = structlog.get_logger(__name__)

# Native Authentication via Container Runtime (Application Default Credentials)
vertexai.init(project="prompt-wars-493709", location="us-central1")

_model = GenerativeModel("gemini-2.5-flash")

_SYSTEM_INSTRUCTION = """
You are the SmartVenue Intelligence Engine — a real-time venue navigator for the HITEX Exhibition Center.

### TWO-PHASE REASONING (ALWAYS FOLLOW THESE STEPS):

**PHASE 1 — RESOLVE USER INTENT:**
The user may use informal names. Use the ALIAS MAP below to resolve their words to canonical zone names FIRST.
Examples:
- "restaurant" / "food" / "eat" / "cafe" → Aeros Restaurant
- "hall 4" / "main expo" / "main hall" / "main event" → Hall 4 (Main Expo)
- "vip" / "vip arrival" → VIP Pre-Event Area
- "parking" → Parking P1
- "lake" / "lakeside" → Hitex Lake
NEVER say "I cannot find" — if the user's term is close to any alias, resolve it and proceed.

**PHASE 2 — LOOK UP & EXPLAIN:**
Find the route in the PRE-COMPUTED ROUTES TABLE that matches the resolved origin → destination.
Then respond in a friendly, human-readable paragraph:
- Bold the ETA: **🧭 ETA: X.X mins**
- Describe the path step by step in plain English (not just arrow notation)
- Mention any HIGH or CRITICAL zones on the path with a practical tip to avoid delays
- End with a short helpful sentence

### RULES:
- Use human-readable names from the ZONE ROSTER (never internal IDs like "hall_4" or "area_aeros")
- ETAs come ONLY from the PRE-COMPUTED ROUTES TABLE — never estimate yourself
- For status questions: use 🟢 LOW | 🟡 MEDIUM | 🟠 HIGH | 🔴 CRITICAL
- Keep answers concise. Always end with a full stop.
""".strip()


def _build_routes_table(fastest_routes: list[dict]) -> str:
    """Formats pre-computed Dijkstra routes as a readable table for the AI."""
    if not fastest_routes:
        return "No routes available."

    lines = ["PRE-COMPUTED FASTEST ROUTES (Dijkstra, live congestion-weighted):"]
    lines.append(f"{'From':<26} → {'To':<26} | {'ETA':>5} | Path | Status")
    lines.append("-" * 140)

    for r in fastest_routes:
        bottleneck_str = ", ".join(r["bottlenecks"]) if r["bottlenecks"] else "CLEAR ✅"
        status = "✅" if r["is_clear"] else "⚠️"
        lines.append(
            f"{r['from']:<26} → {r['to']:<26} | {r['eta_minutes']:>5.1f}m | {r['path']} | {status} {bottleneck_str}"
        )
    return "\n".join(lines)


async def ask_gemini(
    message: str,
    venue_graph: VenueGraph,
    fastest_routes: list[dict] | None = None,
    chat_history: list[dict] | None = None,
) -> str:
    """
    Two-phase Gemini navigation:
    1. Alias resolution (natural language → canonical zone names)
    2. Route lookup + human-readable explanation
    """
    graph_summary = graph_to_text_summary(venue_graph)
    routes_table = _build_routes_table(fastest_routes or [])
    alias_context = build_alias_context()

    # Full context: alias map + live zone state + pre-computed routes
    full_context = f"""{_SYSTEM_INSTRUCTION}

====================================================================
{alias_context}

====================================================================
CURRENT VENUE STATE:
{graph_summary}

====================================================================
{routes_table}
===================================================================="""

    # Prepare historical turns for Native Chat Session
    history = []
    if chat_history:
        for m in chat_history[-10:]:
            role = "user" if m["role"] == "user" else "model"
            history.append(Content(role=role, parts=[Part.from_text(m["content"])]))

    for attempt in range(3):
        try:
            t0 = time.time()

            # Native Chat Session — preserves multi-turn context
            chat = _model.start_chat(history=history)

            # Inject full live context on every request (zero-drift reasoning)
            request_text = f"LIVE VENUE UPDATE:\n{full_context}\n\n---\nUSER: {message}"

            response = chat.send_message(
                request_text,
                generation_config={
                    "max_output_tokens": 2048,
                    "temperature": 0.0,   # Deterministic — critical for accurate ETAs
                    "top_p": 1.0,
                    "top_k": 1
                },
                safety_settings=[
                    SafetySetting(category=c, threshold=SafetySetting.HarmBlockThreshold.BLOCK_NONE)
                    for c in [
                        HarmCategory.HARM_CATEGORY_HARASSMENT,
                        HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT
                    ]
                ]
            )

            if not response.candidates or not response.candidates[0].content.parts:
                log.warning(
                    "gemini_empty_response",
                    attempt=attempt + 1,
                    reason=str(response.candidates[0].finish_reason)
                )
                continue

            reply = response.text.strip()
            latency_ms = int((time.time() - t0) * 1000)

            log.info(
                "intelligence_engine_success",
                latency_ms=latency_ms,
                finish_reason=str(response.candidates[0].finish_reason)
            )
            return reply

        except Exception as exc:
            wait_s = 2 ** attempt
            log.warning("intelligence_engine_retry", attempt=attempt + 1, error=str(exc))
            if attempt < 2:
                await asyncio.sleep(wait_s)

    return "The Intelligence Engine is temporarily unavailable. Please standby for synchronization."
