
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
        "statementHandle": "uuid-sync-123",
        "resultSetMetaData": {
            "rowType": [{"name": "ID"}, {"name": "NAME"}]
        },
        "data": [
            ["1", "Product A"],
            ["2", "Product B"]
        ],
        "code": "090001"
    }
    
    mock_snowflake.post("/api/v2/statements").mock(return_value=httpx.Response(200, json=mock_data))
    
    results = await snowflake_client.execute_query("SELECT * FROM PRODUCTS")
    
    assert len(results) == 2
    assert results[0]["id"] == "1"
    assert results[0]["name"] == "Product A"

# Polling test removed as client currently assumes synchronous execution for MVP

@pytest.mark.asyncio
async def test_execute_query_partitions(mock_snowflake):
    """Test fetching results distributed across partitions."""
    
    # Initial response indicates partitions
    mock_initial = {
        "statementHandle": "uuid-part-123",
        "resultSetMetaData": {
            "rowType": [{"name": "ID"}],
            "partitionInfo": [
                {"rowCount": 1, "url": "/api/v2/statements/uuid/1"}, # Partition 0 (Skipped as it duplicates data)
                {"rowCount": 1, "url": "/api/v2/statements/uuid/2"}  # Partition 1
            ]
        },
        "data": [["1"]], # First chunk (Partition 0 data)
        "code": "090001"
    }
    
    mock_snowflake.post("/api/v2/statements").mock(return_value=httpx.Response(200, json=mock_initial))
    
    # Mock Partition 1 (Partition 0 is skipped)
    # mock_snowflake.get("/api/v2/statements/uuid/1").mock(...) # Not called
    
    # Mock Partition 2 (Index 1)
    mock_snowflake.get("/api/v2/statements/uuid/2").mock(
        return_value=httpx.Response(200, json={"data": [["3"]]})
    )
    
    results = await snowflake_client.execute_query("SELECT * FROM LARGE_TABLE")
    
    # We expect 2 rows: 1 from initial data (P0), 1 from P1. P0 fetch is skipped.
    assert len(results) == 2
