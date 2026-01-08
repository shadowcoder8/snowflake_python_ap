"""
------------------------------------------------------------------------------
Project: Snowflake Data Product API
Developer: Rikesh Chhetri
Description: Configuration management using Pydantic Settings.
------------------------------------------------------------------------------
"""
from typing import Optional, List
import logging
import sys
import structlog
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App Settings
    APP_ENV: str = "development"
    API_KEY: str
    ADMIN_SECRET: Optional[str] = None # Secret for admin endpoints
    LOG_LEVEL: str = "INFO"

    # Rate Limiting
    RATE_LIMIT_HEALTH: str = "5/minute"
    RATE_LIMIT_PRODUCTS: str = "50/minute"
    RATE_LIMIT_PRODUCT_DETAIL: str = "100/minute"

    # Pagination Settings
    DEFAULT_PAGE_LIMIT: int = 10
    MAX_PAGE_LIMIT: int = 1000

    # Snowflake Settings
    SNOWFLAKE_ACCOUNT: str
    SNOWFLAKE_USER: str
    SNOWFLAKE_WAREHOUSE: str
    SNOWFLAKE_ROLE: str
    SNOWFLAKE_DATABASE: str
    SNOWFLAKE_SCHEMA: str
    SNOWFLAKE_PRIVATE_KEY_PATH: Optional[str] = "rsa_key.p8"
    SNOWFLAKE_PRIVATE_KEY_CONTENT: Optional[str] = None # Support for passing key as env var (Codespaces Secrets/Render)
    SNOWFLAKE_PRIVATE_KEY_PASSPHRASE: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    @property
    def valid_api_keys(self) -> List[str]:
        return [key.strip() for key in self.API_KEY.split(",") if key.strip()]

settings = Settings()

# Configure Structlog
def configure_logging():
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if settings.APP_ENV == "production":
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(),
        ]

    structlog.configure(
        processors=processors,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Redirect standard logging to structlog
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=settings.LOG_LEVEL)

configure_logging()
logger = structlog.get_logger()
