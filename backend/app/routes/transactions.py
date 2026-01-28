from __future__ import annotations
import asyncio
import hashlib
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlmodel import Session, select

from app.db.database import get_session
from app.jobs import process_transaction_job
from app.models.transaction import Transaction, TransactionCreate, TransactionRead, TransactionStatus
from app.queue import get_queue
from app.redis_events import publish_tx_event
from app.ws import ws_manager

router = APIRouter(prefix="/transactions", tags=["transactions"])


def fallback_key(payload: TransactionCreate) -> str:
    raw = f"{payload.user_id}|{payload.monto}|{payload.tipo}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@router.get("", response_model=List[TransactionRead])
def list_transactions(session: Session = Depends(get_session)):
    stmt = select(Transaction).order_by(Transaction.created_at.desc())
    return session.exec(stmt).all()


@router.post("/create", response_model=TransactionRead)
def create_transaction(
    payload: TransactionCreate,
    session: Session = Depends(get_session),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    key = idempotency_key or payload.idempotency_key or fallback_key(payload)

    existing = session.exec(select(Transaction).where(Transaction.idempotency_key == key)).first()
    if existing:
        return existing

    tx = Transaction(
        user_id=payload.user_id,
        monto=payload.monto,
        tipo=payload.tipo,
        idempotency_key=key,
        status=TransactionStatus.pending,
    )

    session.add(tx)
    try:
        session.commit()
    except Exception:
        session.rollback()
        existing = session.exec(select(Transaction).where(Transaction.idempotency_key == key)).first()
        if existing:
            return existing
        raise HTTPException(status_code=500, detail="Error creando transacción")

    session.refresh(tx)
    return tx


@router.post("/async-process", response_model=TransactionRead)
def async_process_transaction(
    payload: TransactionCreate,
    session: Session = Depends(get_session),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    fail: bool = Query(default=False, description="Si true, el worker marcará la transacción como fallida"),
):
    key = idempotency_key or payload.idempotency_key or fallback_key(payload)

    existing = session.exec(select(Transaction).where(Transaction.idempotency_key == key)).first()
    if existing:
        return existing

    tx = Transaction(
        user_id=payload.user_id,
        monto=payload.monto,
        tipo=payload.tipo,
        idempotency_key=key,
        status=TransactionStatus.pending,
    )

    session.add(tx)
    session.commit()
    session.refresh(tx)

    # Evento inmediato: para ver "pendiente" en UI aunque venga de demo.sh/curl
    publish_tx_event(
        {
            "event": "tx_created",
            "id": tx.id,
            "user_id": tx.user_id,
            "monto": tx.monto,
            "tipo": tx.tipo,
            "status": tx.status,
            "idempotency_key": tx.idempotency_key,
            "created_at": tx.created_at.isoformat(),
        }
    )

    q = get_queue()
    q.enqueue(process_transaction_job, tx.id, fail)
    return tx


@router.websocket("/stream")
async def transactions_stream(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30)
            except asyncio.TimeoutError:
                # keep-alive sin obligar al cliente a mandar pings
                continue
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception:
        await ws_manager.disconnect(websocket)
        raise
