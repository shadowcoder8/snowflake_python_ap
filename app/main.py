"""
------------------------------------------------------------------------------
Project: Snowflake Data Product API
Developer: Rikesh Chhetri
Description: Main entry point for the FastAPI application.
------------------------------------------------------------------------------
"""
from fastapi import FastAPI, Depends, HTTPException, Query, Path, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from contextlib import asynccontextmanager
from typing import List, Any, Dict, Optional, Union
import httpx
import json

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings, logger
from app.dependencies import verify_api_key, verify_admin_secret
from app.snowflake_client import snowflake_client
from app.models import StandardResponse, MetaData
from app.utils import generate_secure_key, TTLCache
from app.key_manager import key_manager
from app.registry import VIEW_ALLOWLIST
from app.middleware import AuditMiddleware

# Initialize Cache (stores up to 100 queries for 5 minutes)
response_cache = TTLCache(ttl_seconds=300)

# Rate Limit Key Function: Limit by API Key if present, otherwise fallback to IP
def get_rate_limit_key(request: Request) -> str:
    return request.headers.get("X-API-KEY", get_remote_address(request))

# Initialize Rate Limiter with API Key tracking
limiter = Limiter(key_func=get_rate_limit_key)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up Data Product API...")
    yield
    # Shutdown
    logger.info("Shutting down...")
    await snowflake_client.close()

app = FastAPI(
    title="Snowflake Data Product API",
    version="2.1.0",
    description="Developed by Rikesh Chhetri",
    lifespan=lifespan
)

# Register Middleware
app.add_middleware(AuditMiddleware)
app.add_middleware(SlowAPIMiddleware)

# Register Rate Limit Handler
app.state.limiter = limiter
@app.exception_handler(RateLimitExceeded)
async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "status": "error", 
            "code": "RATE_LIMIT_EXCEEDED",
            "message": f"Rate limit exceeded: {exc.detail}",
            "details": "Please wait before sending more requests."
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Simplify validation errors to a string
    errors = []
    for error in exc.errors():
        field = ".".join(str(x) for x in error["loc"])
        msg = error["msg"]
        errors.append(f"{field}: {msg}")
    
    return JSONResponse(
        status_code=422,
        content={
            "status": "error", 
            "code": "VALIDATION_ERROR",
            "message": "The request inputs were invalid.", 
            "details": errors
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    content = {
        "status": "error",
        "code": str(exc.status_code),
        "message": exc.detail
    }
    
    # If detail is a dict, merge it
    if isinstance(exc.detail, dict):
        content.update(exc.detail)
        # Ensure standard keys exist if the dict didn't provide them
        if "message" not in content:
            content["message"] = "An error occurred."
            
    return JSONResponse(
        status_code=exc.status_code,
        content=content
    )

@app.exception_handler(httpx.RequestError)
async def upstream_connection_error_handler(request: Request, exc: httpx.RequestError):
    logger.error(f"Upstream Connection Error: {exc}")
    return JSONResponse(
        status_code=503,
        content={"status": "error", "message": "Service Unavailable: Unable to connect to Snowflake"}
    )

@app.exception_handler(httpx.HTTPStatusError)
async def http_status_error_handler(request: Request, exc: httpx.HTTPStatusError):
    logger.error(f"Upstream API Error: {exc.response.text}")
    
    status_code = exc.response.status_code
    error_code = "UNKNOWN"
    message = "An upstream error occurred."
    details = None

    try:
        error_data = exc.response.json()
        message = error_data.get("message", exc.response.text)
        error_code = error_data.get("code", str(status_code))
        
        # Smart Mapping of Snowflake Errors
        if error_code == "002003": # Object does not exist
            status_code = 404
            message = "The requested data view could not be found in Snowflake."
            details = {"snowflake_message": error_data.get("message")}
        elif error_code == "001003": # SQL Compilation Error
            status_code = 400
            message = "Invalid Query generated."
            details = {"snowflake_message": error_data.get("message")}
            
    except Exception:
        message = exc.response.text
        
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "error",
            "code": error_code,
            "message": message,
            "details": details
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "Internal Server Error"}
    )

@app.get("/health", tags=["System"])
@limiter.limit("5/minute")
async def health_check(request: Request):
    """Checks service health and Snowflake connectivity."""
    snowflake_status = await snowflake_client.check_connection()
    status = "healthy" if snowflake_status else "degraded"
    return {
        "status": status,
        "service": "up",
        "snowflake": "connected" if snowflake_status else "disconnected",
        "developer": "Rikesh Chhetri"
    }

@app.post("/v1/admin/generate-key", tags=["Admin"], dependencies=[Depends(verify_admin_secret)])
async def generate_new_api_key(request: Request):
    """
    Generates a new secure API key and activates it immediately.
    Requires 'X-ADMIN-SECRET' header.
    """
    new_key = generate_secure_key()
    key_manager.add_key(new_key)
    
    return {
        "status": "success",
        "generated_key": new_key,
        "message": "Key generated and activated successfully. It is ready to use immediately."
    }

async def fetch_table_data(table_name: str, limit: int, offset: int, filters: Optional[Dict[str, Any]] = None, response: Optional[Response] = None):
    """
    Helper to fetch paginated data from a table/view with caching and filtering.
    """
    try:
        # Check Cache (only if no filters are applied, for simplicity, or include filters in cache key)
        # Including filters in cache key is better.
        filter_str = str(sorted(filters.items())) if filters else ""
        cache_key = f"{table_name}:{limit}:{offset}:{filter_str}"
        
        cached_result = response_cache.get(cache_key)
        if cached_result:
            logger.info(f"Cache hit for {cache_key}")
            # Add cache hit header if response object is available
            if response:
                response.headers["X-Cache"] = "HIT"
            return cached_result

        query = f"SELECT * FROM {table_name}"
        bindings = {"limit": limit, "offset": offset}
        
        # Add WHERE clauses for filters
        if filters:
            where_clauses = []
            for i, (col, val) in enumerate(filters.items()):
                # Strict column name validation (alphanumeric + underscore only)
                if not col.replace("_", "").isalnum():
                    logger.warning(f"Invalid column name in filter: {col}")
                    continue
                
                param_name = f"filter_{i}"
                where_clauses.append(f"{col} = :{param_name}")
                bindings[param_name] = val
            
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
        
        query += " LIMIT :limit OFFSET :offset"
        
        results = await snowflake_client.execute_query(query, bindings)
        
        # Set headers
        if response:
            response.headers["X-Result-Count"] = str(len(results))
            response.headers["X-Cache"] = "MISS"

        response_obj = StandardResponse(
            data=results,
            meta=MetaData(
                total=len(results), 
                limit=limit,
                offset=offset
            )
        )
        
        # Set Cache
        response_cache.set(cache_key, response_obj)
        
        return response_obj
    except Exception as e:
        logger.error(f"Error fetching {table_name}: {e}")
        raise e

async def stream_table_data(table_name: str, filters: Optional[Dict[str, Any]] = None):
    """
    Helper to stream data from a table/view using NDJSON format.
    Bypasses cache and pagination limits for large data exports.
    """
    try:
        query = f"SELECT * FROM {table_name}"
        bindings = {}
        
        if filters:
            where_clauses = []
            for i, (col, val) in enumerate(filters.items()):
                if not col.replace("_", "").isalnum():
                    continue
                param_name = f"filter_{i}"
                where_clauses.append(f"{col} = :{param_name}")
                bindings[param_name] = val
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
        
        # Generator function
        async def generate():
            async for row in snowflake_client.execute_query_stream(query, bindings):
                yield json.dumps(row) + "\n"
                
        return StreamingResponse(generate(), media_type="application/x-ndjson")
        
    except Exception as e:
        logger.error(f"Error streaming {table_name}: {e}")
        raise e

@app.get(
    "/v1/data/{view_id}",
    response_model=Union[StandardResponse[List[Any]], Any],
    dependencies=[Depends(verify_api_key)],
    tags=["Dynamic Data"]
)
@limiter.limit("50/minute")
async def get_data_view(
    request: Request,
    response: Response,
    view_id: str = Path(..., description="The ID of the view to fetch (e.g., 'companies', 'fbi-crime')"),
    limit: int = Query(settings.DEFAULT_PAGE_LIMIT, ge=1, le=settings.MAX_PAGE_LIMIT, description="Max records to return (ignored if stream=true)"),
    offset: int = Query(0, ge=0, description="Records to skip (ignored if stream=true)"),
    stream: bool = Query(False, description="If true, returns NDJSON stream for large datasets"),
    # Helper params for Swagger UI testing
    test_filter_col: Optional[str] = Query(None, description="For Swagger UI testing: Specify a column name to filter by (e.g., 'industry')"),
    test_filter_val: Optional[str] = Query(None, description="For Swagger UI testing: Specify the value for the filter (e.g., 'Tech')")
):
    """
    Dynamic endpoint to fetch data from any registered view.
    
    **Supported Features:**
    - **Pagination**: `limit` & `offset` (Defaults defined in config)
    - **Streaming**: `?stream=true` (NDJSON format, no size limit)
    - **Generic Filtering**: Any additional query parameters are treated as column filters.
      - Example: `?industry=Tech` -> `WHERE industry = 'Tech'`
    
    **Testing in Swagger UI:**
    Since Swagger UI cannot generate dynamic fields, use `test_filter_col` and `test_filter_val` below to simulate a filter like `?industry=Tech`.
    """
    # 1. Resolve view_id to Table Name
    table_name = None
    if view_id in VIEW_ALLOWLIST:
        table_name = VIEW_ALLOWLIST[view_id]
    elif view_id in VIEW_ALLOWLIST.values():
        table_name = view_id
    
    if not table_name:
        # Fallback case-insensitive
        upper_view_id = view_id.upper().replace("-", "_")
        if upper_view_id in VIEW_ALLOWLIST:
            table_name = VIEW_ALLOWLIST[upper_view_id]
        elif upper_view_id in VIEW_ALLOWLIST.values():
            table_name = upper_view_id
            
    if not table_name:
         raise HTTPException(status_code=404, detail=f"View '{view_id}' not found or not allowed.")

    # 2. Extract Filters
    filters = {}
    
    # Handle explicit Swagger test params
    if test_filter_col and test_filter_val:
        filters[test_filter_col] = test_filter_val

    for key, value in request.query_params.items():
        if key not in ["limit", "offset", "stream", "test_filter_col", "test_filter_val"]:
            filters[key] = value
            
    # 3. Stream or Fetch
    if stream:
        return await stream_table_data(table_name, filters)
    else:
        return await fetch_table_data(table_name, limit, offset, filters, response)
