# Redis token-list semaphore

This module provides a simple Redis-backed counting semaphore implemented as a token list plus a token registry.

Key points
- `init_semaphore(name, permits)` creates tokens and a registry set.
- `acquire_token(name, timeout, lease_secs)` attempts to pop a token and sets a per-token owner key with TTL.
- `release_token(name, token)` returns the token and removes the owner key.
- `reclaim_expired(name)` scans the token registry and returns tokens whose owner keys expired.
- `Reclaimer` class can be used to run periodic reclamation in a separate process.

Running Redis locally for testing:

```powershell
docker run --name local-redis -p 6379:6379 -d redis:7
# then in PowerShell set REDIS_URL if needed
$env:REDIS_URL = 'redis://localhost:6379/0'
```

Example quickstart:

```python
from utils.redis_semaphore import init_semaphore, acquire_token, release_token

init_semaphore('sms:semaphore', permits=5)
token = acquire_token('sms:semaphore', timeout=3)
if token:
    try:
        # do work
        pass
    finally:
        release_token('sms:semaphore', token)
```

Run the reclaimer in background (recommended):

```powershell
python scripts/reclaimer_runner.py --name sms:semaphore --interval 30
```

Use this module in your SMS sending routes to limit concurrent sends across distributed workers.
