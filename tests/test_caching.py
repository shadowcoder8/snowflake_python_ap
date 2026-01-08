import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_caching_mechanism():
    """
    Test that subsequent requests to the same endpoint return cached results
    and do NOT hit the Snowflake client.
    """
    api_key = "test-api-key"
    
    # Mock verify_api_key
    from app.dependencies import verify_api_key
    async def mock_verify_api_key(x_api_key: str = None):
        return api_key
    app.dependency_overrides[verify_api_key] = mock_verify_api_key
    
    # Mock snowflake_client.execute_query
    with patch("app.main.snowflake_client.execute_query", new_callable=AsyncMock) as mock_query:
        # First call result
        mock_query.return_value = [{"id": 1, "val": "first_fetch"}]
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers = {"X-API-KEY": api_key}
            
            # 1. First Request - Should hit Snowflake
            response1 = await client.get("/v1/data/companies?limit=1&offset=0", headers=headers)
            assert response1.status_code == 200
            assert response1.json()["data"][0]["val"] == "first_fetch"
            assert mock_query.call_count == 1
            
            # 2. Second Request (Identical) - Should hit Cache (NOT Snowflake)
            response2 = await client.get("/v1/data/companies?limit=1&offset=0", headers=headers)
            assert response2.status_code == 200
            assert response2.json()["data"][0]["val"] == "first_fetch"
            # Call count should STILL be 1
            assert mock_query.call_count == 1
            
            # 3. Third Request (Different params) - Should hit Snowflake
            mock_query.return_value = [{"id": 2, "val": "second_fetch"}]
            response3 = await client.get("/v1/data/companies?limit=2&offset=0", headers=headers)
            assert response3.status_code == 200
            assert mock_query.call_count == 2

    # Clean up
    app.dependency_overrides = {}
