import json
from typing import Any

import redis.asyncio as aioredis
import ujson
from redis.asyncio.client import PubSub

from core.cache.base import BaseBackend
from core.config import config

redis = aioredis.from_url(url=config.REDIS_URL.unicode_string())


class RedisBackend(BaseBackend):
    async def get(self, key: str) -> Any:
        result = await redis.get(key)
        if not result:
            return

        try:
            return ujson.loads(result.decode("utf8"))
        except UnicodeDecodeError:
            # For security reasons, remove pickle and adding
            # return pickle.loads(result)
            return json.loads(result)

    async def set(self, response: Any, key: str, ttl: int = 60) -> None:
        if isinstance(response, dict):
            response = ujson.dumps(response)
        elif isinstance(response, object):
            # response = pickle.dumps(response)
            response = json.dumps(response)

        await redis.set(name=key, value=response, ex=ttl)

    async def delete_startswith(self, value: str) -> None:
        async for key in redis.scan_iter(f"{value}::*"):
            await redis.delete(key)

    async def subscribe(self, channel: str) -> PubSub:
        pubsub = redis.pubsub()
        await pubsub.subscribe(channel)
        return pubsub

    async def publish(self, channel: str, message: str) -> None:
        await redis.publish(channel, message)

    async def unsubscribe(self, pubsub: PubSub, channel: str) -> None:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
