import time
import json
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import logger

class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Extract client info
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        process_time = (time.time() - start_time) * 1000
        
        # Extract API Key ID (masked) if present
        # We rely on the fact that verify_api_key might have run, 
        # but middleware runs before dependencies usually, or wraps them.
        # However, we can check the header directly.
        api_key = request.headers.get("X-API-KEY")
        key_id = f"sk_...{api_key[-4:]}" if api_key and len(api_key) > 4 else "anonymous"

        # Structured Log
        log_entry = {
            "timestamp": time.time(),
            "event": "api_request",
            "client_ip": client_ip,
            "user_agent": user_agent,
            "method": request.method,
            "path": request.url.path,
            "query": str(request.query_params),
            "status_code": response.status_code,
            "duration_ms": round(process_time, 2),
            "key_id": key_id
        }
        
        # Log at INFO level
        # In a real setup, we might write this to a separate audit.log file
        logger.info(json.dumps(log_entry))
        
        return response
