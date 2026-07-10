"""Tests para worldclass_scraper.modules.auth — AsyncAuthManager.

Los métodos que interactúan con Playwright (login, load_session con browser real)
se testean con mocks de página y browser manager. Los métodos puramente
sincronos o de I/O se testean directamente.
"""
from __future__ import annotations

import asyncio
import json
import os
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from worldclass_scraper.modules.auth import AsyncAuthManager


# ── helpers ───────────────────────────────────────────────────────────────────

def make_browser_manager():
    """Browser manager mínimo para tests que no necesitan Playwright real."""
    bm = MagicMock()
    bm.context = MagicMock()
    bm.browser = MagicMock()
    return bm


def make_page(url: str = 'https://example.com/dashboard', locator_count: int = 1):
    """Página Playwright mockeada.

    page.locator() es SÍNCRONO en Playwright — devuelve un Locator, no una coroutine.
    Solo los métodos del Locator (count, click, etc.) son async.
    """
    page = MagicMock()  # sync para que locator() devuelva MagicMock, no coroutine
    page.url = url

    locator = MagicMock()
    locator.count = AsyncMock(return_value=locator_count)
    locator.first = MagicMock()
    locator.first.input_value = AsyncMock(return_value='')
    page.locator.return_value = locator

    page.goto = AsyncMock()
    page.fill = AsyncMock()
    page.click = AsyncMock()
    page.press = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    page.screenshot = AsyncMock()
    page.content = AsyncMock(return_value='<html></html>')
    return page


# ── storage_exists ────────────────────────────────────────────────────────────

def test_storage_exists_false_when_file_absent(tmp_path):
    bm = make_browser_manager()
    auth = AsyncAuthManager(bm, storage_path=str(tmp_path / 'session.json'))
    assert auth.storage_exists() is False


def test_storage_exists_true_when_file_present(tmp_path):
    session_file = tmp_path / 'session.json'
    session_file.write_text('{}')
    bm = make_browser_manager()
    auth = AsyncAuthManager(bm, storage_path=str(session_file))
    assert auth.storage_exists() is True


# ── load_session ──────────────────────────────────────────────────────────────

def test_load_session_returns_false_when_no_file(tmp_path):
    bm = make_browser_manager()
    auth = AsyncAuthManager(bm, storage_path=str(tmp_path / 'missing.json'))
    result = asyncio.run(auth.load_session())
    assert result is False


def test_load_session_returns_true_when_file_exists(tmp_path):
    session_file = tmp_path / 'session.json'
    session_file.write_text(json.dumps({'cookies': [], 'origins': []}))

    bm = make_browser_manager()
    new_context = AsyncMock()
    bm.browser.new_context = AsyncMock(return_value=new_context)
    bm.context.close = AsyncMock()

    auth = AsyncAuthManager(bm, storage_path=str(session_file))
    result = asyncio.run(auth.load_session())
    assert result is True


def test_load_session_replaces_browser_context(tmp_path):
    session_file = tmp_path / 'session.json'
    state = {'cookies': [], 'origins': []}
    session_file.write_text(json.dumps(state))

    bm = make_browser_manager()
    new_context = AsyncMock()
    bm.browser.new_context = AsyncMock(return_value=new_context)
    bm.context.close = AsyncMock()

    auth = AsyncAuthManager(bm, storage_path=str(session_file))
    asyncio.run(auth.load_session())

    bm.browser.new_context.assert_called_once_with(storage_state=state)
    assert bm.context is new_context


def test_load_session_accepts_explicit_path(tmp_path):
    path = tmp_path / 'other.json'
    path.write_text(json.dumps({'cookies': [], 'origins': []}))

    bm = make_browser_manager()
    bm.browser.new_context = AsyncMock(return_value=AsyncMock())
    bm.context.close = AsyncMock()

    auth = AsyncAuthManager(bm, storage_path=str(tmp_path / 'default.json'))
    result = asyncio.run(auth.load_session(str(path)))
    assert result is True


# ── save_session ──────────────────────────────────────────────────────────────

def test_save_session_calls_context_storage_state(tmp_path):
    bm = make_browser_manager()
    bm.context.storage_state = AsyncMock(return_value=None)

    auth = AsyncAuthManager(bm, storage_path=str(tmp_path / 'session.json'))
    asyncio.run(auth.save_session())

    bm.context.storage_state.assert_called_once()


def test_save_session_fallback_writes_json_when_primary_fails(tmp_path):
    bm = make_browser_manager()
    path = tmp_path / 'session.json'

    async def storage_state_with_path_fails(path=None):
        if path is not None:
            raise RuntimeError('no path kwarg support')
        return {'cookies': [], 'origins': []}

    bm.context.storage_state = storage_state_with_path_fails

    auth = AsyncAuthManager(bm, storage_path=str(path))
    asyncio.run(auth.save_session())
    assert path.exists()
    data = json.loads(path.read_text())
    assert 'cookies' in data


# ── _resolve_login_fields ─────────────────────────────────────────────────────

def test_resolve_fields_uses_provided_selectors():
    bm = make_browser_manager()
    auth = AsyncAuthManager(bm)
    page = make_page(locator_count=1)

    selectors = {
        'email': 'input#email',
        'password': 'input#password',
        'submit': 'button#submit',
    }
    result = asyncio.run(auth._resolve_login_fields(page, selectors))
    assert result['email'] == 'input#email'
    assert result['password'] == 'input#password'


def test_resolve_fields_falls_back_when_primary_missing():
    bm = make_browser_manager()
    auth = AsyncAuthManager(bm)

    call_count = {'n': 0}

    def locator_side_effect(sel):
        call_count['n'] += 1
        loc = MagicMock()
        # primer selector devuelve count=0, el segundo en adelante devuelve 1
        loc.count = AsyncMock(return_value=0 if call_count['n'] <= 1 else 1)
        return loc

    page = MagicMock()
    page.url = 'https://example.com/login'
    page.locator.side_effect = locator_side_effect

    result = asyncio.run(auth._resolve_login_fields(page, {}))
    assert result['email'] is not None


# ── login — flujo exitoso ─────────────────────────────────────────────────────

def test_login_skips_form_when_already_authenticated():
    """Si la URL no contiene 'login', el manager reporta sesión activa sin rellenar."""
    bm = make_browser_manager()
    bm.context.storage_state = AsyncMock(return_value={'cookies': [], 'origins': []})
    auth = AsyncAuthManager(bm, storage_path='/tmp/session_test.json')

    page = make_page(url='https://example.com/dashboard')

    with patch('worldclass_scraper.config.URLS', {'login': '/login', 'contratos': '/contratos'}):
        result = asyncio.run(
            auth.login(page, 'user@test.com', 'pass', 'https://example.com')
        )
    assert result is True
    page.fill.assert_not_called()


def test_login_returns_false_when_stays_on_login_page(tmp_path):
    """Si tras el click la URL sigue en /login, el método retorna False."""
    bm = make_browser_manager()
    bm.context.storage_state = AsyncMock(return_value={'cookies': [], 'origins': []})
    auth = AsyncAuthManager(bm, storage_path=str(tmp_path / 'session.json'))

    page = MagicMock()
    page.url = 'https://example.com/login'
    page.goto = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    page.screenshot = AsyncMock()
    page.content = AsyncMock(return_value='<html></html>')
    page.fill = AsyncMock()
    page.click = AsyncMock()

    # locator() síncrono con count() async que devuelve 1
    locator = MagicMock()
    locator.count = AsyncMock(return_value=1)
    page.locator.return_value = locator

    with patch('worldclass_scraper.config.URLS', {'login': '/login', 'contratos': '/contratos'}):
        result = asyncio.run(
            auth.login(page, 'user@test.com', 'pass', 'https://example.com',
                       output_dir=str(tmp_path))
        )
    assert result is False
