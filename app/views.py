import httpx
from fastapi import FastAPI, Response, Depends
from starlette.responses import StreamingResponse

from app.dependencies import request_init
from middleware.lifespan import on_startup
from middleware.request import Request
from views.render import Text, Json, HTTPException
from data.logger import create_logger
from data.fetch import AsyncLimitClient
from views.render import APIResponse



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

    @app.get("/version", description="Version information")
    async def _():
        return APIResponse(data={
            "version": "0.0.1",
            "download_apk": "test"
        })


    @app.get("/api/v1/proxy")
    async def get_image_data(url, request=Depends(request_init(verify=False, limiter=False))):

        from curl_cffi import AsyncSession

        headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
        }

        try:
            async with AsyncSession(proxy="https://twitter:n4vsD4_kjcAPy3F2az@dc.decodo.com:10000") as session:
                response = await session.get(
                    url,
                    headers=headers,
                    impersonate="chrome110",
                    timeout=180,
                )

                # Get Content-Type from response headers
                content_type = response.headers.get("Content-Type", "image/jpeg")

                # Return image data directly
                return Response(content=response.content, media_type=content_type)

        except Exception as e:
            logger.exception(f"Proxy request failed")
            return Response(content=f"Failed to get image: {str(e)}", status_code=500)