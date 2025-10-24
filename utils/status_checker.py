import asyncio
import time

import aio_pika

import settings
from middleware import Request
from sqlalchemy import text
from typing import Dict, Any

class ServiceStatusChecker:

    @staticmethod
    async def check_database(request: Request) -> Dict[str, Any]:
        """Check database connection status"""

        async with request.context.database.dogex() as session:
            try:
                start_time = time.time()

                # Execute a simple query to validate database connection
                result = await session.execute(text("SELECT 1"))
                response_time = time.time() - start_time

                return {
                    "status": "healthy",
                    "details": "Database connection successful",
                    "response_time": round(response_time, 3)
                }
            except Exception as e:
                return {
                    "status": "unhealthy",
                    "details": f"Failed to connect to database, {e}",
                    "response_time": 0
                }

    @staticmethod
    async def check_redis(request: Request) -> Dict[str, Any]:
        """Check connection status"""
        master_cache = request.context.mastercache.backend
        try:
            start_time = time.time()

            # Execute PING command to validate connection
            pong = await asyncio.wait_for(
                master_cache.ping(),
                timeout=5
            )
            response_time = time.time() - start_time

            return {
                "status": "healthy" if pong else "unhealthy",
                "details": "Redis connection successful",
                "response_time": round(response_time, 3)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "details": f"Failed to connect to Redis, {e}",
                "response_time": 0
            }

    @staticmethod
    async def check_rabbitmq(request: Request) -> Dict[str, Any]:
        """Check connection status"""
        try:
            start_time = time.time()

            # Establish RabbitMQ connection
            connection = await aio_pika.connect_robust(settings.RABBIT_URL)
            channel = await connection.channel()

            # Declare a temporary queue and delete it to validate broker accessibility
            q = await channel.declare_queue("", auto_delete=True)
            await q.delete()
            await connection.close()
            response_time = time.time() - start_time
            return {
                "status": "healthy",
                "details": "RabbitMQ connection successful",
                "response_time": round(response_time, 3)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "details": f"Failed to connect to RabbitMQ, {e}",
                "response_time": 0,
            }

# Create an instance of the status checker
status_checker = ServiceStatusChecker()