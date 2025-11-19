import json
import decimal
from typing import Optional, List, Dict, Any

from sqlalchemy import select, func, and_, or_, cast, String
from sqlalchemy.orm import selectinload, defer

from apps.intelligence.models import (
    IntelligenceModel, EntityIntelligenceModel, EntityModel, 
    TokenChainDataModel, ChainModel, TokenModel
)
from apps.intelligence import models, schemas
from apps.websocket import services as ws_services
from data import create_logger
from middleware import Request
from views.render import JsonResponseEncoder
import settings


logger = create_logger("dogex-intelligence")

def _build_filters(query_params: schemas.IntelligenceQueryParams) -> List:
    """Build filter conditions for intelligence query"""
    filters = []
    
    if query_params.type:
        if query_params.type == "social":
            filters.append(IntelligenceModel.type.in_(["twitter", "farcaster", "binancesquare"]))
        else:
            filters.append(IntelligenceModel.type == query_params.type)
    
    if query_params.subtype:
        filters.append(IntelligenceModel.subtype == query_params.subtype)
    
    if query_params.is_valuable is not None:
        filters.append(IntelligenceModel.is_valuable == bool(query_params.is_valuable))
    
    if hasattr(query_params, 'key_word') and query_params.key_word:
        filters.append(or_(
            IntelligenceModel.content.ilike(f"%{query_params.key_word}%"),
            cast(IntelligenceModel.analyzed["zh"], String).ilike(f"%{query_params.key_word}%")
        ))
    
    return filters

async def list_intelligence(request: Request, query_params: schemas.IntelligenceQueryParams, page: int, page_size: int):
    """
    Get intelligence list
    """
    master_cache = request.context.mastercache.backend
    offset = (page - 1) * page_size
    
    # Build filters
    filters = _build_filters(query_params)
    filters.extend([
        IntelligenceModel.is_deleted == False,
        IntelligenceModel.is_visible == True
    ])

    # Preload related tables
    entity_load_options = selectinload(
        IntelligenceModel.entity_intelligences
    ).selectinload(
        EntityIntelligenceModel.entity
    ).options(
        selectinload(EntityModel.token_entity).selectinload(TokenModel.chain_datas).selectinload(TokenChainDataModel.chain),
        selectinload(EntityModel.tokendata_entity).selectinload(TokenChainDataModel.chain),
        selectinload(EntityModel.entity_tags),
        selectinload(EntityModel.entity_NewsPlatform),
        selectinload(EntityModel.exchange_platform)
    )

    async with request.context.database.dogex() as session:
        # Base query
        sql = select(IntelligenceModel)

        # Influence level filter
        if hasattr(query_params, 'influence_level') and query_params.influence_level is not None:
            sql = sql.join(IntelligenceModel.entity_intelligences).join(EntityIntelligenceModel.entity)
            filters.append(and_(
                EntityIntelligenceModel.type == "author",
                EntityModel.influence_level == query_params.influence_level
            ))

        # Get total count from cache
        cache_key = f"dogex:intelligence:intelligence_list:count:query_params:{query_params.model_dump_json()}"
        total_cached = await master_cache.get(cache_key)
        
        if total_cached is not None:
            total = int(total_cached.decode("utf-8")) if total_cached.decode("utf-8") else 0
        else:
            # Count total
            count_query = sql.where(*filters).options(defer(IntelligenceModel.extra_datas)).distinct()
            total_count_sql = select(func.count()).select_from(count_query.subquery())
            total = (await session.execute(total_count_sql)).scalar()
            await master_cache.set(name=cache_key, value=total, ex=3600 * 6)

        # Query SQL
        sql = sql.where(*filters).options(
            defer(IntelligenceModel.extra_datas), 
            entity_load_options
        ).order_by(
            IntelligenceModel.published_at.desc()
        ).offset(offset).limit(page_size).distinct()

        intelligences = (await session.execute(sql)).scalars().all()

    # Get chain information for all tokens associated with all intelligence items
    chain_infos = await get_chain_infos(request, intelligences)

    # Process results in batch
    result = []
    ai_agent_info = {
        "avatar": "image/h0bk-B4SP5-3nqM8JpjEXSW9u2dXcDbKGGAvI8m7GIgXPC4J_Yp5dZMKC8TPFb2lrZZPBuF3wCOyvWU091MujA==",
        "name": {"en": "Event Hunter", "zh": "Event Hunter"}
    }
    
    for intelligence in intelligences:
        intelligence_info = schemas.IntelligenceListOutSchema.model_validate(intelligence).model_dump()

        # Supplement displayed associated tokens
        intelligence_info["entities"] = await get_showed_tokens_info(
            request, intelligence_info["showed_tokens"], chain_infos, intelligence
        )

        # Supplement author and monitor_time fields
        intelligence_info["author"] = await ws_services.get_author_info(intelligence_info, request.context)
        intelligence_info["monitor_time"] = await ws_services.get_monitor_time(
            intelligence_info["spider_time"], intelligence_info["published_at"]
        )
        intelligence_info["ai_agent"] = ai_agent_info

        # Remove showed_tokens from response
        intelligence_info.pop("showed_tokens", None)
        result.append(intelligence_info)

    return result, total

async def get_chain_infos(request: Request, intelligences: List) -> Dict[str, Any]:
    """Get chain information for all tokens associated with intelligence items"""
    # Collect unique networks from showed_tokens
    networks = set()
    
    for intelligence in intelligences:
        if intelligence.showed_tokens:
            for showed_token in intelligence.showed_tokens:
                if "slug" in showed_token:
                    networks.add(showed_token["slug"])
    
    # Fallback to entity tokendata if no showed_tokens
    if not networks:
        for intelligence in intelligences:
            for ei in intelligence.entity_intelligences:
                if ei.entity and ei.entity.tokendata_entity:
                    for project_chain_data in ei.entity.tokendata_entity:
                        if project_chain_data.network:
                            networks.add(project_chain_data.network)
    
    if not networks:
        return {}
    
    networks_list = list(networks)
    slave_cache = request.context.slavecache.backend
    master_cache = request.context.mastercache.backend
    
    cache_key = f"dogex:intelligence:chain_infos:networks:{networks_list}"
    cached_data = await slave_cache.get(cache_key)
    
    if cached_data is not None:
        await master_cache.expire(name=cache_key, time=settings.EXPIRES_FOR_CHAIN_INFOS)
        return json.loads(cached_data.decode("utf-8"))

    async with request.context.database.dogex() as session:
        sql = select(
            ChainModel.id, ChainModel.network_id, ChainModel.name,
            ChainModel.symbol, ChainModel.slug, ChainModel.logo
        ).where(ChainModel.slug.in_(networks_list))

        results = (await session.execute(sql)).mappings().all()
        data = {str(chain_info["id"]): dict(chain_info) for chain_info in results}

        await master_cache.set(
            name=cache_key, 
            value=json.dumps(data, ensure_ascii=False, cls=JsonResponseEncoder), 
            ex=settings.EXPIRES_FOR_CHAIN_INFOS
        )
        return data



async def get_showed_tokens_info(request: Request, showed_tokens: Optional[List], chain_infos: Dict, intelligence) -> List[Dict]:
    """Get token information for showed tokens with caching"""
    if not showed_tokens:
        return []
    
    master_cache = request.context.mastercache.backend
    slave_cache = request.context.slavecache.backend
    
    # Check cache first
    cache_key = f"dogex:intelligence:latest_entities:intelligence_id:{intelligence.id}"
    cached_entities = await slave_cache.get(cache_key)
    if cached_entities:
        return json.loads(cached_entities.decode("utf-8"))
    
    # Default chain info
    default_chain_info = {
        "id": None, "network_id": None, "name": None, 
        "symbol": None, "logo": None
    }
    
    # Collect token keys for batch query
    token_keys = [
        (showed_token["slug"], showed_token["contract_address"]) 
        for showed_token in showed_tokens
        if "slug" in showed_token and "contract_address" in showed_token
    ]
    
    if not token_keys:
        return []
    
    # Batch query tokens
    async with request.context.database.dogex() as session:
        conditions = [
            and_(
                TokenChainDataModel.network == network,
                TokenChainDataModel.contract_address == contract_address
            )
            for network, contract_address in token_keys
        ]
        
        sql = select(TokenChainDataModel).where(or_(*conditions))
        tokens = (await session.execute(sql)).scalars().all()
        
        # Build lookup dictionary
        token_dict = {
            (token.network, token.contract_address): token
            for token in tokens
        }
    
    # Process tokens
    entities = []
    for showed_token in showed_tokens:
        try:
            network = showed_token["slug"]
            contract_address = showed_token["contract_address"]
            warning_price_usd = float(showed_token.get("warning_price_usd", 0))
            warning_market_cap = float(showed_token.get("warning_market_cap", 0))
            
            token = token_dict.get((network, contract_address))
            if not token:
                logger.error(f"Token not found - intelligence_id: {intelligence.id}, token: {showed_token}")
                continue
            
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
                    "warning_price_usd": warning_price_usd,
                    "warning_market_cap": warning_market_cap,
                    "current_price_usd": token.price_usd or 0,
                    "current_market_cap": token.market_cap or 0,
                    "highest_increase_rate": (token.price_usd / warning_price_usd) if warning_price_usd > 0 else 0
                },
                "chain": chain_infos.get(str(token.chain_id), default_chain_info),
                "is_native": token.is_native or False,
                "created_at": token.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "updated_at": token.updated_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            }
            entities.append(token_data)
            
        except Exception as e:
            logger.error(f"Error processing token {showed_token}: {e}")
            continue
    
    # Cache results
    await master_cache.set(
        name=cache_key, 
        value=json.dumps(entities, ensure_ascii=False, cls=JsonResponseEncoder), 
        ex=settings.EXPIRES_FOR_SHOWED_TOKENS
    )
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

        # Step 4: Traverse showed_token and retrieve the corresponding token data from the dictionary
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

async def cache_intelligence_next_pages(request: Request, query_params: schemas.IntelligenceQueryParams, page: int, page_size: int, page_to_cache: int):
    """
    Cache the intelligence data for the next page
    """
    master_cache = request.context.mastercache.backend

    for cache_page in range(page+1, page + page_to_cache):
        cache_key = f"aigun:intelligence:next_pages_data:query_params:{query_params.model_dump_json()}:page:{cache_page}:page_size:{page_size}"

        if await master_cache.exists(cache_key):
            continue

        result, total = await list_intelligence(request, query_params, cache_page, page_size)


        mapping = {
            "data": json.dumps(result, cls=JsonResponseEncoder),
            "total": total
        }

        await master_cache.hset(name=cache_key, mapping=mapping)
        await master_cache.expire(cache_key, settings.EXPIRES_FOR_INTELLIGENCE)


async def retrieve_token(request: Request, network: str, address: str):
    async with request.context.database.dogex() as session:
        sql = select(models.TokenChainDataModel).where(
            models.TokenChainDataModel.network == network,
            models.TokenChainDataModel.contract_address == address
        )
        
        token = (await session.execute(sql)).scalars().first()
        if not token:
            logger.warning(f"Token not found: {network}:{address}")
            return {}

        token_info = schemas.TokenInfoOutSchema.model_validate(token).model_dump()
        token_info["highest_increase_rate"] = await get_highest_increase_rate_v2(request, network, address)
        return token_info


async def get_highest_increase_rate_v2(request: Request, network: str, address: str) -> float:
    """Get highest increase rate with caching"""
    cache_key = f"dogex:intelligence:highest_increase_rate:network:{network}:address:{address}"
    
    # Try cache first
    cached_rate = await request.context.slavecache.backend.get(cache_key)
    if cached_rate:
        return float(cached_rate.decode("utf-8"))
    
    try:
        async with request.context.database.dogex() as session:
            sql = select(
                func.max(models.EntityIntelligenceModel.highest_increase_rate)
            ).join(
                models.EntityIntelligenceModel.entity
            ).join(
                models.EntityModel.tokendata_entity
            ).where(
                models.TokenChainDataModel.contract_address == address,
                models.TokenChainDataModel.network == network,
                models.EntityIntelligenceModel.is_deleted == False
            )
            
            max_rate = (await session.execute(sql)).scalars().first() or 0.0
            
            # Cache result
            await request.context.mastercache.backend.set(
                name=cache_key, 
                value=max_rate, 
                ex=settings.EXPIRES_FOR_HIGHEST_INCREASE_RATE
            )
            
            return max_rate
            
    except Exception as e:
        logger.exception(f"Failed to get highest increase rate for {network}:{address}: {e}")
        return 0.0


async def retrieve_intelligence(request: Request, intelligence_id: str):
    async with request.context.database.dogex() as session:
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

        sql = select(models.IntelligenceModel).where(
            models.IntelligenceModel.id == intelligence_id,
            models.IntelligenceModel.is_visible == True,
            models.IntelligenceModel.is_deleted == False
        ).options(entity_load_options)

        intelligence = (await session.execute(sql)).scalars().first()
        if not intelligence:
            return {}

        chain_infos = await get_chain_infos(request, [intelligence])

        result = {
            "intelligence": await get_intelligence_info(intelligence, request, chain_infos)
        }

        # Find author entity
        for entity_intelligence in intelligence.entity_intelligences:
            if entity_intelligence.type == "author" and entity_intelligence.entity:
                result["entity"] = schemas.EntityResponse.model_validate(entity_intelligence.entity).model_dump()
                break

        return result


async def get_intelligence_info(intelligence, request, chain_infos):
    intelligence_info = schemas.IntelligenceWithoutEntitiesOutSchema.model_validate(
        intelligence
    ).model_dump()

    intelligence_info["entities"] = await get_intelligence_related_tokens(
        intelligence, request, chain_infos
    )

    return intelligence_info


async def get_intelligence_related_tokens(intelligence, request: Request, chain_infos):
    """Get intelligence related tokens with caching"""
    cache_key = f"dogex:intelligence:latest_entities:intelligence_id:{intelligence.id}"

    # Check cache first
    cached_tokens = await request.context.slavecache.backend.get(cache_key)
    if cached_tokens:
        return json.loads(cached_tokens.decode("utf-8"))

    # Get token list (prefer adjusted_tokens if available)
    token_list = intelligence.adjusted_tokens[-1] if intelligence.adjusted_tokens else intelligence.showed_tokens
    if not token_list:
        return []

    entities = []
    default_chain_info = {"id": None, "network_id": None, "name": None, "symbol": None, "logo": None}

    async with request.context.database.dogex() as session:
        for showed_token in token_list:
            network = showed_token["slug"]
            contract_address = showed_token["contract_address"]
            warning_price_usd = float(showed_token.get("warning_price_usd") or 0)
            warning_market_cap = float(showed_token.get("warning_market_cap") or 0)

            sql = select(models.TokenChainDataModel).where(
                models.TokenChainDataModel.network == network,
                models.TokenChainDataModel.contract_address == contract_address
            )

            token = (await session.execute(sql)).scalars().first()
            if not token:
                logger.error(f"Token not found for intelligence {intelligence.id}: {showed_token}")
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
                        "warning_price_usd": warning_price_usd,
                        "warning_market_cap": warning_market_cap,
                        "current_price_usd": token.price_usd or 0,
                        "current_market_cap": token.market_cap or 0,
                        "highest_increase_rate": 0
                    },
                    "chain": chain_infos.get(str(token.chain_id), default_chain_info),
                    "created_at": token.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    "updated_at": token.updated_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                }
                entities.append(token_data)
            except Exception as e:
                logger.error(f"Error processing token {contract_address}: {e}")

    # Cache result
    await request.context.mastercache.backend.set(
        name=cache_key,
        value=json.dumps(entities, ensure_ascii=False, cls=JsonResponseEncoder),
        ex=settings.EXPIRES_FOR_SHOWED_TOKENS
    )

    return entities



