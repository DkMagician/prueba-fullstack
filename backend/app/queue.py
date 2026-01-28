import os
from redis import Redis
from rq import Queue

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

def get_queue() -> Queue:
    conn = Redis.from_url(REDIS_URL)
    return Queue("default", connection=conn)
