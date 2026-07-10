"""Renderizado de barras de progreso en consola."""
from worldclass_scraper.modules.utils import RESET, BOLD, CYAN, GREEN

PROGRESS_BAR_WIDTH = 30


class ProgressRenderer:
    """Responsabilidad única: renderizar barras de progreso ASCII en stdout."""

    def __init__(self, width: int = PROGRESS_BAR_WIDTH) -> None:
        self.width = width

    def render(self, current: int, total: int) -> str:
        """Devuelve la barra como string coloreado. No imprime por sí misma."""
        if total <= 0:
            return ''
        percentage = min(100, max(0, int((current / total) * 100)))
        filled = int((percentage * self.width) / 100)
        empty = self.width - filled
        return f"[{GREEN}{'█' * filled}{RESET}{' ' * empty}] {percentage:3d}%"

    def print_final(self, current: int, total: int) -> None:
        """Imprime la barra final una sola vez al terminar todos los contratos."""
        bar = self.render(current, total)
        label = f"Procesados: {current}/{total}"
        print(f"  {CYAN}→ {RESET}{bar} {BOLD}{label}{RESET}")
