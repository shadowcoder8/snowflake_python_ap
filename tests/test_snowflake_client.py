
import pytest
import jwt
import httpx
from app.snowflake_client import snowflake_client
from app.security import get_snowflake_jwt
from app.config import settings

@pytest.mark.asyncio
async def test_jwt_generation():
    # Mock load_private_key to return a dummy key
    # We need a valid private key structure for serialization if we want real JWT generation
    # Or we can just mock the whole thing.
    # But this test seems to want to test the JWT structure.
    # We'll skip it if key is missing, or mock the key.
    
    # Let's mock load_private_key
    from unittest.mock import patch
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.backends import default_backend
    
    # Generate a temporary key for testing
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    with patch("app.security.load_private_key", return_value=private_key):
        token = get_snowflake_jwt()
        assert token is not None
        
        # Verify
        decoded = jwt.decode(token, options={"verify_signature": False})
        assert decoded["iss"].startswith(f"{settings.SNOWFLAKE_ACCOUNT.upper()}.{settings.SNOWFLAKE_USER.upper()}")
        assert decoded["sub"] == f"{settings.SNOWFLAKE_ACCOUNT.upper()}.{settings.SNOWFLAKE_USER.upper()}"

@pytest.mark.asyncio
async def test_execute_query_sync_success(mock_snowflake):
    """Test a query that returns results immediately (synchronously)."""
    
    mock_data = {
        "resultSetMetaData": {
            "rowType": [{"name": "ID"}, {"name": "NAME"}]
        },
        "data": [
            ["1", "Product A"],
            ["2", "Product B"]
        ],
        "code": "39000"
    }
    
    mock_snowflake.post("/api/v2/statements").mock(return_value=httpx.Response(200, json=mock_data))
    
    results = await snowflake_client.execute_query("SELECT * FROM PRODUCTS")
    
    assert len(results) == 2
    assert results[0]["ID"] == "1"
    assert results[0]["NAME"] == "Product A"

@pytest.mark.asyncio
async def test_execute_query_polling(mock_snowflake):
    """Test a query that returns 202 and requires polling."""
    
    # 1. Initial Request returns 202
    mock_snowflake.post("/api/v2/statements").mock(
        return_value=httpx.Response(202, json={"statementHandle": "uuid-1234"})
    )
    
    # 2. First Poll returns 202 (Still running)
    mock_snowflake.get("/api/v2/statements/uuid-1234").side_effect = [
        httpx.Response(202, json={"statementHandle": "uuid-1234"}), # First poll
        httpx.Response(200, json={ # Second poll success
            "resultSetMetaData": {
                "rowType": [{"name": "ID"}]
            },
            "data": [["100"]]
        })
    ]
    
    results = await snowflake_client.execute_query("SELECT SLEEP(5)")
    assert len(results) == 1
    assert results[0]["ID"] == "100"

@pytest.mark.asyncio
async def test_execute_query_partitions(mock_snowflake):
    """Test fetching results distributed across partitions."""
    
    # Initial response indicates partitions
    mock_initial = {
        "resultSetMetaData": {
            "rowType": [{"name": "ID"}],
            "partitionInfo": [
                {"rowCount": 1, "url": "/api/v2/statements/uuid/1"},
                {"rowCount": 1, "url": "/api/v2/statements/uuid/2"}
            ]
        },
        "data": [["1"]] # First chunk
    }
    
    mock_snowflake.post("/api/v2/statements").mock(return_value=httpx.Response(200, json=mock_initial))
    
    # Mock Partition 1
    mock_snowflake.get("/api/v2/statements/uuid/1").mock(
        return_value=httpx.Response(200, json={"data": [["2"]]})
    )
    
    # Mock Partition 2
    mock_snowflake.get("/api/v2/statements/uuid/2").mock(
        return_value=httpx.Response(200, json={"data": [["3"]]})
    )
    
    results = await snowflake_client.execute_query("SELECT * FROM LARGE_TABLE")
    
    assert len(results) == 3
    ids = [r["ID"] for r in results]
    assert "1" in ids
    assert "2" in ids
    assert "3" in ids
