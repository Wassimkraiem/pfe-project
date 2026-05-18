from conf.utils import get_env


FLASK_ENV = get_env("FLASK_ENV", default="development")
AWS_REGION = get_env("AWS_REGION", default="us-east-1")
OPENSEARCH_HOST = get_env("OPENSEARCH_HOST", required=True)
OPENSEARCH_PORT = get_env("OPENSEARCH_PORT", required=True)
OPENSEARCH_INITIAL_ADMIN_PASSWORD = get_env(
    "OPENSEARCH_INITIAL_ADMIN_PASSWORD", required=True
)
OPENSEARCH_AUTH_ADMIN = get_env("OPENSEARCH_AUTH_ADMIN", required=True)
SENTRY_DSN = get_env("SENTRY_DSN", required=True)
# API_KEYS = get_env("API_KEYS", required=True)

REDIS_URL = get_env("REDIS_URL", default="redis://localhost:6379/0")
SEARCH_CACHE_TTL = get_env("SEARCH_CACHE_TTL", default="300")
SEARCH_CACHE_ENABLED = get_env("SEARCH_CACHE_ENABLED", default="true")
