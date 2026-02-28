from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class ForecastRead(SQLModel):
    id: str
    question_id: str
    created_at: datetime
    probability: float
    confidence: Optional[float] = None
    method: str
    method_version: str
    explanation_md: str
    inputs_hash: str


class Forecast(SQLModel, table=True):
    __tablename__ = "forecasts"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    question_id: str = Field(foreign_key="questions.id", index=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)

    probability: float = Field(ge=0, le=100)
    confidence: Optional[float] = Field(default=None, ge=0, le=100)

    method: str = Field(default="bayes_logodds_v1")
    method_version: str = Field(default="v0.1.0")

    explanation_md: str
    inputs_hash: str
