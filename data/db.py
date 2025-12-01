from pydantic import BaseModel
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession, create_async_engine, close_all_sessions
from sqlalchemy.orm import declarative_base, as_declarative, declared_attr
from sqlalchemy import Column, Boolean, TIMESTAMP
from sqlalchemy.sql import func
from uuid6 import uuid7
from sqlalchemy.dialects.postgresql import UUID


class CustomBase:
    def as_dict(self):
        """
        Dictionary ORM instance
        """
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


# Base = declarative_base()

DatabaseFactory = async_sessionmaker[AsyncSession]

class DatabaseConfig(BaseModel):
    url: str
    pool_size: int = 20
    max_overflow: int = 50
    autoflush: bool = True


    def __init__(
        self, url: str, *,
        pool_size: int = 20,
        max_overflow: int = 50,
        autoflush: bool = True
    ) -> None:
        super().__init__(
            url=url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            autoflush=autoflush
        )


def declare_database(config: DatabaseConfig | None = None, *, url: str | None = None, pool_size: int = 50, max_overflow: int = 70, autoflush: bool = True) -> DatabaseFactory:
    """
    Declare a database connection factory
    """
    if config is not None:
        url = config.url
        pool_size = config.pool_size
        max_overflow = config.max_overflow
        autoflush = config.autoflush
    assert url is not None, "url is required"

    # Retrieve the schema carried by the connector
    schema = "test"
    if "?schema=" in url:
        url, schema = url.rsplit("?schema=", 1)

    return async_sessionmaker(
        create_async_engine(url) if url.startswith('sqlite') else
        create_async_engine(
            url,
            echo=False,
            pool_size=0,
            max_overflow=100,
            pool_timeout=30,
            pool_recycle=300, # 3600
            pool_pre_ping=True,
            connect_args={"server_settings": {"search_path": schema.lower()}}
        ),
        class_=AsyncSession,
        autoflush=autoflush,
        expire_on_commit=False
    )


@as_declarative()
class Base:
    """
    Common fields
    """
    id = Column(UUID(as_uuid=True), default=uuid7, primary_key=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, default=func.timezone('UTC', func.now()), comment="Creation time")
    updated_at = Column(TIMESTAMP, nullable=True, default=func.timezone('UTC', func.now()), onupdate=func.timezone('UTC', func.now()), comment="Update time")