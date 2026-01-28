import asyncio
import json
import logging
import os
from redis import Redis

from app.ws import ws_manager

logger = logging.getLogger("redis_events")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
EVENTS_CHANNEL = "tx-events"


def publish_tx_event(payload: dict) -> None:
    r = Redis.from_url(REDIS_URL)
    try:
        r.publish(EVENTS_CHANNEL, json.dumps(payload, ensure_ascii=False))
    finally:
        try:
            r.close()
        except Exception:
            pass


async def redis_pubsub_loop() -> None:
    r = Redis.from_url(REDIS_URL)
    pubsub = r.pubsub()
    pubsub.subscribe(EVENTS_CHANNEL)

    logger.info("Subscribed to Redis channel=%s", EVENTS_CHANNEL)

    try:
        while True:
            msg = await asyncio.to_thread(pubsub.get_message, True, 1.0)

            if msg and msg.get("type") == "message":
                data = msg.get("data")
                if isinstance(data, bytes):
                    data = data.decode("utf-8", errors="replace")
                logger.info("Redis event: %s", data)
                await ws_manager.broadcast_text(str(data))

            await asyncio.sleep(0.05)

    except asyncio.CancelledError:
        logger.info("redis_pubsub_loop cancelled")
        raise
    finally:
        try:
            pubsub.close()
        except Exception:
            pass
        try:
            r.close()
        except Exception:
            pass
        logger.info("Redis Pub/Sub closed")
