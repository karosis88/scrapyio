import typing

from httpx._types import (
    AuthTypes,
    CertTypes,
    CookieTypes,
    HeaderTypes,
    ProxiesTypes,
    QueryParamTypes,
    VerifyTypes,
)

PROXY_CHAIN: typing.List[str] = []

ITEM_MIDDLEWARES: typing.List[str] = ["middlewares.ProxyCheckMiddleWare"]

# Middlewares
#   path to the middlewares
#   example: 'scrapyio.middlewares.BaseMiddleWare'
MIDDLEWARES: typing.List[str] = []

# Timeout for httpx request
REQUEST_TIMEOUT: int = 5

# Default headers for httpx request
DEFAULT_HEADERS: typing.Optional[HeaderTypes] = None

# Default cookies for httpx request
DEFAULT_COOKIES: typing.Optional[CookieTypes] = {}

# Default query parameters for httpx request
DEFAULT_PARAMS: typing.Optional[QueryParamTypes] = None

# Default auth for httpx request
DEFAULT_AUTH: typing.Optional[AuthTypes] = None

# Default for SSL verify mode
DEFAULT_VERIFY_SSL: VerifyTypes = True

# Default certs for httpx request
DEFAULT_CERTS: typing.Optional[CertTypes] = None

# Default HTTP version
HTTP_1: bool = True
HTTP_2: bool = False

# Default HTTP proxies
DEFAULT_PROXIES: typing.Optional[ProxiesTypes] = None

# Follow redirects for HTTP request
FOLLOW_REDIRECTS: bool = False

# Trust env for httpx request
DEFAULT_TRUST_ENV: bool = False

# Enable stream by default
ENABLE_STREAM_BY_DEFAULT: bool = False

# Logging configuration

DEFAULT_LOGGING_CONFIG: typing.Dict = {
    "version": 1,
    "handlers": {
        "scrapyio-stream": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": "DEBUG",
            "stream": "ext://sys.stderr",
        },
    },
    "formatters": {
        "standard": {
            "format": "%(levelname)s [%(module)s:%(lineno)d]"
            " [%(asctime)s] %(name)s - %(message)s"
        }
    },
    "loggers": {
        "scrapyio": {
            "handlers": ["scrapyio-stream"],
            "level": "DEBUG",
            "propagate": False,
        }
    },
}
