"""
Small runner to start the `Reclaimer` for a named semaphore.

Run this as a background process (supervisor, systemd, or separate container) to reclaim
expired tokens for a semaphore key.

Usage:
  python scripts/reclaimer_runner.py --name sms:semaphore --interval 30

Requires: REDIS_URL env var if Redis is not at default location.
"""
import argparse
import time
from utils.redis_semaphore import Reclaimer


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--name", required=True, help="semaphore base name (e.g. sms:semaphore)")
    p.add_argument("--interval", type=float, default=30.0, help="reclaim interval seconds")
    args = p.parse_args()

    r = Reclaimer(args.name, interval=args.interval)
    try:
        print(f"Starting reclaimer for {args.name} (interval={args.interval}s)")
        r.run_forever()
    except KeyboardInterrupt:
        print("Stopping reclaimer")
        r.stop()


if __name__ == "__main__":
    main()
