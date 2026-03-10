"""
Rate limiter for the LLM wrapper.

Implements three layers of protection:
  1. Token-bucket — limits sustained request rate (per-client and global).
  2. Concurrent-request semaphore — caps simultaneous in-flight LLM calls.
  3. Request-cost gating — rejects oversized payloads (too many tables / rows).

All limits are configurable via environment variables.
"""

import logging
import os
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)

# ── Configuration (env overridable) ───────────────────────────────────────────

# Token bucket: max tokens and refill rate
MAX_TOKENS = int(os.environ.get("LLM_RATE_MAX_TOKENS", "1000"))       # bucket size
REFILL_RATE = float(os.environ.get("LLM_RATE_REFILL_PER_SEC", "100")) # tokens/sec

# Concurrency: max simultaneous LLM calls
MAX_CONCURRENT = int(os.environ.get("LLM_MAX_CONCURRENT", "10"))

# Request size limits
MAX_TABLES_PER_REQUEST = int(os.environ.get("LLM_MAX_TABLES", "30"))
MAX_ROWS_PER_TABLE = int(os.environ.get("LLM_MAX_ROWS_PER_TABLE", "500"))


# ── Token Bucket ──────────────────────────────────────────────────────────────

class TokenBucket:
    """Thread-safe token-bucket rate limiter."""

    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate       # tokens per second
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self):
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(float(self.capacity), self._tokens + elapsed * self.refill_rate)
        self._last_refill = now

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume `tokens`.  Returns True on success, False if rate-limited."""
        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    def wait_time(self, tokens: int = 1) -> float:
        """Seconds until `tokens` will be available (0 if available now)."""
        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                return 0.0
            deficit = tokens - self._tokens
            return deficit / self.refill_rate


# ── Singletons ────────────────────────────────────────────────────────────────

# Global bucket — shared across all clients
_global_bucket = TokenBucket(capacity=MAX_TOKENS, refill_rate=REFILL_RATE)

# Per-client buckets (keyed by IP or schema_id)
_client_buckets: dict[str, TokenBucket] = {}
_client_lock = threading.Lock()

# Concurrency semaphore
_concurrency_sem = threading.Semaphore(MAX_CONCURRENT)


def _get_client_bucket(client_id: str) -> TokenBucket:
    with _client_lock:
        if client_id not in _client_buckets:
            # Per-client: smaller bucket (half the global), same refill rate
            _client_buckets[client_id] = TokenBucket(
                capacity=max(1, MAX_TOKENS // 2),
                refill_rate=REFILL_RATE / 2,
            )
        return _client_buckets[client_id]


# ── Public API ────────────────────────────────────────────────────────────────

class RateLimitExceeded(Exception):
    """Raised when a rate limit is hit."""
    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after


def check_rate_limit(client_id: str = "global", cost: int = 1) -> None:
    """
    Check both global and per-client rate limits.

    Args:
        client_id: Typically the schema_id or IP address.
        cost:      Number of tokens to consume (1 per LLM API call).

    Raises:
        RateLimitExceeded with a retry_after hint.
    """
    # 1. Global limit
    if not _global_bucket.consume(cost):
        wait = _global_bucket.wait_time(cost)
        logger.warning(f"Global rate limit hit (retry in {wait:.1f}s)")
        raise RateLimitExceeded(
            f"Server is busy — too many generation requests. Please retry in {wait:.0f}s.",
            retry_after=wait,
        )

    # 2. Per-client limit
    bucket = _get_client_bucket(client_id)
    if not bucket.consume(cost):
        wait = bucket.wait_time(cost)
        logger.warning(f"Per-client rate limit hit for '{client_id}' (retry in {wait:.1f}s)")
        raise RateLimitExceeded(
            f"You're sending requests too fast. Please retry in {wait:.0f}s.",
            retry_after=wait,
        )


def acquire_concurrency_slot(timeout: float = 30.0) -> bool:
    """
    Block until a concurrency slot is available (or timeout).

    Returns True if a slot was acquired, False on timeout.
    Caller MUST call release_concurrency_slot() when done.
    """
    acquired = _concurrency_sem.acquire(timeout=timeout)
    if not acquired:
        logger.warning("Concurrency limit reached — request timed out waiting for a slot")
    return acquired


def release_concurrency_slot() -> None:
    """Release a previously acquired concurrency slot."""
    _concurrency_sem.release()


def validate_request_size(
    num_tables: int,
    num_rows: dict[str, int] | None = None,
) -> None:
    """
    Reject obviously abusive payloads before they reach the LLM.

    Raises:
        RateLimitExceeded if limits are exceeded.
    """
    if num_tables > MAX_TABLES_PER_REQUEST:
        raise RateLimitExceeded(
            f"Too many tables ({num_tables}). Maximum is {MAX_TABLES_PER_REQUEST}."
        )

    if num_rows:
        for table, count in num_rows.items():
            if count > MAX_ROWS_PER_TABLE:
                raise RateLimitExceeded(
                    f"Too many rows requested for table '{table}' ({count}). "
                    f"Maximum is {MAX_ROWS_PER_TABLE} per table."
                )
