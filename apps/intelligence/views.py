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

logger = create_logger('dogex-intelligence')


@router.get("/")
async def get_intelligences_list(
        query_params: IntelligenceQueryParams = Depends(),
        request=Depends(request_init(verify=False, limiter=False)),
        page_query: PaginationQueryParams = Depends()
):
    """
    Query intelligence list and cache subsequent page data in the background
    """
    cache_key = f"dogex:intelligence:next_pages_data:query_params:{query_params.model_dump_json()}:user:{request.user_id}:page:{page_query.page}:page_size:{page_query.page_size}"

    master_cache = request.context.mastercache.backend
    request.user_id = getattr(request, 'user_id', None) or "anonymous"

    # query the current page
    result, total = await list_intelligence(request, query_params, page_query.page, page_query.page_size)
    mapping = {
        "data": json.dumps(result, cls=JsonResponseEncoder),
        "total": total
    }

    # Cache the current page and total
    await master_cache.hset(name=cache_key, mapping=mapping)
    await master_cache.expire(cache_key, settings.EXPIRES_FOR_INTELLIGENCE)


    return APIResponse(code=code.CODE_OK, msg=msg.SUCCESS, data=result, page=page_query.page, page_size=page_query.page_size, total=total)



@router.get("/token/info")
async def get_token_info(network: str, address: str, token_type: Optional[str] = None,
                         request=Depends(request_init(verify=False, limiter=False))):
    """
    Get token details
    """

    token = await retrieve_token(request, network, address)
    return APIResponse(data=token, is_pagination=False)