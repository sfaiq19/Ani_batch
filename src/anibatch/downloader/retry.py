import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx

from anibatch.core.exceptions import DownloaderError

T = TypeVar("T")

RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}
NON_RETRYABLE_STATUS_CODES = {400, 401, 403, 404, 405, 410}


def is_retryable_exception(exc: Exception) -> bool:
    """Determine if an exception should trigger a retry."""
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        if code in RETRYABLE_STATUS_CODES:
            return True
        if code in NON_RETRYABLE_STATUS_CODES:
            return False
        return False
    return isinstance(
        exc, (httpx.TimeoutException, httpx.NetworkError, ConnectionError, TimeoutError)
    )


async def with_retry[T](
    operation: Callable[[], Awaitable[T]],
    max_attempts: int = 3,
    initial_delay: float = 0.5,
    backoff_factor: float = 2.0,
    on_retry: Callable[[int, Exception, float], None] | None = None,
) -> T:
    """Execute an async operation with exponential backoff for retryable errors."""
    attempt = 1
    delay = initial_delay

    while True:
        try:
            return await operation()
        except Exception as exc:
            if attempt >= max_attempts or not is_retryable_exception(exc):
                if isinstance(exc, DownloaderError):
                    raise
                raise DownloaderError(
                    f"Download operation failed after {attempt} attempts: {exc}"
                ) from exc

            if on_retry:
                on_retry(attempt, exc, delay)

            await asyncio.sleep(delay)
            delay *= backoff_factor
            attempt += 1
