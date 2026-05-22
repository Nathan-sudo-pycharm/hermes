import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from app.models import CircuitBreakerState

logger = logging.getLogger(__name__)

FAILURE_THRESHOLD = 3
OPEN_TIMEOUT_SECONDS = 30


async def _get_or_create(session, worker_id: str) -> CircuitBreakerState:
    result = await session.execute(
        select(CircuitBreakerState).where(CircuitBreakerState.worker_id == worker_id)
    )
    cb = result.scalar_one_or_none()
    if not cb:
        cb = CircuitBreakerState(worker_id=worker_id, state="CLOSED", failure_count=0)
        session.add(cb)
        await session.flush()
    return cb


async def record_failure(session, worker_id: str):
    cb = await _get_or_create(session, worker_id)
    now = datetime.now(timezone.utc)

    cb.failure_count += 1
    cb.last_failure_at = now
    cb.updated_at = now

    if cb.state == "HALF_OPEN":
        # Probe failed — reopen
        cb.state = "OPEN"
        cb.opened_at = now
        cb.next_retry_at = now + timedelta(seconds=OPEN_TIMEOUT_SECONDS)
        logger.warning(f"Circuit HALF_OPEN→OPEN for {worker_id} (probe failed)")

    elif cb.state == "CLOSED" and cb.failure_count >= FAILURE_THRESHOLD:
        cb.state = "OPEN"
        cb.opened_at = now
        cb.next_retry_at = now + timedelta(seconds=OPEN_TIMEOUT_SECONDS)
        logger.warning(f"Circuit CLOSED→OPEN for {worker_id} (failures={cb.failure_count})")


async def record_success(session, worker_id: str):
    cb = await _get_or_create(session, worker_id)
    now = datetime.now(timezone.utc)

    if cb.state == "HALF_OPEN":
        cb.state = "CLOSED"
        cb.failure_count = 0
        cb.opened_at = None
        cb.next_retry_at = None
        cb.updated_at = now
        logger.info(f"Circuit HALF_OPEN→CLOSED for {worker_id} (probe succeeded)")

    elif cb.state == "CLOSED":
        cb.failure_count = 0
        cb.updated_at = now


async def check_transition(session, worker_id: str):
    """
    Call this on Heartbeat.
    Transitions OPEN → HALF_OPEN if the timeout has expired.
    """
    cb = await _get_or_create(session, worker_id)
    now = datetime.now(timezone.utc)

    if cb.state == "OPEN" and cb.next_retry_at and cb.next_retry_at <= now:
        cb.state = "HALF_OPEN"
        cb.updated_at = now
        logger.info(f"Circuit OPEN→HALF_OPEN for {worker_id} (timeout expired)")