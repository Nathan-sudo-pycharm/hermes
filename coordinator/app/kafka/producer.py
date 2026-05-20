from confluent_kafka import Producer
from app.core.config import settings
import json
import logging

logger = logging.getLogger(__name__)

# Global producer instance — created once, reused for all publishes.
# confluent_kafka Producer is thread-safe.
_producer: Producer = None


def get_producer() -> Producer:
    """
    Returns the global Kafka producer instance.
    Creates it on first call (lazy initialization).
    """
    global _producer
    if _producer is None:
        _producer = Producer({
            "bootstrap.servers": "kafka:29092",
            "client.id": "hermes-coordinator",
        })
    return _producer


def delivery_report(err, msg):
    """
    Callback fired by confluent_kafka when a message is delivered or fails.
    Logs the result — does not raise exceptions.
    """
    if err:
        logger.error(f"Message delivery failed: {err}")
    else:
        logger.info(f"Message delivered to {msg.topic()} partition {msg.partition()} offset {msg.offset()}")


async def publish_task(task_message: dict) -> None:
    """
    Publishes a task message to the hermes.tasks Kafka topic.
    The message key is the task_execution_id — this ensures
    all retries for the same task go to the same partition.
    """
    producer = get_producer()
    topic = settings.KAFKA_TASKS_TOPIC

    producer.produce(
        topic=topic,
        key=task_message["task_execution_id"],
        value=json.dumps(task_message).encode("utf-8"),
        callback=delivery_report
    )
    # poll(0) triggers delivery callbacks without blocking
    producer.poll(0)
    logger.info(f"Published task {task_message['task_execution_id']} to {topic}")
    