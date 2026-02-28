from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship

class EvidenceItem(SQLModel, table=True):
    __tablename__ = "evidence_items"

    id: Optional[str] = Field(default=None, primary_key=True)
    question_id: str = Field(foreign_key="questions.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    indicator_type: str
    direction: int = Field(ge=-1, le=1)
    weight: float
    note: Optional[str] = None
