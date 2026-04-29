from langchain_core.tools import tool
from langchain_groq import ChatGroq
import json
import os
from models.database import async_session
from models.interaction import Interaction
from sqlalchemy import update

@tool
async def edit_interaction(input: str, interaction_id: str) -> dict:
    """
    Update ONE OR MORE specific fields in the current interaction without touching other fields.
    Call this when the user wants to correct or change part of an existing interaction.
    """
    if not interaction_id:
        return {
            "type": "form_update",
            "fields": {},
            "ai_message": "No interaction is currently loaded to edit."
        }
        
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0, api_key=os.getenv("GROQ_API_KEY"))
    
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
        
    if fields_to_update:
        try:
            async with async_session() as session:
                stmt = update(Interaction).where(Interaction.id == interaction_id).values(**fields_to_update)
                await session.execute(stmt)
                await session.commit()
        except Exception as e:
            print("DB update error:", e)
            
    return {
        "type": "form_update",
        "fields": fields_to_update,
        "ai_message": "Updated! I've made those changes to the interaction."
    }
