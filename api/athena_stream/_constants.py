import httpx

# default timeout is 10 minutes
DEFAULT_TIMEOUT = httpx.Timeout(timeout=600.0, connect=5.0)
DEFAULT_MAX_RETRIES = 2
DEFAULT_CONNECTION_LIMITS = httpx.Limits(max_connections=1000, max_keepalive_connections=100)

INITIAL_RETRY_DELAY = 0.5
DEFAULT_RETRY_DELAY = 1.0
MAX_RETRY_DELAY = 8.0
DEFAULT_WRITE_ROW_BATCH_SIZE = 4000
DEFAULT_WRITE_COL_BATCH_SIZE = 90