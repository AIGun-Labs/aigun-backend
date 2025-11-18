import json
import decimal
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


async def get_intelligence_latest_entities_v2(request: Request, intelligence_id_list: list[str]):
    """
    Get real-time token data for intelligence
    """
    master_cache = request.context.mastercache.backend
    slave_cache = request.context.slavecache.backend

    data_dict = {}
    for intelligence_id in intelligence_id_list:
        key = f"dogex:intelligence:latest_entities:intelligence_id:{str(intelligence_id)}"

        cache_data  = await slave_cache.get(key)


        data_dict[key] = cache_data

    result = data_dict

    data = {}
    showed_token_intelligence_id_list = []  # Intelligence that needs to be checked back through showed_token

    for key, val in result.items():
        intel_id = key.strip().rsplit(":", maxsplit=1)[-1]
        if not val:
            showed_token_intelligence_id_list.append(intel_id)
            continue
        # val = json.loads(val.decode("utf-8"))
        data[intel_id] = val

    # Check back the showed_token field of the intelligence list
    async with request.context.database.dogex() as session:
        sql = select(
            models.IntelligenceModel.id,
            models.IntelligenceModel.showed_tokens,
            models.IntelligenceModel.adjusted_tokens
        ).where(
            models.IntelligenceModel.id.in_(showed_token_intelligence_id_list)
        )

        # Batch get showed_token
        result = (await session.execute(sql)).mappings().all()
        if not result:
            return await refresh_token_data_from_cache_v2(request, data)

        # Convert to serializable types
        result = [dict(item) for item in result]

        for intel_data in result:
            intel_id = intel_data["id"]
            showed_tokens = intel_data["showed_tokens"]
            adjusted_tokens = intel_data["adjusted_tokens"]

            if adjusted_tokens is not None:
                showed_tokens = adjusted_tokens[-1]

            showed_token_infos = await get_showed_token_without_chain_infos(request, showed_tokens, intel_id)

            data[intel_id] = showed_token_infos

        return await refresh_token_data_from_cache_v2(request, data)


async def refresh_token_data_from_cache_v2(request: Request, data):
    """
    Only perform real-time queries for tokens within the visible screen
    """
    master_cache = request.context.mastercache.backend
    slave_cache = request.context.slavecache.backend

    for key, token_list in data.items():

        refreshed_token_list = []
        # Get each token data from cache
        for token in token_list:
            network = token.get("chain", {}).get("slug", "")
            address = token.get("contract_address", "")

            # Get cached token data
            token_cache_key = f"token:network:{network}:address:{address}"

            token_data = await slave_cache.get(token_cache_key)
            if token_data:
                token_data = json.loads(token_data.decode("utf-8"), parse_float=decimal.Decimal)

                # Update token data
                token["stats"]["current_price_usd"] = token_data.get("price_usd") if token_data.get("price_usd") else token["stats"]["current_price_usd"]
                token["stats"]["current_market_cap"] = token_data.get("market_cap") if token_data.get("market_cap") else token["stats"]["current_market_cap"]
                token["stats"]["liquidity"] = token_data.get("liquidity") if token_data.get("liquidity") else token["stats"]["liquidity"]
                token["stats"]["volume_24h"] = token_data.get("volume_24h") if token_data.get("volume_24h") else token["stats"]["volume_24h"]


            refreshed_token_list.append(token)

        data[key] = refreshed_token_list

    return data


async def get_showed_token_without_chain_infos(request: Request, showed_tokens: Optional[List], intelligence_id):
    """
    showed token data
    """
    master_cache = request.context.mastercache.backend
    slave_cache = request.context.slavecache.backend

    # First get hot data from cache
    key = f"dogex:intelligence:latest_entities:intelligence_id:{str(intelligence_id)}"
    entities = await slave_cache.get(key)
    if entities:
        return json.loads(entities.decode("utf-8"))

    # Compatible with empty showed_tokens situation (no cold data conversion)
    entities = []

    # The passed showed_tokens have already been filtered from adjusted_token and showed_tokens
    if not showed_tokens:
        return []

    # showed_tokens exist (actual data that has been displayed to users after cooling down, no need to sort or filter again)
    # Step 1: Collect all (network, contract_address) pairs that need to be queried
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

        sql = select(models.TokenChainDataModel).where(
            or_(*conditions)
        ).options(
            selectinload(models.TokenChainDataModel.chain)
        )

        tokens = (await session.execute(sql)).scalars().all()

        # Step 3: Build lookup dictionary with key as (network, contract_address)
        token_dict = {
            (token.network, token.contract_address): token
            for token in tokens
        }

        # todo Step 4: Traverse showed_token and retrieve the corresponding token data from the dictionary
        for showed_token in showed_tokens:
            network = showed_token["slug"]
            contract_address = showed_token["contract_address"]
            warning_price_usd = float(showed_token["warning_price_usd"])
            warning_market_cap = float(showed_token["warning_market_cap"])

            try:
                liquidity = float(showed_token["liquidity"])
            except:
                liquidity = 0
            try:
                volume_24h = float(showed_token["volume_24h"])
            except:
                volume_24h = 0

            # Find the token from the dictionary
            token = token_dict.get((network, contract_address))

            if not token:
                logger.error(
                    f"The token in showed_token does not exist，intelligence_id: {str(intelligence_id)}, token info：{showed_token}")
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
                        "liquidity": token.liquidity if token.liquidity else 0,
                        "volume_24h": token.volume_24h if token.volume_24h else 0,
                        "highest_increase_rate": "0"
                    },
                    "chain": {
                        "id": token.chain.id,
                        "network_id": token.chain.network_id,
                        "name": token.chain.name,
                        "symbol": token.chain.symbol,
                        "slug": token.chain.slug,
                        "logo": token.chain.logo
                    },
                    "created_at": token.created_at,
                    "updated_at": token.updated_at,
                    "intel_version": 100
                }
            except:
                token_data = None
            entities.append(token_data)
        # cold to hot
        await master_cache.set(name=key, value=json.dumps(entities, ensure_ascii=False, cls=JsonResponseEncoder), ex=settings.EXPIRES_FOR_SHOWED_TOKENS)
        return entities



async def retrieve_token(request: Request, network: str, address: str):


    async with request.context.database.dogex() as session:
        sql = select(
            models.TokenChainDataModel
        ).where(
            models.TokenChainDataModel.network == network,
            models.TokenChainDataModel.contract_address == address
        )

        token = (await session.execute(sql)).scalars().first()

        if not token:

            logger.warning(f"Token does not exist，network: {network}, address: {address}")
            return {}

        token_info = schemas.TokenInfoOutSchema.model_validate(token).model_dump()

        token_info["highest_increase_rate"] = await get_highest_increase_rate_v2(request, network, address)

        return token_info


async def get_highest_increase_rate_v2(request: Request, network: str, address: str):
    """
    new version to get the highest increase rate
    """
    try:
        master_cache = request.context.mastercache.backend
        slave_cache = request.context.slavecache.backend
        key = f"dogex:intelligence:highest_increase_rate:network:{network}:address:{address}"

        # get from cache
        highest_increase_rate = await slave_cache.get(key)
        if highest_increase_rate:
            return float(highest_increase_rate.decode("utf-8"))

        async with request.context.database.dogex() as session:
            # Take the highest profit value among all intelligence (the token may appear in multiple intelligence, and multiple intelligence represent multiple highest profits)
            sql = select(
                func.max(models.EntityIntelligenceModel.highest_increase_rate).label('max_rate')
            ).join(
                models.EntityIntelligenceModel.entity
            ).join(
                models.EntityModel.tokendata_entity
            ).where(
                and_(
                    models.TokenChainDataModel.contract_address == address,
                    models.TokenChainDataModel.network == network,
                    models.EntityIntelligenceModel.is_deleted == False
                )
            )

            max_rate = (await session.execute(sql)).scalars().first()
            if not max_rate:
                max_rate = 0.0

            await master_cache.set(name=key, value=max_rate, ex=settings.EXPIRES_FOR_HIGHEST_INCREASE_RATE)

            return max_rate

    except Exception as e:
        logger.exception(f"Failed to obtain all the intelligence of the token and the maximum profit, {e}")
        max_rate = 0.0
        return max_rate



async def retrieve_intelligence(request: Request, intelligence_id: str):

    async with request.context.database.dogex() as session:

        # Preloading relevant tables
        entity_load_options = (
            selectinload(IntelligenceModel.entity_intelligences)
            .selectinload(EntityIntelligenceModel.entity)
            .options(
                selectinload(EntityModel.token_entity)
                .selectinload(TokenModel.chain_datas)
                .selectinload(TokenChainDataModel.chain),
                selectinload(EntityModel.tokendata_entity).selectinload(
                    TokenChainDataModel.chain
                ),
                selectinload(EntityModel.entity_tags),
                selectinload(EntityModel.entity_NewsPlatform),
                selectinload(EntityModel.exchange_platform),
            )
        )


        # SQL
        sql = (
            select(models.IntelligenceModel)
            .where(
                models.IntelligenceModel.id == intelligence_id,
                models.IntelligenceModel.is_visible == True,
                models.IntelligenceModel.is_deleted == False,
            )
            .options(entity_load_options)
        )

        intelligence = (await session.execute(sql)).scalars().first()

        # Intelligence does not exist
        if intelligence is None:
            return {}

        # Get all chain information
        chain_infos = await get_chain_infos(request, [intelligence])

        # Extract entities
        intel_dict = {
            "intelligence": await get_intelligence_info(
                intelligence, request, chain_infos
            )
        }

        # The entity details of the entity intelligence association table with type author
        for entity_intelligence in intelligence.entity_intelligences:
            if entity_intelligence.type == "author":
                if entity_intelligence.entity:
                    intel_dict["entity"] = schemas.EntityResponse.model_validate(
                        entity_intelligence.entity
                    ).model_dump()

        return intel_dict


async def get_intelligence_info(intelligence, request, chain_infos):

    # The data of the intelligence itself
    intelligence_info: dict = (
        schemas.IntelligenceWithoutEntitiesOutSchema.model_validate(intelligence).model_dump()
    )

    related_tokens: Optional[List] = await get_intelligence_related_tokens(
        intelligence, request, chain_infos
    )

    intelligence_info["entities"] = related_tokens

    return intelligence_info


async def get_intelligence_related_tokens(intelligence, request: Request, chain_infos):
    """
    Obtain intelligence related tokens
    """
    master_cache = request.context.mastercache.backend
    slave_cache = request.context.slavecache.backend

    # Chain default model
    chain_info = {
        "id": None,
        "network_id": None,
        "name": None,
        "symbol": None,
        "logo": None,
    }

    # search for hot data first
    key = f"dogex:intelligence:latest_entities:intelligence_id:{str(intelligence.id)}"
    related_tokens = await slave_cache.get(key)
    if related_tokens:
        return json.loads(related_tokens.decode("utf-8"))

    entities = []

    token_list = intelligence.showed_tokens

    # If there is manual alignment, take the manually aligned data
    if intelligence.adjusted_tokens is not None:
        data =  intelligence.adjusted_tokens
        token_list = data[-1]

    if not token_list:
        return []

    for showed_token in token_list:
        network = showed_token["slug"]
        contract_address = showed_token["contract_address"]
        warning_price_usd = (float(showed_token["warning_price_usd"]) if showed_token["warning_price_usd"] else 0 )
        warning_market_cap = (float(showed_token["warning_market_cap"]) if showed_token["warning_market_cap"] else 0)

        async with request.context.database.dogex() as session:
            sql = select(models.TokenChainDataModel).where(
                models.TokenChainDataModel.network == network,
                models.TokenChainDataModel.contract_address == contract_address,
            )

            token = (await session.execute(sql)).scalars().first()
            if not token:
                logger.error(f"The token for cooling does not exist，intelligence_id: {str(intelligence.id)}, token info：{showed_token}")
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
                        "warning_price_usd": (warning_price_usd if warning_price_usd else 0),
                        "warning_market_cap": (warning_market_cap if warning_market_cap else 0),
                        "current_price_usd": token.price_usd if token.price_usd else 0,
                        "current_market_cap": (token.market_cap if token.market_cap else 0),
                        "highest_increase_rate": 0,
                    },
                    "chain": (chain_infos.get(str(token.chain_id)) if chain_infos.get(str(token.chain_id)) else chain_info),
                    "created_at": token.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    "updated_at": token.updated_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                }
            except:
                token_data = None
            entities.append(token_data)

    await master_cache.set(
        name=key,
        value=json.dumps(entities, ensure_ascii=False, cls=JsonResponseEncoder),
        ex=settings.EXPIRES_FOR_SHOWED_TOKENS,
    )
    return entities


