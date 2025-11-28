# AIGun Backend 🚀

AIGun is the world's first AI exchange platform that revolutionizes how users interact with financial markets through AI-driven intelligence analysis.

## Overview

AIGun is an innovative AI-driven platform that continuously monitors real-time market information, including news feeds and social media (e.g., Twitter), to identify potential investment opportunities. Our intelligent system analyzes data, extracts relevant assets, and presents actionable insights to users, empowering them to make informed trading decisions.

## Problem Statement

In rapidly changing financial markets, information overload is a major challenge. Traders struggle to:

- **Keep up with information:** Manually sift through vast amounts of news and social media to find relevant signals
- **Analyze effectively:** Identify valuable insights from noise and assess the true impact of information on asset prices
- **React quickly:** Seize fleeting opportunities before they disappear

## Our Solution

AIGun addresses these challenges by providing an intelligent layer between raw market data and user actions:

- **Real-time information monitoring:** Continuously scans and absorbs data from multiple sources like financial news and Twitter
- **AI agent analysis:** Proprietary AI agents process information, identifying sentiment, key events, and potential price movements
- **Value extraction:** Automatically identifies relevant cryptocurrencies or other assets based on AI analysis
- **Actionable insights:** Users receive concise, high-value alerts and summaries highlighting potential trading opportunities

## Tech Stack

- **Framework:** FastAPI (Python)
- **Database:** PostgreSQL with SQLAlchemy ORM
- **Cache:** Redis (Master-Slave configuration)
- **Message Queue:** RabbitMQ
- **WebSocket:** Real-time intelligence streaming
- **Authentication:** JWT (RS256)
- **Deployment:** Docker, Uvicorn

## Project Structure

```
aigun-backend/
├── app/                          # Core application
│   ├── dependencies.py           # Dependency injection, auth, rate limiting
│   ├── services.py               # Common service methods
│   ├── views.py                  # Root endpoints (health checks)
│   └── __init__.py               # FastAPI app factory
├── apps/                         # Feature modules
│   ├── intelligence/             # Intelligence/market data module
│   │   ├── models.py             # Database models
│   │   ├── schemas.py            # Pydantic schemas
│   │   ├── services.py           # Business logic
│   │   ├── views.py              # API endpoints
│   │   └── test_views.py         # Unit tests
│   ├── websocket/                # WebSocket real-time streaming
│   │   ├── models.py             # WebSocket models
│   │   ├── schemas.py            # Message schemas
│   │   ├── services.py           # WebSocket services
│   │   └── views.py              # WebSocket endpoints
│   └── user/                     # User & AI Agent module
│       ├── models.py             # User models
│       ├── schemas.py            # User schemas
│       └── services.py           # User services
├── data/                         # Data layer
│   ├── cache.py                  # Redis cache wrapper
│   ├── db.py                     # Database configuration
│   ├── rabbit.py                 # RabbitMQ wrapper
│   ├── fetch.py                  # HTTP client with rate limiting
│   ├── logger.py                 # Logging configuration
│   └── context.py                # Application context
├── middleware/                   # Middleware components
│   ├── request.py                # Request middleware
│   ├── security.py               # JWT authentication
│   ├── limiter.py                # Rate limiting
│   ├── lifespan.py               # App lifecycle management
│   └── apploader.py              # Dynamic app loading
├── views/                        # Response rendering
│   └── render.py                 # JSON/Text response classes
├── utils/                        # Utilities
│   ├── exceptions.py             # Custom exceptions
│   └── status_checker.py         # Service health checks
├── settings.py                   # Configuration
├── docker-compose.yaml           # Docker composition
├── Dockerfile                    # Docker image
└── requirements.txt              # Python dependencies
```

## Key Features

### 1. Intelligence Analysis System
- Real-time market intelligence aggregation from Twitter, news, and exchanges
- AI-powered sentiment analysis and value scoring
- Token/asset extraction and tracking
- Multi-chain support (Ethereum, Solana, BSC, etc.)

### 2. WebSocket Real-Time Streaming
- Subscription-based intelligence delivery
- Heartbeat mechanism with time-wheel algorithm
- AI Agent-based filtering
- Guest and authenticated user support

### 3. Caching Strategy
- Multi-layer caching (hot/cold data separation)
- Cache breakdown prevention with distributed locks
- Pre-fetching for pagination
- TTL-based cache expiration

### 4. Rate Limiting
- Global and per-endpoint rate limiting
- IP-based and user-based throttling
- Cloudflare integration for IP detection

### 5. Authentication & Authorization
- JWT (RS256) token-based authentication
- Optional authentication for public endpoints
- Account validation and obsolescence checks

## API Endpoints

### Health & Status
- `GET /` - Get server time and IP
- `GET /ping` - Simple health check
- `GET /health` - Comprehensive service health check (PostgreSQL, Redis, RabbitMQ)

### Intelligence
- `GET /api/v1/intelligence/` - List intelligence with pagination and filtering
  - Query params: `is_valuable`, `type`, `subtype`, `page`, `size`
- `GET /api/v1/intelligence/entities` - Get latest token data for intelligence IDs
- `GET /api/v1/intelligence/token/info` - Get token details by network and address
- `GET /api/v1/intelligence/{intelligence_id}` - Get intelligence detail

### WebSocket
- `WS /ws/v1/intelligence/` - Real-time intelligence streaming
  - Message types: `init`, `ping`, `heartbeat`, `follow_agent`, `unfollow_agent`

## Database Models

### Core Models
- **IntelligenceModel:** Market intelligence/news items
- **EntityModel:** Entities (influencers, exchanges, projects)
- **TokenModel:** Cryptocurrency projects
- **TokenChainDataModel:** Token data per blockchain
- **ChainModel:** Blockchain networks
- **AccountModel:** Social media accounts (Twitter, etc.)
- **AiAgentModel:** AI analysis agents
- **SubSet:** Subscription sets for WebSocket filtering

## Environment Variables

```env
# Database
DATABASE_URLS=["postgresql+asyncpg://user:pass@host:5432/dbname"]

# Redis
CACHE_URL=redis://:password@host:6379/0
SLAVE_CACHE_URL=redis://:password@host:6379/0

# RabbitMQ
RABBIT_URL=amqp://user:pass@host:5672/

# JWT
JWT_PUBLIC_KEY=<RS256_PUBLIC_KEY>

# Rate Limiting
LIMITER_CONFIG={"GLOBAL_THROTTLE_RATES": {"limit_times": 100, "limit_seconds": 60}}

# Cache Expiration (seconds)
EXPIRES_FOR_INTELLIGENCE=300
EXPIRES_FOR_CHAIN_INFOS=3600
EXPIRES_FOR_SHOWED_TOKENS=300
EXPIRES_FOR_AUTHOR_INFO=3600
EXPIRES_FOR_AI_AGENT_LIST=86400

# Pagination
PAGE=1
PAGE_SIZE=20
MIN_PAGE_SIZE=1
MAX_PAGE_SIZE=100

# Logging
LOGGING_FORMAT=json  # or "text"

# Environment
ENV=production
```

## Installation & Setup

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- RabbitMQ 3.9+

### Local Development

1. **Clone the repository**
```bash
git clone <repository-url>
cd aigun-backend
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
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

### Docker Deployment

1. **Build and run with Docker Compose**
```bash
docker-compose up -d
```

2. **View logs**
```bash
docker-compose logs -f aigun-server
```

3. **Stop services**
```bash
docker-compose down
```

## WebSocket Usage

### Connection Flow

1. **Connect to WebSocket**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/v1/intelligence/');
```

2. **Send init message**
```javascript
ws.send(JSON.stringify({
  type: 'init',
  data: {
    subscriptions: 'agent-id-1#agent-id-2'  // AI Agent subscription IDs
  }
}));
```

3. **Receive welcome message**
```javascript
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'welcome') {
    console.log('Connected:', data.message);
  }
};
```

4. **Send heartbeat (every 60s)**
```javascript
setInterval(() => {
  ws.send(JSON.stringify({ type: 'ping' }));
}, 60000);
```

5. **Receive intelligence messages**
```javascript
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'message') {
    console.log('Intelligence:', data.data);
  }
};
```

## Caching Architecture

### Cache Layers
1. **L1 - Hot Cache:** Frequently accessed intelligence data (5 min TTL)
2. **L2 - Chain Info Cache:** Blockchain metadata (1 hour TTL)
3. **L3 - Token Cache:** Real-time token prices (5 min TTL)
4. **L4 - Author Cache:** Social media account info (1 hour TTL)

### Cache Keys Pattern
- Intelligence list: `aigun:intelligence:page:{params}:{page}:{size}`
- Token entities: `dogex:intelligence:latest_entities:intelligence_id:{id}`
- Chain info: `dogex:intelligence:chain_infos:networks:{networks}`
- Author info: `aigun:intelligence:author_info:intelligence_id:{id}`

## Performance Optimizations

1. **Batch Database Queries:** Reduce N+1 queries with SQLAlchemy selectinload
2. **Pre-fetching:** Background tasks pre-cache next 3 pages
3. **Distributed Locks:** Prevent cache stampede with Redis locks
4. **Connection Pooling:** PostgreSQL connection pool (size: 20, overflow: 50)
5. **Async I/O:** Full async/await pattern throughout

## Testing

Run unit tests:
```bash
python -m pytest apps/intelligence/test_views.py -v
```

## Monitoring & Logging

### Log Formats
- **JSON Format:** Structured logs for production
- **Text Format:** Human-readable logs for development

### Log Levels
- `INFO`: Normal operations
- `WARNING`: Potential issues
- `ERROR`: Error conditions
- `EXCEPTION`: Exceptions with stack traces

### Health Check Response
```json
{
  "status": "healthy",
  "services": {
    "postgresql": {"status": "healthy", "response_time": 0.003},
    "redis": {"status": "healthy", "response_time": 0.001},
    "rabbitmq": {"status": "healthy", "response_time": 0.015}
  }
}
```

## Security

- **JWT Authentication:** RS256 algorithm with public key verification
- **Rate Limiting:** Configurable per-endpoint and global limits
- **CORS:** Configured for cross-origin requests
- **Input Validation:** Pydantic schemas for all inputs
- **SQL Injection Prevention:** SQLAlchemy ORM with parameterized queries

## Links

- [Website](https://www.aigun.ai/)
- [X (Twitter)](https://x.com/aigun_ai)
- [Telegram](https://t.me/AIGunX)

## License

Proprietary - All rights reserved

## Contributing

This is a private project. For inquiries, please contact the development team.

---

**Built with ❤️ by the AIGun Team**
