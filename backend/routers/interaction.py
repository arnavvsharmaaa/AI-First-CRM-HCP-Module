from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.database import async_session
from models.hcp import HCP
from schemas.interaction import ChatRequest
from websocket_manager import manager
import asyncio

router = APIRouter()

async def get_db():
    async with async_session() as session:
        yield session

from agent.graph import graph
from langchain_core.messages import HumanMessage
import json

@router.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    async def process_message():
        print(f"--- New Chat Request ---")
        print(f"Session ID: {request.session_id}")
        print(f"Message: {request.message}")

        # Notify frontend that AI is thinking
        await manager.broadcast_to_session(request.session_id, {
            "type": "thinking",
            "value": True
        })

        try:
            initial_state = {
                "messages": [HumanMessage(content=request.message)],
                "session_id": request.session_id,
                "interaction_id": None,
                "form_updates": []
            }

            print("Invoking LangGraph agent...")
            result = await graph.ainvoke(initial_state)
            print(f"Graph invocation complete. Result keys: {result.keys()}")

            messages = result.get("messages", [])
            print(f"Processing {len(messages)} messages from graph output...")

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
                print(f"Checking message of type: {m.type}")
                if m.type != "tool":
                    # Capture the last AI text message as fallback reply
                    if m.type == "ai" and hasattr(m, "content") and isinstance(m.content, str) and m.content:
                        merged_ai_message = m.content
                    continue

                # --- Parse tool message content ---
                content = m.content
                print(f"Tool content type: {type(content)}")

                if isinstance(content, str):
                    try:
                        tool_data = json.loads(content)
                    except Exception as parse_err:
                        print(f"Could not parse tool content as JSON: {parse_err}, raw: {content[:200]}")
                        tool_data = content
                else:
                    tool_data = content

                print(f"Parsed tool data: {tool_data}")

                if not isinstance(tool_data, dict):
                    print("Tool data is not a dict — skipping.")
                    continue

                if tool_data.get("type") != "form_update":
                    print(f"Tool data type is '{tool_data.get('type')}' (not form_update) — skipping.")
                    continue

                print("Found form_update from tool — merging fields...")

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

                print(f"Broadcasting merged form_update — fields: {list(merged_fields.keys())}")
                await manager.broadcast_to_session(request.session_id, payload)
            else:
                print("No form_update fields found in any tool message. Broadcasting default AI message.")
                await manager.broadcast_to_session(request.session_id, {
                    "type": "form_update",
                    "fields": {},
                    "ai_message": merged_ai_message,
                    "aiSuggestedFollowups": []
                })

        except Exception:
            import traceback
            print("!!! Error in agent processing !!!")
            traceback.print_exc()

        print("Agent processing complete. Sending thinking=false")
        await manager.broadcast_to_session(request.session_id, {
            "type": "thinking",
            "value": False
        })

    # Fire-and-forget so the HTTP response returns immediately
    asyncio.create_task(process_message())

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
