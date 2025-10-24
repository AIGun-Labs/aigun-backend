import time

import asyncio
from fastapi import FastAPI, Depends
from app.dependencies import request_init
from middleware.request import Request
from utils.status_checker import status_checker
from views.render import Text
from data.logger import create_logger



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


    @app.get("/check")
    async def check_services_status(request=Depends(request_init(verify=False, limiter=False))):
        """
        Check the health status of all services
        - Database
        - Cache
        - Message queue
        """
        # Check all services in parallel
        db_task = asyncio.create_task(status_checker.check_database(request))
        redis_task = asyncio.create_task(status_checker.check_redis(request))
        rabbitmq_task = asyncio.create_task(status_checker.check_rabbitmq(request))

        # Wait for all checks to complete
        db_status, redis_status, rabbitmq_status = await asyncio.gather(
            db_task, redis_task, rabbitmq_task,
            return_exceptions=False
        )

        # Determine overall status
        services = {
            "database": db_status,
            "redis": redis_status,
            "rabbitmq": rabbitmq_status
        }

        all_healthy = all(service["status"] == "healthy" for service in services.values())
        overall_status = "healthy" if all_healthy else "unhealthy"

        return {
            "status": overall_status,
            "timestamp": time.time(),
            "services": services
        }
