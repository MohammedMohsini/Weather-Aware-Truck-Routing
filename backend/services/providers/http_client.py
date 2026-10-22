from __future__ import annotations

import time
from typing import Any, Callable

import httpx


def request_with_retries(
    request: Callable[..., httpx.Response],
    *args: Any,
    attempts: int = 3,
    retry_delay_seconds: float = 0.2,
    **kwargs: Any,
) -> httpx.Response:
    """Retry idempotent provider requests after transient transport or server errors."""
    if attempts < 1:
        raise ValueError('At least one provider request attempt is required.')

    for attempt in range(attempts):
        try:
            response = request(*args, **kwargs)
        except httpx.TransportError:
            if attempt == attempts - 1:
                raise
        else:
            if response.status_code < 500 and response.status_code != 429:
                return response
            if attempt == attempts - 1:
                return response

        time.sleep(retry_delay_seconds * (2**attempt))

    raise RuntimeError('Provider retry loop exited unexpectedly.')
