"""
------------------------------------------------------------------------------
Project: Snowflake Data Product API
Developer: Rikesh Chhetri
Description: Security utilities for JWT generation and key management.
------------------------------------------------------------------------------
"""
from datetime import datetime, timedelta, timezone
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import jwt
import os
import hashlib
import base64
from typing import Optional, Tuple
from app.config import settings, logger

# Global cache
_PRIVATE_KEY_CACHE = None
_JWT_CACHE: Optional[Tuple[str, datetime]] = None

def load_private_key():
    """Loads the private key from the specified path with caching."""
    global _PRIVATE_KEY_CACHE
    
    if _PRIVATE_KEY_CACHE:
        return _PRIVATE_KEY_CACHE
        
    try:
        if settings.SNOWFLAKE_PRIVATE_KEY_CONTENT:
            logger.info("Loading private key from environment variable (SNOWFLAKE_PRIVATE_KEY_CONTENT)")
            key_bytes = settings.SNOWFLAKE_PRIVATE_KEY_CONTENT.encode()
        else:
            logger.info(f"Loading private key from file: {os.path.abspath(settings.SNOWFLAKE_PRIVATE_KEY_PATH)}")
            with open(settings.SNOWFLAKE_PRIVATE_KEY_PATH, "rb") as key_file:
                key_bytes = key_file.read()

        private_key = serialization.load_pem_private_key(
            key_bytes,
            password=settings.SNOWFLAKE_PRIVATE_KEY_PASSPHRASE.encode() if settings.SNOWFLAKE_PRIVATE_KEY_PASSPHRASE else None,
            backend=default_backend()
        )
        _PRIVATE_KEY_CACHE = private_key
        return private_key
    except Exception as e:
        logger.error(f"Failed to load private key: {e}")
        raise

def get_snowflake_jwt() -> str:
    """Generates or retrieves a valid JWT for Snowflake authentication."""
    global _JWT_CACHE
    
    now = datetime.now(timezone.utc)
    
    # Check if we have a valid cached token (with 5 minutes buffer)
    if _JWT_CACHE:
        token, expires_at = _JWT_CACHE
        if now < (expires_at - timedelta(minutes=5)):
            return token
            
    try:
        private_key = load_private_key()
        
        account = settings.SNOWFLAKE_ACCOUNT.upper()
        user = settings.SNOWFLAKE_USER.upper()
        qualified_username = f"{account}.{user}"
        
        lifetime = timedelta(minutes=59) # Max 60 minutes
        expires_at = now + lifetime
        
        # Calculate Public Key Fingerprint
        public_key = private_key.public_key()
        public_key_der = public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        sha256_hash = hashlib.sha256(public_key_der).digest()
        fingerprint = base64.b64encode(sha256_hash).decode('utf-8')
        
        payload = {
            "iss": f"{qualified_username}.SHA256:{fingerprint}",
            "sub": qualified_username,
            "iat": now,
            "exp": expires_at
        }

        encoded_jwt = jwt.encode(
            payload,
            private_key,
            algorithm="RS256"
        )
        
        # Update cache
        _JWT_CACHE = (encoded_jwt, expires_at)
        
        return encoded_jwt
    except Exception as e:
        logger.error(f"Failed to generate Snowflake JWT: {e}")
        raise
