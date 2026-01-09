# app/utils/cache_manager.py
import json
from typing import Optional, Any
from app.utils.mock_redis import MockRedis
from app.models.schemas import ItemOut

class CacheManager:
    def __init__(self):
        self.redis = MockRedis.from_url("local")
        self.ttl = 3600  # Default 1 hour TTL

    def get_item(self, item_id: str) -> Optional[dict]:
        """Retrieve an item from cache."""
        cached = self.redis.get(f"item:{item_id}")
        if cached:
            return json.loads(cached.decode("utf-8"))
        return None

    def set_item(self, item_id: str, item_data: dict):
        """Store an item in cache."""
        # Convert datetime objects to string if they exist
        # ItemOut objects handled by pydantic's model_dump/json
        self.redis.setex(f"item:{item_id}", self.ttl, json.dumps(item_data, default=str))

    def invalidate_item(self, item_id: str):
        """Remove an item from cache."""
        self.redis.delete(f"item:{item_id}")

cache_manager = CacheManager()
