import json
from fastapi import Depends, APIRouter
import settings
from views.render import APIResponse
from data import code,msg
from app.dependencies import request_init
from apps.intelligence.schemas import IntelligenceQueryParams
from apps.intelligence.services import *
from app.dependencies import PaginationQueryParams
from data.logger import create_logger
from views.render import JsonResponseEncoder



router = APIRouter(prefix='/api/v1/intelligence', tags=['intelligence'])

logger = create_logger('aigun-intelligence')


@router.get("/")
async def get_intelligences_list(
        query_params: IntelligenceQueryParams = Depends(),
        request=Depends(request_init(verify=False, limiter=False)),
        page_query: PaginationQueryParams = Depends()
):
    """
    Query intelligence list and cache subsequent page data in the background
    """
    user_id = getattr(request, 'user_id', None) or "anonymous"
    cache_key = f"aigun:intelligence:{hash((query_params.model_dump_json(), user_id, page_query.page, page_query.page_size))}"
    
    result, total = await list_intelligence(request, query_params, page_query.page, page_query.page_size)
    
    # Cache with expiration in single operation
    await request.context.mastercache.backend.hset(
        name=cache_key,
        mapping={"data": json.dumps(result, cls=JsonResponseEncoder), "total": total}
    )
    await request.context.mastercache.backend.expire(cache_key, settings.EXPIRES_FOR_INTELLIGENCE)
    
    return APIResponse(code=code.CODE_OK, msg=msg.SUCCESS, data=result, 
                      page=page_query.page, page_size=page_query.page_size, total=total)



@router.get("/token/info")
async def get_token_info(network: str, address: str, token_type: Optional[str] = None,
                         request=Depends(request_init(verify=False, limiter=False))):
    """
    Get token details
    """

    token = await retrieve_token(request, network, address)
    return APIResponse(data=token, is_pagination=False)



@router.get("/intelligence/{intelligence_id}")
async def get_intelligence_info(
    intelligence_id: str, request=Depends(request_init(verify=False))
):
    """
    intelligence detail
    """

    result = await retrieve_intelligence(request, intelligence_id)

    return APIResponse(
        code=code.CODE_OK, msg=msg.SUCCESS, data=result, is_pagination=False
    )

