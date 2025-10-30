import json
from typing import Optional, List

from sqlalchemy import select
from apps.intelligence.models import *
from apps.intelligence import models

from sqlalchemy.orm import selectinload
from apps.intelligence import schemas
from apps.websocket import services as ws_services
from data import create_logger

from middleware import Request
from sqlalchemy import and_, or_
from sqlalchemy import cast, String

from sqlalchemy.orm import defer

from views.render import JsonResponseEncoder

logger = create_logger("dogex-intelligence")

async def list_intelligence(request: Request, query_params: schemas.IntelligenceQueryParams, page: int, page_size: int):
    """
    Get intelligence list
    """

    master_cache = request.context.mastercache.backend
    offset: int = (page - 1) * page_size

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

    # Filter by value judgment
    if query_params.is_valuable is not None:
        valuable_condition = (IntelligenceModel.is_valuable == bool(query_params.is_valuable))
        filter_list.append(valuable_condition)

    # Filter by keyword
    if query_params.key_word:
        key_word_condition = or_(
            IntelligenceModel.content.ilike(f"%{query_params.key_word}%"),
            cast(IntelligenceModel.analyzed["zh"], String).ilike(
                f"%{query_params.key_word}%"
            )
        )
        filter_list.append(key_word_condition)


    # Preload related tables
    entity_load_options = selectinload(
        IntelligenceModel.entity_intelligences
    ).selectinload(
        EntityIntelligenceModel.entity
    ).options(
          selectinload(EntityModel.token_entity).selectinload(TokenModel.chain_datas).selectinload(
              TokenChainDataModel.chain),
          selectinload(EntityModel.tokendata_entity).selectinload(TokenChainDataModel.chain),
          selectinload(EntityModel.entity_tags),
          selectinload(EntityModel.entity_NewsPlatform),
          selectinload(EntityModel.exchange_platform)
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

        # Supplement displayed associated tokens
        intelligence_info["entities"] = await get_showed_tokens_info(request, intelligence_info["showed_tokens"], chain_infos, intelligence)

        # Supplement author field
        intelligence_info["author"] = await ws_services.get_author_info(intelligence_info, request.context)

        # Supplement monitor_time field
        intelligence_info["monitor_time"] = await ws_services.get_monitor_time(intelligence_info["spider_time"], intelligence_info["published_at"])

        intelligence_info["ai_agent"] = {
            "avatar": "image/h0bk-B4SP5-3nqM8JpjEXSW9u2dXcDbKGGAvI8m7GIgXPC4J_Yp5dZMKC8TPFb2lrZZPBuF3wCOyvWU091MujA==",
            "name": {
                "en": "Event Hunter",
                "zh": "Event Hunter"
            }
        }

        del intelligence_info["showed_tokens"]

        result.append(intelligence_info)

    return result, total

async def get_chain_infos(reqeust: Request, intelligences):
    # Retrieve chain messages of all associated tokens with all intelligence from showed_token
    networks = []
    for intelligence in intelligences:
        showed_tokens = intelligence.showed_tokens
        if not showed_tokens:
            networks = []
            break
        for showed_token in showed_tokens:
            network = showed_token["slug"]
            networks.append(network)

    # Compatible with situations where showed_token is empty
    if not networks:
        for intelligence in intelligences:
            for ei in intelligence.entity_intelligences:
                if ei.type == "author":
                    pass

                if ei.entity and ei.entity.tokendata_entity:
                    for project_chain_data in ei.entity.tokendata_entity:
                        networks.append(project_chain_data.network)

    slave_cache = reqeust.context.slavecache.backend
    master_cache = reqeust.context.mastercache.backend

    data = await slave_cache.get(f"dogex:intelligence:chain_infos:networks:{networks}")
    if data is not None:
        await master_cache.expire(name=f"dogex:intelligence:chain_infos:networks:{networks}", time=settings.EXPIRES_FOR_CHAIN_INFOS)
        return json.loads(data.decode("utf-8"))

    async with reqeust.context.database.dogex() as session:
        sql = select(
            models.ChainModel.id,
            models.ChainModel.network_id,
            models.ChainModel.name,
            models.ChainModel.symbol,
            models.ChainModel.slug,
            models.ChainModel.logo
        ).where(
            models.ChainModel.slug.in_(networks)
        )

        results = (await session.execute(sql)).mappings().all()

        data = {str(chain_info["id"]): chain_info for chain_info in results}

        await master_cache.set(name=f"dogex:intelligence:chain_infos:networks:{networks}", value=json.dumps(data, ensure_ascii=False, cls=JsonResponseEncoder), ex=settings.EXPIRES_FOR_CHAIN_INFOS)

        return data



async def get_showed_tokens_info(request: Request, showed_tokens: Optional[List], chain_infos, intelligence):
    # Chain default model
    chain_info = {
        "id": None,
        "network_id": None,
        "name": None,
        "symbol": None,
        "logo": None,
    }
    master_cache = request.context.mastercache.backend
    slave_cache = request.context.slavecache.backend

    # Retrieve hot data from the cache first
    key = f"dogex:intelligence:latest_entities:intelligence_id:{str(intelligence.id)}"
    entities = await slave_cache.get(key)
    if entities:
        return json.loads(entities.decode("utf-8"))

    # Compatible with situations where showed_token is empty (without cold data conversion)
    entities = []

    if not showed_tokens:
        return []

    # Showed_token exists (the actual data that has been displayed to users after being cooled down does not need to be sorted or filtered anymore)
    # Step 1: Collect all pairs of (network, contract_address) that need to be queried
    token_keys = [(showed_token["slug"], showed_token["contract_address"]) for showed_token in showed_tokens]

    # Step 2: Batch query all tokens (one database query)
    async with request.context.database.dogex() as session:
        # Build OR conditions to match all tokens
        conditions = [
            and_(
                models.TokenChainDataModel.network == network,
                models.TokenChainDataModel.contract_address == contract_address
            )
            for network, contract_address in token_keys
        ]

        sql = select(models.TokenChainDataModel).where(or_(*conditions))

        tokens = (await session.execute(sql)).scalars().all()

        # Step 3: Build a lookup dictionary with the key (network, contract_address)
        token_dict = {
            (token.network, token.contract_address): token
            for token in tokens
        }

    # Step 4: Traverse showed_token and retrieve the corresponding token data from the dictionary
    for showed_token in showed_tokens:
        network = showed_token["slug"]
        contract_address = showed_token["contract_address"]
        warning_price_usd = float(showed_token["warning_price_usd"])
        warning_market_cap = float(showed_token["warning_market_cap"])

        # Search for tokens from the dictionary
        token = token_dict.get((network, contract_address))

        if not token:
            logger.error(f"The token in showed_token does not exist，intelligence_id: {str(intelligence.id)}, token info：{showed_token}")
            continue
        try:
            token_data = {
                "id": token.id,
                "entity_id": token.entity_id,
                "name": token.name,
                "symbol": token.symbol,
                "standard": token.standard,
                "decimals": token.decimals,
                "contract_address": token.contract_address,
                "logo": token.logo,
                "stats": {
                    "warning_price_usd": warning_price_usd if warning_price_usd else 0,
                    "warning_market_cap": warning_market_cap if warning_market_cap else 0,
                    "current_price_usd": token.price_usd if token.price_usd else 0,
                    "current_market_cap": token.market_cap if token.market_cap else 0,
                    "highest_increase_rate": token.price_usd / warning_price_usd if warning_price_usd != 0 else 0
                },
                "chain": chain_infos.get(str(token.chain_id)) if chain_infos.get(str(token.chain_id)) else chain_info,
                "is_native": token.is_native if token.is_native is not None else False,
                "created_at": token.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "updated_at": token.updated_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            }
        except:
            token_data = None
        entities.append(token_data)

    # Cold data to hot data conversion
    await master_cache.set(name=key, value=json.dumps(entities, ensure_ascii=False, cls=JsonResponseEncoder), ex=settings.EXPIRES_FOR_SHOWED_TOKENS)
    return entities
