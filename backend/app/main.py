import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.database import create_db_and_tables
from app.redis_events import redis_pubsub_loop
from app.routes.transactions import router as transactions_router
from app.routes.summaries import router as summaries_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    task = asyncio.create_task(redis_pubsub_loop())

    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Prueba Full-Stack Python", lifespan=lifespan)


@app.get("/health")
def health():
    return {"ok": True}


app.include_router(transactions_router)
app.include_router(summaries_router)
