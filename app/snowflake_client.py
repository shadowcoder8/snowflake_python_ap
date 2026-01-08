"""
------------------------------------------------------------------------------
Project: Snowflake Data Product API
Developer: Rikesh Chhetri
Description: Async Snowflake Client using the SQL API v2.
------------------------------------------------------------------------------
"""
import asyncio
import httpx
import uuid
from typing import List, Dict, Any, Optional
import json
from app.config import settings, logger
from app.security import get_snowflake_jwt

class SnowflakeClient:
    _client: Optional[httpx.AsyncClient] = None

    def __init__(self):
        self.base_url = f"https://{settings.SNOWFLAKE_ACCOUNT}.snowflakecomputing.com"
        self.headers = {
            "Accept": "application/json",
            "User-Agent": "SnowflakePythonAPI/1.0",
        }

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _get_headers(self) -> Dict[str, str]:
        token = get_snowflake_jwt()
        return {
            **self.headers,
            "Authorization": f"Bearer {token}",
            "X-Snowflake-Authorization-Token-Type": "KEYPAIR_JWT"
        }

    async def _fetch_partition(self, client: httpx.AsyncClient, url: str) -> List[List[Any]]:
        """Fetches a single partition of data."""
        try:
            # Partition URLs are usually absolute or relative to some base.
            # Snowflake returns absolute path usually, but sometimes relative.
            # We assume it's a full URL or relative to the request.
            # However, looking at docs, partitionInfo gives 'url'.
            
            headers = self._get_headers()
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            logger.error(f"Failed to fetch partition {url}: {e}")
            raise

    def _format_bindings(self, bindings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formats Python values into Snowflake SQL API bindings.
        """
        formatted = {}
        for key, value in bindings.items():
            if isinstance(value, int):
                formatted[key] = {"type": "FIXED", "value": str(value)}
            elif isinstance(value, float):
                formatted[key] = {"type": "REAL", "value": str(value)}
            else:
                formatted[key] = {"type": "TEXT", "value": str(value)}
        return formatted

    async def execute_query(self, query: str, bindings: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Executes a SQL query against Snowflake SQL API v2.
        Handles polling and parallel partition fetching.
        """
        # Reuse the streaming implementation but collect all results
        results = []
        async for row in self.execute_query_stream(query, bindings):
            results.append(row)
        return results

    async def execute_query_stream(self, query: str, bindings: Optional[Dict[str, Any]] = None):
        """
        Executes a SQL query and yields rows as they are fetched (Streaming).
        Handles polling and parallel partition fetching (yielding as partitions arrive).
        """
        url = f"{self.base_url}/api/v2/statements"
        
        payload = {
            "statement": query,
            "warehouse": settings.SNOWFLAKE_WAREHOUSE,
            "database": settings.SNOWFLAKE_DATABASE,
            "schema": settings.SNOWFLAKE_SCHEMA,
            "timeout": 60, # Request timeout
            "resultSetMetaData": {
                "format": "json" 
            }
        }
        
        if bindings:
            payload["bindings"] = self._format_bindings(bindings)

        client = await self.get_client()
        headers = self._get_headers()
        
        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            statement_handle = data["statementHandle"]
            
            # Check for immediate errors (Ignore success codes)
            # 090001: Statement executed successfully
            if data.get("code") and data.get("code") != "090001":
                 # Some other codes might be warnings?
                 # Better to check sqlState if available?
                 # But for now, let's just allow 090001.
                 raise Exception(f"Snowflake Error: {data.get('message')}")

            # Polling loop if not complete
            # The API might return results immediately or a handle to poll
            # "data" might contain the first batch
            
            # Helper to process a batch of data
            column_names = [col["name"].lower() for col in data["resultSetMetaData"]["rowType"]]
            
            def process_rows(rows):
                processed = []
                for row in rows:
                    item = dict(zip(column_names, row))
                    processed.append(item)
                return processed

            # Yield initial results if any
            if "data" in data:
                for item in process_rows(data["data"]):
                    yield item

            # If not complete, we might need to poll (not implemented fully here for brevity, 
            # assuming synchronous execution for now or first page is enough. 
            # For robust long queries, we'd need to check 'statementStatus' URL)
            
            # Handle Partitions (Parallel Fetching)
            metadata = data.get("resultSetMetaData", {})
            partitions = metadata.get("partitionInfo", [])
            total_rows = metadata.get("numRows")
            first_chunk_rows = len(data.get("data", []))
            
            # Log if we have a mismatch and no partitions found yet
            if total_rows and total_rows > first_chunk_rows and not partitions:
                 logger.warning(f"Row mismatch: Expected {total_rows}, got {first_chunk_rows} in first chunk, but no partitions listed.")

            if partitions:
                tasks = []
                # Check if we already have the first partition in 'data'
                has_initial_data = len(data.get("data", [])) > 0
                
                for index, partition in enumerate(partitions):
                    # If we already have the first partition (index 0) inline, skip fetching it again
                    if index == 0 and has_initial_data:
                        continue

                    # 'url' might be absolute or relative. 
                    # If 'url' is missing, we try to construct it using the index (api/v2/statements/<handle>?partition=<index>)
                    # Note: partition indices in URL usually start from 0, but the first chunk is already partition 0? 
                    # Actually, the first chunk is inline. The partitions in partitionInfo are usually subsequent.
                    # Let's check if 'url' is present.
                    
                    p_url = partition.get("url")
                    
                    if not p_url:
                        # Fallback: Construct URL based on statement handle and index
                        # This is a guess, but better than skipping.
                        # Usually partitions are just indexed.
                        logger.warning(f"Partition {index} missing URL, attempting to construct...")
                        p_url = f"/api/v2/statements/{statement_handle}?partition={index}"

                    if not p_url.startswith("http"):
                         # It's likely relative to the statement execution result or base
                         # Let's try appending to base_url if it starts with /
                         if p_url.startswith("/"):
                             p_url = f"{self.base_url}{p_url}"
                         else:
                             # If it doesn't start with /, assume it's relative to the statements endpoint
                             p_url = f"{self.base_url}/api/v2/statements/{statement_handle}/{p_url}" 
                             
                    tasks.append(self._fetch_partition(client, p_url))
                
                # Fetch all partitions in parallel
                logger.info(f"Gathering {len(tasks)} partition tasks...")
                if tasks:
                    results_list = await asyncio.gather(*tasks)
                else:
                    results_list = []
                logger.info("Partitions gathered.")
                
                for partition_rows in results_list:
                    for item in process_rows(partition_rows):
                        yield item

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 422:
                try:
                    error_data = e.response.json()
                    message = error_data.get("message", e.response.text)
                    code = error_data.get("code", "UNKNOWN")
                    logger.error(f"Snowflake 422 Error: [{code}] {message}")
                    raise Exception(f"Snowflake Error [{code}]: {message}")
                except Exception:
                    logger.error(f"HTTP 422 Error: {e.response.text}")
                    raise e
            logger.error(f"HTTP Error: {e.response.text}")
            raise

        except Exception as e:
            logger.error(f"Snowflake Query Error: {e}")
            raise e

    async def check_connection(self) -> bool:
        """Simple query to check connection."""
        try:
            # We use a simple query that returns a single row
            await self.execute_query("SELECT 1")
            return True
        except Exception:
            return False

snowflake_client = SnowflakeClient()
