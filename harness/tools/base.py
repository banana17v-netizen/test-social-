import functools, time
from dataclasses import dataclass
from typing import Callable, Literal
from pydantic import BaseModel
from harness import LOGGER as log

try:
    from anthropic import RateLimitError
except ImportError:
    class RateLimitError(Exception): pass

@dataclass
class _Entry:
    value: object
    expires: float

class TTLCache:
    def __init__(self): self._data: dict[str, _Entry] = {}
    def get(self, key): return self._data.get(key)
    def set(self, key, value, ttl): self._data[key] = _Entry(value, time.time() + ttl)
    def clear(self): self._data.clear()

CACHE = TTLCache()

class ToolResult(BaseModel):
    data: dict
    source_health: Literal["ok", "degraded", "down"]

def tool_harness(cache_ttl: int = 120, max_retries: int = 2):
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs) -> ToolResult:
            key = f"{fn.__name__}:{args}:{kwargs}"
            if (cached := CACHE.get(key)) and cached.expires > time.time():
                return cached.value
            for attempt in range(max_retries + 1):
                try:
                    data = fn(*args, **kwargs)
                    result = ToolResult(data=data, source_health="ok")
                    CACHE.set(key, result, ttl=cache_ttl)
                    return result
                except RateLimitError:
                    time.sleep(2 ** attempt)
                except Exception as e:
                    log.warning(f"{fn.__name__} attempt {attempt} failed: {e}")
            return ToolResult(data={}, source_health="down")
        return wrapper
    return decorator

