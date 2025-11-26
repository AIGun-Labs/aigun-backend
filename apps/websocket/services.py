import json
import settings
from apps.websocket import schemas as ws_schemas
from apps.intelligence import models
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from data.logger import create_logger
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from views.render import JsonResponseEncoder


logger = create_logger('aigun-intelligence-ws')


def remove_part_info(intelligence: Dict[str, Any]) -> Dict[str, Any]:
    """Remove unnecessary fields from intelligence data"""
    for key in ["source_id", "abstract", "is_visible", "is_deleted"]:
        intelligence.pop(key, None)
    return intelligence


async def get_author_info(intelligence: Union[Dict[str, Any], Any], context: Any) -> Dict[str, Any]:
    """Get author information with caching"""
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
        # Query with eager loading
        intel = (await session.execute(
            select(models.IntelligenceModel)
            .where(models.IntelligenceModel.id == intelligence_id)
            .options(
                selectinload(models.IntelligenceModel.entity_intelligences)
                .selectinload(models.EntityIntelligenceModel.entity)
                .selectinload(models.EntityModel.entity_datasources)
                .selectinload(models.EntityDatasource.account)
            )
        )).scalars().first()

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

            platform_name = (
                entity_intelligence.master_type.strip().split(",", 1)[0][1:]
                if entity_intelligence.master_type else "twitter"
            )

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
                subtype = intelligence.get("subtype") if isinstance(intelligence, dict) else intel.subtype
                description = ws_schemas.twitter_action_prompt_mapping.get(
                    subtype, "'s new release on X has sparked investment opportunities."
                )
                data["prompt"] = account.name + description

            # Cache and return
            await context.mastercache.backend.set(
                name=cache_key,
                value=json.dumps(data, ensure_ascii=False, cls=JsonResponseEncoder),
                ex=settings.EXPIRES_FOR_AUTHOR_INFO
            )
            return data

    return default_author_info


async def get_monitor_time(created_at: Union[str, datetime, None], published_at: Union[str, datetime, None]) -> int:
    """Calculate monitor time in milliseconds between created_at and published_at"""
    try:
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        if isinstance(published_at, str):
            published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))

        if isinstance(created_at, datetime) and isinstance(published_at, datetime):
            return int((created_at - published_at).total_seconds() * 1000)

        return 0
    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to calculate monitor time: {e}")
        return 0


async def get_all_chain_info(intelligence: Dict[str, Any], context: Any) -> Dict[str, Dict[str, Any]]:
    """Get chain information for all entities in intelligence"""
    chain_slugs = {entity["network"] for entity in intelligence.get("entities", [])}

    if not chain_slugs:
        return {}

    async with context.database.dogex() as session:
        results = (await session.execute(
            select(
                models.ChainModel.slug,
                models.ChainModel.id,
                models.ChainModel.network_id,
                models.ChainModel.name,
                models.ChainModel.symbol,
                models.ChainModel.logo
            ).where(models.ChainModel.slug.in_(chain_slugs))
        )).mappings().all()

        return {
            chain["slug"]: {
                "id": str(chain["id"]),
                "network_id": str(chain["network_id"]),
                "name": chain["name"],
                "symbol": chain["symbol"],
                "slug": chain["slug"],
                "logo": chain["logo"]
            }
            for chain in results
        }


def handle_entity_info(entity_list: List[Dict[str, Any]], chain_mapping_info: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Transform entity list with chain information"""
    return [
        {
            "id": str(e.get("id")),
            "entity_id": str(e.get("entityId")),
            "name": e.get("name"),
            "symbol": e.get("symbol"),
            "standard": e.get("standard"),
            "decimals": e.get("decimals"),
            "contract_address": e.get("contractAddress"),
            "logo": e.get("logo"),
            "stats": {
                "warning_price_usd": e.get("price_usd") or "0",
                "warning_market_cap": e.get("market_cap") or "0",
                "current_price_usd": e.get("price_usd") or "0",
                "current_market_cap": e.get("market_cap") or "0",
                "liquidity": e.get("liquidity") or "0",
                "volume_24h": e.get("volume_24h") or "0",
                "highest_increase_rate": "0",
            },
            "chain": chain_mapping_info.get(e.get("network"), {}),
            "is_native": e.get("is_native", False),
            "created_at": e.get("createdAt"),
            "updated_at": e.get("updatedAt")
        }
        for e in entity_list
    ]