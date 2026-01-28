from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlmodel import Field, SQLModel


class TransactionStatus(str, Enum):
    pending = "pendiente"
    processed = "procesado"
    failed = "fallido"


class TransactionBase(SQLModel):
    user_id: str
    monto: float
    tipo: str


class Transaction(TransactionBase, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    status: TransactionStatus = Field(default=TransactionStatus.pending)
    idempotency_key: str = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TransactionCreate(TransactionBase):
    idempotency_key: Optional[str] = None


class TransactionRead(TransactionBase):
    id: str
    status: TransactionStatus
    idempotency_key: str
    created_at: datetime
