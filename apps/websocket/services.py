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


logger = create_logger('dogex-intelligence-ws')


def remove_part_info(intelligence):
    del intelligence["source_id"]
    del intelligence["abstract"]
    del intelligence["is_visible"]
    del intelligence["is_deleted"]

    return intelligence


async def get_author_info(intelligence, context):
    slave_cache = context.slavecache.backend
    master_cache = context.mastercache.backend

    intelligence_subtype = intelligence["subtype"]

    # Check cache
    author_info = await slave_cache.get(f"dogex:intelligence:author_info:intelligence_id:{str(intelligence["id"])}")
    if author_info is not None:
        await master_cache.expire(name=f"dogex:intelligence:author_info:intelligence_id:{str(intelligence["id"])}", time=settings.EXPIRES_FOR_AUTHOR_INFO)
        return json.loads(author_info.decode("utf-8"))

    # Query database
    if isinstance(intelligence, dict):
        intelligence_id = intelligence["id"]
    else:
        intelligence_id = intelligence.id

    author_info = {
        "platform": {
            "id": None,
            "name": None,
            "logo": None
        },
        "slug": None,
        "avatar": None,
        "action": None
    }

    async with context.database.dogex() as session:
        sql = select(
            models.IntelligenceModel
        ).where(
            models.IntelligenceModel.id == intelligence_id
        ).options(
            selectinload(
                models.IntelligenceModel.entity_intelligences
            ).selectinload(
                models.EntityIntelligenceModel.entity
            ).selectinload(
                models.EntityModel.entity_datasources
            ).selectinload(
                models.EntityDatasource.account
            )
        )

        intelligence = (await session.execute(sql)).scalars().first()

        # Filter entities with type 'author'
        if intelligence and intelligence.entity_intelligences:
            for entity_intelligence in intelligence.entity_intelligences:
                if entity_intelligence.type == "author":

                    account_id = entity_intelligence.master_id
                    if not account_id:
                        return author_info

                    sql = select(
                        models.AccountModel
                    ).where(
                        models.AccountModel.id == account_id
                    )

                    account = (await session.execute(sql)).scalars().first()
                    if not account:
                        logger.error(f"No corresponding account data for intelligence, account_id:{account_id}, intelligence_id:{intelligence_id}")
                        return author_info

                    name = entity_intelligence.master_type.strip().split(",", maxsplit=1)[0][1:] if entity_intelligence.master_type else "twitter"

                    logo_mapping = {
                        "twitter": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b7/X_logo.jpg/960px-X_logo.jpg?20230724061250"
                    }

                    data = {
                        "platform": {
                            "id": account.id,
                            "name": name,
                            "logo": logo_mapping[name]
                        },
                        "slug": account.screen_name,
                        "avatar": account.avatar,
                        "prompt": None
                    }

                    # Supplement operation type prompt
                    try:
                        if intelligence.type == "twitter":
                            author_name = account.name
                            # action = ws_schemas.twitter_action_prompt_mapping[intelligence.subtype]
                            # end = ws_schemas.is_valuable_end_prompt_mapping[intelligence.is_valuable]
                            try:
                                description = ws_schemas.twitter_action_prompt_mapping[intelligence_subtype]
                            except KeyError:
                                description = "'s new release on X has sparked investment opportunities."

                            data["prompt"] = author_name + description
                    except:
                        pass

                    await master_cache.set(name=f"dogex:intelligence:author_info:intelligence_id:{str(intelligence.id)}", value=json.dumps(data, ensure_ascii=False, cls=JsonResponseEncoder), ex=settings.EXPIRES_FOR_AUTHOR_INFO)

                    return data



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