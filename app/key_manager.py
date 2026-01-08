import json
import os
from typing import List, Set
from app.config import settings, logger

KEY_FILE = "api_keys.json"

class KeyManager:
    def __init__(self):
        self._keys: Set[str] = set()
        self._load_keys()

    def _load_keys(self):
        """Loads keys from the JSON file. If not exists, falls back to env vars."""
        if os.path.exists(KEY_FILE):
            try:
                with open(KEY_FILE, "r") as f:
                    data = json.load(f)
                    self._keys = set(data.get("keys", []))
                    logger.info(f"Loaded {len(self._keys)} API keys from {KEY_FILE}")
            except Exception as e:
                logger.error(f"Failed to load api_keys.json: {e}")
        
        # Always include keys from .env as backup/initialization
        env_keys = settings.valid_api_keys
        if env_keys:
            count_before = len(self._keys)
            self._keys.update(env_keys)
            if len(self._keys) > count_before:
                self._save_keys() # Sync env keys to file

    def _save_keys(self):
        """Saves current keys to the JSON file."""
        try:
            with open(KEY_FILE, "w") as f:
                json.dump({"keys": list(self._keys)}, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save api_keys.json: {e}")

    def add_key(self, key: str):
        """Adds a new key and saves it."""
        self._keys.add(key)
        self._save_keys()
        logger.info("Added new API key")

    def revoke_key(self, key: str):
        """Removes a key and saves."""
        if key in self._keys:
            self._keys.remove(key)
            self._save_keys()
            logger.info("Revoked API key")

    def is_valid(self, key: str) -> bool:
        """Checks if a key exists."""
        # Reload checks could be added here for multi-worker sync, 
        # but for now in-memory set is fast and simple.
        return key in self._keys

# Global instance
key_manager = KeyManager()
