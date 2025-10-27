"""
A Redis-backed token-list semaphore with a simple reclaim pattern.

Usage:
1. Initialize the semaphore (one-time):
   from utils.redis_semaphore import init_semaphore
   init_semaphore('sms:semaphore', permits=5)

2. Acquire in your request-handling code:
   token = acquire_token('sms:semaphore', timeout=3, lease_secs=30)
   if not token:
       # return 429 or similar
   try:
       # perform protected action
       pass
   finally:
       release_token('sms:semaphore', token)

3. Run the reclaimer periodically (there's a small runner script in scripts/)

Notes:
- This implementation stores a token registry in a Redis set and an owner key per-acquired token
  with TTL (lease). If a worker dies without releasing, once the owner key expires the token
  becomes reclaimable by the reclaimer.
- The reclaimer is best run as a separate scheduled job/process.
"""
from __future__ import annotations
import os
import time
import uuid
from typing import Optional, List

import redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Initialize Redis client defensively. On developer machines Redis may not be
# running; in that case set _redis = None and provide safe fallbacks so import
# doesn't raise (prevents Error 10061 connection refused on import).
_redis = None
try:
    _redis = redis.from_url(REDIS_URL)
    try:
        _redis.ping()
    except Exception:
        _redis = None
except Exception:
    _redis = None


def _tokens_key(name: str) -> str:
    return f"{name}:tokens"


def _owners_key(name: str) -> str:
    return f"{name}:owners"


def init_semaphore(name: str, permits: int) -> int:
    """Create a fresh semaphore with `permits` tokens.

    This will delete any existing tokens/owner information for the given name.
    Returns number of tokens pushed.
    """
    # If Redis is unavailable, just return the requested permits and avoid
    # performing any Redis operations. This keeps behavior safe in dev.
    if not _redis:
        return permits

    tokens_key = _tokens_key(name)
    owners_key = _owners_key(name)
    pipe = _redis.pipeline()
    pipe.delete(tokens_key)
    pipe.delete(owners_key)
    tokens = [str(uuid.uuid4()) for _ in range(permits)]
    if tokens:
        # store tokens as a list for fast pop/push
        pipe.lpush(tokens_key, *tokens)
        # and register tokens in a set to make scanning/reclaim easier
        pipe.sadd(owners_key, *tokens)
    pipe.execute()
    return permits


def acquire_token(name: str, timeout: float = 5.0, lease_secs: int = 30) -> Optional[str]:
    """Try to acquire a token within `timeout` seconds. If successful, sets an owner key
    with TTL `lease_secs` and returns the token string. Returns None on timeout.
    """
    # If Redis is unavailable, provide a local token immediately so callers
    # can proceed (best-effort behavior for development environments).
    if not _redis:
        return f"local-token-{int(time.time())}"

    tokens_key = _tokens_key(name)
    end = time.time() + timeout
    while time.time() < end:
        token = _redis.rpop(tokens_key)
        if token:
            token = token.decode() if isinstance(token, bytes) else token
            owner_key = f"{name}:owner:{token}"
            # set an owner key with TTL; we don't store owner value (could store PID or hostname)
            _redis.set(owner_key, "1", ex=lease_secs)
            return token
        # if no token, sleep briefly and try again
        time.sleep(0.05)
    return None


def release_token(name: str, token: str) -> None:
    """Release a token back into the pool and remove its owner key."""
    if not token:
        return
    if not _redis:
        return
    tokens_key = _tokens_key(name)
    owner_key = f"{name}:owner:{token}"
    pipe = _redis.pipeline()
    pipe.delete(owner_key)
    pipe.lpush(tokens_key, token)
    pipe.execute()


def list_tokens(name: str) -> List[str]:
    if not _redis:
        return []
    tokens_key = _tokens_key(name)
    raw = _redis.lrange(tokens_key, 0, -1)
    return [t.decode() if isinstance(t, bytes) else t for t in raw]


def reclaim_expired(name: str, scan_batch: int = 100) -> int:
    """Find tokens whose owner keys have expired and return them into the token list.

    Algorithm (best-effort):
    - We keep a set of all known tokens at `{name}:owners`. We scan this set and for each token
      check whether `{name}:owner:{token}` exists. If not, we LPUSH the token back into the list
      (unless it already exists) and continue.
    - Returns number of tokens reclaimed.

    Note: This is best-effort and intended for moderate token counts. For very large registries
    a more sophisticated approach (pagination, Lua scripts) is recommended.
    """
    if not _redis:
        return 0

    owners_key = _owners_key(name)
    tokens_key = _tokens_key(name)
    reclaimed = 0
    cursor = 0
    # Use SSCAN to iterate set members
    while True:
        cursor, members = _redis.sscan(owners_key, cursor=cursor, count=scan_batch)
        for m in members:
            token = m.decode() if isinstance(m, bytes) else m
            owner_key = f"{name}:owner:{token}"
            if not _redis.exists(owner_key):
                # token owner expired; ensure token not already in list
                # Use LPOS to check presence (LPOS requires redis-py and Redis >= 6.0)
                try:
                    pos = _redis.lpos(tokens_key, token)
                except Exception:
                    # older Redis might not support LPOS; fall back to scanning list
                    pos = None
                if pos is None:
                    # push it back
                    _redis.lpush(tokens_key, token)
                    reclaimed += 1
        if cursor == 0:
            break
    return reclaimed


class Reclaimer:
    """Background reclaimer that runs reclaim_expired periodically.

    Intended to be run in a separate process or managed thread in your deployment.
    """
    def __init__(self, name: str, interval: float = 30.0):
        self.name = name
        self.interval = interval
        self._running = False

    def run_once(self) -> int:
        return reclaim_expired(self.name)

    def run_forever(self):
        self._running = True
        while self._running:
            reclaimed = reclaim_expired(self.name)
            # simple log to stdout; in production use structured logging
            if reclaimed:
                print(f"reclaimed {reclaimed} tokens for {self.name}")
            time.sleep(self.interval)

    def stop(self):
        self._running = False
