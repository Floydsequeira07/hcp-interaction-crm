from datetime import date as date_type, time as time_type
from typing import Optional
from pydantic import BaseModel


class InteractionCreate(BaseModel):
    hcp_name: str
    interaction_type: str
    date: Optional[date_type] = None
    time: Optional[time_type] = None
    attendees: str
    topics_discussed: str
    materials_shared: str
    samples_distributed: str
    sentiment: str
    outcomes: str
    follow_up_actions: str


class InteractionResponse(InteractionCreate):
    id: int

    class Config:
        from_attributes = True