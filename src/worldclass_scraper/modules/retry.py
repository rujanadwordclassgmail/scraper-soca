import asyncio
import random
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional, TypeVar

T = TypeVar('T')

RetryPredicate = Callable[[Exception, int], bool]
RetryCallback = Callable[[Exception, int], Awaitable[None]]
AsyncFunc = Callable[[], Awaitable[T]]

@dataclass
class RetryPolicy:
    retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    jitter: float = 0.1
    timing_factor: float = 1.0

    def delay_for(self, attempt: int) -> float:
        raw = self.base_delay * (2 ** (attempt - 1))
        delay = min(self.max_delay, raw)
        jitter_amount = random.random() * self.jitter * delay
        return max(0.0, (delay + jitter_amount) * self.timing_factor)

    async def sleep(self, attempt: int) -> float:
        delay = self.delay_for(attempt)
        if delay > 0:
            await asyncio.sleep(delay)
        return delay


async def retry_async(
    coro_func: AsyncFunc,
    retry_policy: RetryPolicy,
    retry_if: Optional[RetryPredicate] = None,
    on_retry: Optional[RetryCallback] = None,
) -> T:
    retry_if = retry_if or (lambda exc, attempt: True)
    last_exception: Optional[Exception] = None

    for attempt in range(1, retry_policy.retries + 1):
        try:
            return await coro_func()
        except Exception as exc:
            last_exception = exc
            if attempt >= retry_policy.retries or not retry_if(exc, attempt):
                raise

            if on_retry is not None:
                await on_retry(exc, attempt)

            await retry_policy.sleep(attempt)

    assert last_exception is not None
    raise last_exception
