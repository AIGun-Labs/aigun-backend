# AIGun Backend

AIGun is an AI-driven financial intelligence platform that continuously monitors real-time market information from multiple sources, analyzes data using AI agents, and delivers actionable insights to traders via WebSocket streaming.

## Table of Contents

- [Overview](#overview)
- [User Journey](#user-journey)
- [Architecture](#architecture)
- [Open-Source Dependencies](#open-source-dependencies)
- [Getting Started](#getting-started)
- [Deployment](#deployment)
- [API Reference](#api-reference)
- [Configuration](#configuration)

## Overview

In rapidly changing financial markets, information overload is a major challenge. AIGun addresses this by providing an intelligent layer between raw market data and user actions:

- **Real-time Information Monitoring**: Continuously scans data from financial news and Twitter/X
- **AI Agent Analysis**: Proprietary AI agents process information, identifying sentiment and key events
- **Value Extraction**: Automatically identifies relevant cryptocurrencies based on AI analysis
- **Actionable Insights**: Users receive concise, high-value alerts highlighting trading opportunities

## User Journey

```mermaid
flowchart TD
    subgraph Entry["1. Entry Point"]
        A[User Opens App] --> B{Has Account?}
        B -->|No| C[Browse as Guest]
        B -->|Yes| D[Authenticate via JWT]
    end

    subgraph Browse["2. Browse Intelligence"]
        C --> E[View Public Intelligence Feed]
        D --> E
        E --> F{Filter Options}
        F -->|By Type| G[Twitter / News / Exchange]
        F -->|By Value| H[High Value Intelligence]
        F -->|By Keyword| I[Search Specific Topics]
        G --> J[Paginated Results]
        H --> J
        I --> J
    end

    subgraph Analyze["3. Deep Analysis"]
        J --> K[Select Intelligence Item]
        K --> L[View Full Details]
        L --> M{Contains Tokens?}
        M -->|Yes| N[View Token Data]
        N --> O[Price / Market Cap / Holders]
        M -->|No| P[Read Analysis Only]
    end

    subgraph RealTime["4. Real-Time Streaming"]
        D --> Q[Connect WebSocket]
        Q --> R[Send Init Message]
        R --> S[Subscribe to AI Agents]
        S --> T[Receive Live Intelligence]
        T --> U{New Intelligence}
        U -->|Matches Subscription| V[Display Alert]
        U -->|No Match| T
        V --> W[Take Trading Action]
    end

    subgraph Actions["5. User Actions"]
        O --> W
        P --> W
        W --> X{Decision}
        X -->|Buy| Y[Execute Trade]
        X -->|Hold| Z[Continue Monitoring]
        X -->|Ignore| T
        Z --> T
    end
```

### Journey Steps

| Step | Action | Endpoint | Description |
|------|--------|----------|-------------|
| 1 | Authentication | JWT Token | Optional - guests can browse public feed |
| 2 | Browse Feed | `GET /api/v1/intelligence/` | View paginated intelligence with filters |
| 3 | View Details | `GET /api/v1/intelligence/{id}` | Get full intelligence item details |
| 4 | Token Analysis | `GET /api/v1/intelligence/token/info` | Retrieve token price and market data |
| 5 | Real-Time Feed | `WS /ws/v1/intelligence/` | Subscribe to live intelligence stream |
| 6 | Agent Follow | WebSocket Message | Filter stream by specific AI agents |

## Architecture

### System Architecture

```mermaid
flowchart TB
    subgraph Clients["Client Layer"]
        WEB[Web Application]
        MOBILE[Mobile App]
        BOT[Trading Bots]
    end

    subgraph Gateway["API Gateway"]
        LB[Load Balancer]
        CORS[CORS Middleware]
        AUTH[JWT Authentication]
        RATE[Rate Limiter]
    end

    subgraph Application["Application Layer - FastAPI"]
        ROUTER[Dynamic Router]

        subgraph Modules["Auto-Discovered Modules"]
            INTEL[Intelligence Module]
            USER[User Module]
            WS[WebSocket Module]
        end

        subgraph Services["Core Services"]
            CACHE_SVC[Cache Service]
            DB_SVC[Database Service]
            MQ_SVC[Message Queue Service]
        end
    end

    subgraph DataLayer["Data Layer"]
        subgraph Redis["Redis Cluster"]
            MASTER[(Master\nWrites)]
            SLAVE[(Slave\nReads)]
        end

        DB[(PostgreSQL\nPrimary Storage)]

        MQ[RabbitMQ\nMessage Broker]
    end

    subgraph External["External Data Sources"]
        TWITTER[Twitter/X API]
        NEWS[News Feeds]
        CHAIN[Blockchain APIs]
        EXCHANGE[Exchange APIs]
    end

    subgraph AI["AI Processing Layer"]
        AGENTS[AI Agents]
        ANALYSIS[Sentiment Analysis]
        EXTRACT[Entity Extraction]
    end

    %% Client connections
    WEB --> LB
    MOBILE --> LB
    BOT --> LB

    %% Gateway flow
    LB --> CORS
    CORS --> AUTH
    AUTH --> RATE
    RATE --> ROUTER

    %% Router to modules
    ROUTER --> INTEL
    ROUTER --> USER
    ROUTER --> WS

    %% Module to services
    INTEL --> CACHE_SVC
    INTEL --> DB_SVC
    USER --> DB_SVC
    WS --> MQ_SVC
    WS --> CACHE_SVC

    %% Services to data layer
    CACHE_SVC --> MASTER
    CACHE_SVC --> SLAVE
    DB_SVC --> DB
    MQ_SVC --> MQ

    %% External data flow
    TWITTER --> AI
    NEWS --> AI
    CHAIN --> AI
    EXCHANGE --> AI

    %% AI to message queue
    AI --> MQ
    AGENTS --> ANALYSIS
    ANALYSIS --> EXTRACT
    EXTRACT --> MQ
```

### Component Overview

| Layer | Component | Technology | Purpose |
|-------|-----------|------------|---------|
| **Gateway** | Load Balancer | Nginx / Cloud LB | Traffic distribution |
| **Gateway** | Authentication | JWT RS256 | Secure token verification |
| **Gateway** | Rate Limiter | Custom + Redis | Request throttling |
| **Application** | Web Framework | FastAPI 0.115 | Async API server |
| **Application** | WebSocket | Starlette | Real-time streaming |
| **Data** | Primary DB | PostgreSQL 15 | Persistent storage |
| **Data** | Cache | Redis 7 (Master-Slave) | Two-tier caching |
| **Data** | Message Queue | RabbitMQ 3.9+ | Async message distribution |

### Data Flow Architecture

```mermaid
sequenceDiagram
    participant C as Client
    participant API as FastAPI
    participant Cache as Redis
    participant DB as PostgreSQL
    participant MQ as RabbitMQ
    participant AI as AI Agents

    rect rgb(240, 248, 255)
        Note over C,DB: REST API Flow
        C->>API: GET /api/v1/intelligence/
        API->>Cache: Check cache (slave)
        alt Cache Hit
            Cache-->>API: Return cached data
        else Cache Miss
            API->>Cache: Acquire distributed lock
            API->>DB: Query database
            DB-->>API: Return results
            API->>Cache: Store in cache (master)
            API->>API: Trigger prefetch (next 3 pages)
        end
        API-->>C: JSON Response
    end

    rect rgb(255, 248, 240)
        Note over C,AI: WebSocket Flow
        C->>API: WS Connect
        API-->>C: Connection established
        C->>API: init (subscribe agents)
        API->>MQ: Register consumer

        loop Real-time Updates
            AI->>MQ: Publish intelligence
            MQ->>API: Deliver message
            API->>API: Filter by subscriptions
            API-->>C: Push intelligence
        end
    end
```

### Key Architecture Patterns

1. **Application Factory Pattern**: Modular app initialization in `app/__init__.py`
2. **Auto-Discovery**: Modules in `apps/` are automatically registered via `middleware/apploader.py`
3. **Context Injection**: Centralized `Context` class holds all dependencies (cache, db, mq)
4. **Two-Tier Caching**: Master for writes, slave for reads with stampede prevention
5. **Time-Wheel Heartbeat**: Efficient WebSocket connection management (300 slots, 1s tick)

## Open-Source Dependencies

### Core Framework

| Package | Version | License | Description |
|---------|---------|---------|-------------|
| [FastAPI](https://fastapi.tiangolo.com/) | 0.115.14 | MIT | Modern async web framework for building APIs |
| [Starlette](https://www.starlette.io/) | 0.47.1 | BSD-3 | ASGI framework powering FastAPI |
| [Uvicorn](https://www.uvicorn.org/) | latest | BSD-3 | Lightning-fast ASGI server |
| [Pydantic](https://docs.pydantic.dev/) | 2.11.7 | MIT | Data validation using Python type hints |

### Database & ORM

| Package | Version | License | Description |
|---------|---------|---------|-------------|
| [SQLAlchemy](https://www.sqlalchemy.org/) | 2.0.38 | MIT | Python SQL toolkit and ORM |
| [asyncpg](https://github.com/MagicStack/asyncpg) | latest | Apache-2.0 | Fast PostgreSQL driver for asyncio |

### Caching

| Package | Version | License | Description |
|---------|---------|---------|-------------|
| [redis-py](https://github.com/redis/redis-py) | 5.2.1 | MIT | Python client for Redis |

### Message Queue

| Package | Version | License | Description |
|---------|---------|---------|-------------|
| [aio-pika](https://aio-pika.readthedocs.io/) | 9.5.5 | Apache-2.0 | Async RabbitMQ client for asyncio |
| [aiormq](https://github.com/mosquito/aiormq) | 6.8.1 | Apache-2.0 | Pure Python AMQP 0.9.1 client |

### HTTP & Networking

| Package | Version | License | Description |
|---------|---------|---------|-------------|
| [HTTPX](https://www.python-httpx.org/) | 0.28.1 | BSD-3 | Full-featured async HTTP client |
| [websockets](https://websockets.readthedocs.io/) | latest | BSD-3 | WebSocket client and server library |
| [anyio](https://anyio.readthedocs.io/) | 4.9.0 | MIT | Async networking and concurrency library |

### Security & Authentication

| Package | Version | License | Description |
|---------|---------|---------|-------------|
| [python-jose](https://python-jose.readthedocs.io/) | 3.4.0 | MIT | JavaScript Object Signing and Encryption |
| [cryptography](https://cryptography.io/) | latest | Apache-2.0 / BSD-3 | Cryptographic recipes and primitives |
| [pycryptodome](https://pycryptodome.readthedocs.io/) | latest | BSD-2 | Low-level cryptographic primitives |

### Utilities

| Package | Version | License | Description |
|---------|---------|---------|-------------|
| [uuid7](https://github.com/stevesimmons/uuid7) | 0.1.0 | MIT | UUID version 7 implementation |
| [xxhash](https://github.com/ifduyue/python-xxhash) | 3.5.0 | BSD-2 | Extremely fast non-cryptographic hash |
| [orjson](https://github.com/ijl/orjson) | latest | Apache-2.0 / MIT | Fast, correct JSON library |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | 1.1.1 | BSD-3 | Read key-value pairs from .env files |
| [colorama](https://github.com/tartley/colorama) | 0.4.6 | BSD-3 | Cross-platform colored terminal text |
| [yarl](https://github.com/aio-libs/yarl) | 1.19.0 | Apache-2.0 | URL parsing and manipulation |

### Infrastructure (Docker Images)

| Image | Version | Description |
|-------|---------|-------------|
| [python](https://hub.docker.com/_/python) | 3.12-alpine | Python runtime |
| [postgres](https://hub.docker.com/_/postgres) | 15-alpine | PostgreSQL database |
| [redis](https://hub.docker.com/_/redis) | 7-alpine | Redis cache |
| [rabbitmq](https://hub.docker.com/_/rabbitmq) | 3.9+ | RabbitMQ message broker |

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL 14+
- Redis 7+
- RabbitMQ 3.9+

### Quick Start (Local Development)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd aigun-backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # or
   .\venv\Scripts\activate   # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run the application**
   ```bash
   uvicorn app:app --host 0.0.0.0 --port 8000 --reload
   ```

6. **Verify installation**
   ```bash
   curl http://localhost:8000/health
   ```

## Deployment

### Docker Compose (Recommended for Development)

Deploy all services with a single command:

```bash
# Start all services in background
docker-compose up -d

# View real-time logs
docker-compose logs -f aigun-server

# Check service status
docker-compose ps

# Stop all services
docker-compose down

# Stop and remove volumes (full cleanup)
docker-compose down -v
```

**Services started:**
| Service | Port | Description |
|---------|------|-------------|
| PostgreSQL | 5432 | Primary database |
| Redis | 6379 | Cache layer |
| AIGun Server | 8000 | Application |

### Docker Standalone

Build and run the application container independently:

```bash
# Build the Docker image
docker build -t aigun-backend:latest .

# Run with environment file
docker run -d \
  --name aigun-server \
  -p 8000:8000 \
  --env-file .env \
  aigun-backend:latest

# Run with inline environment variables
docker run -d \
  --name aigun-server \
  -p 8000:8000 \
  -e DATABASE_URL_DOGEX="postgresql+asyncpg://user:pass@host:5432/db" \
  -e CACHE_URL="redis://redis:6379/0" \
  -e SLAVE_CACHE_URL="redis://redis:6379/0" \
  aigun-backend:latest
```

### Production Deployment

#### 1. Environment Configuration

Create production environment file:

```bash
# Required variables
DATABASE_URL_DOGEX=postgresql+asyncpg://user:password@db-host:5432/aigun?schema=public
CACHE_URL=redis://:password@redis-master:6379/0
SLAVE_CACHE_URL=redis://:password@redis-slave:6379/0
RABBIT_URL=amqp://user:password@rabbitmq:5672/
JWT_PUBLIC_FILE=/etc/aigun/keys/pub.pem

# Optional tuning
GLOBAL_LIMIT_TIMES=150
GLOBAL_LIMIT_SECONDS=60
ENV=production
LOGGING_FORMAT=json
```

#### 2. Process Manager (Gunicorn)

```bash
# Install Gunicorn
pip install gunicorn

# Run with Uvicorn workers
gunicorn app:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

#### 3. Reverse Proxy (Nginx)

```nginx
upstream aigun_backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

server {
    listen 80;
    server_name api.yourdomain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/ssl/certs/your-cert.pem;
    ssl_certificate_key /etc/ssl/private/your-key.pem;

    # REST API endpoints
    location / {
        proxy_pass http://aigun_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket endpoints
    location /ws/ {
        proxy_pass http://aigun_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }

    # Health check (no auth required)
    location /health {
        proxy_pass http://aigun_backend;
        access_log off;
    }
}
```

#### 4. Systemd Service

```ini
# /etc/systemd/system/aigun.service
[Unit]
Description=AIGun Backend API
After=network.target postgresql.service redis.service

[Service]
Type=exec
User=aigun
Group=aigun
WorkingDirectory=/opt/aigun-backend
Environment="PATH=/opt/aigun-backend/venv/bin"
ExecStart=/opt/aigun-backend/venv/bin/gunicorn app:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable aigun
sudo systemctl start aigun
sudo systemctl status aigun
```

#### 5. Health Monitoring

```bash
# Health check endpoint
curl -s http://localhost:8000/health | jq

# Expected response
{
  "status": "healthy",
  "services": {
    "postgresql": {"status": "healthy", "response_time": 0.003},
    "redis": {"status": "healthy", "response_time": 0.001},
    "rabbitmq": {"status": "healthy", "response_time": 0.015}
  }
}
```

### Kubernetes Deployment

For Kubernetes environments, ensure:

1. **ConfigMap** for non-sensitive environment variables
2. **Secrets** for database passwords and JWT keys
3. **HorizontalPodAutoscaler** for automatic scaling
4. **Ingress** with WebSocket support annotations
5. **PersistentVolumeClaims** for database storage

## API Reference

### REST Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/` | No | Server time and IP |
| `GET` | `/ping` | No | Simple health check |
| `GET` | `/health` | No | Comprehensive service health |
| `GET` | `/api/v1/intelligence/` | Optional | List intelligence (paginated) |
| `GET` | `/api/v1/intelligence/{id}` | Optional | Get intelligence detail |
| `GET` | `/api/v1/intelligence/entities` | Optional | Get token data for intelligence |
| `GET` | `/api/v1/intelligence/token/info` | Optional | Get detailed token information |

### WebSocket

| Endpoint | Description |
|----------|-------------|
| `WS /ws/v1/intelligence/` | Real-time intelligence streaming |

**Message Types:**
- `init` - Initialize connection with subscriptions
- `ping` - Client heartbeat (send every 60s)
- `heartbeat` - Server heartbeat response
- `follow_agent` - Subscribe to AI agent
- `unfollow_agent` - Unsubscribe from AI agent
- `message` - Intelligence data push

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL_DOGEX` | Yes | - | PostgreSQL connection string |
| `CACHE_URL` | Yes | - | Redis master URL |
| `SLAVE_CACHE_URL` | Yes | - | Redis slave URL |
| `RABBIT_URL` | Yes | - | RabbitMQ connection string |
| `JWT_PUBLIC_FILE` | Yes | - | Path to RS256 public key |
| `ENV` | No | `dev` | Environment (dev/production/testing) |
| `GLOBAL_LIMIT_TIMES` | No | `150` | Rate limit request count |
| `GLOBAL_LIMIT_SECONDS` | No | `60` | Rate limit window (seconds) |
| `LOGGING_FORMAT` | No | `json` | Log format (json/text) |

### Testing

```bash
# Run intelligence module tests
python -m pytest apps/intelligence/test_views.py -v

# Run with coverage
python -m pytest apps/intelligence/test_views.py -v --cov=apps/intelligence
```

## Links

- [Website](https://www.aigun.ai/)
- [X (Twitter)](https://x.com/aigun_ai)
- [Telegram](https://t.me/AIGunX)

## License

Proprietary - All rights reserved

---

**Built by the AIGun Team**
