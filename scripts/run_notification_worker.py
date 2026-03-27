#!/usr/bin/env python3
"""
Run the notification worker as a standalone process.
Usage: python -m scripts.run_notification_worker [--interval 30] [--batch 50]
"""
import argparse
import asyncio
import logging
import sys

# Ensure project root is on path
sys.path.insert(0, "")

from app.services.notifications.worker import worker_loop

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    p = argparse.ArgumentParser(description="HSM Notification worker")
    p.add_argument("--interval", type=int, default=30, help="Seconds between poll cycles")
    p.add_argument("--batch", type=int, default=50, help="Max jobs per cycle")
    args = p.parse_args()
    asyncio.run(worker_loop(interval_seconds=args.interval, batch_size=args.batch))


if __name__ == "__main__":
    main()
