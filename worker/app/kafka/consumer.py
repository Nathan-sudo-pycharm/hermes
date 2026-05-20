from confluent_kafka import Consumer, KafkaError
from app.core.config import settings
import json
import logging
import asyncio

logger = logging.getLogger(__name__)


def create_consumer() -> Consumer:
    return Consumer({
        "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
        "group.id": "hermes-workers",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": True,
        "auto.commit.interval.ms": 5000,
        "client.id": settings.WORKER_ID,
    })


async def start_consumer():
    """
    Main consumer loop — runs forever, polling Kafka for new tasks.
    Retries on connection errors instead of crashing.
    """
    logger.info(f"Worker {settings.WORKER_ID} starting consumer...")

    while True:
        consumer = create_consumer()
        try:
            consumer.subscribe([settings.KAFKA_TASKS_TOPIC])
            logger.info(f"Worker {settings.WORKER_ID} subscribed to {settings.KAFKA_TASKS_TOPIC}")

            while True:
                loop = asyncio.get_event_loop()
                msg = await loop.run_in_executor(None, lambda: consumer.poll(timeout=1.0))

                if msg is None:
                    continue

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        logger.error(f"Kafka error: {msg.error()} — retrying in 5s")
                        break  # break inner loop to recreate consumer

                try:
                    task = json.loads(msg.value().decode("utf-8"))
                    logger.info(f"Worker {settings.WORKER_ID} received task: {task['task_execution_id']} step: {task['step_name']}")

                    from app.executor.task_runner import run_task
                    await run_task(task)

                except Exception as e:
                    logger.error(f"Error processing message: {e}")

        except Exception as e:
            logger.error(f"Consumer error: {e} — retrying in 5s")
        finally:
            consumer.close()

        # Wait before retrying
        await asyncio.sleep(5)