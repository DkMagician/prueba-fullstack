import time
from sqlmodel import Session, select

from app.db.database import engine
from app.models.transaction import Transaction, TransactionStatus
from app.models.summary import Summary, SummaryStatus
from app.redis_events import publish_tx_event


def process_transaction_job(transaction_id: str, fail: bool = False) -> dict:
    time.sleep(3)
    with Session(engine) as session:
        tx = session.exec(select(Transaction).where(Transaction.id == transaction_id)).first()
        if not tx:
            return {"ok": False, "error": "transaction_not_found"}

        tx.status = TransactionStatus.failed if fail else TransactionStatus.processed
        session.add(tx)
        session.commit()
        session.refresh(tx)

        publish_tx_event(
            {"event": "tx_status_updated", "id": tx.id, "status": tx.status, "user_id": tx.user_id}
        )

        return {"ok": True, "id": tx.id, "status": tx.status}


def _mock_summarize(text: str, max_words: int = 60) -> str:
    # resumen determinista y simple (para demo)
    words = text.strip().split()
    if not words:
        return ""
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words]) + " ..."


def summarize_text_job(summary_id: str, fail: bool = False) -> dict:
    time.sleep(2)
    with Session(engine) as session:
        s = session.exec(select(Summary).where(Summary.id == summary_id)).first()
        if not s:
            return {"ok": False, "error": "summary_not_found"}

        if fail:
            s.status = SummaryStatus.failed
            s.error = "forced_failure"
            s.result = None
        else:
            s.result = _mock_summarize(s.text)
            s.status = SummaryStatus.processed
            s.error = None

        session.add(s)
        session.commit()
        session.refresh(s)

        publish_tx_event(
            {
                "event": "summary_updated",
                "id": s.id,
                "status": s.status,
                "source": s.source,
                "preview": (s.result or "")[:120],
            }
        )

        return {"ok": True, "id": s.id, "status": s.status}
