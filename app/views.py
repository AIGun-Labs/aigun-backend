import time

import asyncio
from fastapi import FastAPI, Depends
from app.dependencies import request_init
from middleware.request import Request
from utils.status_checker import status_checker
from views.render import Text, Json
from data.logger import create_logger
from data.db import declare_database
from data.cache import Cache, RedisConfig
from data.rabbit import RabbitMQ, RabbitConfig
import settings
from sqlalchemy import text



logger = create_logger("dogex-intelligence")

def on_init(app: FastAPI):
    """
    Load root public views
    """

    @app.get('/', description="Get time and IP")
    async def _(request: Request):
        request = Request.from_request(request)
        return Text([request.now, request.ip])


    @app.get('/ping', description="Health check")
    async def _():
        return Text('pong')

    @app.get('/health', description="Service health check")
    async def health_check():
        errors = []
        
        # Check all services concurrently
        results = await asyncio.gather(
            _pg_check(), _redis_check(), _rabbit_check(), return_exceptions=True
        )
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                service = ["PostgreSQL", "Redis", "RabbitMQ"][i]
                errors.append(f"{service}: {str(result)}")
        
        return Json({"status": "unhealthy", "errors": errors}, status_code=503) if errors else Json({"status": "healthy"})
    
    async def _pg_check():
        async with declare_database(url=settings.DATABASE_URLS[0])() as s:
            await s.execute(text("SELECT 1"))
    
    async def _redis_check():
        c = Cache(RedisConfig(url=settings.CACHE_URL))
        try: await c.backend.ping()
        finally: await c.close()
    
    async def _rabbit_check():
        await RabbitMQ(RabbitConfig(url=settings.RABBIT_URL)).ensure_connection()



