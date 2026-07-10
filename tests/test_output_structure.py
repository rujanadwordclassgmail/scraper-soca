import importlib
import os
import sys
import tempfile
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _install_dummy_scraper_dependencies():
    playwright_mod = types.ModuleType('playwright')
    playwright_async_mod = types.ModuleType('playwright.async_api')

    async def async_playwright():
        class DummyPlaywright:
            async def start(self):
                return self

            async def stop(self):
                pass

            @property
            def chromium(self):
                class Chromium:
                    async def launch(self, headless=True):
                        class Browser:
                            async def new_context(self):
                                class Context:
                                    async def new_page(self):
                                        class Page:
                                            def set_default_navigation_timeout(self, timeout):
                                                pass

                                            def set_default_timeout(self, timeout):
                                                pass

                                        return Page()

                                    async def close(self):
                                        pass

                                return Context()

                            async def close(self):
                                pass

                        return Browser()

                return Chromium()

        return DummyPlaywright()

    playwright_async_mod.async_playwright = async_playwright
    playwright_async_mod.Browser = object
    playwright_async_mod.BrowserContext = object
    playwright_async_mod.Page = object
    playwright_async_mod.Playwright = object

    sys.modules['playwright'] = playwright_mod
    sys.modules['playwright.async_api'] = playwright_async_mod

    browser_module = types.ModuleType('worldclass_scraper.modules.browser')
    class DummyBrowserManager:
        def __init__(self, headless=True, navigation_timeout=60000, action_timeout=30000):
            pass

        async def start(self):
            pass

        async def new_page(self):
            return None

        async def close(self):
            pass

    browser_module.AsyncBrowserManager = DummyBrowserManager
    sys.modules['worldclass_scraper.modules.browser'] = browser_module

    auth_module = types.ModuleType('worldclass_scraper.modules.auth')
    class DummyAuthManager:
        def __init__(self, browser_manager, storage_path=None):
            pass

        async def load_session(self):
            return False

    auth_module.AsyncAuthManager = DummyAuthManager
    sys.modules['worldclass_scraper.modules.auth'] = auth_module

    extractors_module = types.ModuleType('worldclass_scraper.modules.extractors')
    class DummyContractExtractor:
        def __init__(self, output_dir, debug=False):
            pass

    extractors_module.ContractExtractor = DummyContractExtractor
    sys.modules['worldclass_scraper.modules.extractors'] = extractors_module

    exporters_module = types.ModuleType('worldclass_scraper.modules.exporters')

    class DummyExcelExporter:
        def __init__(self, output_dir):
            self.output_dir = output_dir

        def export_csv(self, rows, filepath):
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as fh:
                fh.write('dummy')

        def export(self, rows, filepath, sheet_names=None, sheet_field='Estado_Contrato'):
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as fh:
                fh.write('dummy')

    class DummyAbstractExporter:
        pass

    class DummyExportOrchestrator:
        def __init__(self, exporter, output_dir, logger=None,
                     partial_export=False, partial_format='csv', save_every=0):
            self.exporter = exporter
            self.output_dir = output_dir

        async def export_partial(self, rows, prefix):
            pass

        async def export_site_reports(self, sitio, rows, mode, sede_override='',
                                       export_csv=True, export_xlsx=False):
            import asyncio
            from datetime import datetime
            from worldclass_scraper.modules.utils import slugify
            date_suffix = datetime.now().strftime('%Y%m%d')
            template = sitio.get('excel_template', 'contratos_{SEDE}_{ESTADO}.xlsx')
            groups: dict = {}
            for row in rows:
                sede = row.get('Sede') or sede_override or 'SIN_SEDE'
                estado = row.get('Estado_Contrato') or 'NO_ESTADO'
                groups.setdefault((sede, estado), []).append(row)
            for (sede_name, estado_name), group_rows in groups.items():
                sede_slug = slugify(sede_name)
                estado_slug = slugify(estado_name)
                reports_dir = os.path.join(self.output_dir, mode, sede_slug, 'reports')
                os.makedirs(reports_dir, exist_ok=True)
                base = template.replace('{SEDE}', sede_slug).replace('{ESTADO}', estado_slug)
                stem = os.path.splitext(base)[0]
                if export_csv:
                    path = os.path.join(reports_dir, f'{stem}_{date_suffix}.csv')
                    await asyncio.to_thread(self.exporter.export_csv, group_rows, path)

        async def export_combined(self, rows, mode, filename, export_csv=True, export_xlsx=False):
            return []

    exporters_module.AbstractExporter = DummyAbstractExporter
    exporters_module.ExcelExporter = DummyExcelExporter
    exporters_module.ExportOrchestrator = DummyExportOrchestrator
    sys.modules['worldclass_scraper.modules.exporters'] = exporters_module

    logging_module = types.ModuleType('worldclass_scraper.modules.logging')
    class DummyScraperLogger:
        def __init__(self, log_dir=None):
            pass

        def summary(self, msg):
            pass

        def debug(self, msg):
            pass

        def error(self, msg):
            pass

    logging_module.ScraperLogger = DummyScraperLogger
    sys.modules['worldclass_scraper.modules.logging'] = logging_module

    retry_module = types.ModuleType('worldclass_scraper.modules.retry')
    class DummyRetryPolicy:
        pass

    async def retry_async(fn, *args, **kwargs):
        return await fn(*args, **kwargs)

    retry_module.RetryPolicy = DummyRetryPolicy
    retry_module.retry_async = retry_async
    sys.modules['worldclass_scraper.modules.retry'] = retry_module

    # ── módulos nuevos (post-refactor) ───────────────────────────────────────
    progress_module = types.ModuleType('worldclass_scraper.modules.progress')
    class DummyProgressRenderer:
        def render(self, current, total):
            return ''
        def print_final(self, current, total):
            pass
    progress_module.ProgressRenderer = DummyProgressRenderer
    sys.modules['worldclass_scraper.modules.progress'] = progress_module

    concurrency_module = types.ModuleType('worldclass_scraper.modules.concurrency')
    class DummyAdaptiveConcurrencyController:
        def __init__(self, initial=2, **kwargs):
            self.concurrency = initial
            self.site_name = ''
            self._error_streak = 0
        @property
        def error_streak(self):
            return self._error_streak
        @property
        def error_threshold(self):
            return 10
        def on_error(self, msg):
            return False
        def on_success(self):
            return False
    concurrency_module.AdaptiveConcurrencyController = DummyAdaptiveConcurrencyController
    sys.modules['worldclass_scraper.modules.concurrency'] = concurrency_module

    filters_module = types.ModuleType('worldclass_scraper.modules.filters')
    class DummyFilterManager:
        def __init__(self, selectors, base_url=''):
            pass
        async def apply_filters(self, page, filtros, estado):
            pass
        async def collect_contract_urls(self, page, estado, output_dir='', debug=False):
            return []
    filters_module.FilterManager = DummyFilterManager
    sys.modules['worldclass_scraper.modules.filters'] = filters_module


def _import_scraper_module():
    _install_dummy_scraper_dependencies()
    if 'worldclass_scraper.scraper' in sys.modules:
        del sys.modules['worldclass_scraper.scraper']
    return importlib.import_module('worldclass_scraper.scraper')


def test_slugified_sede_report_directory(tmp_path):
    scraper_module = _import_scraper_module()
    AsyncWorldClassScraper = scraper_module.AsyncWorldClassScraper
    scraper = AsyncWorldClassScraper(
        base_url='https://example.com',
        email='test@example.com',
        password='secret',
        headless=True,
        log_dir=str(tmp_path / 'logs'),
        output_dir=str(tmp_path / 'output'),
    )

    sitio = {'nombre': 'worldclass', 'filtros': {'sede': 'WC - Santo domingo'}}
    rows = [
        {'Sede': 'WC - Santo domingo', 'Estado_Contrato': 'CASH', 'Numero_Contrato': 'WCG123'},
    ]

    async def run_export():
        await scraper.export_site_reports(sitio, mode='worldclass', rows=rows, export_csv=True, export_xlsx=False)

    import asyncio
    asyncio.run(run_export())

    expected_dir = tmp_path / 'output' / 'worldclass' / 'wc-santo-domingo' / 'reports'
    assert expected_dir.exists()
    output_files = list(expected_dir.glob('*.csv'))
    assert len(output_files) == 1
    assert 'wc-santo-domingo' in output_files[0].name
    assert 'cash' in output_files[0].name


def test_slugify_normalizes_sede():
    from worldclass_scraper.modules.utils import slugify
    assert slugify('WC - Santo domingo') == 'wc-santo-domingo'


