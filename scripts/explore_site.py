"""
KIRO-7 — Site Explorer
Hace login en worldclass.systemsoca.com y mapea toda la estructura del sitio:
  - Menú de navegación y sus rutas
  - HTML y screenshot de cada sección encontrada
  - Todos los formularios con sus campos
  - Todos los links internos únicos
  - Estructura de datos visible en tablas

Salida: output/exploration/
"""
import asyncio
import json
import os
import sys
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from worldclass_scraper.config import (
    WORLDCLASS_EMAIL,
    WORLDCLASS_PASSWORD,
    WORLDCLASS_BASE_URL,
    PAGE_NAVIGATION_TIMEOUT,
    PAGE_ACTION_TIMEOUT,
    PAGE_READY_STATE_TIMEOUT,
)
from worldclass_scraper.modules.browser import AsyncBrowserManager

BASE_URL = WORLDCLASS_BASE_URL
OUTPUT_DIR = ROOT / 'output' / 'exploration'
MAX_DEPTH = 2          # cuántos niveles de links seguir
MAX_PAGES = 60         # tope de páginas a explorar


def slugify(text: str) -> str:
    text = re.sub(r'[^a-z0-9]+', '-', text.lower().strip())
    return text.strip('-') or 'page'


def is_internal(url: str) -> bool:
    parsed = urlparse(url)
    base = urlparse(BASE_URL)
    return (not parsed.netloc) or (parsed.netloc == base.netloc)


def normalize_url(url: str, current_page_url: str) -> str:
    if url.startswith(('http://', 'https://')):
        return url
    return urljoin(current_page_url, url)


async def login(browser_manager: AsyncBrowserManager) -> 'Page':
    page = await browser_manager.new_page()
    print(f'  → Navegando a login: {BASE_URL}/login')
    await page.goto(f'{BASE_URL}/login', timeout=PAGE_NAVIGATION_TIMEOUT, wait_until='domcontentloaded')
    try:
        await page.wait_for_load_state('networkidle', timeout=PAGE_READY_STATE_TIMEOUT)
    except Exception:
        pass

    # Rellenar credenciales
    for selector in ['input[type="email"]', 'input#email', 'input[name="email"]']:
        if await page.locator(selector).count() > 0:
            await page.fill(selector, WORLDCLASS_EMAIL)
            break

    for selector in ['input[type="password"]', 'input#password', 'input[name="password"]']:
        if await page.locator(selector).count() > 0:
            await page.fill(selector, WORLDCLASS_PASSWORD)
            break

    for selector in ['button[type="submit"]', 'input[type="submit"]', 'button:has-text("Ingresar")', 'button:has-text("Login")']:
        if await page.locator(selector).count() > 0:
            await page.click(selector)
            break

    try:
        await page.wait_for_load_state('networkidle', timeout=PAGE_READY_STATE_TIMEOUT)
    except Exception:
        pass
    await asyncio.sleep(1.5)

    if 'login' in page.url.lower():
        raise RuntimeError(f'Login fallido — seguimos en {page.url}')

    print(f'  ✓ Login exitoso → {page.url}')
    return page


async def capture_page(page, url: str, label: str, out_dir: Path) -> dict:
    """Navega a url, guarda screenshot + HTML, retorna metadata."""
    try:
        await page.goto(url, timeout=PAGE_NAVIGATION_TIMEOUT, wait_until='domcontentloaded')
        try:
            await page.wait_for_load_state('networkidle', timeout=PAGE_READY_STATE_TIMEOUT)
        except Exception:
            pass
        await asyncio.sleep(0.5)

        slug = slugify(label)
        html_path = out_dir / f'{slug}.html'
        img_path = out_dir / f'{slug}.png'

        html = await page.content()
        html_path.write_text(html, encoding='utf-8')
        await page.screenshot(path=str(img_path), full_page=True)

        # Extraer título
        title = await page.title()

        # Extraer todos los links internos
        raw_links = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('a[href]'))
                .map(a => ({ href: a.href, text: a.textContent.trim().substring(0, 80) }))
                .filter(l => l.href && !l.href.startsWith('javascript') && !l.href.startsWith('mailto'));
        }''')

        # Extraer nav/menu links (prioridad)
        nav_links = await page.evaluate('''() => {
            const navSelectors = ['nav a', '.navbar a', '.sidebar a', '.menu a',
                                  '.nav a', '[class*="nav"] a', '[class*="menu"] a',
                                  '[class*="sidebar"] a'];
            const seen = new Set();
            const links = [];
            for (const sel of navSelectors) {
                for (const a of document.querySelectorAll(sel)) {
                    const href = a.href;
                    const text = a.textContent.trim();
                    if (href && !href.startsWith('javascript') && !seen.has(href)) {
                        seen.add(href);
                        links.push({ href, text: text.substring(0, 80) });
                    }
                }
            }
            return links;
        }''')

        # Extraer formularios
        forms = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('form')).map(form => ({
                action: form.action,
                method: form.method,
                fields: Array.from(form.querySelectorAll('input, select, textarea')).map(f => ({
                    tag: f.tagName.toLowerCase(),
                    type: f.type || '',
                    name: f.name || '',
                    id: f.id || '',
                    placeholder: f.placeholder || '',
                    options: f.tagName === 'SELECT'
                        ? Array.from(f.options).map(o => ({ value: o.value, text: o.text.trim() }))
                        : []
                }))
            }));
        }''')

        # Extraer cabeceras de tablas (estructura de datos)
        tables = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('table')).map(t => ({
                headers: Array.from(t.querySelectorAll('thead th, thead td'))
                    .map(th => th.textContent.trim()).filter(Boolean),
                row_count: t.querySelectorAll('tbody tr').length
            }));
        }''')

        print(f'    ✓ {label} | links={len(raw_links)} | forms={len(forms)} | tables={len(tables)}')

        return {
            'url': url,
            'label': label,
            'title': title,
            'html_file': str(html_path.name),
            'screenshot': str(img_path.name),
            'nav_links': nav_links,
            'all_links': raw_links,
            'forms': forms,
            'tables': tables,
            'captured_at': datetime.now().isoformat(),
        }

    except Exception as exc:
        print(f'    ✗ Error capturando {url}: {exc}')
        return {'url': url, 'label': label, 'error': str(exc)}


async def explore():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print('=' * 60)
    print('  KIRO-7 — SITE EXPLORER')
    print(f'  Target : {BASE_URL}')
    print(f'  Output : {OUTPUT_DIR}')
    print('=' * 60)

    browser = AsyncBrowserManager(
        headless=True,
        navigation_timeout=PAGE_NAVIGATION_TIMEOUT,
        action_timeout=PAGE_ACTION_TIMEOUT,
    )
    await browser.start()

    try:
        # FASE 1: Login y captura del dashboard
        print('\n[FASE 1] Login y dashboard...')
        page = await login(browser)
        dashboard_url = page.url

        pages_explored: list[dict] = []
        visited: set[str] = {dashboard_url}

        dashboard_data = await capture_page(page, dashboard_url, 'dashboard', OUTPUT_DIR)
        pages_explored.append(dashboard_data)

        # FASE 2: Mapear menú de navegación
        print('\n[FASE 2] Mapeando menú de navegación...')
        nav_links = dashboard_data.get('nav_links', [])

        # Agregar links conocidos del dominio para no perdernos nada
        known_paths = [
            '/contratos', '/clientes', '/pagos', '/reportes', '/sedes',
            '/usuarios', '/configuracion', '/admin', '/dashboard', '/home',
            '/ventas', '/socios', '/membresias', '/cobros', '/facturacion',
        ]
        for path in known_paths:
            nav_links.append({'href': f'{BASE_URL}{path}', 'text': path.strip('/')})

        # Deduplicar
        seen_nav = set()
        unique_nav = []
        for link in nav_links:
            href = link.get('href', '')
            if href and href not in seen_nav and is_internal(href):
                seen_nav.add(href)
                unique_nav.append(link)

        print(f'  → {len(unique_nav)} rutas a explorar')

        # FASE 3: Explorar cada sección
        print('\n[FASE 3] Explorando secciones...')
        queue = [(lnk['href'], lnk.get('text', '?'), 1) for lnk in unique_nav if lnk['href'] not in visited]

        while queue and len(pages_explored) < MAX_PAGES:
            url, label, depth = queue.pop(0)

            if url in visited:
                continue
            visited.add(url)

            # Solo URLs internas del mismo dominio
            if not is_internal(url):
                continue

            # Saltar assets, logout y anchors
            parsed = urlparse(url)
            path = parsed.path.lower()
            if any(path.endswith(ext) for ext in ['.css', '.js', '.png', '.jpg', '.ico', '.pdf']):
                continue
            if 'logout' in path or 'salir' in path:
                continue
            if parsed.fragment and not parsed.path:
                continue

            slug_label = label if label and label != '?' else path.strip('/').replace('/', '-') or 'page'
            print(f'\n  [{len(pages_explored)+1}] {slug_label} → {url}')

            data = await capture_page(page, url, slug_label, OUTPUT_DIR)
            pages_explored.append(data)

            # Si hay profundidad disponible, encolar sus links internos
            if depth < MAX_DEPTH and 'all_links' in data:
                for link in data['all_links']:
                    href = normalize_url(link.get('href', ''), url)
                    if href and href not in visited and is_internal(href):
                        text = link.get('text', '') or urlparse(href).path
                        queue.append((href, text[:50], depth + 1))

        # FASE 4: Guardar mapa completo en JSON
        print('\n[FASE 4] Guardando mapa de sitio...')
        site_map = {
            'base_url': BASE_URL,
            'explored_at': datetime.now().isoformat(),
            'total_pages': len(pages_explored),
            'pages': pages_explored,
        }
        map_path = OUTPUT_DIR / 'site_map.json'
        map_path.write_text(json.dumps(site_map, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f'  ✓ site_map.json guardado ({len(pages_explored)} páginas)')

        # FASE 5: Resumen de entidades encontradas
        print('\n[FASE 5] Resumen de entidades detectadas...')
        all_tables: dict[str, list] = {}
        all_forms: list[dict] = []

        for p in pages_explored:
            for t in p.get('tables', []):
                if t.get('headers'):
                    key = ' | '.join(t['headers'])
                    if key not in all_tables:
                        all_tables[key] = []
                    all_tables[key].append(p['url'])
            for f in p.get('forms', []):
                fields = [fld['name'] or fld['id'] for fld in f.get('fields', []) if fld.get('name') or fld.get('id')]
                if fields:
                    all_forms.append({'url': p['url'], 'action': f.get('action', ''), 'fields': fields})

        entities_path = OUTPUT_DIR / 'entities_detected.json'
        entities = {'tables': all_tables, 'forms': all_forms}
        entities_path.write_text(json.dumps(entities, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f'  ✓ entities_detected.json | tablas={len(all_tables)} | formularios={len(all_forms)}')

        print('\n' + '=' * 60)
        print(f'  MISIÓN COMPLETA — {len(pages_explored)} páginas exploradas')
        print(f'  Archivos en: {OUTPUT_DIR}')
        print('=' * 60)

    finally:
        await browser.close()


if __name__ == '__main__':
    asyncio.run(explore())
