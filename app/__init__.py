from typing import Any, List
from fastapi import FastAPI, APIRouter, Depends
from middleware import register_middleware
from middleware.apploader import register_by
from middleware.lifespan import lifespan_context


def api_router_register(obj: APIRouter | List[APIRouter], app: Any):
    if isinstance(obj, APIRouter):
        app.include_router(obj)
        return True
    for router_obj in obj:
        app.include_router(router_obj)
    else:
        return True


def create_app() -> FastAPI:

    app: FastAPI = FastAPI(
        lifespan=lifespan_context,
        docs_url=None,
        redoc_url=None,
        openapi_url=None
    )

    register_by('on_init', app, api_router_register)

    register_middleware(app)

    return app