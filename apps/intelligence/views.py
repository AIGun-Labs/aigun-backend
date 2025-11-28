import json
import asyncio
from typing import Tuple, Optional, List, Dict, Any
from fastapi import Depends, APIRouter, BackgroundTasks
import settings
from views.render import APIResponse
from data import code, msg
from app.dependencies import request_init
from apps.intelligence.schemas import IntelligenceQueryParams
from apps.intelligence.services import (
    list_intelligence, get_intelligence_latest_entities_v2,
    retrieve_token, retrieve_intelligence,
    get_from_cache, prefetch_pages
)
from app.dependencies import PaginationQueryParams
from data.logger import create_logger
from views.render import JsonResponseEncoder
from middleware import Request


router = APIRouter(prefix='/api/v1/intelligence', tags=['intelligence'])

logger = create_logger('aigun-intelligence')


@router.get("/")
async def get_intelligences_list(
        query_params: IntelligenceQueryParams = Depends(),
        page_query: PaginationQueryParams = Depends(),
        background_tasks: BackgroundTasks = BackgroundTasks(),
        request=Depends(request_init(verify=False, limiter=False))
):
    """
    Query intelligence list with pre-caching and cache breakdown prevention
    """
    cache_key = f"aigun:intelligence:page:{query_params.model_dump_json()}:{page_query.page}:{page_query.page_size}"
    slave_cache = request.context.slavecache.backend
    master_cache = request.context.mastercache.backend
    
    # Try cache first
    result, total = await get_from_cache(cache_key, slave_cache, master_cache)
    if result:
        background_tasks.add_task(prefetch_pages, request, query_params, page_query.page, page_query.page_size)
        return APIResponse(data=result, page=page_query.page, page_size=page_query.page_size, total=total)
    
    # Cache breakdown prevention
    lock_key = f"{cache_key}:lock"
    lock_acquired = await master_cache.set(lock_key, "1", ex=10, nx=True)
    
    if not lock_acquired:
        for _ in range(20):
            await asyncio.sleep(0.1)
            result, total = await get_from_cache(cache_key, slave_cache, master_cache)
            if result:
                background_tasks.add_task(prefetch_pages, request, query_params, page_query.page, page_query.page_size)
                return APIResponse(data=result, page=page_query.page, page_size=page_query.page_size, total=total)
    
    try:
        result, total = await list_intelligence(request, query_params, page_query.page, page_query.page_size)
        await master_cache.hset(cache_key, mapping={"data": json.dumps(result, cls=JsonResponseEncoder), "total": total})
        await master_cache.expire(cache_key, settings.EXPIRES_FOR_INTELLIGENCE)
        background_tasks.add_task(prefetch_pages, request, query_params, page_query.page, page_query.page_size)
        return APIResponse(data=result, page=page_query.page, page_size=page_query.page_size, total=total)
    finally:
        if lock_acquired:
            await master_cache.delete(lock_key)


@router.get("/entities")
async def list_intelligence_latest_entity(
        intelligence_ids: str,
        request = Depends(request_init(verify=False, limiter=True))
) -> APIResponse:
    """
    Get the latest associated token data
    """
    intelligence_ids = intelligence_ids.strip().split(",")

    entity_list = await get_intelligence_latest_entities_v2(request, intelligence_ids)
    return APIResponse(data=entity_list)



@router.get("/token/info")
async def get_token_info(
        network: str,
        address: str,
        request = Depends(request_init(verify=False, limiter=False))
) -> APIResponse:
    """
    Get token details
    """

    token = await retrieve_token(request, network, address)
    return APIResponse(data=token, is_pagination=False)



@router.get("/intelligence/{intelligence_id}")
async def get_intelligence_info(
        intelligence_id: str,
        request = Depends(request_init(verify=False))
) -> APIResponse:
    """
    intelligence detail
    """

    result = await retrieve_intelligence(request, intelligence_id)

    return APIResponse(
        code=code.CODE_OK, msg=msg.SUCCESS, data=result, is_pagination=False
    )

