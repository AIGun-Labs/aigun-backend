
from sqlalchemy import select
from apps.intelligence.models import *

from sqlalchemy.orm import selectinload
from apps.intelligence import schemas
from apps.websocket import services as ws_services

from middleware import Request
from sqlalchemy import and_, or_
from sqlalchemy import cast, String

from sqlalchemy.orm import defer


async def list_intelligence(request: Request, query_params: schemas.IntelligenceQueryParams, page: int, page_size: int):
    """
    Get intelligence list
    """

    master_cache = request.context.mastercache.backend
    offset: int = (page - 1) * page_size

    user_followed_tag_ids = ["01998fe3-dc40-748e-bf30-b9acc6e94497"]

    filter_list = []

    # Filter by type
    if query_params.type:
        type_condition = IntelligenceModel.type == query_params.type
        if query_params.type == "social":
            platforms = ["twitter", "farcaster", "binancesquare"]
            type_condition = IntelligenceModel.type.in_(platforms)
        filter_list.append(type_condition)

    # Filter by subtype
    if query_params.subtype:
        subtype_condition = (IntelligenceModel.subtype == query_params.subtype)
        filter_list.append(subtype_condition)


    # Preload related tables
    entity_load_options = selectinload(
        IntelligenceModel.entity_intelligences
    ).selectinload(
        EntityIntelligenceModel.entity
    )

    # Query intelligence data and immediately release database connection
    async with request.context.database.dogex() as session:

        # Base query
        sql = select(IntelligenceModel)

        # Influence level filter
        if query_params.influence_level is not None:
            sql = sql.join(IntelligenceModel.entity_intelligences).join(EntityIntelligenceModel.entity)
            sql = sql.where(and_(
                EntityIntelligenceModel.type == "author",
                EntityModel.influence_level == query_params.influence_level
            ))


        # Get total count from cache
        total = await master_cache.get(f"dogex:intelligence:intelligence_list:count:query_params:{query_params.model_dump_json()}")
        if total is not None:
            total = int(total.decode("utf-8")) if total.decode("utf-8") else 0
        else:
            # Count total
            distinct_query = sql.where(*filter_list).options(defer(IntelligenceModel.extra_datas), entity_load_options).distinct()
            total_count_sql = select(func.count()).select_from(distinct_query.subquery())
            # Get total count
            total: int = (await session.execute(total_count_sql)).scalar()

            await master_cache.set(name=f"dogex:intelligence:intelligence_list:count:query_params:{query_params.model_dump_json()}", value=total, ex=3600 * 6)

        filter_list.append(IntelligenceModel.is_deleted == False)
        filter_list.append(IntelligenceModel.is_visible == True)

        # Query SQL
        sql = sql.where(*filter_list).options(defer(IntelligenceModel.extra_datas), entity_load_options).order_by(
            IntelligenceModel.published_at.desc()).offset(offset).limit(page_size).distinct()

        # Get results
        intelligences = (await session.execute(sql)).scalars().all()

    # Get chain information for all tokens associated with all intelligence items
    chain_infos = await get_chain_infos(request, intelligences)

    result = []
    for intelligence in intelligences:
        intelligence_info = schemas.IntelligenceListOutSchema.model_validate(intelligence).model_dump()


        result.append(intelligence_info)

    return result, total

