from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship

class Source(SQLModel, table=True):
    __tablename__ = "sources"

    id: Optional[str] = Field(default=None, primary_key=True)
    url: str = Field(index=True)
    publisher: Optional[str] = None
    title: Optional[str] = None
    published_at: Optional[datetime] = None
    credibility_score: Optional[float] = Field(default=None, ge=0, le=100)
