FROM python:3.12.4-alpine AS build

RUN pip install aio_pika  redis redis-om
RUN pip install asyncpg   sqlalchemy
RUN pip install fastapi  uvicorn  httpx[cli,http2]  requests aiohttp  curl_cffi
RUN pip install uuid6 email_validator  cryptography
RUN pip install orjson  fastapi_limiter websockets
RUN pip install colorama   python-jose  pycryptodome


FROM build AS deploy

WORKDIR /app

COPY . .