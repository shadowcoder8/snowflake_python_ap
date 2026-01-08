import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_generic_filtering():
    """
    Test that query parameters are correctly translated into SQL WHERE clauses.
    """
    api_key = "test-api-key"
    
    # Mock verify_api_key
    from app.dependencies import verify_api_key
    async def mock_verify_api_key(x_api_key: str = None):
        return api_key
    app.dependency_overrides[verify_api_key] = mock_verify_api_key
    
    # Mock snowflake_client.execute_query
    with patch("app.main.snowflake_client.execute_query", new_callable=AsyncMock) as mock_query:
        mock_query.return_value = []
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers = {"X-API-KEY": api_key}
            
            # Request with filters
            # /v1/data/companies?industry=Tech&state=CA
            response = await client.get(
                "/v1/data/companies?industry=Tech&state=CA&limit=10&offset=0", 
                headers=headers
            )
            
            assert response.status_code == 200
            
            # Verify the call arguments
            call_args = mock_query.call_args
            query = call_args[0][0]
            bindings = call_args[0][1]
            
            # Check SQL construction
            assert "SELECT * FROM COMPANY_INDEX" in query
            assert "WHERE" in query
            assert "industry = :filter_0" in query or "industry = :filter_1" in query
            assert "state = :filter_0" in query or "state = :filter_1" in query
            
            # Check bindings
            assert bindings["limit"] == 10
            assert bindings["offset"] == 0
            # Bindings order might vary, so check values exist
            assert "Tech" in bindings.values()
            assert "CA" in bindings.values()

    # Clean up
    app.dependency_overrides = {}
