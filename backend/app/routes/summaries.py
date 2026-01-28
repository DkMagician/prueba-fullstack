from __future__ import annotations
import hashlib
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlmodel import Session, select

from app.db.database import get_session
from app.jobs import summarize_text_job
from app.models.summary import Summary, SummaryCreate, SummaryRead, SummaryStatus
from app.queue import get_queue
from app.redis_events import publish_tx_event

router = APIRouter(prefix="/summaries", tags=["summaries"])


def fallback_key(payload: SummaryCreate) -> str:
    raw = f"{payload.source}|{payload.text}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@router.get("", response_model=List[SummaryRead])
def list_summaries(session: Session = Depends(get_session)):
    stmt = select(Summary).order_by(Summary.created_at.desc())
    return session.exec(stmt).all()


@router.get("/{summary_id}", response_model=SummaryRead)
def get_summary(summary_id: str, session: Session = Depends(get_session)):
    s = session.exec(select(Summary).where(Summary.id == summary_id)).first()
    if not s:
        raise HTTPException(status_code=404, detail="summary_not_found")
    return s


@router.post("/async", response_model=SummaryRead)
def create_summary_async(
    payload: SummaryCreate,
    session: Session = Depends(get_session),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    fail: bool = Query(default=False, description="Si true, el worker marcará el summary como fallido"),
):
    key = idempotency_key or payload.idempotency_key or fallback_key(payload)

    existing = session.exec(select(Summary).where(Summary.idempotency_key == key)).first()
    if existing:
        return existing

    s = Summary(source=payload.source, text=payload.text, idempotency_key=key, status=SummaryStatus.pending)
    session.add(s)

    try:
        session.commit()
    except Exception:
        session.rollback()
        existing = session.exec(select(Summary).where(Summary.idempotency_key == key)).first()
        if existing:
            return existing
        raise HTTPException(status_code=500, detail="Error creando summary")

    session.refresh(s)

    # Evento inmediato para que el frontend lo muestre en "pendiente"
    publish_tx_event(
        {
            "event": "summary_created",
            "id": s.id,
            "status": s.status,
            "source": s.source,
            "idempotency_key": s.idempotency_key,
            "created_at": s.created_at.isoformat(),
        }
    )

    q = get_queue()
    q.enqueue(summarize_text_job, s.id, fail)
    return s
