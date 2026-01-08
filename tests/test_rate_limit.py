import pytest
from httpx import AsyncClient
from app.main import app
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_rate_limit_exceeded():
    """
    Test that the API correctly enforces the rate limit (50 requests per minute).
    We will send 51 requests and verify the 51st fails with 429.
    """
    api_key = "test-rate-limit-key"
    
    # Mock verify_api_key to accept our test key
    from app.dependencies import verify_api_key
    async def mock_verify_api_key(x_api_key: str = None):
        if x_api_key == api_key:
            return api_key
        return api_key

    app.dependency_overrides[verify_api_key] = mock_verify_api_key
    
    # Mock snowflake_client.execute_query to return fast success
    with patch("app.main.snowflake_client.execute_query", new_callable=AsyncMock) as mock_query:
        mock_query.return_value = [{"id": 1, "name": "Test Co"}]
        
        from httpx import ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers = {"X-API-KEY": api_key}
            
            # Send 50 requests - should succeed
            for i in range(50):
                response = await client.get("/v1/data/companies", headers=headers)
                assert response.status_code == 200, f"Request {i+1} failed with {response.status_code}"
            
            # Send 51st request - should fail
            response = await client.get("/v1/data/companies", headers=headers)
            assert response.status_code == 429
            
            data = response.json()
            assert data["status"] == "error"
            assert "Rate limit exceeded" in data["message"]
            # slowapi detail format is "50 per 1 minute"
            assert "50 per 1 minute" in data["message"]

    # Clean up
    app.dependency_overrides = {}
