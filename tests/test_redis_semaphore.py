"""Basic smoke test for utils.redis_semaphore.

This test will run only if REDIS_URL is set in the environment. It's a small smoke test that
initializes a small semaphore, acquires all tokens, ensures acquire fails when exhausted, then
releases and re-acquires.
"""
import os
import time

import pytest

redis_url = os.getenv("REDIS_URL")


pytestmark = pytest.mark.skipif(not redis_url, reason="REDIS_URL not set")


def test_token_lifecycle():
    from utils.redis_semaphore import init_semaphore, acquire_token, release_token, list_tokens

    name = "tests:sms:sem"
    init_semaphore(name, permits=3)
    tokens = []
    for _ in range(3):
        t = acquire_token(name, timeout=1, lease_secs=5)
        assert t is not None
        tokens.append(t)

    # now semaphore exhausted
    t = acquire_token(name, timeout=0.5)
    assert t is None

    # release one and acquire again
    release_token(name, tokens[0])
    t2 = acquire_token(name, timeout=1)
    assert t2 is not None
