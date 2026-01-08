import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from unittest.mock import patch, AsyncMock
from fastapi import HTTPException
import json

@pytest.mark.asyncio
async def test_streaming_response():
    """
    Test that ?stream=true returns NDJSON data using the generator.
    """
    api_key = "test-api-key"
    
    # Mock verify_api_key
    from app.dependencies import verify_api_key
    async def mock_verify_api_key(x_api_key: str = None):
        return api_key
    app.dependency_overrides[verify_api_key] = mock_verify_api_key
    
    # Mock snowflake_client.execute_query_stream (generator)
    async def mock_stream_generator(query, bindings):
        yield {"id": 1, "name": "Row1"}
        yield {"id": 2, "name": "Row2"}
        
    with patch("app.main.snowflake_client.execute_query_stream", side_effect=mock_stream_generator) as mock_stream:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers = {"X-API-KEY": api_key}
            
            # Request with stream=true
            response = await client.get("/v1/data/companies?stream=true", headers=headers)
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/x-ndjson"
            
            # Verify content is NDJSON
            lines = response.text.strip().split("\n")
            assert len(lines) == 2
            assert json.loads(lines[0]) == {"id": 1, "name": "Row1"}
            assert json.loads(lines[1]) == {"id": 2, "name": "Row2"}

    app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_rate_limit_independent_keys():
    """
    Test that rate limits are enforced independently per API key.
    """
    # We need to use the real limiter, but we can mock the backend storage or just rely on in-memory.
    # Since tests run in sequence/parallel, we need to be careful.
    # The limiter is configured in main.py.
    
    # We'll use 2 different keys.
    key1 = "key-user-1"
    key2 = "key-user-2"
    
    # We need to override verify_api_key to accept these keys
    from app.dependencies import verify_api_key
    from fastapi import Request
    
    async def allow_any_key(request: Request):
        key = request.headers.get("X-API-KEY")
        if not key:
             raise HTTPException(status_code=403, detail="Forbidden")
        return key
        
    app.dependency_overrides[verify_api_key] = allow_any_key

    # Mock Snowflake to avoid actual calls (we only care about rate limit middleware)
    with patch("app.main.snowflake_client.execute_query", new_callable=AsyncMock) as mock_query:
        mock_query.return_value = []
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. Exhaust Key 1 (Limit 50)
            # We assume the limiter state is fresh or we might need to reset it.
            # slowapi stores state in app.state.limiter.
            
            # Sending 50 requests for Key 1
            for _ in range(50):
                resp = await client.get("/v1/data/companies", headers={"X-API-KEY": key1})
                assert resp.status_code == 200
            
            # 51st for Key 1 -> 429
            resp = await client.get("/v1/data/companies", headers={"X-API-KEY": key1})
            assert resp.status_code == 429
            
            # 2. Key 2 should still be allowed!
            resp = await client.get("/v1/data/companies", headers={"X-API-KEY": key2})
            assert resp.status_code == 200
            
    app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_response_metadata_and_headers():
    """
    Test that the response metadata excludes 'message' if null,
    and custom headers (X-Result-Count, X-Cache) are present.
    """
    api_key = "test-api-key"
    
    # Mock verify_api_key
    from app.dependencies import verify_api_key
    async def mock_verify_api_key(x_api_key: str = None):
        return api_key
    app.dependency_overrides[verify_api_key] = mock_verify_api_key
    
    # Mock snowflake_client.execute_query
    mock_data = [{"id": 1, "val": "A"}, {"id": 2, "val": "B"}]
    with patch("app.main.snowflake_client.execute_query", new_callable=AsyncMock) as mock_query:
        mock_query.return_value = mock_data
        
        # We also need to clear cache to ensure we get a fresh response with headers
        from app.main import response_cache
        response_cache.cache.clear()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers = {"X-API-KEY": api_key}
            
            # 1. Fetch Data
            response = await client.get("/v1/data/companies?limit=10&offset=0", headers=headers)
            
            assert response.status_code == 200
            data = response.json()
            
            # Check Meta
            assert "meta" in data
            meta = data["meta"]
            assert meta["total"] == 2
            assert meta["limit"] == 10
            assert meta["offset"] == 0
            assert "message" not in meta  # Should be absent
            
            # Check Headers
            assert "X-Result-Count" in response.headers
            assert response.headers["X-Result-Count"] == "2"
            assert "X-Cache" in response.headers
            assert response.headers["X-Cache"] == "MISS"

            # 2. Check Cache Hit
            response_cached = await client.get("/v1/data/companies?limit=10&offset=0", headers=headers)
            assert response_cached.status_code == 200
            assert response_cached.headers["X-Cache"] == "HIT"
            
    app.dependency_overrides = {}
