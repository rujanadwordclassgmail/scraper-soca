"""Gestión de autenticación y sesiones Playwright.

Responsabilidades:
  - Guardar / cargar storage_state en disco.
  - Ejecutar el flujo de login (navegar, rellenar campos, click, verificar).
  - Resolver selectores de login con fallbacks.

No conoce nada de extracción de contratos ni de lógica de negocio.
"""
from __future__ import annotations

import json
import os
from typing import Dict, Optional

from playwright.async_api import Page


class AsyncAuthManager:
    """Gestión desacoplada de autenticación / storage_state para Playwright."""

    def __init__(self, browser_manager, storage_path: str = 'auth_session.json') -> None:
        self.browser_manager = browser_manager
        self.storage_path = storage_path

    # ── sesión persistida ───────────────────────────────────────────────────

    def storage_exists(self) -> bool:
        return os.path.exists(self.storage_path)

    async def load_session(self, storage_path: Optional[str] = None) -> bool:
        """Carga storage_state desde disco y reemplaza el contexto activo.

        Retorna True si la sesión fue cargada, False si no existe el archivo.
        """
        path = storage_path or self.storage_path
        if not os.path.exists(path):
            return False

        with open(path, 'r', encoding='utf-8') as fh:
            storage = json.load(fh)

        try:
            if getattr(self.browser_manager, 'context', None):
                await self.browser_manager.context.close()
        except Exception:
            pass

        self.browser_manager.context = await self.browser_manager.browser.new_context(
            storage_state=storage
        )
        return True

    async def save_session(self, storage_path: Optional[str] = None) -> None:
        """Guarda el storage_state del contexto activo en disco."""
        path = storage_path or self.storage_path
        try:
            await self.browser_manager.context.storage_state(path=path)
        except Exception:
            try:
                state = await self.browser_manager.context.storage_state()
                with open(path, 'w', encoding='utf-8') as fh:
                    json.dump(state, fh, indent=2)
            except Exception:
                pass

    # ── flujo de login ──────────────────────────────────────────────────────

    async def login(
        self,
        page: Page,
        email: str,
        password: str,
        login_url: str,
        selectors: Optional[Dict[str, str]] = None,
        output_dir: str = 'output',
    ) -> bool:
        """Navega a login_url, rellena credenciales y retorna True si tuvo éxito.

        Guarda automáticamente la sesión si el login es exitoso.
        """
        from worldclass_scraper.config import URLS  # import local para evitar circular

        destination = f"{login_url}{URLS['login']}"
        print(f'→ Navegando a login: {destination}')
        await page.goto(destination, wait_until='domcontentloaded')
        try:
            await page.wait_for_load_state('networkidle', timeout=15000)
        except Exception:
            pass

        if 'login' not in page.url.lower():
            print('✓ Ya existen credenciales activas o redirección fuera de login')
            return True

        fields = await self._resolve_login_fields(page, selectors or {})
        if not fields['email'] or not fields['password']:
            await self._save_debug_login_state(page, output_dir)
            raise RuntimeError(
                'No se pudieron ubicar los campos de usuario y contraseña en la página de login.'
            )

        await page.fill(fields['email'], email)
        await page.fill(fields['password'], password)

        if fields['submit'] and await page.locator(fields['submit']).count() > 0:
            await page.click(fields['submit'])
        else:
            await page.press(fields['password'], 'Enter')

        try:
            await page.wait_for_load_state('networkidle', timeout=15000)
        except Exception:
            pass

        if 'login' not in page.url.lower():
            print('✓ Login exitoso')
            await self.save_session()
            return True

        screenshots_dir = os.path.join(output_dir, 'screenshots')
        os.makedirs(screenshots_dir, exist_ok=True)
        error_path = os.path.join(screenshots_dir, 'login_error.png')
        await page.screenshot(path=error_path)
        print(f'✗ Login fallido — screenshot guardado en {error_path}')
        return False

    async def perform_login_and_save(
        self,
        page: Page,
        email: str,
        password: str,
        storage_path: Optional[str] = None,
        selectors: Optional[dict] = None,
        login_url: Optional[str] = None,
    ) -> bool:
        """Compatibilidad con el contrato anterior (usado en scraper.py legacy)."""
        path = storage_path or self.storage_path
        sel = selectors or {}

        if login_url:
            await page.goto(login_url)

        if sel.get('email'):
            await page.fill(sel['email'], email)
        if sel.get('password'):
            await page.fill(sel['password'], password)
        if sel.get('submit'):
            await page.click(sel['submit'])

        try:
            await page.wait_for_load_state('networkidle')
        except Exception:
            pass

        success = 'login' not in page.url.lower()
        if success:
            await self.save_session(path)
        return success

    # ── privados ────────────────────────────────────────────────────────────

    async def _resolve_login_fields(
        self, page: Page, selectors: Dict[str, str]
    ) -> Dict[str, Optional[str]]:
        """Detecta selectores de email, password y submit con fallbacks."""
        email_candidates = [
            selectors.get('email', ''),
            'input[type="email"]',
            'input[name*="email"]',
            'input[id*="email"]',
            'input[type="text"]',
        ]
        email_selector = None
        for sel in filter(None, email_candidates):
            if await page.locator(sel).count() > 0:
                email_selector = sel
                break

        password_candidates = [
            selectors.get('password', ''),
            'input[type="password"]',
            'input[name*="pass"]',
            'input[id*="pass"]',
        ]
        password_selector = None
        for sel in filter(None, password_candidates):
            if await page.locator(sel).count() > 0:
                password_selector = sel
                break

        submit_primary = selectors.get('submit', 'button[type="submit"], input[type="submit"]')
        submit_selector: Optional[str] = submit_primary
        if not submit_primary or await page.locator(submit_primary).count() == 0:
            for sel in [
                'button[type="submit"]',
                'button:has-text("Ingresar")',
                'button:has-text("Login")',
                'button:has-text("Entrar")',
            ]:
                if await page.locator(sel).count() > 0:
                    submit_selector = sel
                    break

        return {'email': email_selector, 'password': password_selector, 'submit': submit_selector}

    async def _save_debug_login_state(self, page: Page, output_dir: str) -> None:
        debug_dir = os.path.join(output_dir, 'debug')
        os.makedirs(debug_dir, exist_ok=True)
        try:
            await page.screenshot(path=os.path.join(debug_dir, 'login_page.png'))
        except Exception:
            pass
        try:
            content = await page.content()
            with open(os.path.join(debug_dir, 'login_page.html'), 'w', encoding='utf-8') as fh:
                fh.write(content)
        except Exception:
            pass
