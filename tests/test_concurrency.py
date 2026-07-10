"""Tests para worldclass_scraper.modules.concurrency — AdaptiveConcurrencyController."""
import pytest
from worldclass_scraper.modules.concurrency import AdaptiveConcurrencyController


# ── helpers ───────────────────────────────────────────────────────────────────

def make_ctrl(**kwargs) -> AdaptiveConcurrencyController:
    defaults = dict(
        initial=4,
        min_concurrency=1,
        max_concurrency=8,
        error_threshold=3,
        reduction_step=1,
        stable_threshold=5,
        recovery_step=1,
        auto_reduce=True,
        auto_recovery=True,
    )
    defaults.update(kwargs)
    return AdaptiveConcurrencyController(**defaults)


TRANSIENT_MSG = 'TargetClosedError: browser closed'
NON_TRANSIENT_MSG = 'ValueError: bad input'


# ── init ──────────────────────────────────────────────────────────────────────

def test_init_clamps_initial_to_min():
    ctrl = AdaptiveConcurrencyController(initial=0, min_concurrency=2, max_concurrency=8)
    assert ctrl.concurrency == 2


def test_init_clamps_initial_to_max():
    ctrl = AdaptiveConcurrencyController(initial=20, min_concurrency=1, max_concurrency=8)
    assert ctrl.concurrency == 8


def test_init_error_threshold_minimum_is_1():
    ctrl = AdaptiveConcurrencyController(error_threshold=0)
    assert ctrl.error_threshold == 1


# ── on_error ─────────────────────────────────────────────────────────────────

def test_non_transient_error_does_not_accumulate_streak():
    ctrl = make_ctrl()
    ctrl.on_error(NON_TRANSIENT_MSG)
    assert ctrl.error_streak == 0


def test_non_transient_error_resets_stable_streak():
    ctrl = make_ctrl()
    # acumular estabilidad
    for _ in range(3):
        ctrl.on_success()
    assert ctrl.stable_streak == 3
    ctrl.on_error(NON_TRANSIENT_MSG)
    assert ctrl.stable_streak == 0


def test_transient_error_increments_streak():
    ctrl = make_ctrl()
    ctrl.on_error(TRANSIENT_MSG)
    assert ctrl.error_streak == 1


def test_transient_error_resets_stable_streak():
    ctrl = make_ctrl()
    for _ in range(3):
        ctrl.on_success()
    ctrl.on_error(TRANSIENT_MSG)
    assert ctrl.stable_streak == 0


def test_reduction_triggers_at_threshold():
    ctrl = make_ctrl(initial=4, error_threshold=3, reduction_step=1)
    for _ in range(3):
        ctrl.on_error(TRANSIENT_MSG)
    # al alcanzar el threshold se reduce y se resetea el streak
    assert ctrl.concurrency == 3
    assert ctrl.error_streak == 0


def test_reduction_returns_true_when_concurrency_lowered():
    ctrl = make_ctrl(initial=4, error_threshold=1, reduction_step=1)
    result = ctrl.on_error(TRANSIENT_MSG)
    assert result is True


def test_reduction_does_not_go_below_min():
    ctrl = make_ctrl(initial=1, min_concurrency=1, error_threshold=1, reduction_step=1)
    ctrl.on_error(TRANSIENT_MSG)
    assert ctrl.concurrency == 1


def test_reduction_disabled_when_auto_reduce_false():
    ctrl = make_ctrl(initial=4, error_threshold=1, auto_reduce=False)
    ctrl.on_error(TRANSIENT_MSG)
    assert ctrl.concurrency == 4


def test_all_transient_marker_variants():
    markers = [
        'Target page, context or browser has been closed',
        'TargetClosedError',
        'Page.goto: Timeout',
        'timeout_extract',
        'Locator.text_content: Target page',
    ]
    for marker in markers:
        ctrl = make_ctrl(error_threshold=1)
        ctrl.on_error(marker)
        assert ctrl.error_streak == 0  # se redujo y reseteó
        assert ctrl.concurrency == 3   # 4 - 1


# ── on_success ────────────────────────────────────────────────────────────────

def test_success_increments_stable_streak():
    ctrl = make_ctrl()
    ctrl.on_success()
    assert ctrl.stable_streak == 1


def test_recovery_triggers_at_stable_threshold():
    ctrl = make_ctrl(initial=2, max_concurrency=8, stable_threshold=5, recovery_step=1)
    for _ in range(5):
        ctrl.on_success()
    assert ctrl.concurrency == 3
    assert ctrl.stable_streak == 0  # se resetea tras recuperar


def test_recovery_returns_true_when_concurrency_raised():
    ctrl = make_ctrl(initial=2, max_concurrency=8, stable_threshold=1, recovery_step=1)
    result = ctrl.on_success()
    assert result is True


def test_recovery_does_not_exceed_max():
    ctrl = make_ctrl(initial=8, max_concurrency=8, stable_threshold=1, recovery_step=1)
    ctrl.on_success()
    assert ctrl.concurrency == 8


def test_recovery_disabled_when_auto_recovery_false():
    ctrl = make_ctrl(initial=2, stable_threshold=1, auto_recovery=False)
    ctrl.on_success()
    assert ctrl.concurrency == 2


# ── logger integration ────────────────────────────────────────────────────────

def test_logger_called_on_reduction(tmp_path):
    from worldclass_scraper.modules.logging import ScraperLogger
    logger = ScraperLogger(str(tmp_path / 'logs'))
    ctrl = make_ctrl(initial=4, error_threshold=1, logger=logger, site_name='test')
    ctrl.on_error(TRANSIENT_MSG)
    log_file = tmp_path / 'logs' / 'run_summary.log'
    assert log_file.exists()
    content = log_file.read_text()
    assert 'auto_reduce_concurrency' in content


def test_logger_called_on_recovery(tmp_path):
    from worldclass_scraper.modules.logging import ScraperLogger
    logger = ScraperLogger(str(tmp_path / 'logs'))
    ctrl = make_ctrl(initial=2, stable_threshold=1, recovery_step=1, logger=logger, site_name='test')
    ctrl.on_success()
    log_file = tmp_path / 'logs' / 'run_summary.log'
    assert log_file.exists()
    content = log_file.read_text()
    assert 'auto_recovery_concurrency' in content
