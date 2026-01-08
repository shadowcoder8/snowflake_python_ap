"""
------------------------------------------------------------------------------
Project: Snowflake Data Product API
Developer: Rikesh Chhetri
Description: Dependency injection helpers for API authentication and authorization.
------------------------------------------------------------------------------
"""
import secrets
from fastapi import Header, HTTPException, Security
from typing import Annotated
from app.config import settings
from app.key_manager import key_manager

async def verify_api_key(x_api_key: Annotated[str, Header(description="API Key for external clients")]):
    """Verifies the X-API-KEY header securely against the dynamic key manager."""
    is_valid = False
    
    # Use KeyManager for validation
    if key_manager.is_valid(x_api_key):
        is_valid = True
    # Fallback to compare_digest against env vars if manager fails (redundant but safe)
    else:
        for valid_key in settings.valid_api_keys:
            if secrets.compare_digest(x_api_key, valid_key):
                is_valid = True
                break
            
    if not is_valid:
        raise HTTPException(
            status_code=401, 
            detail={
                "error": "Authentication Failed",
                "message": "Invalid API Key provided. Please check your credentials.",
                "tip": "Ensure you are using the correct 'X-API-KEY' header."
            }
        )
    return x_api_key

async def verify_admin_secret(x_admin_secret: Annotated[str, Header(description="Admin Secret for privileged operations")]):
    """Verifies the X-ADMIN-SECRET header."""
    if not settings.ADMIN_SECRET:
        raise HTTPException(status_code=503, detail="Admin access not configured")
        
    if not secrets.compare_digest(x_admin_secret, settings.ADMIN_SECRET):
        raise HTTPException(status_code=403, detail="Invalid Admin Secret")
    return x_admin_secret
