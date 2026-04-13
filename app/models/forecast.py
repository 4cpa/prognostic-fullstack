from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
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

    raw_probability: Optional[float] = None
    calibrated_probability: Optional[float] = None
    summary: Optional[str] = None

    direct_answer: Optional[str] = None
    answer_label: Optional[str] = None
    answer_confidence_band: Optional[str] = None
    answer_rationale_short: Optional[str] = None
    question_type: Optional[str] = None
    scenarios: Optional[List[Dict[str, Any]]] = None

    runtime_calibration_meta: Optional[Dict[str, Any]] = None
    calibration_signals: Optional[Dict[str, Any]] = None
    diagnostics: Optional[Dict[str, Any]] = None

    sources: Optional[List[Dict[str, Any]]] = None
    claims: Optional[List[Dict[str, Any]]] = None
    top_pro_claims: Optional[List[Dict[str, Any]]] = None
    top_contra_claims: Optional[List[Dict[str, Any]]] = None
    top_uncertainties: Optional[List[Dict[str, Any]]] = None

    updated_at: Optional[datetime] = None


class Forecast(SQLModel, table=True):
    __tablename__ = "forecasts"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    question_id: str = Field(foreign_key="questions.id", index=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

    probability: float = Field(ge=0, le=1)
    confidence: Optional[float] = Field(default=None, ge=0, le=1)

    raw_probability: Optional[float] = Field(default=None, ge=0, le=1)
    calibrated_probability: Optional[float] = Field(default=None, ge=0, le=1)

    method: str = Field(default="bayes_logodds_v1")
    method_version: str = Field(default="v0.1.0")

    summary: Optional[str] = Field(default=None)
    explanation_md: str
    inputs_hash: str

    direct_answer: Optional[str] = Field(default=None)
    answer_label: Optional[str] = Field(default=None)
    answer_confidence_band: Optional[str] = Field(default=None)
    answer_rationale_short: Optional[str] = Field(default=None)

    runtime_calibration_meta: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    calibration_signals: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    diagnostics: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )

    sources: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    claims: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    top_pro_claims: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    top_contra_claims: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    top_uncertainties: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
