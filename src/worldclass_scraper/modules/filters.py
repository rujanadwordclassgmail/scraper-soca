"""Aplicación de filtros de búsqueda y recolección de URLs de contratos.

Responsabilidades:
  - Seleccionar sede, fechas y estado en el formulario web.
  - Paginar la lista de resultados y recolectar hrefs de contratos.

No conoce nada de extracción de campos individuales ni de exportación.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from playwright.async_api import Page

from worldclass_scraper.modules.progress import ProgressRenderer
from worldclass_scraper.modules.utils import RESET, BOLD, CYAN, GREEN, YELLOW


class FilterManager:
    """Encapsula la lógica de filtros de búsqueda y paginación."""

    def __init__(self, selectors: Dict[str, str], base_url: str = '') -> None:
        self.selectors = selectors
        self.base_url = base_url
        self._progress = ProgressRenderer()

    # ── público ─────────────────────────────────────────────────────────────

    async def apply_filters(self, page: Page, filtros: Dict[str, Any], estado: str) -> None:
        """Aplica sede, fechas y estado en el formulario y lanza la búsqueda."""
        print(f'{BOLD}{CYAN}PASO FILTROS{RESET}')

        if filtros.get('sede'):
            selected = await self._select_option(page, self.selectors['sede'], filtros['sede'])
            if selected:
                print(f"  {GREEN}✔ Sede seleccionada{RESET}: {filtros['sede']}")
            else:
                print(f"  {YELLOW}⚠ Sede no seleccionada{RESET}: {filtros['sede']} — se usa la configuración actual")
        else:
            print(f'  {YELLOW}⚠ Sede omitida{RESET}: no se proporcionó valor')

        await page.wait_for_timeout(300)

        for selector_key, valor, label in [
            ('fecha_inicial', filtros.get('fecha_inicial', ''), 'Fecha inicial'),
            ('fecha_final',   filtros.get('fecha_final', ''),   'Fecha final'),
        ]:
            formatted = self._format_date(valor)
            sel = self.selectors[selector_key]
            await page.evaluate(
                f"""() => {{
                    const el = document.querySelector('{sel}');
                    if (el) {{
                        el.value = '{formatted}';
                        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                }}"""
            )
            print(f'  {GREEN}✔ {label}{RESET}: {formatted}')

        await page.wait_for_timeout(300)

        selected = await self._select_option(page, self.selectors['estado'], estado)
        if selected:
            print(f'  {GREEN}✔ Estado seleccionado{RESET}: {estado}')
        else:
            print(f'  {YELLOW}⚠ Estado no seleccionado{RESET}: {estado} — revisa el valor o el selector')

        await page.wait_for_timeout(300)

        f1 = await page.locator(self.selectors['fecha_inicial']).first.input_value()
        f2 = await page.locator(self.selectors['fecha_final']).first.input_value()
        print(f"  • Fecha inicial: '{f1}' | Fecha final: '{f2}'")

        await self._click_buscar(page)
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(1000)
        try:
            await page.wait_for_selector('a[href*="/vercontrato/"]', timeout=10000)
        except Exception:
            print('  [WARN] No se detectaron enlaces de contrato tras Buscar')
        await page.wait_for_timeout(1000)

    async def collect_contract_urls(
        self,
        page: Page,
        estado: str,
        output_dir: str = '',
        debug: bool = False,
    ) -> List[str]:
        """Recorre todas las páginas de resultados y devuelve las URLs de contratos."""
        urls: List[str] = []
        pagina = 1
        total_pages = await self._determine_total_pages(page)

        while True:
            label = f'Página {pagina}/{total_pages}' if total_pages else f'Página {pagina}'
            bar = self._progress.render(pagina, total_pages or pagina)
            print(f'  → {label}: recolectando enlaces... {bar}')

            enlaces = await page.locator(self.selectors['contrato_link']).all()
            print(f'    → {len(enlaces)} contratos encontrados | total acumulado: {len(urls) + len(enlaces)}')

            for enlace in enlaces:
                try:
                    href = await enlace.get_attribute('href')
                    if not href:
                        continue
                    url = href if href.startswith('http') else f'{self.base_url}{href}'
                    if url not in urls:
                        urls.append(url)
                except Exception:
                    continue

            if pagina == 1 and debug and output_dir:
                debug_dir = os.path.join(output_dir, 'debug')
                os.makedirs(debug_dir, exist_ok=True)
                await page.screenshot(path=os.path.join(debug_dir, f'debug_paginacion_{estado}.png'))

            siguiente = page.locator('ul.pagination li:not(.disabled) a[rel="next"]')
            if await siguiente.count() == 0:
                print(f'  ✓ Fin de paginación ({pagina} página(s), {len(urls)} contratos)')
                break

            next_href = await siguiente.first.get_attribute('href')
            if not next_href:
                print(f'  {YELLOW}[WARN]{RESET} No se encontró href en el botón siguiente de paginación')
                break

            print(f'    → Navegando a página {pagina + 1}...')
            await page.goto(next_href, wait_until='domcontentloaded')
            try:
                await page.wait_for_load_state('networkidle', timeout=15000)
            except Exception:
                pass
            await page.wait_for_timeout(1500)
            pagina += 1

        return urls

    # ── privados ─────────────────────────────────────────────────────────────

    @staticmethod
    def _format_date(value: str) -> str:
        try:
            return datetime.strptime(value, '%Y-%m-%d').strftime('%m/%d/%Y')
        except ValueError:
            return value

    @staticmethod
    async def _determine_total_pages(page: Page) -> Optional[int]:
        total = await page.evaluate(
            "() => {"
            "  const items = Array.from(document.querySelectorAll('ul.pagination li a'));"
            "  const pages = items.map(a => parseInt(a.textContent.trim())).filter(n => !isNaN(n));"
            "  return pages.length ? Math.max(...pages) : null;"
            "}"
        )
        return int(total) if isinstance(total, int) and total > 0 else None

    async def _select_option(self, page: Page, selector: str, value: str) -> bool:
        if await page.locator(selector).count() == 0:
            return False

        if await page.select_option(selector, label=value):
            await self._dispatch_change(page, selector)
            return True

        if await page.select_option(selector, value=value):
            await self._dispatch_change(page, selector)
            return True

        # Fallback: búsqueda case-insensitive vía JS
        result = await page.evaluate(
            """(selector, value) => {
                const select = document.querySelector(selector);
                if (!select) return null;
                const lc = value.trim().toLowerCase();
                for (const opt of select.options) {
                    if (opt.text.trim().toLowerCase() === lc || opt.value.trim().toLowerCase() === lc) {
                        select.value = opt.value;
                        select.dispatchEvent(new Event('input', { bubbles: true }));
                        select.dispatchEvent(new Event('change', { bubbles: true }));
                        return opt.value;
                    }
                }
                return null;
            }""",
            selector,
            value,
        )
        return bool(result)

    @staticmethod
    async def _dispatch_change(page: Page, selector: str) -> None:
        await page.evaluate(
            """selector => {
                const el = document.querySelector(selector);
                if (el) {
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }""",
            selector,
        )

    async def _click_buscar(self, page: Page) -> None:
        for locator_expr in [
            self.selectors.get('buscar', ''),
            'button:has-text("Buscar")',
            'button[type="button"]:has-text("Buscar")',
            'button[type="submit"]',
        ]:
            if not locator_expr:
                continue
            btn = page.locator(locator_expr)
            if await btn.count() > 0:
                await btn.first.click()
                print('  → Botón Buscar clickeado')
                return
        print('  [WARN] No se encontró botón Buscar')
