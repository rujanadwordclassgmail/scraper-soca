"""Control adaptativo de concurrencia.

Responsabilidad única: decidir cuántos workers corren en función de rachas
de errores y éxitos. No conoce nada de Playwright ni de contratos.
"""
from __future__ import annotations

from worldclass_scraper.modules.logging import ScraperLogger


class AdaptiveConcurrencyController:
    """Sube y baja la concurrencia de forma autónoma según señales externas.

    Uso:
        ctrl = AdaptiveConcurrencyController(initial=3, ...)
        # al detectar un error:
        ctrl.on_error("TargetClosedError ...")
        current_workers = ctrl.concurrency
        # al detectar un éxito:
        ctrl.on_success()
    """

    def __init__(
        self,
        initial: int = 2,
        min_concurrency: int = 1,
        max_concurrency: int = 8,
        error_threshold: int = 10,
        reduction_step: int = 1,
        stable_threshold: int = 20,
        recovery_step: int = 1,
        auto_reduce: bool = True,
        auto_recovery: bool = True,
        logger: ScraperLogger | None = None,
        site_name: str = '',
    ) -> None:
        self.concurrency = max(min_concurrency, min(max_concurrency, initial))
        self.min_concurrency = min_concurrency
        self.max_concurrency = max_concurrency
        self.error_threshold = max(1, error_threshold)
        self.reduction_step = reduction_step
        self.stable_threshold = stable_threshold
        self.recovery_step = recovery_step
        self.auto_reduce = auto_reduce
        self.auto_recovery = auto_recovery
        self._logger = logger
        self.site_name = site_name

        self._error_streak = 0
        self._stable_streak = 0

    # ── señales externas ────────────────────────────────────────────────────

    def on_error(self, message: str) -> bool:
        """Registra un error; retorna True si se redujo la concurrencia."""
        transient_markers = (
            'Target page, context or browser has been closed',
            'TargetClosedError',
            'Page.goto: Timeout',
            'timeout_extract',
            'Locator.text_content: Target page',
        )
        is_transient = any(m in message for m in transient_markers)

        if is_transient:
            self._error_streak += 1
            self._stable_streak = 0
        else:
            self._error_streak = 0
            self._stable_streak = 0

        if not self.auto_reduce:
            return False

        if self._error_streak >= self.error_threshold:
            old = self.concurrency
            self.concurrency = max(self.min_concurrency, self.concurrency - self.reduction_step)
            self._error_streak = 0
            if self.concurrency < old and self._logger:
                self._logger.summary(
                    f"auto_reduce_concurrency from={old} to={self.concurrency} | sitio={self.site_name}"
                )
            return self.concurrency < old
        return False

    def on_success(self) -> bool:
        """Registra un éxito; retorna True si se recuperó la concurrencia."""
        if not self.auto_recovery:
            return False

        self._stable_streak += 1
        if self._stable_streak >= self.stable_threshold:
            old = self.concurrency
            self.concurrency = min(self.max_concurrency, self.concurrency + self.recovery_step)
            self._stable_streak = 0
            if self.concurrency > old and self._logger:
                self._logger.summary(
                    f"auto_recovery_concurrency from={old} to={self.concurrency}"
                    f" | stable_streak_reached={self.stable_threshold} | sitio={self.site_name}"
                )
            return self.concurrency > old
        return False

    @property
    def error_streak(self) -> int:
        return self._error_streak

    @property
    def stable_streak(self) -> int:
        return self._stable_streak
