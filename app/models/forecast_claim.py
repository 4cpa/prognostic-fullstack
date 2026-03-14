from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlmodel import Field, SQLModel


class ForecastClaimBase(SQLModel):
    forecast_id: str = Field(index=True)

    claim_text: str
    claim_type: str = Field(default="background", index=True)

    source_url: str
    source_title: str
    source_type: str = Field(default="other", index=True)

    claim_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    time_relevance: float = Field(default=0.0, ge=0.0, le=1.0)

    source_quality_weight: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    claim_confidence_weight: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    time_relevance_weight: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    relevance_weight: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    freshness_weight: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    independence_weight: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    specificity_weight: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    support_boost: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    final_weight: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    direction: Optional[int] = Field(default=0)
    signed_weight: Optional[float] = None

    supporting_source_count: Optional[int] = Field(default=1, ge=0)
    supporting_domain_count: Optional[int] = Field(default=1, ge=0)


class ForecastClaim(ForecastClaimBase, table=True):
    __tablename__ = "forecast_claims"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class ForecastClaimCreate(ForecastClaimBase):
    pass


class ForecastClaimRead(ForecastClaimBase):
    id: str
    created_at: datetime


class ForecastClaimPublic(SQLModel):
    id: str
    claim_text: str
    claim_type: str
    source_url: str
    source_title: str
    source_type: str
    claim_confidence: float
    time_relevance: float
    final_weight: Optional[float] = None
    direction: Optional[int] = 0
    signed_weight: Optional[float] = None
    supporting_source_count: Optional[int] = 1
    supporting_domain_count: Optional[int] = 1
