import os

import pika
from dotenv import load_dotenv

load_dotenv()


def produce(host, body):
    username = os.environ.get("RABBITMQ_DEFAULT_USER")
    password = os.environ.get("RABBITMQ_DEFAULT_PASS")
    port = int(os.environ.get("RABBITMQ_PORT", "5672"))

    if not username or not password:
        raise RuntimeError("RabbitMQ username and password are required")

    credentials = pika.PlainCredentials(username, password)
    parameters = pika.ConnectionParameters(
        host=host,
        port=port,
        credentials=credentials,
        heartbeat=60,
        blocked_connection_timeout=30,
    )

    connection = pika.BlockingConnection(parameters)
    try:
        channel = connection.channel()
        channel.exchange_declare(exchange="jobs", exchange_type="direct")
        channel.queue_declare(queue="router_jobs")
        channel.queue_bind(
            queue="router_jobs",
            exchange="jobs",
            routing_key="check_interfaces",
        )
        channel.basic_publish(
            exchange="jobs",
            routing_key="check_interfaces",
            body=body,
        )
    finally:
        connection.close()


if __name__ == "__main__":
    produce("localhost", "192.168.1.44")
