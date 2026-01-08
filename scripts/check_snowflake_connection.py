
import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from app.snowflake_client import snowflake_client
from app.config import settings
from app.registry import load_view_registry

async def main():
    print(f"--- Snowflake Connectivity Check ---")
    print(f"Account: {settings.SNOWFLAKE_ACCOUNT}")
    print(f"User: {settings.SNOWFLAKE_USER}")
    print(f"Warehouse: {settings.SNOWFLAKE_WAREHOUSE}")
    print(f"Database: {settings.SNOWFLAKE_DATABASE}")
    print(f"Schema: {settings.SNOWFLAKE_SCHEMA}")
    print("------------------------------------")

    # 1. Check Basic Connectivity
    print("\n[1] Checking Basic Connectivity (SELECT 1)...")
    try:
        if await snowflake_client.check_connection():
            print("✅ Connection Successful!")
        else:
            print("❌ Connection Failed.")
            return
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return

    # 2. Load Registry
    print("\n[2] Loading View Registry...")
    try:
        registry = load_view_registry()
        print(f"✅ Loaded {len(registry)} views from registry.")
    except Exception as e:
        print(f"❌ Failed to load registry: {e}")
        registry = {}

    # 3. Check Permissions for each View
    print("\n[3] Checking Permissions for Views...")
    success_count = 0
    fail_count = 0
    
    for slug, table_name in registry.items():
        print(f"   > Checking '{slug}' -> '{table_name}'...", end=" ", flush=True)
        try:
            # 1. Check permission with LIMIT 1
            query_perm = f"SELECT * FROM {table_name} LIMIT 1"
            await asyncio.wait_for(snowflake_client.execute_query(query_perm), timeout=5.0)
            
            # 2. Check Count (if permission ok)
            # Use a slightly longer timeout for count
            query_count = f"SELECT COUNT(*) as CNT FROM {table_name}"
            count_res = await asyncio.wait_for(snowflake_client.execute_query(query_count), timeout=10.0)
            count = int(count_res[0]['cnt']) if count_res else 0
            
            print(f"✅ OK (Rows: {count})")

            # 3. Check Partition Fetching (reproduce 821 vs 1000 issue)
            if count > 1000:
                print(f"     > Verifying LIMIT 1000...", end=" ", flush=True)
                try:
                    query_limit = f"SELECT * FROM {table_name} LIMIT 1000"
                    # Set a strict timeout of 8 seconds for this check
                    limit_res = await asyncio.wait_for(snowflake_client.execute_query(query_limit), timeout=8.0)
                    rows = len(limit_res)
                    if rows == 1000:
                        print(f"✅ Fetched {rows}")
                    else:
                        print(f"⚠️ Fetched {rows} (Expected 1000)")
                except asyncio.TimeoutError:
                    print(f"⚠️ SKIPPED (Timeout > 8s)")
                except Exception as e:
                    print(f"⚠️ FAILED (Query Error: {str(e)})")
            else:
                print(f"     > Skipping LIMIT 1000 (Table has {count} rows)")
            
            success_count += 1
        except asyncio.TimeoutError:
            print(f"❌ TIMEOUT (5s)")
            fail_count += 1
        except Exception as e:
            print(f"❌ FAILED")
            # Clean error message
            msg = str(e)
            if "Snowflake Error" in msg:
                print(f"     Reason: {msg}")
            else:
                print(f"     Error: {msg}")
            fail_count += 1

    print("\n------------------------------------")
    print(f"Summary: {success_count} Passed, {fail_count} Failed.")
    
    if fail_count > 0:
        print("\n⚠️  Some views are not accessible. Please check:")
        print("   1. Does the table/view exist in the configured Schema?")
        print(f"   2. Does user '{settings.SNOWFLAKE_USER}' have SELECT privileges?")
        print(f"   3. Is the Warehouse '{settings.SNOWFLAKE_WAREHOUSE}' running?")

    await snowflake_client.close()

if __name__ == "__main__":
    asyncio.run(main())
