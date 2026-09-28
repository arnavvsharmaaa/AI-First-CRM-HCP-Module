from langchain_core.tools import tool
from langchain_groq import ChatGroq
import json
from datetime import datetime
import uuid
import os
from models.database import async_session
from models.interaction import Interaction

@tool
async def log_interaction(input: str) -> dict:
    """
    Parse a natural language description of an HCP interaction and extract all structured data to populate the form.
    Call this when the user describes a NEW interaction.
    """
    llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0, api_key=os.getenv("GROQ_API_KEY"))
    now = datetime.now()

    # The model has no clock — give it today's date so "today"/"yesterday" resolve correctly
    system_prompt = f"""You are a CRM data extraction assistant for pharmaceutical field reps.
Extract structured interaction data from the user's natural language input.
Return ONLY valid JSON with these exact fields: hcp_name, interaction_type,
date, time, attendees, topics_discussed, materials_shared, samples_distributed,
sentiment, outcomes, follow_up_actions.
Today is {now.strftime("%A %Y-%m-%d")} and the current time is {now.strftime("%H:%M")}.
Resolve relative dates ("today", "yesterday", "last Monday") against today's date.
Format date as YYYY-MM-DD and time as HH:MM (24-hour).
Use today's date if not specified. Use "neutral" sentiment if not mentioned.
For interaction_type use one of: Meeting, Call, Email, Conference.
Do not wrap JSON in markdown blocks."""
    
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
    except Exception:
        extracted = {"hcp_name": "Unknown", "topics_discussed": input}

    def ensure_str(val, default=""):
        if val is None:
            return default
        if isinstance(val, list):
            return ", ".join(str(v) for v in val if v is not None)
        return str(val)
        
    def ensure_list(val):
        if val is None:
            return []
        if isinstance(val, list):
            return val
        return [val]

    fields = {
        "id": uuid.uuid4(),
        "hcpName": ensure_str(extracted.get("hcp_name", "Unknown HCP"), "Unknown HCP"),
        "interactionType": ensure_str(extracted.get("interaction_type", "Meeting"), "Meeting"),
        "date": ensure_str(extracted.get("date", now.strftime("%Y-%m-%d")), now.strftime("%Y-%m-%d")),
        "time": ensure_str(extracted.get("time", now.strftime("%H:%M")), now.strftime("%H:%M")),
        "attendees": ensure_list(extracted.get("attendees", [])),
        "topicsDiscussed": ensure_str(extracted.get("topics_discussed", "")),
        "materialsShared": ensure_list(extracted.get("materials_shared", [])),
        "samplesDistributed": ensure_list(extracted.get("samples_distributed", [])),
        "sentiment": ensure_str(extracted.get("sentiment", "neutral"), "neutral"),
        "outcomes": ensure_str(extracted.get("outcomes", "")),
        "followUpActions": ensure_str(extracted.get("follow_up_actions", "")),
        "aiSuggestedFollowups": []
    }
    
    async with async_session() as session:
        interaction = Interaction(**fields)
        session.add(interaction)
        await session.commit()
    
    fields["id"] = str(fields["id"])
    return {
        "type": "form_update",
        "fields": fields,
        "interaction_id": fields["id"],
        "ai_message": f"Got it! I've logged your interaction with {fields['hcpName']}.",
        "aiSuggestedFollowups": []
    }
