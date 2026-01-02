import json
import os
import time
from typing import Optional

CACHE_FILE = "local_cache.json"

class MockRedis:
    def __init__(self, url=None):
        self.file = CACHE_FILE
        # Ensure file exists
        if not os.path.exists(self.file):
            with open(self.file, "w") as f:
                json.dump({}, f)

    def _read_cache(self):
        try:
            with open(self.file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _write_cache(self, data):
        with open(self.file, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def from_url(cls, url):
        return cls(url)

    def get(self, key):
        data = self._read_cache()
        item = data.get(key)
        if not item:
            return None
        
        # Check expiry
        if item["expiry"] < time.time():
            del data[key]
            self._write_cache(data)
            return None
            
        return item["value"].encode("utf-8") # Real Redis returns bytes

    def setex(self, key, time_seconds, value):
        data = self._read_cache()
        data[key] = {
            "value": value,
            "expiry": time.time() + time_seconds
        }
        self._write_cache(data)
        return True
