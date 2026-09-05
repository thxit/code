import os
import pickle
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Any
from loguru import logger


class DataCache:
    def __init__(self, cache_dir: str = "./data_cache", expire_hours: int = 4):
        self.cache_dir = cache_dir
        self.expire_hours = expire_hours
        os.makedirs(cache_dir, exist_ok=True)

    def _get_cache_key(self, *args, **kwargs) -> str:
        raw = str(args) + str(sorted(kwargs.items()))
        return hashlib.md5(raw.encode()).hexdigest()

    def _get_cache_path(self, key: str) -> str:
        return os.path.join(self.cache_dir, f"{key}.pkl")

    def get(self, *args, **kwargs) -> Optional[Any]:
        key = self._get_cache_key(*args, **kwargs)
        cache_path = self._get_cache_path(key)
        if not os.path.exists(cache_path):
            return None
        try:
            with open(cache_path, "rb") as f:
                cached = pickle.load(f)
            cached_time = cached.get("timestamp", 0)
            if datetime.now().timestamp() - cached_time > self.expire_hours * 3600:
                os.remove(cache_path)
                return None
            logger.debug(f"Cache hit: {key[:8]}")
            return cached.get("data")
        except Exception:
            return None

    def set(self, data: Any, *args, **kwargs):
        key = self._get_cache_key(*args, **kwargs)
        cache_path = self._get_cache_path(key)
        try:
            with open(cache_path, "wb") as f:
                pickle.dump({"timestamp": datetime.now().timestamp(), "data": data}, f)
            logger.debug(f"Cache set: {key[:8]}")
        except Exception as e:
            logger.warning(f"Cache write failed: {e}")

    def clear_expired(self):
        now = datetime.now().timestamp()
        for filename in os.listdir(self.cache_dir):
            if not filename.endswith(".pkl"):
                continue
            filepath = os.path.join(self.cache_dir, filename)
            try:
                with open(filepath, "rb") as f:
                    cached = pickle.load(f)
                if now - cached.get("timestamp", 0) > self.expire_hours * 3600:
                    os.remove(filepath)
            except Exception:
                os.remove(filepath)
