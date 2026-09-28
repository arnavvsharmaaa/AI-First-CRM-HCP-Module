from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.database import async_session
from models.hcp import HCP
from schemas.interaction import ChatRequest
from websocket_manager import manager
import asyncio
import logging
import re

# Configure file logging
logging.basicConfig(
    level=logging.INFO,
    filename='debug.log',
    format='%(asctime)s - %(message)s'
)
logger = logging.getLogger(__name__)

print("=== interaction.py module loaded ===")
logger.info("=== interaction.py module loaded ===")

router = APIRouter()

async def get_db():
    async with async_session() as session:
        yield session

from agent.graph import graph
from langchain_core.messages import HumanMessage
import json

def _exception_chain(exc: BaseException) -> str:
    """'TypeA: msg <- TypeB: msg <- ...' following __cause__/__context__."""
    parts, seen = [], set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        # Redact credentials — e.g. httpx echoes a rejected Authorization header
        msg = re.sub(r"Bearer(\s|\n)*[^\s'\"]+", "Bearer [redacted]", str(exc))
        msg = re.sub(r"gsk_[A-Za-z0-9]+", "gsk_[redacted]", msg)
        parts.append(f"{type(exc).__module__}.{type(exc).__name__}: {msg[:200]}")
        exc = exc.__cause__ or exc.__context__
    return " <- ".join(parts)


@router.get("/api/test")
async def test_endpoint():
    print("=== TEST ENDPOINT HIT ===")
    return {"status": "test_ok"}

@router.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    logger.info(f"=== HTTP POST /api/chat received ===")
    logger.info(f"Session ID: {request.session_id}")
    logger.info(f"Message: {request.message}")
    logger.info(f"Interaction ID: {request.interaction_id}")
    print(f"=== HTTP POST /api/chat received ===", flush=True)
    print(f"Session ID: {request.session_id}", flush=True)
    print(f"Message: {request.message}", flush=True)
    
    # Temporarily make it synchronous for debugging
    print(f"--- New Chat Request ---", flush=True)
    print(f"Session ID: {request.session_id}", flush=True)
    print(f"Message: {request.message}", flush=True)

    # Notify frontend that AI is thinking
    await manager.broadcast_to_session(request.session_id, {
        "type": "thinking",
        "value": True
    })

    try:
        initial_state = {
            "messages": [HumanMessage(content=request.message)],
            "session_id": request.session_id,
            "interaction_id": request.interaction_id,
            "form_updates": []
        }

        print("Invoking LangGraph agent...", flush=True)
        result = await graph.ainvoke(initial_state)
        print(f"Graph invocation complete. Result keys: {result.keys()}", flush=True)

        messages = result.get("messages", [])
        print(f"Processing {len(messages)} messages from graph output...", flush=True)

        # ----------------------------------------------------------------
        # Collect form_update payloads from EVERY tool message.
        # We iterate forward (chronological order) so that later tool
        # results (e.g. suggest_followups) can extend — not overwrite —
        # earlier ones (e.g. log_interaction).
        # ----------------------------------------------------------------
        merged_fields: dict = {}
        merged_ai_message: str = "I've processed your request."
        merged_interaction_id: str | None = None

        for m in messages:
            print(f"Checking message of type: {m.type}", flush=True)
            if m.type != "tool":
                # Capture the last AI text message as fallback reply
                if m.type == "ai" and hasattr(m, "content") and isinstance(m.content, str) and m.content:
                    merged_ai_message = m.content
                continue

            # --- Parse tool message content ---
            content = m.content
            print(f"Tool content type: {type(content)}", flush=True)

            if isinstance(content, str):
                try:
                    tool_data = json.loads(content)
                except Exception as parse_err:
                    print(f"Could not parse tool content as JSON: {parse_err}, raw: {content[:200]}", flush=True)
                    tool_data = content
            else:
                tool_data = content

            print(f"Parsed tool data: {tool_data}", flush=True)

            if not isinstance(tool_data, dict):
                print("Tool data is not a dict — skipping.", flush=True)
                continue

            if tool_data.get("type") != "form_update":
                print(f"Tool data type is '{tool_data.get('type')}' (not form_update) — skipping.", flush=True)
                continue

            print("Found form_update from tool — merging fields...", flush=True)

            # Merge fields (later tools extend, not overwrite, existing keys
            # unless they provide a non-empty value)
            incoming_fields = tool_data.get("fields", {})
            for key, value in incoming_fields.items():
                # Only overwrite if the incoming value is non-empty / non-null
                if value is not None and value != "" and value != []:
                    merged_fields[key] = value
                elif key not in merged_fields:
                    # Still capture it if we have nothing yet
                    merged_fields[key] = value

            # Keep the most informative AI message
            if tool_data.get("ai_message"):
                merged_ai_message = tool_data["ai_message"]

            # Capture interaction_id if present
            if tool_data.get("interaction_id") and not merged_interaction_id:
                merged_interaction_id = tool_data["interaction_id"]

        # ----------------------------------------------------------------
        # Broadcast a single, merged form_update to the frontend
        # ----------------------------------------------------------------
        if merged_fields:
            payload = {
                "type": "form_update",
                "fields": merged_fields,
                "ai_message": merged_ai_message,
            }
            if merged_interaction_id:
                payload["interaction_id"] = merged_interaction_id

            print(f"Broadcasting merged form_update — fields: {list(merged_fields.keys())}", flush=True)
            await manager.broadcast_to_session(request.session_id, payload)
        else:
            print("No form_update fields found in any tool message. Broadcasting default AI message.", flush=True)
            await manager.broadcast_to_session(request.session_id, {
                "type": "form_update",
                "fields": {},
                "ai_message": merged_ai_message,
                "aiSuggestedFollowups": []
            })

    except Exception as exc:
        import traceback
        print("!!! Error in agent processing !!!", flush=True)
        traceback.print_exc()
        # One-line summary of the whole cause chain — log viewers often cut long tracebacks
        print(f"AGENT ERROR CHAIN: {_exception_chain(exc)}", flush=True)

        # Tell the user instead of silently dropping the reply
        await manager.broadcast_to_session(request.session_id, {
            "type": "form_update",
            "fields": {},
            "ai_message": "⚠️ Sorry, the AI service is unavailable right now, so I couldn't process that. Please try again in a moment."
        })

    print("Agent processing complete. Sending thinking=false", flush=True)
    await manager.broadcast_to_session(request.session_id, {
        "type": "thinking",
        "value": False
    })
    
    return {"status": "ok"}


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    try:
        while True:
            # Keep connection alive; listen for any client messages
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)


@router.get("/api/hcps/search")
async def search_hcps(q: str = "", db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(HCP).where(HCP.name.ilike(f"%{q}%")))
    hcps = result.scalars().all()
    return [{"id": str(hcp.id), "name": hcp.name, "specialty": hcp.specialty} for hcp in hcps]
