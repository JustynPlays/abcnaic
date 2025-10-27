"""
SMS helper that integrates Twilio (Verify or Programmable SMS) and uses the
Redis token-list semaphore (`utils.redis_semaphore`) to limit concurrent sends.

Environment variables used:
 - TWILIO_ACCOUNT_SID
 - TWILIO_AUTH_TOKEN
 - TWILIO_FROM  (for Programmable SMS)
 - TWILIO_VERIFY_SERVICE_SID (optional; if set, Verify is used)
 - REDIS_URL (used by redis client and redis_semaphore)

Usage:
  from utils.sms import send_otp, verify_otp
  send_otp(phone) -> {'ok': True, 'method': 'verify'|'sms'}
  verify_otp(phone, code) -> True/False

The module stores OTPs in Redis when using Programmable SMS (short TTL).
"""
from __future__ import annotations
import os
import random
import time
from typing import Optional

import phonenumbers
from twilio.rest import Client
import redis

# Defer importing the semaphore helpers; they may depend on Redis being available.
try:
    from utils.redis_semaphore import acquire_token, release_token
except Exception:
    # Provide safe fallbacks so SMS sending can proceed without Redis/semaphore.
    def acquire_token(semaphore_name: str, timeout: str = 3, lease_secs: int = 30):
        return f"local-token-{int(time.time())}"

    def release_token(semaphore_name: str, token: str):
        return None

# Configuration from env
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM = os.getenv("TWILIO_FROM")
TWILIO_VERIFY_SERVICE_SID = os.getenv("TWILIO_VERIFY_SERVICE_SID")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Initialize Redis client if available. Some dev machines don't have Redis running;
# in that case set _redis to None and proceed without rate-limiting/semaphore behavior.
_redis = None
try:
    _redis = redis.from_url(REDIS_URL)
    try:
        _redis.ping()
    except Exception:
        _redis = None
except Exception:
    _redis = None

_client = None
if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    _client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def normalize_phone(raw: str, default_region: str = "PH") -> str:
    """Parse and return E.164 formatted phone number or raise ValueError."""
    pn = phonenumbers.parse(raw, default_region)
    if not phonenumbers.is_possible_number(pn) or not phonenumbers.is_valid_number(pn):
        raise ValueError("invalid phone")
    return phonenumbers.format_number(pn, phonenumbers.PhoneNumberFormat.E164)


def _generate_otp(n: int = 6) -> str:
    return ''.join(str(random.randint(0, 9)) for _ in range(n))


def _rate_limit_ok(phone: str, per_seconds: int = 60, daily_limit: int = 5) -> bool:
    """Simple rate limiter using Redis: 1-per-`per_seconds`,  per-day `daily_limit`.
    Returns True if allowed, False if rate-limited.
    """
    # If Redis is unavailable, skip rate limiting and allow sending.
    if not _redis:
        return True

    short_key = f"sms:rate:short:{phone}"
    day_key = f"sms:rate:day:{phone}:{time.strftime('%Y-%m-%d')}"
    # short window
    if _redis.exists(short_key):
        return False
    pipe = _redis.pipeline()
    pipe.set(short_key, 1, ex=per_seconds)
    pipe.incr(day_key)
    pipe.expire(day_key, 60 * 60 * 24)
    pipe.execute()
    # check day count
    count = int(_redis.get(day_key) or 0)
    return count <= daily_limit


def send_otp(raw_phone: str, semaphore_name: str = "sms:semaphore") -> dict:
    """Send an OTP to `raw_phone`. Uses Twilio Verify if configured, otherwise sends a
    programmable SMS and stores an OTP in Redis with a short TTL.

    This function acquires a token from the Redis semaphore before sending and releases it
    after the attempt.
    Returns a dict with keys: ok, method, error (optional).
    """
    try:
        phone = normalize_phone(raw_phone)
    except ValueError:
        return {"ok": False, "error": "invalid_phone"}

    if not _rate_limit_ok(phone):
        return {"ok": False, "error": "rate_limited"}

    token = acquire_token(semaphore_name, timeout=3, lease_secs=30)
    if not token:
        return {"ok": False, "error": "server_busy"}

    try:
        if TWILIO_VERIFY_SERVICE_SID and _client:
            # use Verify
            _client.verify.services(TWILIO_VERIFY_SERVICE_SID).verifications.create(
                to=phone, channel="sms"
            )
            return {"ok": True, "method": "verify"}

        # fallback: programmable SMS with Redis-stored OTP
        if not _client or not TWILIO_FROM:
            return {"ok": False, "error": "twilio_not_configured"}

        # Programmable SMS path requires Redis to store OTP state; if Redis is
        # unavailable, return an explicit error to avoid silent failures.
        if not _redis:
            return {"ok": False, "error": "redis_unavailable"}

        otp = _generate_otp(6)
        otp_key = f"sms:otp:{phone}"
        # store OTP with TTL 5 minutes and allow 3 attempts
        pipe = _redis.pipeline()
        pipe.set(otp_key, otp, ex=300)
        pipe.set(f"{otp_key}:tries", 3, ex=300)
        pipe.execute()

        body = f"Your verification code is {otp}. It expires in 5 minutes."
        _client.messages.create(body=body, from_=TWILIO_FROM, to=phone)
        return {"ok": True, "method": "sms"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        try:
            release_token(semaphore_name, token)
        except Exception:
            # don't break on release failure
            pass


def verify_otp(raw_phone: str, code: str) -> bool:
    """Verify an OTP previously sent.
    If Verify is configured, check with Twilio Verify. Otherwise check Redis-stored OTP.
    On successful verification the Redis stored OTP is deleted.
    """
    phone = normalize_phone(raw_phone)
    if TWILIO_VERIFY_SERVICE_SID and _client:
        try:
            chk = _client.verify.services(TWILIO_VERIFY_SERVICE_SID).verification_checks.create(
                to=phone, code=code
            )
            return getattr(chk, "status", None) == "approved"
        except Exception:
            return False

    # If Verify service is not configured we require Redis to check stored OTPs.
    if not TWILIO_VERIFY_SERVICE_SID and not _redis:
        return False

    otp_key = f"sms:otp:{phone}"
    stored = _redis.get(otp_key)
    if not stored:
        return False
    stored = stored.decode() if isinstance(stored, bytes) else stored
    tries_key = f"{otp_key}:tries"
    tries = int(_redis.get(tries_key) or 0)
    if tries <= 0:
        # expired or locked
        _redis.delete(otp_key)
        _redis.delete(tries_key)
        return False
    if stored == code:
        _redis.delete(otp_key)
        _redis.delete(tries_key)
        return True
    else:
        _redis.decr(tries_key)
        return False


def send_message(raw_phone: str, body: str, semaphore_name: str = "sms:semaphore") -> dict:
    """Send an arbitrary SMS message to `raw_phone` using the semaphore to limit concurrency.
    Returns dict {ok: bool, error: str?} similar to send_otp.
    """
    try:
        phone = normalize_phone(raw_phone)
    except ValueError:
        return {"ok": False, "error": "invalid_phone"}

    token = acquire_token(semaphore_name, timeout=3, lease_secs=30)
    if not token:
        return {"ok": False, "error": "server_busy"}

    try:
        if not _client or not TWILIO_FROM:
            return {"ok": False, "error": "twilio_not_configured"}

        _client.messages.create(body=body, from_=TWILIO_FROM, to=phone)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        try:
            release_token(semaphore_name, token)
        except Exception:
            pass
