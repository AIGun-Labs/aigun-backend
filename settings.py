import os
try:
    from dotenv import load_dotenv # type: ignore
    load_dotenv(override=True)
except: pass



# PG Configuration
DATABASE_DICT: dict[str, str] = {}

for env_name, env_value in os.environ.items():
    if env_name.startswith('DATABASE_URL_'):
        DATABASE_DICT[env_name.removeprefix('DATABASE_URL_').lower()] = env_value

DATABASE_URLS = os.getenv('DATABASE_URLS', 'sqlite:///./.db').split(',')


# REDIS Configuration
CACHE_URL = os.getenv('CACHE_URL', 'redis://localhost:6379/0')
SLAVE_CACHE_URL = os.getenv('SLAVE_CACHE_URL', 'redis://localhost:6379/0')


# --------------Message Queue-----------------
# Message Queue Configuration
RABBIT_URL = os.getenv('RABBIT_URL', 'amqp://guest:guest@localhost:5672/')
# RABBIT_URL = os.getenv('RABBIT_URL', 'amqp://test_user:123456@localhost:5672/')


# Intelligence Queue Name
INTELLIGENCE_QUEUE = os.getenv("INTELLIGENCE_QUEUE", "intelligence_queue_test")

# Intelligence Consumer Queue Name
INTELLIGENCE_CONSUMER_QUEUE = os.getenv("INTELLIGENCE_CONSUMER_QUEUE", "intelligence_consumer_queue_test")


# JWT Configuration
EXPIRES_FOR_TOKEN = int(os.getenv('EXPIRES_FOR_TOKEN', 60 * 30))
JWT_PRIVATE_FILE_PATH = os.getenv('JWT_PRIVATE_FILE')

# Read private key file content
try:
    with open(JWT_PRIVATE_FILE_PATH, 'r') as f:
        JWT_PRIVATE_KEY = f.read().strip()
except FileNotFoundError:
    JWT_PRIVATE_KEY = ""


# Read public key file content
JWT_PUBLIC_FILE_PATH = os.getenv('JWT_PUBLIC_FILE')

try:
    with open(JWT_PUBLIC_FILE_PATH, 'r') as f:
        JWT_PUBLIC_KEY = f.read().strip()
except FileNotFoundError:
    JWT_PUBLIC_KEY = ""


# Device Verification Secret Key
DEVICE_PRIVATE_KEY = os.getenv('DEVICE_PRIVATE_KEY')


# Pagination Configuration
PAGE = os.getenv('PAGE', 1)
PAGE_SIZE = os.getenv('PAGE_SIZE', 10)
MIN_PAGE_SIZE: int = os.getenv('MIN_PAGE_SIZE', 1)
MAX_PAGE_SIZE: int = os.getenv('MAX_PAGE_SIZE', 100)

# Logging
LOGGING_FORMAT = os.getenv("LOGGING_FORMAT", "json")

# Rate Limiting Configuration
LIMITER_CONFIG = {
    "GLOBAL_THROTTLE_RATES": {
        "limit_times": os.getenv('GLOBAL_LIMIT_TIMES', 150),
        "limit_seconds": os.getenv('GLOBAL_LIMIT_SECONDS', 60)
    },
    "RECEIVE_THROTTLE_RATES": {
        "limit_times": os.getenv('RECEIVE_LIMIT_TIMES', 60),
        "limit_seconds": os.getenv('RECEIVE_LIMIT_SECONDS', 60)
    }
}




# --------------Cache Time-----------------
# access_token validity period
# EXPIRES_FOR_ACCESS_TOKEN = int(os.getenv('EXPIRES_FOR_ACCRESS_TOKEN', 60 * 30))
EXPIRES_FOR_ACCESS_TOKEN = int(os.getenv('EXPIRES_FOR_ACCRESS_TOKEN', 86400 * 366 * 3)) # For testing, temporarily set to 3 years

# refresh_token
EXPIRES_FOR_REFRESH_TOKEN = int(os.getenv('EXPIRES_FOR_REFRESH_TOKEN', 86400 * 366 * 3))

# Intelligence Page Cache Time
EXPIRES_FOR_INTELLIGENCE = int(os.getenv('EXPIRES_FOR_INTELLIGENCE', 60 * 3))

# Intelligence Real-time Hot Data Cache Time
EXPIRES_FOR_INTELLIGENCE_HOT_DATA = int(os.getenv('EXPIRES_FOR_INTELLIGENCE_HOT_DATA', 3600 * 24 * 3))

# Intelligence Author Info Cache Time
EXPIRES_FOR_AUTHOR_INFO = int(os.getenv('EXPIRES_FOR_AUTHOR_INFO', 60 * 10))

# Intelligence Chain Info Cache Time
EXPIRES_FOR_CHAIN_INFOS = int(os.getenv('EXPIRES_FOR_CHAIN_INFOS', 60 * 10))

# Intelligence Related Token Cache Time (Cold to Hot related tokens)
EXPIRES_FOR_SHOWED_TOKENS = int(os.getenv('EXPIRES_FOR_CHAIN_INFOS', 3600 * 24))

# Search Token Cache Time
EXPIRES_FOR_SEARCH_TOKEN = int(os.getenv('EXPIRES_FOR_SEARCH_TOKEN', 60 * 10))

# Search Token Cache Time
EXPIRES_FOR_LATEST_APPEAR_TOKEN = int(os.getenv('EXPIRES_FOR_SEARCH_TOKEN', 60))

# Token URLs Cache Time
EXPIRES_FOR_TOKEN_URLS = int(os.getenv('EXPIRES_FOR_SEARCH_TOKEN', 86400 * 3))

# AI Agent List Cache Time
EXPIRES_FOR_AI_AGENT_LIST = int(os.getenv('EXPIRES_FOR_AI_AGENT_LIST', 60 * 5))

# The Highest Increase Rate Cache Time
EXPIRES_FOR_HIGHEST_INCREASE_RATE = int(os.getenv('EXPIRES_FOR_AI_AGENT_LIST', 60 * 30))


# Wallet Root Path
WALLET_API_BASE_URL = os.getenv('WALLET_API_BASE_URL', "https://api.idogex.ai")




# ----------Secret Keys-----------------
# Wallet AES Encryption Key
WALLET_INFO_SECRET_KEY = os.getenv('WALLET_INFO_SECRET_KEY')

CMC_API_KEY = os.getenv('CMC_API_KEY')




# Others
SET = os.getenv('SET', 'dev')
ENV = os.getenv('ENV', 'dev') # development, production, testing
SUB_QUEUE_NAME = os.getenv('SUB_QUEUE_NAME', 'dev-message') # message is production environment, dev-message is testing environment
CHECK_SALT = os.getenv('CHECK_SALT', 'check_salt')
JWT_SECRET = os.getenv('JWT_SECRET', 'jwt_secret')
URL_FILTERS = os.getenv('URL_FILTERS', '/ping').split(',')

QUICK_KEY = os.getenv('QUICK_KEY', 'QN_IPFS_API')
AI_SERVER = os.getenv('AI_SERVER', 'http://127.0.0.1:8000/api/v1/ai/analyze')
INFLUENCE_LEVEL_VALUE = os.getenv('INFLUENCE_LEVEL_VALUE', ("EX", "S", "A", "B"))

SERVER_LAYER = int(os.getenv('SERVER_LAYER', '2'))
SERVER_APP_LAYER = int(os.getenv('SERVER_APP_LAYER', '5'))

TASK_WORKER = os.getenv('TASK_WORKER', 'TaskWorker')
PULL_WORKER = os.getenv('PULL_WORKER', 'PullWorker')


EXPIRES_FOR_TOKEN_SOCIAL_LINK_TYPES = int(os.getenv('EXPIRES_FOR_TOKEN_SOCIAL_LINK_TYPES', 3600 * 12))