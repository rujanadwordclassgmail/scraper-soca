"""Tests para worldclass_scraper.modules.retry — RetryPolicy y retry_async."""
import asyncio
import pytest

from worldclass_scraper.modules.retry import RetryPolicy, retry_async


# ── RetryPolicy.delay_for ─────────────────────────────────────────────────────

class TestRetryPolicyDelayFor:
    def test_first_attempt_equals_base_delay(self):
        policy = RetryPolicy(base_delay=2.0, max_delay=60.0, jitter=0.0, timing_factor=1.0)
        delay = policy.delay_for(1)
        assert delay == pytest.approx(2.0, abs=0.01)

    def test_second_attempt_doubles(self):
        policy = RetryPolicy(base_delay=2.0, max_delay=60.0, jitter=0.0, timing_factor=1.0)
        delay = policy.delay_for(2)
        assert delay == pytest.approx(4.0, abs=0.01)

    def test_third_attempt_quadruples(self):
        policy = RetryPolicy(base_delay=2.0, max_delay=60.0, jitter=0.0, timing_factor=1.0)
        delay = policy.delay_for(3)
        assert delay == pytest.approx(8.0, abs=0.01)

    def test_capped_at_max_delay(self):
        policy = RetryPolicy(base_delay=10.0, max_delay=15.0, jitter=0.0, timing_factor=1.0)
        # attempt=3 → raw=40.0 → capped at 15.0
        delay = policy.delay_for(3)
        assert delay == pytest.approx(15.0, abs=0.01)

    def test_timing_factor_scales_delay(self):
        policy = RetryPolicy(base_delay=2.0, max_delay=60.0, jitter=0.0, timing_factor=0.5)
        delay = policy.delay_for(1)
        assert delay == pytest.approx(1.0, abs=0.01)

    def test_timing_factor_zero_gives_zero(self):
        policy = RetryPolicy(base_delay=5.0, max_delay=60.0, jitter=0.0, timing_factor=0.0)
        assert policy.delay_for(1) == 0.0

    def test_jitter_adds_positive_amount(self):
        policy = RetryPolicy(base_delay=10.0, max_delay=60.0, jitter=0.5, timing_factor=1.0)
        # Con jitter, el delay debe ser >= base_delay (jitter es positivo)
        delays = [policy.delay_for(1) for _ in range(20)]
        assert all(d >= 10.0 for d in delays)

    def test_delay_never_negative(self):
        policy = RetryPolicy(base_delay=0.0, max_delay=0.0, jitter=0.0, timing_factor=0.0)
        assert policy.delay_for(1) >= 0.0


# ── RetryPolicy.sleep ─────────────────────────────────────────────────────────

class TestRetryPolicySleep:
    def test_sleep_zero_delay_does_not_sleep(self):
        policy = RetryPolicy(base_delay=0.0, max_delay=0.0, jitter=0.0, timing_factor=0.0)
        import time
        start = time.monotonic()
        asyncio.run(policy.sleep(1))
        elapsed = time.monotonic() - start
        assert elapsed < 0.1  # prácticamente instantáneo

    def test_sleep_returns_delay_value(self):
        policy = RetryPolicy(base_delay=0.0, max_delay=0.0, jitter=0.0, timing_factor=0.0)
        result = asyncio.run(policy.sleep(1))
        assert result == 0.0


# ── retry_async — comportamiento básico ───────────────────────────────────────

class TestRetryAsyncSuccess:
    def test_returns_value_on_first_success(self):
        async def always_ok():
            return 42

        result = asyncio.run(retry_async(always_ok, RetryPolicy(retries=3)))
        assert result == 42

    def test_returns_value_after_transient_failure(self):
        calls = {'n': 0}

        async def fails_once():
            calls['n'] += 1
            if calls['n'] < 2:
                raise ValueError('transient')
            return 'ok'

        policy = RetryPolicy(retries=3, base_delay=0.0, jitter=0.0)
        result = asyncio.run(retry_async(fails_once, policy))
        assert result == 'ok'
        assert calls['n'] == 2

    def test_calls_on_retry_callback(self):
        calls = {'retries': 0}

        async def always_fails():
            raise RuntimeError('fail')

        async def on_retry(exc, attempt):
            calls['retries'] += 1

        policy = RetryPolicy(retries=3, base_delay=0.0, jitter=0.0)
        with pytest.raises(RuntimeError):
            asyncio.run(retry_async(always_fails, policy, on_retry=on_retry))

        assert calls['retries'] == 2  # intento 1 y 2 llaman on_retry, 3 lanza

    def test_raises_after_exhausting_retries(self):
        async def always_fails():
            raise ValueError('always bad')

        policy = RetryPolicy(retries=3, base_delay=0.0, jitter=0.0)
        with pytest.raises(ValueError, match='always bad'):
            asyncio.run(retry_async(always_fails, policy))

    def test_total_calls_equals_retries(self):
        calls = {'n': 0}

        async def always_fails():
            calls['n'] += 1
            raise RuntimeError('fail')

        policy = RetryPolicy(retries=4, base_delay=0.0, jitter=0.0)
        with pytest.raises(RuntimeError):
            asyncio.run(retry_async(always_fails, policy))

        assert calls['n'] == 4


# ── retry_async — retry_if predicate ─────────────────────────────────────────

class TestRetryAsyncPredicate:
    def test_no_retry_when_predicate_returns_false(self):
        calls = {'n': 0}

        async def always_fails():
            calls['n'] += 1
            raise ValueError('stop immediately')

        policy = RetryPolicy(retries=5, base_delay=0.0, jitter=0.0)
        with pytest.raises(ValueError):
            asyncio.run(retry_async(
                always_fails,
                policy,
                retry_if=lambda exc, attempt: False,
            ))

        assert calls['n'] == 1  # no se reintentó

    def test_retry_only_for_specific_exception_type(self):
        calls = {'n': 0}

        async def fails_with_value_error():
            calls['n'] += 1
            if calls['n'] < 3:
                raise ValueError('retriable')
            raise TypeError('not retriable')

        policy = RetryPolicy(retries=5, base_delay=0.0, jitter=0.0)
        with pytest.raises(TypeError):
            asyncio.run(retry_async(
                fails_with_value_error,
                policy,
                retry_if=lambda exc, attempt: isinstance(exc, ValueError),
            ))

        assert calls['n'] == 3  # 2 ValueError reintentados, 1 TypeError no

    def test_predicate_receives_correct_attempt_number(self):
        attempts_seen = []

        async def always_fails():
            raise RuntimeError('fail')

        async def on_retry(exc, attempt):
            attempts_seen.append(attempt)

        policy = RetryPolicy(retries=4, base_delay=0.0, jitter=0.0)
        with pytest.raises(RuntimeError):
            asyncio.run(retry_async(
                always_fails,
                policy,
                on_retry=on_retry,
            ))

        assert attempts_seen == [1, 2, 3]  # on_retry se llama en intentos 1,2,3 (no en el 4 que lanza)

    def test_default_predicate_always_retries(self):
        calls = {'n': 0}

        async def always_fails():
            calls['n'] += 1
            raise RuntimeError('fail')

        policy = RetryPolicy(retries=3, base_delay=0.0, jitter=0.0)
        with pytest.raises(RuntimeError):
            asyncio.run(retry_async(always_fails, policy))

        assert calls['n'] == 3  # sin predicate → siempre reintenta hasta agotar


# ── retry_async — timing_factor ───────────────────────────────────────────────

class TestRetryAsyncTiming:
    def test_timing_factor_zero_runs_fast(self):
        """Con timing_factor=0 y base_delay>0 el sleep es 0 → ejecución rápida."""
        import time

        async def always_fails():
            raise RuntimeError('fail')

        policy = RetryPolicy(retries=3, base_delay=5.0, jitter=0.0, timing_factor=0.0)
        start = time.monotonic()
        with pytest.raises(RuntimeError):
            asyncio.run(retry_async(always_fails, policy))
        elapsed = time.monotonic() - start
        assert elapsed < 0.5  # no durmió los 5 segundos
