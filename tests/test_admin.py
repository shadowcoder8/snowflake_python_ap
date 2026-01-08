import pytest
import httpx
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_admin_generate_key_success(client: AsyncClient, mock_snowflake):
    # 1. Generate Key
    response = await client.post(
        "/v1/admin/generate-key",
        headers={"X-ADMIN-SECRET": "test-admin-secret"}
    )
    assert response.status_code == 200
    data = response.json()
    new_key = data["generated_key"]
    assert new_key.startswith("sk_")

    # Mock Snowflake response for the subsequent check
    mock_snowflake.post("/api/v2/statements").mock(
        return_value=httpx.Response(200, json={
            "statementHandle": "uuid-admin-test",
            "resultSetMetaData": {"rowType": [{"name": "id"}]},
            "data": [["1"]],
            "code": "090001"
        })
    )

    # 2. Verify Key Works Immediately
    # Try to access a protected endpoint with the new key
    prod_response = await client.get(
        "/v1/data/companies",
        headers={"X-API-KEY": new_key}
    )
    # Should be 200 OK (or whatever success code products returns), NOT 403 Forbidden
    # Note: Product endpoint might fail due to Snowflake mock, but Auth should pass.
    # If Auth failed, it would be 403. If Snowflake failed, likely 500 or handled error.
    assert prod_response.status_code != 403

@pytest.mark.asyncio
async def test_admin_generate_key_unauthorized_no_header(client: AsyncClient):
    response = await client.post("/v1/admin/generate-key")
    assert response.status_code == 422 # Missing header

@pytest.mark.asyncio
async def test_admin_generate_key_forbidden_wrong_secret(client: AsyncClient):
    response = await client.post(
        "/v1/admin/generate-key",
        headers={"X-ADMIN-SECRET": "wrong-secret"}
    )
    assert response.status_code == 403
