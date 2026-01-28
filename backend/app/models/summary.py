from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlmodel import Field, SQLModel


class SummaryStatus(str, Enum):
    pending = "pendiente"
    processed = "procesado"
    failed = "fallido"


class SummaryBase(SQLModel):
    source: str = "manual"
    text: str


class Summary(SummaryBase, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    status: SummaryStatus = Field(default=SummaryStatus.pending)
    result: Optional[str] = None
    error: Optional[str] = None
    idempotency_key: str = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SummaryCreate(SummaryBase):
    idempotency_key: Optional[str] = None


class SummaryRead(SQLModel):
    id: str
    source: str
    status: SummaryStatus
    result: Optional[str]
    error: Optional[str]
    idempotency_key: str
    created_at: datetime
