import redis.asyncio as aioredis
from pydantic import BaseModel, Field, field_serializer, field_validator, computed_field, SerializationInfo
from typing import TypeVar, TypeVarTuple, Unpack, Any, overload, AsyncGenerator, Generator, Type, Tuple
import json as jsonlib
import asyncio
import yarl
import re


ModelType = TypeVar("ModelType", bound=BaseModel)
_Type = TypeVar("_Type")
_TypeGroup = TypeVarTuple("_TypeGroup")

__all__ = ["RedisConfig", "Cache"]


REDIS_URL_RE = re.compile(r'redis://(?::(?P<password>[^:@]+)@)?(?P<host>[^:@]+):(?P<port>\d+)/(?P<db>\d+)(?:\?(?P<query>.*))?')


class RedisConfig(BaseModel):
    host: str = "localhost"
    port: int = 6379
    password: str | None = None
    db: int = 0
    encoding: str | None = None

    def __init__(self, url: str | yarl.URL | None = None, **kwargs):
        if url is not None:
            if isinstance(url, str):
                if '#' in url:
                    d = REDIS_URL_RE.match(url).groupdict()
                    url = yarl.URL(f"redis://{d['host']}:{d['port']}/{d['db']}{f'?{d['query']}' if d['query'] else ''}").with_password(d['password'])
                else:
                    url = yarl.URL(url)
            kwargs.update({
                'host': url.host,
                'port': url.port,
                'password': url.password,
                'db': int(url.path[1:] or 0),
                'encoding': url.query.get('encoding'),
            })
        super().__init__(**kwargs)

    @field_serializer("encoding", when_used='always')
    @classmethod
    def serialize_encoding(cls, value: str | None):
        return value or 'utf-8'

    @computed_field
    @property
    def decode_responses(self) -> bool:
        return self.encoding is not None


class Cache:
    def __init__(
        self,
        config: RedisConfig | None = None,
        *,
        host: str | None = None,
        port: int = 6379,
        password: str | None = None,
        db: int | str = 0,
        loop: asyncio.AbstractEventLoop | None = None
    ) -> None:
        params = config.model_dump() if config is not None else {}
        if host is not None:
            params['host'] = host
        if port != 6379:
            params['port'] = port
        if password is not None:
            params['password'] = password
        if db != 0:
            params['db'] = db
        # Prohibit using decode_responses parameter and custom encoding
        self._redis = aioredis.Redis(**params)
        self._loop = loop or asyncio.get_event_loop()

    @property
    def backend(self) -> aioredis.Redis:
        """
        Get cache backend object
        """
        return self._redis

    async def close(self):
        await self._redis.close()

    async def delete(self, key: str):
        """
        Delete data from cache

        :param key: Cache key
        """
        await self._redis.delete(str(key))

    @overload
    async def get(self, key: str, model: Type[_Type], *,
                  strict: bool | None = None, context: dict[str, Any] | None = None) -> _Type | None:
        """
        Get data from cache

        :param key: Cache key
        :param model: Data model (return given type or None)
        1. If specified as pydantic, automatic JSON deserialization will be performed
        2. If specified as bytes, raw bytes data will be returned directly
        3. If specified as str, UTF-8 decoding will be used
        4. If specified as int, big-endian conversion will be used
        5. If specified as other types, json.loads will be used for deserialization and returned as that type
        """
        ...

    @overload
    async def get(self, key: str, model: Type[Tuple[Unpack[_TypeGroup]]]) -> Tuple[Unpack[_TypeGroup]] | None:
        """
        Get data from cache

        :param key: Cache key
        :param model: Data model (return given type or None)
        1. If specified as pydantic, automatic JSON deserialization will be performed
        2. If specified as bytes, raw bytes data will be returned directly
        3. If specified as str, UTF-8 decoding will be used
        4. If specified as int, big-endian conversion will be used
        5. If specified as other types, json.loads will be used for deserialization and returned as that type
        """
        ...

    @overload
    async def get(self, key: str) -> bytes | None:
        """
        Get data from cache

        :param key: Cache key

        :return: Raw bytes data
        """
        ...

    async def get(self, key: str, model: Type[_Type] | Type[Tuple[Unpack[_TypeGroup]]] | None = None, *,
                  strict: bool | None = None, context: dict[str, Any] | None = None):
        key = str(key)
        data: bytes | None = await self._redis.get(key)
        if data is None:
            return None
        elif model is None or model is bytes:
            return data
        elif model is str:
            return data.decode()
        elif model is int:
            return int.from_bytes(data, 'big')  # Always use big-endian
        elif issubclass(model, BaseModel):
            return model.model_validate_json(data, strict=strict, context=context)
        else:
            return jsonlib.loads(data)

    @overload
    async def set(self, key: str, value: str | bytes, *, expire: float | int | None = None) -> None:
        """
        Set cache data

        :param key: Cache key
        :param value: Cache value (raw data)
        :param expire: Expiration time (milliseconds)
        """
        ...

    @overload
    async def set(self, key: str, value: int, *, expire: float | int | None = None) -> None:
        """
        Set cache data

        :param key: Cache key
        :param value: Cache value (big-endian byte array of int)
        :param expire: Expiration time (milliseconds)
        """
        ...

    @overload
    async def set(self, key: str, value: ModelType, *, expire: float | int | None = None, **dump_kws) -> None:
        """
        Set cache data

        :param key: Cache key
        :param value: Cache value (pydantic model)
        :param expire: Expiration time (milliseconds)
        :param dump_kws: Additional parameters for model_dump_json
        """
        ...

    @overload
    async def set(self, key: str, value: Any, *, expire: float | int | None = None, **dump_kws) -> None:
        """
        Set cache data

        :param key: Cache key
        :param value: Cache value (json serializable data)
        :param expire: Expiration time (milliseconds)
        :param dump_kws: Additional parameters for json.dumps
        """
        ...

    async def set(self, key: str, value: Any, *, expire: float | int | None = None, **dump_kws):
        key = str(key)
        if isinstance(expire, float):
            expire = int(expire * 1000)
        if isinstance(value, (str, bytes)):
            await self._redis.set(key, value, px=expire)
        elif isinstance(value, int):
            await self._redis.set(key, value.to_bytes((value.bit_length() + 7) // 8, 'big'), px=expire)
        elif isinstance(value, BaseModel):
            await self._redis.set(key, value.model_dump_json(**dump_kws), px=expire)
        else:
            await self._redis.set(key, jsonlib.dumps(value, **dump_kws), px=expire)

    @overload
    async def smembers(self, key: str, model: Type[_Type], *,
                       strict: bool | None = None, context: dict[str, Any] | None = None) -> list[_Type]:
        """
        Get all members from Redis set and parse according to specified model type

        :param key: Redis set key name
        :param model: Data model (return list of given type)
        1. If specified as pydantic, automatic JSON deserialization will be performed
        2. If specified as bytes, raw bytes data will be returned directly
        3. If specified as str, UTF-8 decoding will be used
        4. If specified as int, big-endian conversion will be used
        5. If specified as other types, json.loads will be used for deserialization and returned as that type
        """
        ...

    @overload
    async def smembers(self, key: str, model: Type[Tuple[Unpack[_TypeGroup]]]) -> list[Tuple[Unpack[_TypeGroup]]]:
        """
        Get all members from Redis set and parse according to specified model type

        :param key: Redis set key name
        :param model: Data model (return list of given type)
        1. If specified as pydantic, automatic JSON deserialization will be performed
        2. If specified as bytes, raw bytes data will be returned directly
        3. If specified as str, UTF-8 decoding will be used
        4. If specified as int, big-endian conversion will be used
        5. If specified as other types, json.loads will be used for deserialization and returned as that type
        """
        ...

    @overload
    async def smembers(self, key: str) -> list[bytes]:
        """
        Get all members from Redis set

        :param key: Redis set key name

        :return: List of raw bytes data
        """
        ...

    async def smembers(self, key: str, model: Type[_Type] | Type[Tuple[Unpack[_TypeGroup]]] | None = None, *,
                       strict: bool | None = None, context: dict[str, Any] | None = None):
        key = str(key)
        data: set[bytes] = await self._redis.smembers(key)
        result = []
        for item in data:
            if model is None or model is bytes:
                result.append(item)
            elif model is str:
                result.append(item.decode())
            elif model is int:
                result.append(int.from_bytes(item, 'big'))
            elif issubclass(model, BaseModel):
                result.append(model.model_validate_json(item, strict=strict, context=context))
            else:
                result.append(jsonlib.loads(item))
        return result

    async def sadd(self, key: str, *values: Any):
        """
        Add one or more elements to Redis set

        :param key: Redis set key name
        :param values: Elements to add
        :return: Number of elements successfully added to the set
        """
        key = str(key)
        byte_values = []
        for value in values:
            if isinstance(value, str):
                byte_values.append(value.encode())
            elif isinstance(value, bytes):
                byte_values.append(value)
            elif isinstance(value, int):
                byte_values.append(value.to_bytes((value.bit_length() + 7) // 8, 'big'))
            elif isinstance(value, BaseModel):
                byte_values.append(value.model_dump_json().encode())
            else:
                byte_values.append(jsonlib.dumps(value).encode())
        return await self._redis.sadd(key, *byte_values)

    async def srem(self, key: str, *values: Any):
        """
        Remove one or more elements from Redis set

        :param key: Redis set key name
        :param values: Elements to remove
        :return: Number of elements successfully removed from the set
        """
        key = str(key)
        byte_values = []
        for value in values:
            if isinstance(value, str):
                byte_values.append(value.encode())
            elif isinstance(value, bytes):
                byte_values.append(value)
            elif isinstance(value, int):
                byte_values.append(value.to_bytes((value.bit_length() + 7) // 8, 'big'))
            elif isinstance(value, BaseModel):
                byte_values.append(value.model_dump_json().encode())
            else:
                byte_values.append(jsonlib.dumps(value).encode())
        return await self._redis.srem(key, *byte_values)

    async def scard(self, key: str):
        """
        Get the number of elements in Redis set

        :param key: Redis set key name
        :return: Number of elements in the set
        """
        key = str(key)
        return await self._redis.scard(key)

    async def sismember(self, key: str, value: Any):
        """
        Check if element exists in Redis set

        :param key: Redis set key name
        :param value: Element to check
        :return: Return True if element exists in the set, otherwise False
        """
        key = str(key)
        if isinstance(value, str):
            byte_value = value.encode()
        elif isinstance(value, bytes):
            byte_value = value
        elif isinstance(value, int):
            byte_value = value.to_bytes((value.bit_length() + 7) // 8, 'big')
        elif isinstance(value, BaseModel):
            byte_value = value.model_dump_json().encode()
        else:
            byte_value = jsonlib.dumps(value).encode()
        return await self._redis.sismember(key, byte_value)