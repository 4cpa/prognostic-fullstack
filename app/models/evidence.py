from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class EvidenceCreate(SQLModel):
    indicator_type: str
    direction: int  # -1 or +1
    weight: float
    note: Optional[str] = None


class EvidenceRead(SQLModel):
    id: str
    question_id: str
    created_at: datetime
    indicator_type: str
    direction: int
    weight: float
    note: Optional[str] = None


class EvidenceItem(SQLModel, table=True):
    __tablename__ = "evidence_items"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    question_id: str = Field(foreign_key="questions.id", index=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)

    indicator_type: str
    direction: int
    weight: float
    note: Optional[str] = None
