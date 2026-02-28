from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import SQLModel, Field


class QuestionStatus(str, Enum):
    open = "open"
    resolved_yes = "resolved_yes"
    resolved_no = "resolved_no"
    void = "void"


# ------------------------
# API Schemas
# ------------------------

class QuestionCreate(SQLModel):
    title: str
    description: str
    category: str = "politics"
    region: Optional[str] = None
    country: Optional[str] = None
    resolve_at: datetime
    resolution_criteria: str
    resolution_source_policy: str = "official + 1 major wire (Reuters/AP/AFP)"


class QuestionRead(SQLModel):
    id: str
    title: str
    description: str
    category: str
    region: Optional[str] = None
    country: Optional[str] = None
    created_at: datetime
    resolve_at: datetime
    resolution_criteria: str
    resolution_source_policy: str
    status: QuestionStatus
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolution_notes: Optional[str] = None


# ------------------------
# Database Model
# ------------------------

class Question(SQLModel, table=True):
    __tablename__ = "questions"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)

    title: str
    description: str

    category: str = Field(default="politics")
    region: Optional[str] = None
    country: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolve_at: datetime

    resolution_criteria: str
    resolution_source_policy: str = Field(
        default="official + 1 major wire (Reuters/AP/AFP)"
    )

    status: QuestionStatus = Field(default=QuestionStatus.open)

    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolution_notes: Optional[str] = None
