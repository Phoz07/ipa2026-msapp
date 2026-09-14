import os
import time
from datetime import datetime, timezone
from urllib.parse import quote_plus

import pika
from bson import json_util
from dotenv import load_dotenv
from netmiko import ConnectHandler
from netmiko.exceptions import (
    NetmikoAuthenticationException,
    NetmikoBaseException,
    NetmikoTimeoutException,
)
from pika.exceptions import AMQPError
from pymongo import MongoClient
from pymongo.errors import PyMongoError

load_dotenv()

EXCHANGE = "jobs"
QUEUE = "router_jobs"
ROUTING_KEY = "check_interfaces"
COMMAND = "show ip interface brief"


def get_mongo_uri():
    configured_uri = os.environ.get("MONGO_URI")
    if configured_uri:
        return configured_uri

    username = os.environ.get("MONGO_INITDB_ROOT_USERNAME")
    password = os.environ.get("MONGO_INITDB_ROOT_PASSWORD")
    host = os.environ.get("MONGO_HOST", "mongo")
    port = os.environ.get("MONGO_PORT", "27017")

    if username and password:
        return (
            f"mongodb://{quote_plus(username)}:{quote_plus(password)}"
            f"@{host}:{port}/?authSource=admin"
        )

    return f"mongodb://{host}:{port}/"


def get_rabbitmq_parameters():
    username = os.environ.get("RABBITMQ_DEFAULT_USER")
    password = os.environ.get("RABBITMQ_DEFAULT_PASS")

    if not username or not password:
        raise RuntimeError("RabbitMQ username and password are required")

    return pika.ConnectionParameters(
        host=os.environ.get("RABBITMQ_HOST", "rabbitmq"),
        port=int(os.environ.get("RABBITMQ_PORT", "5672")),
        credentials=pika.PlainCredentials(username, password),
        heartbeat=60,
        blocked_connection_timeout=30,
    )


def parse_router_job(body):
    router = json_util.loads(body.decode("utf-8"))
    required_fields = ("ip_address", "username", "password")
    missing_fields = [field for field in required_fields if not router.get(field)]

    if missing_fields:
        raise ValueError(f"Missing router fields: {', '.join(missing_fields)}")

    return router


def collect_interfaces(router):
    device = {
        "device_type": router.get(
            "device_type", os.environ.get("ROUTER_DEVICE_TYPE", "cisco_ios")
        ),
        "host": router["ip_address"],
        "username": router["username"],
        "password": router["password"],
        "conn_timeout": int(os.environ.get("SSH_CONNECT_TIMEOUT", "10")),
        "auth_timeout": int(os.environ.get("SSH_AUTH_TIMEOUT", "10")),
        "banner_timeout": int(os.environ.get("SSH_BANNER_TIMEOUT", "15")),
    }

    with ConnectHandler(**device) as connection:
        return connection.send_command(
            COMMAND,
            use_textfsm=True,
            read_timeout=int(os.environ.get("SSH_COMMAND_TIMEOUT", "30")),
        )


def save_result(results, router, output):
    document = {
        "router_id": router.get("_id"),
        "ip_address": router["ip_address"],
        "command": COMMAND,
        "parsed": isinstance(output, list),
        "result": output,
        "timestamp": datetime.now(timezone.utc),
    }
    results.insert_one(document)


def create_callback(results):
    def process_message(channel, method, properties, body):
        del properties

        try:
            router = parse_router_job(body)
            output = collect_interfaces(router)
            save_result(results, router, output)
            channel.basic_ack(delivery_tag=method.delivery_tag)
            print(
                f"Saved interface data from {router['ip_address']}",
                flush=True,
            )
        except (
            NetmikoAuthenticationException,
            NetmikoBaseException,
            NetmikoTimeoutException,
            PyMongoError,
            UnicodeDecodeError,
            ValueError,
        ) as exc:
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            print(f"Worker job failed: {exc}", flush=True)

    return process_message


def consume():
    database_name = os.environ.get("MONGO_DB", "mydatabase")
    results_collection = os.environ.get(
        "MONGO_RESULTS_COLLECTION", "router_interface_results"
    )

    with MongoClient(get_mongo_uri(), serverSelectionTimeoutMS=5000) as mongo_client:
        mongo_client.admin.command("ping")
        results = mongo_client[database_name][results_collection]

        connection = pika.BlockingConnection(get_rabbitmq_parameters())
        try:
            channel = connection.channel()
            channel.exchange_declare(exchange=EXCHANGE, exchange_type="direct")
            channel.queue_declare(queue=QUEUE)
            channel.queue_bind(
                queue=QUEUE,
                exchange=EXCHANGE,
                routing_key=ROUTING_KEY,
            )
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(
                queue=QUEUE,
                on_message_callback=create_callback(results),
            )
            print("Worker1 is waiting for router jobs", flush=True)
            channel.start_consuming()
        finally:
            if connection.is_open:
                connection.close()


def main():
    retry_interval = int(os.environ.get("WORKER_RETRY_INTERVAL", "5"))

    while True:
        try:
            consume()
        except (AMQPError, OSError, PyMongoError, RuntimeError) as exc:
            print(f"Worker connection failed: {exc}; retrying", flush=True)
            time.sleep(retry_interval)


if __name__ == "__main__":
    main()
