import os
import time

from bson import json_util
from database import get_router_info
from pika.exceptions import AMQPError
from producer import produce
from pymongo.errors import PyMongoError


def scheduler():
    interval = float(os.environ.get("SCHEDULER_INTERVAL", "10"))
    rabbitmq_host = os.environ.get("RABBITMQ_HOST", "rabbitmq")
    run_count = 0

    while True:
        started_at = time.monotonic()
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        try:
            routers = get_router_info()
            for router in routers:
                produce(rabbitmq_host, json_util.dumps(router))

            print(
                f"[{timestamp}] run #{run_count}: "
                f"published {len(routers)} router job(s)",
                flush=True,
            )
        except (
            PyMongoError,
            AMQPError,
            OSError,
            RuntimeError,
            ValueError,
        ) as exc:
            print(f"[{timestamp}] run #{run_count} failed: {exc}", flush=True)

        run_count += 1
        elapsed = time.monotonic() - started_at
        time.sleep(max(0, interval - elapsed))


if __name__ == "__main__":
    scheduler()
