FROM python:3.12.4-alpine AS build

RUN apk add --no-cache gcc musl-dev libffi-dev

RUN pip install --no-cache-dir aio_pika redis redis-om
RUN pip install --no-cache-dir asyncpg sqlalchemy
RUN pip install --no-cache-dir fastapi uvicorn httpx requests aiohttp
RUN pip install --no-cache-dir uuid6 uuid7 email_validator cryptography
RUN pip install --no-cache-dir orjson fastapi_limiter websockets
RUN pip install --no-cache-dir colorama python-jose pycryptodome
RUN pip install --no-cache-dir python-dotenv xxhash pydantic


FROM build AS deploy

WORKDIR /app

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]