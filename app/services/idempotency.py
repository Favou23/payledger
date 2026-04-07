import json

from redis.asyncio import Redis


async def check_idempotency(redis: Redis, key: str) -> dict | None:
    cached = await redis.get(f"idempotency:{key}")
    if not cached:
        return None
    return json.loads(cached)


async def store_idempotency(redis: Redis, key: str, response: dict, ttl: int = 86400) -> None:
    await redis.setex(f"idempotency:{key}", ttl, json.dumps(response, default=str))
