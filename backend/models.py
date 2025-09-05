from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class Preferences(BaseModel):
    user_id: str = "demo"
    keywords: List[str] = []
    firms: List[str] = []
    sectors: List[str] = [] 
    geos: List[str] = []


class DealItem(BaseModel):
    id: str
    title: str
    link: str
    summary: str
    published: Optional[datetime] = None
    event_type: str = "Other"
    entities: List[str] = []
    firms: List[str] = []
    score: int = 0
    relationship_badges: List[str] = []
    # relevance: float = 0.0

class DealEnvelope(BaseModel):
    kind: str = "deal_item"
    data: DealItem