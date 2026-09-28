from typing import Annotated, Optional
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.prebuilt import InjectedState
import json
import os
import uuid
from models.database import async_session
from models.interaction import Interaction
from sqlalchemy import update

EDITABLE_FIELDS = {
    "hcpName", "interactionType", "date", "time", "attendees",
    "topicsDiscussed", "materialsShared", "samplesDistributed", "sentiment",
    "outcomes", "followUpActions",
}

@tool
async def edit_interaction(
    input: str,
    interaction_id: Annotated[Optional[str], InjectedState("interaction_id")] = None,
) -> dict:
    """
    Update ONE OR MORE specific fields in the current interaction without touching other fields.
    Call this when the user wants to correct or change part of an existing interaction.
    """
    # interaction_id is injected from graph state (sent by the frontend), not chosen by the LLM
    if not interaction_id:
        return {
            "type": "form_update",
            "fields": {},
            "ai_message": "No interaction is currently loaded to edit. Log or load an interaction first."
        }

    try:
        interaction_uuid = uuid.UUID(str(interaction_id))
    except ValueError:
        return {
            "type": "form_update",
            "fields": {},
            "ai_message": f"The current interaction ID '{interaction_id}' is not valid, so nothing was changed."
        }

    llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0, api_key=os.getenv("GROQ_API_KEY"))

    system_prompt = """You are a CRM field editor. The user wants to update specific fields of a logged interaction.
Identify ONLY the fields that need to change based on the user's input.
Return ONLY valid JSON with:
{ "fields_to_update": { "field_name": "new_value" } }
Valid field names: hcpName, interactionType, date, time, attendees,
topicsDiscussed, materialsShared, samplesDistributed, sentiment,
outcomes, followUpActions.
Do NOT include unchanged fields. Do not wrap in markdown."""

    response = await llm.ainvoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": input}
    ])

    content = response.content.strip()
    if content.startswith("```json"): content = content[7:]
    if content.startswith("```"): content = content[3:]
    if content.endswith("```"): content = content[:-3]

    try:
        extracted = json.loads(content.strip())
        fields_to_update = extracted.get("fields_to_update", {})
    except Exception:
        fields_to_update = {}

    # Drop anything that isn't a real column so the UPDATE can't fail on a bad key
    fields_to_update = {k: v for k, v in fields_to_update.items() if k in EDITABLE_FIELDS}

    if not fields_to_update:
        return {
            "type": "form_update",
            "fields": {},
            "ai_message": "I couldn't tell which fields to change. Try e.g. \"change sentiment to negative\"."
        }

    try:
        async with async_session() as session:
            stmt = update(Interaction).where(Interaction.id == interaction_uuid).values(**fields_to_update)
            result = await session.execute(stmt)
            await session.commit()
            rowcount = result.rowcount
    except Exception as e:
        print("DB update error:", e)
        return {
            "type": "form_update",
            "fields": {},
            "ai_message": "Sorry, saving that change to the database failed, so nothing was updated."
        }

    if rowcount == 0:
        return {
            "type": "form_update",
            "fields": {},
            "ai_message": "I couldn't find the current interaction in the database, so nothing was updated."
        }

    return {
        "type": "form_update",
        "fields": fields_to_update,
        "interaction_id": str(interaction_uuid),
        "ai_message": "Updated! I've made those changes to the interaction."
    }
