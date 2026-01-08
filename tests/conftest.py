
import os
import pytest
from httpx import AsyncClient, ASGITransport
import respx
from unittest.mock import patch

# Load test env before importing app
# We need to make sure the app sees these values
os.environ["APP_ENV"] = "test"
os.environ["API_KEY"] = "test-api-key"
os.environ["ADMIN_SECRET"] = "test-admin-secret"
os.environ["SNOWFLAKE_ACCOUNT"] = "testaccount"
os.environ["SNOWFLAKE_USER"] = "testuser"
os.environ["SNOWFLAKE_WAREHOUSE"] = "testwh"
os.environ["SNOWFLAKE_ROLE"] = "testrole"
os.environ["SNOWFLAKE_DATABASE"] = "testdb"
os.environ["SNOWFLAKE_SCHEMA"] = "testschema"
os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"] = "test_private_key.p8"

# Now we can safely import the app
from app.main import app, response_cache
from app.config import settings

@pytest.fixture(autouse=True)
def clear_cache():
    """Clears the global response cache before every test."""
    response_cache.cache.clear()
    yield

@pytest.fixture(autouse=True)
def mock_jwt():
    """Mocks JWT generation to avoid file access."""
    with patch("app.snowflake_client.get_snowflake_jwt", return_value="mock-jwt-token"):
        yield

@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.fixture
def mock_snowflake():
    """Mocks the Snowflake API."""
    with respx.mock(base_url=f"https://{settings.SNOWFLAKE_ACCOUNT}.snowflakecomputing.com") as respx_mock:
        yield respx_mock
