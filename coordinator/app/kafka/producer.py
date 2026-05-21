from confluent_kafka import Producer
from app.core.config import settings
import json
import logging

logger = logging.getLogger(__name__)

_producer: Producer = None


def get_producer() -> Producer:
    global _producer
    if _producer is None:
        _producer = Producer({
            "bootstrap.servers": "kafka:29092",
            "client.id": "hermes-coordinator",
        })
    return _producer


def delivery_report(err, msg):
    if err:
        logger.error(f"Message delivery failed: {err}")
    else:
        logger.info(f"Message delivered to {msg.topic()} partition {msg.partition()} offset {msg.offset()}")


async def publish_task(task_message: dict, topic: str = None) -> None:
    """
    Publishes a task message to Kafka.
    Defaults to hermes.tasks — pass topic='hermes.tasks.dlq' for DLQ.
    """
    producer = get_producer()
    target_topic = topic or settings.KAFKA_TASKS_TOPIC

    producer.produce(
        topic=target_topic,
        key=task_message["task_execution_id"],
        value=json.dumps(task_message).encode("utf-8"),
        callback=delivery_report
    )
    producer.poll(0)
    logger.info(f"Published task {task_message['task_execution_id']} to {target_topic}")