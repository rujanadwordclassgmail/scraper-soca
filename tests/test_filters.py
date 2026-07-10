"""Tests para worldclass_scraper.modules.filters — FilterManager.

Los métodos que dependen de Playwright se testean con mocks de página.
Los métodos estáticos/puros se testean directamente.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from worldclass_scraper.modules.filters import FilterManager


# ── helpers ───────────────────────────────────────────────────────────────────

SELECTORS = {
    'sede':            'select#bus_sede',
    'fecha_inicial':   'input#bus_f1',
    'fecha_final':     'input#bus_f2',
    'estado':          'select#bus_estado',
    'buscar':          'button[onclick*="buscarXcs"]',
    'contrato_link':   'a[href*="/vercontrato/"]',
}


def make_manager() -> FilterManager:
    return FilterManager(selectors=SELECTORS, base_url='https://example.com')


def make_locator(count: int = 0, href: str | None = None):
    """Locator síncrono (locator() en Playwright es sync). Sus métodos son async."""
    loc = MagicMock()
    loc.count = AsyncMock(return_value=count)
    loc.all = AsyncMock(return_value=[])
    loc.first = MagicMock()
    loc.first.input_value = AsyncMock(return_value='')
    loc.first.get_attribute = AsyncMock(return_value=href)
    if href is not None:
        loc.get_attribute = AsyncMock(return_value=href)
    return loc


def make_page(url: str = 'https://example.com/contratos') -> MagicMock:
    """
    page.locator() es SÍNCRONO en Playwright — devuelve un Locator, no una coroutine.
    Usamos MagicMock para page para que locator() devuelva un MagicMock directamente.
    """
    page = MagicMock()
    page.url = url
    page.evaluate = AsyncMock(return_value=None)
    page.wait_for_timeout = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    page.wait_for_selector = AsyncMock()
    page.goto = AsyncMock()
    page.screenshot = AsyncMock()
    page.select_option = AsyncMock(return_value=['option_value'])

    # locator() síncrono con métodos async internos
    default_loc = MagicMock()
    default_loc.count = AsyncMock(return_value=0)
    default_loc.first = MagicMock()
    default_loc.first.input_value = AsyncMock(return_value='')
    default_loc.all = AsyncMock(return_value=[])
    default_loc.get_attribute = AsyncMock(return_value=None)
    page.locator.return_value = default_loc

    return page


# ── _format_date (static, no mock needed) ────────────────────────────────────

class TestFormatDate:
    def test_valid_iso_date_converted_to_us_format(self):
        assert FilterManager._format_date('2024-03-15') == '03/15/2024'

    def test_invalid_format_returned_as_is(self):
        assert FilterManager._format_date('15/03/2024') == '15/03/2024'

    def test_empty_string_returned_as_is(self):
        assert FilterManager._format_date('') == ''

    def test_partial_date_returned_as_is(self):
        assert FilterManager._format_date('2024-03') == '2024-03'

    def test_boundary_dates(self):
        assert FilterManager._format_date('2023-01-01') == '01/01/2023'
        assert FilterManager._format_date('2026-12-31') == '12/31/2026'


# ── _determine_total_pages ────────────────────────────────────────────────────

class TestDetermineTotalPages:
    def test_returns_none_when_no_pagination(self):
        page = make_page()
        page.evaluate = AsyncMock(return_value=None)
        result = asyncio.run(FilterManager._determine_total_pages(page))
        assert result is None

    def test_returns_page_count_when_present(self):
        page = make_page()
        page.evaluate = AsyncMock(return_value=5)
        result = asyncio.run(FilterManager._determine_total_pages(page))
        assert result == 5

    def test_returns_none_for_zero(self):
        page = make_page()
        page.evaluate = AsyncMock(return_value=0)
        result = asyncio.run(FilterManager._determine_total_pages(page))
        assert result is None

    def test_returns_none_for_string_result(self):
        page = make_page()
        page.evaluate = AsyncMock(return_value='not_a_number')
        result = asyncio.run(FilterManager._determine_total_pages(page))
        assert result is None


# ── collect_contract_urls — sin paginación ────────────────────────────────────

class TestCollectContractUrlsSinglePage:
    def _build_page(self, hrefs: list[str]) -> MagicMock:
        page = make_page()
        page.evaluate = AsyncMock(return_value=None)  # no pagination

        # enlaces de contratos: cada enlace es un MagicMock con get_attribute async
        link_locators = []
        for href in hrefs:
            loc = MagicMock()
            loc.get_attribute = AsyncMock(return_value=href)
            link_locators.append(loc)

        contract_locator = MagicMock()
        contract_locator.all = AsyncMock(return_value=link_locators)

        # botón "siguiente" ausente
        siguiente_locator = MagicMock()
        siguiente_locator.count = AsyncMock(return_value=0)

        def locator_factory(sel):
            if 'vercontrato' in sel:
                return contract_locator
            if 'pagination' in sel:
                return siguiente_locator
            loc = MagicMock()
            loc.count = AsyncMock(return_value=0)
            loc.all = AsyncMock(return_value=[])
            return loc

        page.locator.side_effect = locator_factory
        return page

    def test_returns_absolute_urls(self):
        page = self._build_page(['/vercontrato/1', '/vercontrato/2'])
        manager = make_manager()
        urls = asyncio.run(manager.collect_contract_urls(page, 'CASH'))
        assert urls == [
            'https://example.com/vercontrato/1',
            'https://example.com/vercontrato/2',
        ]

    def test_preserves_already_absolute_urls(self):
        page = self._build_page(['https://other.com/vercontrato/99'])
        manager = make_manager()
        urls = asyncio.run(manager.collect_contract_urls(page, 'CASH'))
        assert urls == ['https://other.com/vercontrato/99']

    def test_skips_none_hrefs(self):
        page = make_page()
        page.evaluate = AsyncMock(return_value=None)

        loc_none = MagicMock()
        loc_none.get_attribute = AsyncMock(return_value=None)
        loc_valid = MagicMock()
        loc_valid.get_attribute = AsyncMock(return_value='/vercontrato/5')

        contract_locator = MagicMock()
        contract_locator.all = AsyncMock(return_value=[loc_none, loc_valid])

        siguiente_locator = MagicMock()
        siguiente_locator.count = AsyncMock(return_value=0)

        def locator_factory(sel):
            if 'vercontrato' in sel:
                return contract_locator
            loc = MagicMock()
            loc.count = AsyncMock(return_value=0)
            loc.all = AsyncMock(return_value=[])
            return loc

        page.locator.side_effect = locator_factory
        manager = make_manager()
        urls = asyncio.run(manager.collect_contract_urls(page, 'CASH'))
        assert urls == ['https://example.com/vercontrato/5']

    def test_deduplicates_urls(self):
        page = self._build_page(['/vercontrato/1', '/vercontrato/1'])
        manager = make_manager()
        urls = asyncio.run(manager.collect_contract_urls(page, 'CASH'))
        assert len(urls) == 1

    def test_empty_page_returns_empty_list(self):
        page = self._build_page([])
        manager = make_manager()
        urls = asyncio.run(manager.collect_contract_urls(page, 'CASH'))
        assert urls == []


# ── collect_contract_urls — con paginación ────────────────────────────────────

class TestCollectContractUrlsMultiPage:
    def test_follows_next_page_and_collects_all_urls(self):
        """Simula 2 páginas: primera tiene 1 contrato, segunda tiene 1 contrato.

        Estrategia: los locators de 'siguiente' son stateful — el primero
        devuelve count=1 la primera vez que se llama a count() y count=0 en
        adelante. Así el loop termina tras la segunda página.
        """
        page = make_page()

        # evaluate: primera llamada → total_pages=2, el resto → None
        eval_calls = {'n': 0}

        async def evaluate_side(expr, *args):
            eval_calls['n'] += 1
            return 2 if eval_calls['n'] == 1 else None

        page.evaluate.side_effect = evaluate_side

        # enlaces de cada página
        link1 = MagicMock()
        link1.get_attribute = AsyncMock(return_value='/vercontrato/1')
        link2 = MagicMock()
        link2.get_attribute = AsyncMock(return_value='/vercontrato/2')

        # locator de contratos: primera llamada devuelve [link1], segunda [link2]
        contract_calls = {'n': 0}
        contract_locator = MagicMock()

        async def contract_all():
            contract_calls['n'] += 1
            return [link1] if contract_calls['n'] == 1 else [link2]

        contract_locator.all = contract_all

        # locator de paginación: primera llamada a count() devuelve 1, luego 0
        siguiente_calls = {'n': 0}
        siguiente_locator = MagicMock()
        siguiente_locator.first = MagicMock()
        siguiente_locator.first.get_attribute = AsyncMock(
            return_value='https://example.com/contratos?page=2'
        )

        async def siguiente_count():
            siguiente_calls['n'] += 1
            return 1 if siguiente_calls['n'] == 1 else 0

        siguiente_locator.count = siguiente_count

        def locator_factory(sel):
            if 'vercontrato' in sel:
                return contract_locator
            if 'pagination' in sel:
                return siguiente_locator
            loc = MagicMock()
            loc.count = AsyncMock(return_value=0)
            loc.all = AsyncMock(return_value=[])
            return loc

        page.locator.side_effect = locator_factory

        manager = make_manager()
        urls = asyncio.run(manager.collect_contract_urls(page, 'CASH'))

        # debe haber navegado exactamente a la página 2
        page.goto.assert_called_once_with(
            'https://example.com/contratos?page=2', wait_until='domcontentloaded'
        )
        assert urls == [
            'https://example.com/vercontrato/1',
            'https://example.com/vercontrato/2',
        ]
