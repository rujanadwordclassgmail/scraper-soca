"""Tests para worldclass_scraper.modules.browser — AsyncBrowserManager.

Los tests usan mocks de Playwright porque no se puede lanzar un browser real
en entornos sin display. Se testea la lógica de orquestación y manejo de errores,
no la integración con Chromium.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from worldclass_scraper.modules.browser import AsyncBrowserManager


# ── helpers ───────────────────────────────────────────────────────────────────

def make_mock_page(navigation_timeout=60000, action_timeout=30000):
    page = MagicMock()
    page.set_default_navigation_timeout = MagicMock()
    page.set_default_timeout = MagicMock()
    page.close = AsyncMock()
    return page


def make_mock_context(page=None):
    ctx = AsyncMock()
    mock_page = page or make_mock_page()
    ctx.new_page = AsyncMock(return_value=mock_page)
    ctx.close = AsyncMock()
    return ctx, mock_page


def make_mock_browser(context=None):
    browser = AsyncMock()
    mock_ctx = context or make_mock_context()[0]
    browser.new_context = AsyncMock(return_value=mock_ctx)
    browser.close = AsyncMock()
    return browser


def make_mock_playwright(browser=None):
    pw = AsyncMock()
    mock_browser = browser or make_mock_browser()
    chromium = MagicMock()
    chromium.launch = AsyncMock(return_value=mock_browser)
    pw.chromium = chromium
    pw.stop = AsyncMock()
    return pw, mock_browser


# ── __init__ ──────────────────────────────────────────────────────────────────

class TestAsyncBrowserManagerInit:
    def test_default_values(self):
        bm = AsyncBrowserManager()
        assert bm.headless is True
        assert bm.navigation_timeout == 60000
        assert bm.action_timeout == 30000
        assert bm.playwright is None
        assert bm.browser is None
        assert bm.context is None

    def test_custom_values(self):
        bm = AsyncBrowserManager(headless=False, navigation_timeout=30000, action_timeout=10000)
        assert bm.headless is False
        assert bm.navigation_timeout == 30000
        assert bm.action_timeout == 10000


# ── start ─────────────────────────────────────────────────────────────────────

class TestAsyncBrowserManagerStart:
    def test_start_initializes_all_components(self):
        bm = AsyncBrowserManager()
        pw, mock_browser = make_mock_playwright()
        mock_ctx = make_mock_context()[0]
        mock_browser.new_context = AsyncMock(return_value=mock_ctx)

        with patch('worldclass_scraper.modules.browser.async_playwright') as mock_ap:
            mock_ap.return_value.start = AsyncMock(return_value=pw)
            asyncio.run(bm.start())

        assert bm.playwright is pw
        assert bm.browser is mock_browser
        assert bm.context is mock_ctx

    def test_start_launches_with_headless_setting(self):
        bm = AsyncBrowserManager(headless=False)
        pw, mock_browser = make_mock_playwright()
        mock_ctx = make_mock_context()[0]
        mock_browser.new_context = AsyncMock(return_value=mock_ctx)

        with patch('worldclass_scraper.modules.browser.async_playwright') as mock_ap:
            mock_ap.return_value.start = AsyncMock(return_value=pw)
            asyncio.run(bm.start())

        pw.chromium.launch.assert_called_once_with(headless=False)


# ── new_page ──────────────────────────────────────────────────────────────────

class TestAsyncBrowserManagerNewPage:
    def test_raises_if_context_is_none(self):
        bm = AsyncBrowserManager()
        bm.context = None
        with pytest.raises(RuntimeError, match='Browser context no iniciado'):
            asyncio.run(bm.new_page())

    def test_returns_page_with_timeouts_set(self):
        bm = AsyncBrowserManager(navigation_timeout=12000, action_timeout=6000)
        mock_page = make_mock_page()
        ctx, _ = make_mock_context(page=mock_page)
        bm.context = ctx

        page = asyncio.run(bm.new_page())

        assert page is mock_page
        mock_page.set_default_navigation_timeout.assert_called_once_with(12000)
        mock_page.set_default_timeout.assert_called_once_with(6000)

    def test_sets_context_to_none_on_closed_error(self):
        bm = AsyncBrowserManager()
        ctx = AsyncMock()
        ctx.new_page = AsyncMock(side_effect=Exception('Target closed'))
        bm.context = ctx

        with pytest.raises(Exception):
            asyncio.run(bm.new_page())

        assert bm.context is None

    def test_sets_context_to_none_on_target_error(self):
        bm = AsyncBrowserManager()
        ctx = AsyncMock()
        ctx.new_page = AsyncMock(side_effect=Exception('Target page error'))
        bm.context = ctx

        with pytest.raises(Exception):
            asyncio.run(bm.new_page())

        assert bm.context is None

    def test_does_not_clear_context_on_unrelated_error(self):
        bm = AsyncBrowserManager()
        ctx = AsyncMock()
        ctx.new_page = AsyncMock(side_effect=ValueError('unrelated'))
        bm.context = ctx

        with pytest.raises(ValueError):
            asyncio.run(bm.new_page())

        assert bm.context is ctx  # no se limpió


# ── is_context_alive ──────────────────────────────────────────────────────────

class TestIsContextAlive:
    def test_returns_false_when_context_is_none(self):
        bm = AsyncBrowserManager()
        bm.context = None
        result = asyncio.run(bm.is_context_alive())
        assert result is False

    def test_returns_true_when_page_can_be_created_and_closed(self):
        bm = AsyncBrowserManager()
        mock_page = make_mock_page()
        ctx, _ = make_mock_context(page=mock_page)
        bm.context = ctx

        result = asyncio.run(bm.is_context_alive())
        assert result is True
        mock_page.close.assert_called_once()

    def test_returns_false_and_clears_context_on_exception(self):
        bm = AsyncBrowserManager()
        ctx = AsyncMock()
        ctx.new_page = AsyncMock(side_effect=Exception('context dead'))
        bm.context = ctx

        result = asyncio.run(bm.is_context_alive())
        assert result is False
        assert bm.context is None


# ── close ─────────────────────────────────────────────────────────────────────

class TestAsyncBrowserManagerClose:
    def _make_full_manager(self):
        bm = AsyncBrowserManager()
        ctx = AsyncMock()
        ctx.close = AsyncMock()
        browser = AsyncMock()
        browser.close = AsyncMock()
        pw = AsyncMock()
        pw.stop = AsyncMock()
        bm.context = ctx
        bm.browser = browser
        bm.playwright = pw
        return bm, ctx, browser, pw

    def test_closes_all_components(self):
        bm, ctx, browser, pw = self._make_full_manager()
        asyncio.run(bm.close())
        ctx.close.assert_called_once()
        browser.close.assert_called_once()
        pw.stop.assert_called_once()

    def test_sets_all_to_none_after_close(self):
        bm, _, _, _ = self._make_full_manager()
        asyncio.run(bm.close())
        assert bm.context is None
        assert bm.browser is None
        assert bm.playwright is None

    def test_close_handles_context_exception_gracefully(self):
        bm = AsyncBrowserManager()
        ctx = AsyncMock()
        ctx.close = AsyncMock(side_effect=Exception('already closed'))
        browser = AsyncMock()
        browser.close = AsyncMock()
        pw = AsyncMock()
        pw.stop = AsyncMock()
        bm.context = ctx
        bm.browser = browser
        bm.playwright = pw

        # No debe lanzar excepción
        asyncio.run(bm.close())
        assert bm.context is None
        browser.close.assert_called_once()

    def test_close_with_none_components_does_not_raise(self):
        bm = AsyncBrowserManager()
        # Todos None — no debe lanzar
        asyncio.run(bm.close())
        assert bm.context is None
        assert bm.browser is None
        assert bm.playwright is None

    def test_close_handles_browser_exception_gracefully(self):
        bm = AsyncBrowserManager()
        browser = AsyncMock()
        browser.close = AsyncMock(side_effect=Exception('browser error'))
        pw = AsyncMock()
        pw.stop = AsyncMock()
        bm.browser = browser
        bm.playwright = pw

        asyncio.run(bm.close())
        assert bm.browser is None
        pw.stop.assert_called_once()
