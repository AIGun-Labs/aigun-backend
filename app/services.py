"""
Common service methods
"""
import json
import base64
import aiohttp
import asyncio
import random
from typing import Dict, Optional

from fastapi import HTTPException
from middleware import Request
from datetime import datetime, UTC


def format_time(value: datetime | int) -> str:
    """
    Convert datetime / timestamp to ISO 8601 format
    """
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    if isinstance(value, int):
        return datetime.fromtimestamp(value, UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    return str(value)


async def send_to_queue(request: Request, queue: str, data: Dict):
    """
    Send message
    """
    try:
        connection = request.context.amqp
        await connection.send(queue, json.dumps(data).encode())
        return True
    except Exception as e:
        return False

def get_query_params(request: Request):
    """
    Get query parameters
    """
    query_params = None
    if request.query_params:
        query_params = request.query_params

    return query_params


async def get_body_data(request: Request) -> Optional[Dict]:
    """
    Get request body data
    """
    try:

        raw_body = await request.body()  # Get raw bytes
        json_data = raw_body.decode("utf-8")

    except:
        json_data = None

    return json_data



class DistributedLock:

    @staticmethod
    async def acquire_lock_with_retry(master_redis, lock_key, lock_value, timeout=30, retry_interval=0.5):
        end_time = asyncio.get_event_loop().time() + timeout

        while asyncio.get_event_loop().time() < end_time:
            lock_acquired = await master_redis.set(lock_key, lock_value, nx=True, ex=30)
            if lock_acquired:
                return True

            # Random backoff to reduce Redis pressure
            await asyncio.sleep(retry_interval + random.uniform(0, 0.05))

        return False


    @staticmethod
    async def release_lock(master_redis, lock_key, lock_value: str) -> None:
        """
        Safely release lock (Lua script ensures atomicity)
        """
        lua_script = """
        if redis.call("GET", KEYS[1]) == ARGV[1] then
            return redis.call("DEL", KEYS[1])
        else
            return 0
        end
        """

        await master_redis.eval(lua_script, 1, lock_key, lock_value.encode())


redis_distributed_lock = DistributedLock()