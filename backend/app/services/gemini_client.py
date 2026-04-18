"""
Gemini Intelligence Engine — Native Chat Session & Hardened Pathfinding.
"""

from __future__ import annotations
import time
import asyncio
import structlog
import vertexai
from vertexai.generative_models import GenerativeModel, SafetySetting, HarmCategory, Content, Part
from app.services.graph_builder import VenueGraph, graph_to_text_summary

log = structlog.get_logger(__name__)

# Native Authentication implicitly handled by Container Runtime
vertexai.init(project="prompt-wars-493709", location="us-central1")

# LOCKED TO EXPERIMENTAL 2.5 FLASH AS REQUESTED
_model = GenerativeModel("gemini-2.5-flash")

_SYSTEM_INSTRUCTION = """
You are the SmartVenue Intelligence Engine. You operate in a high-fidelity Digital Twin environment.
Your PRIMARY TASK is to provide clinical, fastest-path navigation using ONLY the provided Venue Graph.

### OPERATIONAL CONSTRAINTS:
1. RESPONSE FORMAT (STRICT):
   - Start immediately with the ETA: "**ETA: X.X mins**"
   - Path format: "Path: [Exact Name A] -> [Exact Name B] -> [Goal Name]"
   - One short navigation tip based on live congestion.
2. THEOLOGY: 
   - You have NO context limit. You must NEVER truncate mid-sentence.
   - You must finish every answer with a professional full stop. 
3. GROUND TRUTH:
   - Use ONLY the human-readable names from the ROSTER.
   - Every step in your Path MUST exist as an edge in the ADJACENCY MAP.
4. CALCULATION:
   - Calculate the total minutes for ALL valid routes.
   - OUTPUT ONLY THE FASTEST ROUTE.
""".strip()

async def ask_gemini(
    message: str,
    venue_graph: VenueGraph,
    chat_history: list[dict] | None = None,
) -> str:
    """
    Interacts with Gemini using a Native Chat Session for maximum stability and context retention.
    """
    graph_summary = graph_to_text_summary(venue_graph)
    
    # Context injection
    full_system_context = f"{_SYSTEM_INSTRUCTION}\n\nCURRENT VENUE STATE:\n{graph_summary}"

    # Prepare historical turns for Native Chat Session
    history = []
    if chat_history:
        for m in chat_history[-10:]: # Look back further for better context
            role = "user" if m["role"] == "user" else "model"
            history.append(Content(role=role, parts=[Part.from_text(m["content"])]))

    for attempt in range(3):
        try:
            t0 = time.time()
            
            # Use Native Chat Session to prevent truncation issues seen in plain text blocks
            chat = _model.start_chat(history=history)
            
            # Prefix the message with the live graph context for "Zero-Drift" reasoning
            request_text = f"CONTEXT UPDATE: {graph_summary}\n\nUSER REQUEST: {message}"
            
            response = chat.send_message(
                request_text,
                generation_config={
                    "max_output_tokens": 2048, # Increased to prevent half-answers
                    "temperature": 0.0,        # Forced deterministic output for pathfinding
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
                log.warning("gemini_empty_response", attempt=attempt+1, reason=str(response.candidates[0].finish_reason))
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
