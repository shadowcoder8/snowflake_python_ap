import secrets
import string
import time
from collections import OrderedDict
from typing import Any, Optional, Tuple

def generate_secure_key(length=32, prefix="sk_"):
    """Generates a secure, high-entropy API key."""
    alphabet = string.ascii_letters + string.digits
    api_key = ''.join(secrets.choice(alphabet) for _ in range(length))
    return f"{prefix}{api_key}"

class TTLCache:
    """Simple LRU Cache with Time To Live (TTL)."""
    def __init__(self, capacity: int = 100, ttl_seconds: int = 300):
        self.cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self.capacity = capacity
        self.ttl = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        if key not in self.cache:
            return None
        value, timestamp = self.cache[key]
        if time.time() - timestamp > self.ttl:
            del self.cache[key]
            return None
        self.cache.move_to_end(key)
        return value

    def set(self, key: str, value: Any) -> None:
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = (value, time.time())
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)
