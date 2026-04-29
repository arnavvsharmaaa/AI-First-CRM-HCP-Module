import uuid
from sqlalchemy import Column, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from .database import Base

class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hcpName = Column(String, nullable=False)
    interactionType = Column(String, default="Meeting")
    date = Column(String)  # 'YYYY-MM-DD'
    time = Column(String)  # 'HH:MM'
    attendees = Column(JSONB, default=list)
    topicsDiscussed = Column(Text, default="")
    materialsShared = Column(JSONB, default=list)
    samplesDistributed = Column(JSONB, default=list)
    sentiment = Column(String, default="neutral")
    outcomes = Column(Text, default="")
    followUpActions = Column(Text, default="")
    aiSuggestedFollowups = Column(JSONB, default=list)
