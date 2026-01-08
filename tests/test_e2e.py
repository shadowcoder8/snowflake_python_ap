
import pytest
import httpx
from app.config import settings

@pytest.mark.asyncio
async def test_health_check(client, mock_snowflake):
    # Mock successful connection check
    mock_snowflake.post("/api/v2/statements").mock(
        return_value=httpx.Response(200, json={
            "statementHandle": "uuid-health",
            "resultSetMetaData": {"rowType": [{"name": "1"}]},
            "data": [["1"]],
            "code": "090001"
        })
    )
    
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["snowflake"] == "connected"

@pytest.mark.asyncio
async def test_health_check_snowflake_down(client, mock_snowflake):
    # Mock connection failure
    mock_snowflake.post("/api/v2/statements").mock(
        return_value=httpx.Response(500)
    )
    
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["snowflake"] == "disconnected"

@pytest.mark.asyncio
async def test_get_companies_unauthorized(client):
    response = await client.get("/v1/data/companies")
    assert response.status_code == 422 # Missing header
    # Check new validation error format
    data = response.json()
    assert data["status"] == "error"
    assert "The request inputs were invalid." in data["message"]
    
    # Let's try with invalid key
    response = await client.get("/v1/data/companies", headers={"X-API-KEY": "wrong-key"})
    assert response.status_code == 401 # Changed from 403 to 401 in dependencies.py
    assert response.json()["message"] == "Invalid API Key provided. Please check your credentials."

@pytest.mark.asyncio
async def test_get_companies_bad_param(client):
    # Test validation error (limit > 1000)
    response = await client.get("/v1/data/companies?limit=1001", headers={"X-API-KEY": settings.API_KEY})
    assert response.status_code == 422
    data = response.json()
    assert data["status"] == "error"
    assert "The request inputs were invalid." in data["message"]
    assert "query.limit" in str(data["details"])

@pytest.mark.asyncio
async def test_snowflake_connection_error(client, mock_snowflake):
    # Mock connection error
    mock_snowflake.post("/api/v2/statements").mock(side_effect=httpx.ConnectError("Connection failed"))
    
    response = await client.get("/v1/data/companies", headers={"X-API-KEY": settings.API_KEY})
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "error"
    assert "Service Unavailable" in data["message"]

@pytest.mark.asyncio
async def test_get_companies_success(client, mock_snowflake):
    mock_data = {
        "statementHandle": "uuid-comp",
        "resultSetMetaData": {
            "rowType": [{"name": "id"}, {"name": "name"}]
        },
        "data": [
            ["c1", "Company 1"],
            ["c2", "Company 2"]
        ],
        "code": "090001"
    }
    
    mock_snowflake.post("/api/v2/statements").mock(
        return_value=httpx.Response(200, json=mock_data)
    )
    
    response = await client.get("/v1/data/companies?limit=5&offset=0", headers={"X-API-KEY": settings.API_KEY})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert len(body["data"]) == 2
    assert body["meta"]["limit"] == 5

@pytest.mark.asyncio
async def test_snowflake_bad_request(client, mock_snowflake):
    # Mock a 400 Bad Request from Snowflake (like the one user saw)
    error_json = {
        "code": "391917",
        "message": "Invalid parameter. Cannot deserialize value..."
    }
    mock_snowflake.post("/api/v2/statements").mock(
        return_value=httpx.Response(400, json=error_json)
    )
    
    response = await client.get("/v1/data/companies", headers={"X-API-KEY": settings.API_KEY})
    
    # My new handler should catch httpx.HTTPStatusError (raised by raise_for_status)
    # and return the error message.
    # Wait, my execute_query calls raise_for_status.
    
    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "error"
    assert "Invalid parameter" in data["message"]
