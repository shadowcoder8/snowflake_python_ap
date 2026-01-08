
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_swagger_test_params_filtering():
    """
    Test that test_filter_col and test_filter_val are treated as filters.
    """
    api_key = "test-api-key"
    
    # Mock verify_api_key
    from app.dependencies import verify_api_key
    async def mock_verify_api_key():
        return api_key
    app.dependency_overrides[verify_api_key] = mock_verify_api_key
    
    # Mock snowflake_client.execute_query
    with patch("app.main.snowflake_client.execute_query", new_callable=AsyncMock) as mock_query:
        mock_query.return_value = []
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers = {"X-API-KEY": api_key}
            
            # Request with swagger test params
            response = await client.get(
                "/v1/data/companies?test_filter_col=status&test_filter_val=Active", 
                headers=headers
            )
            
            if response.status_code != 200:
                print(response.json())
            
            assert response.status_code == 200
            
            # Verify the call arguments
            call_args = mock_query.call_args
            query = call_args[0][0]
            bindings = call_args[0][1]
            
            # Check SQL construction
            assert "WHERE" in query
            assert "status = :filter_0" in query
            
            # Check bindings
            assert bindings["filter_0"] == "Active"

    # Clean up
    app.dependency_overrides = {}
