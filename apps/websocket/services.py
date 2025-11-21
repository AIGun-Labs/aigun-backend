import json
import settings
from apps.websocket import schemas as ws_schemas
from apps.intelligence import models
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from data.logger import create_logger
from typing import List
from datetime import datetime
from views.render import JsonResponseEncoder


logger = create_logger('aigun-intelligence-ws')


def remove_part_info(intelligence):
    del intelligence["source_id"]
    del intelligence["abstract"]
    del intelligence["is_visible"]
    del intelligence["is_deleted"]

    return intelligence


async def get_author_info(intelligence, context):
    intelligence_id = intelligence["id"] if isinstance(intelligence, dict) else intelligence.id
    cache_key = f"aigun:intelligence:author_info:intelligence_id:{intelligence_id}"

    # Check cache
    cached_info = await context.slavecache.backend.get(cache_key)
    if cached_info:
        await context.mastercache.backend.expire(name=cache_key, time=settings.EXPIRES_FOR_AUTHOR_INFO)
        return json.loads(cached_info.decode("utf-8"))

    default_author_info = {
        "platform": {"id": None, "name": None, "logo": None},
        "slug": None,
        "avatar": None,
        "action": None
    }

    async with context.database.dogex() as session:
        sql = select(models.IntelligenceModel).where(
            models.IntelligenceModel.id == intelligence_id
        ).options(
            selectinload(models.IntelligenceModel.entity_intelligences)
            .selectinload(models.EntityIntelligenceModel.entity)
            .selectinload(models.EntityModel.entity_datasources)
            .selectinload(models.EntityDatasource.account)
        )

        intel = (await session.execute(sql)).scalars().first()
        if not intel or not intel.entity_intelligences:
            return default_author_info

        # Find author entity
        for entity_intelligence in intel.entity_intelligences:
            if entity_intelligence.type != "author" or not entity_intelligence.master_id:
                continue

            account = (await session.execute(
                select(models.AccountModel).where(models.AccountModel.id == entity_intelligence.master_id)
            )).scalars().first()

            if not account:
                logger.error(f"Account not found: {entity_intelligence.master_id} for intelligence {intelligence_id}")
                continue

            platform_name = (entity_intelligence.master_type.strip().split(",", 1)[0][1:]
                             if entity_intelligence.master_type else "twitter")

            data = {
                "platform": {
                    "id": account.id,
                    "name": platform_name,
                    "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b7/X_logo.jpg/960px-X_logo.jpg?20230724061250"
                },
                "slug": account.screen_name,
                "avatar": account.avatar,
                "prompt": None
            }

            # Add prompt for twitter
            if intel.type == "twitter":
                try:
                    description = ws_schemas.twitter_action_prompt_mapping.get(
                        intelligence.get("subtype") if isinstance(intelligence, dict) else intel.subtype,
                        "'s new release on X has sparked investment opportunities."
                    )
                    data["prompt"] = account.name + description
                except:
                    pass

            # Cache and return
            await context.mastercache.backend.set(
                name=cache_key,
                value=json.dumps(data, ensure_ascii=False, cls=JsonResponseEncoder),
                ex=settings.EXPIRES_FOR_AUTHOR_INFO
            )
            return data

    return default_author_info



async def get_monitor_time(created_at, published_at):
    """
    Returns milliseconds
    """
    monitor_time = 0

    if isinstance(created_at, str):
        published_at = int(datetime.fromisoformat(published_at).timestamp() * 1000)
        created_at = int(datetime.fromisoformat(created_at).timestamp() * 1000)

        monitor_time = created_at - published_at

    elif isinstance(created_at, datetime):
        monitor_time = int((created_at - published_at).total_seconds() * 1000)

    return monitor_time


async def get_all_chain_info(intelligence, context):

    chain_id_list = []
    for entity in intelligence["entities"]:
        chain_id_list.append(entity["network"])

    async with context.database.dogex() as session:
        sql = select(
            models.ChainModel.id,
            models.ChainModel.network_id,
            models.ChainModel.name,
            models.ChainModel.symbol,
            models.ChainModel.slug,
            models.ChainModel.logo
        ).where(
            models.ChainModel.slug.in_(chain_id_list)
        )

        results = (await session.execute(sql)).mappings().all()

        results = [dict(item) for item in results]

        # Convert UUID to string to prevent JSON serialization error
        for chain_info in results:
            chain_info["id"] = str(chain_info["id"])
            chain_info["network_id"] = str(chain_info["network_id"])

        return {str(chain_info["slug"]): chain_info  for chain_info in results}


def handle_entity_info(entity_list: List, chain_mapping_info: dict):
    entities = []

    for entity in entity_list:
        data = {
            "id": str(entity.get("id")),
            "entity_id": str(entity.get("entityId")),
            "name": entity.get("name"),
            "symbol": entity.get("symbol"),
            "standard": entity.get("standard"),
            "decimals": entity.get("decimals"),
            "contract_address": entity.get("contractAddress"),
            "logo": entity.get("logo"),
            "stats": {
                "warning_price_usd": entity.get("price_usd") if entity.get("price_usd") else "0",
                "warning_market_cap": entity.get("market_cap") if entity.get("market_cap") else "0",
                "current_price_usd": entity.get("price_usd")  if entity["price_usd"] else "0",
                "current_market_cap": entity.get("market_cap") if entity.get("market_cap") else "0",
                "liquidity": entity.get("liquidity") if entity.get("liquidity") else "0",
                "volume_24h": entity.get("volume_24h") if entity.get("volume_24h") else "0",
                "highest_increase_rate": "0",
            },
            "chain": chain_mapping_info[str(entity.get("network"))],
            "is_native": entity.get("is_native") if entity.get("is_native") is not None else False,
            "created_at": entity.get("createdAt"),
            "updated_at": entity.get("updatedAt")
        }

        entities.append(data)

    return entities