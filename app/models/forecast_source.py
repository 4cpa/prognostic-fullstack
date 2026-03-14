from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlmodel import Field, SQLModel


class ForecastSourceBase(SQLModel):
    forecast_id: str = Field(index=True)
    url: str
    title: str
    publisher: str
    domain: Optional[str] = None
    source_type: str = Field(default="other", index=True)
    published_at: Optional[str] = None
    query: Optional[str] = None
    retrieval_method: Optional[str] = None

    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    credibility_score: float = Field(default=0.0, ge=0.0, le=1.0)
    freshness_score: float = Field(default=0.0, ge=0.0, le=1.0)
    overall_score: float = Field(default=0.0, ge=0.0, le=1.0)

    stance: str = Field(default="neutral", index=True)
    signal_strength: float = Field(default=0.0, ge=0.0, le=1.0)

    summary: Optional[str] = None


class ForecastSource(ForecastSourceBase, table=True):
    __tablename__ = "forecast_sources"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class ForecastSourceCreate(ForecastSourceBase):
    pass


class ForecastSourceRead(ForecastSourceBase):
    id: str
    created_at: datetime


class ForecastSourcePublic(SQLModel):
    id: str
    url: str
    title: str
    publisher: str
    domain: Optional[str] = None
    source_type: str
    published_at: Optional[str] = None
    relevance_score: float
    credibility_score: float
    freshness_score: float
    overall_score: float
    stance: str
    signal_strength: float
    summary: Optional[str] = None
