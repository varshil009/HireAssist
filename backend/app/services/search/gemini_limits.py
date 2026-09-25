from __future__ import annotations

import logging
import re
import threading
import time

from ...config import settings

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_last_request_monotonic = 0.0

_RETRYABLE = re.compile(
    r"429|resource.?exhausted|rate.?limit|quota|too many requests|503|unavailable",
    re.IGNORECASE,
)


def _min_interval_seconds() -> float:
    rpm = max(1, settings.gemini_rpm)
    return 60.0 / rpm


def _wait_for_rpm_slot() -> None:
    global _last_request_monotonic
    interval = _min_interval_seconds()
    with _lock:
        now = time.monotonic()
        delay = _last_request_monotonic + interval - now
        if delay > 0:
            logger.debug("Gemini RPM throttle sleeping %.2fs", delay)
            time.sleep(delay)
        _last_request_monotonic = time.monotonic()


def _is_retryable(exc: BaseException) -> bool:
    msg = str(exc)
    return bool(_RETRYABLE.search(msg))


def generate_content_with_limits(client, *, model: str, contents: str, config):
    """Call Gemini with RPM spacing and exponential backoff (max retries from settings)."""
    last_exc: BaseException | None = None
    base = _min_interval_seconds()
    attempts = max(1, settings.gemini_max_retries)

    for attempt in range(attempts):
        _wait_for_rpm_slot()
        try:
            return client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
        except Exception as exc:
            last_exc = exc
            if attempt >= attempts - 1 or not _is_retryable(exc):
                raise
            backoff = base * (2**attempt)
            logger.warning(
                "Gemini call failed (attempt %s/%s), retry in %.1fs: %s",
                attempt + 1,
                attempts,
                backoff,
                exc,
            )
            time.sleep(backoff)

    assert last_exc is not None
    raise last_exc
