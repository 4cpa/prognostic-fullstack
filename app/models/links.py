from __future__ import annotations

from typing import Optional

from sqlmodel import SQLModel, Field


class EvidenceSourceLink(SQLModel, table=True):
    __tablename__ = "evidence_sources"

    evidence_id: str = Field(foreign_key="evidence_items.id", primary_key=True)
    source_id: str = Field(foreign_key="sources.id", primary_key=True)
    claim_excerpt: Optional[str] = None


class ForecastEvidenceLink(SQLModel, table=True):
    __tablename__ = "forecast_evidence"

    forecast_id: str = Field(foreign_key="forecasts.id", primary_key=True)
    evidence_id: str = Field(foreign_key="evidence_items.id", primary_key=True)


class ForecastSourceLink(SQLModel, table=True):
    __tablename__ = "forecast_source_links"

    forecast_id: str = Field(foreign_key="forecasts.id", primary_key=True)
    source_id: str = Field(foreign_key="sources.id", primary_key=True)
    claim_excerpt: Optional[str] = None
