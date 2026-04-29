from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from uuid import UUID

class InteractionBase(BaseModel):
    hcpName: str
    interactionType: Optional[str] = "Meeting"
    date: Optional[str] = ""
    time: Optional[str] = ""
    attendees: Optional[List[str]] = []
    topicsDiscussed: Optional[str] = ""
    materialsShared: Optional[List[Dict[str, Any]]] = []
    samplesDistributed: Optional[List[Dict[str, Any]]] = []
    sentiment: Optional[str] = "neutral"
    outcomes: Optional[str] = ""
    followUpActions: Optional[str] = ""
    aiSuggestedFollowups: Optional[List[str]] = []

class InteractionCreate(InteractionBase):
    pass

class InteractionResponse(InteractionBase):
    id: UUID

    class Config:
        from_attributes = True

class ChatRequest(BaseModel):
    message: str
    session_id: str
