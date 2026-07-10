"""Orquestador principal del scraper.

Responsabilidades (y solo estas):
  - Coordinar el ciclo: login → filtros → recolección → extracción → exportación.
  - Gestionar el ciclo de vida del navegador.
  - Controlar el pool de tareas concurrentes y el timeout por contrato.
  - Reportar progreso y resumen final en stdout.

Todo lo demás vive en módulos especializados.
"""
from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List, Optional

from worldclass_scraper.config import (
    CONCURRENCY,
    DEBUG,
    EMAIL,
    EXCEL_COMBINADO,
    EXCEL_COMBINADO_FILENAME,
    EXPORT_CSV,
    EXPORT_XLSX,
    HEADLESS,
    LOG_DIR,
    OUTPUT_DIR,
    MAX_RETRIES,
    MODO,
    PAGE_ACTION_TIMEOUT,
    PAGE_NAVIGATION_TIMEOUT,
    PAGE_READY_STATE_TIMEOUT,
    PARTIAL_EXPORT,
    PARTIAL_FORMAT,
    RETRY_BASE_DELAY,
    RETRY_JITTER,
    RETRY_MAX_DELAY,
    SAVE_EVERY,
    SELECTORS,
    SITIOS,
    TIMING_FACTOR,
    URLS,
    PASSWORD,
    AUTO_REDUCE_ON_ERRORS,
    ERROR_THRESHOLD,
    MIN_CONCURRENCY,
    CONCURRENCY_REDUCTION_STEP,
    AUTO_RECOVERY,
    STABLE_THRESHOLD,
    RECOVERY_STEP,
    MAX_CONCURRENCY,
)
from worldclass_scraper.modules.browser import AsyncBrowserManager
from worldclass_scraper.modules.auth import AsyncAuthManager
from worldclass_scraper.modules.concurrency import AdaptiveConcurrencyController
from worldclass_scraper.modules.extractors import ContractExtractor
from worldclass_scraper.modules.exporters import ExcelExporter, ExportOrchestrator
from worldclass_scraper.modules.filters import FilterManager
from worldclass_scraper.modules.logging import ScraperLogger
from worldclass_scraper.modules.progress import ProgressRenderer
from worldclass_scraper.modules.retry import RetryPolicy, retry_async
from worldclass_scraper.modules.utils import RESET, BOLD, GREEN, YELLOW, CYAN, MAGENTA, RED


class AsyncWorldClassScraper:

    def __init__(
        self,
        base_url: str,
        email: str,
        password: str,
        headless: bool = True,
        timing_factor: float = 1.0,
        log_dir: str = LOG_DIR,
        output_dir: str = OUTPUT_DIR,
        max_retries: int = MAX_RETRIES,
        save_every: int = SAVE_EVERY,
        concurrency: int = CONCURRENCY,
    ) -> None:
        self.base_url = base_url
        self.email = email
        self.password = password
        self.headless = headless
        self.timing_factor = max(0.0, float(timing_factor))
        self.log_dir = log_dir
        self.output_dir = output_dir
        self.max_retries = max(1, max_retries)
        self.save_every = max(0, save_every)
        self.current_site = ''

        # ── módulos especializados ────────────────────────────────────────
        self.browser_manager = AsyncBrowserManager(
            headless=self.headless,
            navigation_timeout=PAGE_NAVIGATION_TIMEOUT,
            action_timeout=PAGE_ACTION_TIMEOUT,
        )
        self.logger = ScraperLogger(self.log_dir)
        self.extractor = ContractExtractor(self.output_dir, debug=DEBUG)
        self.exporter = ExcelExporter(self.output_dir)
        self.export_orchestrator = ExportOrchestrator(
            exporter=self.exporter,
            output_dir=self.output_dir,
            logger=self.logger,
            partial_export=PARTIAL_EXPORT,
            partial_format=PARTIAL_FORMAT,
            save_every=save_every,
        )
        self.concurrency_ctrl = AdaptiveConcurrencyController(
            initial=concurrency,
            min_concurrency=MIN_CONCURRENCY,
            max_concurrency=MAX_CONCURRENCY,
            error_threshold=ERROR_THRESHOLD,
            reduction_step=CONCURRENCY_REDUCTION_STEP,
            stable_threshold=STABLE_THRESHOLD,
            recovery_step=RECOVERY_STEP,
            auto_reduce=AUTO_REDUCE_ON_ERRORS,
            auto_recovery=AUTO_RECOVERY,
            logger=self.logger,
        )
        self.progress = ProgressRenderer()

        # ── estado mutable de ejecución ───────────────────────────────────
        self.main_page = None
        self.auth_manager: Optional[AsyncAuthManager] = None
        self.page_ready_state_timeout = PAGE_READY_STATE_TIMEOUT
        self.results: List[Dict[str, Any]] = []
        self.partial_checkpoint = 0
        self.save_lock = asyncio.Lock()
        self.stats = {'extracted': 0, 'errors': 0, 'skips': 0, 'processed': 0}

    # ── propiedades de compatibilidad ────────────────────────────────────────

    @property
    def concurrency(self) -> int:
        return self.concurrency_ctrl.concurrency

    # ── ciclo de vida del navegador ───────────────────────────────────────────

    async def start(self) -> None:
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        await self.browser_manager.start()

        storage_path = os.path.join(self.output_dir, 'auth_session.json')
        self.auth_manager = AsyncAuthManager(self.browser_manager, storage_path=storage_path)

        loaded = False
        try:
            loaded = await self.auth_manager.load_session()
        except Exception as exc:
            self.logger.error(f'auth_load_error={exc}')

        self.main_page = await self.browser_manager.new_page()
        if loaded:
            self.logger.summary(f'session_loaded={storage_path}')

    async def stop(self) -> None:
        if self.main_page:
            try:
                await self.main_page.close()
            except Exception:
                pass
            self.main_page = None
        await self.browser_manager.close()

    async def _recreate_browser_context(self) -> None:
        for attr in ('main_page', None):
            try:
                if attr and getattr(self, attr, None):
                    await getattr(self, attr).close()
            except Exception:
                pass
        for ctx_attr in ('context', 'browser'):
            try:
                obj = getattr(self.browser_manager, ctx_attr, None)
                if obj:
                    await obj.close()
            except Exception:
                pass

        await self.browser_manager.start()
        self.main_page = await self.browser_manager.new_page()

        if self.auth_manager and self.auth_manager.storage_exists():
            try:
                await self.auth_manager.load_session()
                await self.main_page.close()
                self.main_page = await self.browser_manager.new_page()
            except Exception:
                pass

    # ── login ─────────────────────────────────────────────────────────────────

    async def login(self) -> bool:
        return await self.auth_manager.login(
            page=self.main_page,
            email=self.email,
            password=self.password,
            login_url=self.base_url,
            selectors=SELECTORS,
            output_dir=self.output_dir,
        )

    # ── navegación con retry ──────────────────────────────────────────────────

    def _calculate_delay(self, seconds: float) -> float:
        return max(0.0, float(seconds) * self.timing_factor)

    async def _wait(self, seconds: float) -> None:
        delay = self._calculate_delay(seconds)
        if delay > 0:
            await asyncio.sleep(delay)

    def _is_transient_error(self, exc: Exception) -> bool:
        markers = [
            'TargetClosedError',
            'Target page, context or browser has been closed',
            'net::ERR_',
            'ERR_ABORTED',
            'Timeout',
            'Frame detached',
        ]
        return any(m in str(exc) for m in markers)

    async def _wait_for_page_ready(self, page: Any) -> None:
        try:
            await page.wait_for_load_state('networkidle', timeout=self.page_ready_state_timeout)
        except Exception:
            pass

    async def _goto(self, page: Any, url: str, reintentos: int = 3) -> None:
        policy = RetryPolicy(
            retries=reintentos,
            base_delay=RETRY_BASE_DELAY,
            max_delay=RETRY_MAX_DELAY,
            jitter=RETRY_JITTER,
            timing_factor=self.timing_factor,
        )

        async def navigate() -> None:
            await page.goto(url, timeout=PAGE_NAVIGATION_TIMEOUT, wait_until='domcontentloaded')
            await self._wait_for_page_ready(page)

        async def on_retry(exc: Exception, attempt: int) -> None:
            nonlocal page
            self.logger.error(f'retry_goto={attempt}/{reintentos} | url={url} | mensaje={exc}')
            try:
                await page.close()
            except Exception:
                pass
            try:
                page = await self.browser_manager.new_page()
            except Exception as e:
                self.logger.error(f'new_page_failed={e} | recreating browser context')
                await self._recreate_browser_context()
                page = await self.browser_manager.new_page()

        await retry_async(
            navigate,
            policy,
            retry_if=lambda exc, attempt: attempt < reintentos and self._is_transient_error(exc),
            on_retry=on_retry,
        )

    # ── extracción de un contrato ─────────────────────────────────────────────

    async def extract_contract_page(self, url: str, estado: str, sede: str = '') -> Optional[Dict[str, Any]]:
        page = await self.browser_manager.new_page()
        try:
            await self._goto(page, url)
            await self._wait(0.3)
            if DEBUG:
                debug_dir = os.path.join(self.output_dir, 'debug')
                os.makedirs(debug_dir, exist_ok=True)
                debug_path = os.path.join(debug_dir, f'debug_detalle_{url.split("/")[-1]}.html')
                if not os.path.exists(debug_path):
                    with open(debug_path, 'w', encoding='utf-8') as fd:
                        fd.write(await page.content())
            return await self.extractor.extract(page, url, estado, sede)
        finally:
            await page.close()

    # ── acumulación de resultados ─────────────────────────────────────────────

    async def _append_result(self, detail: Dict[str, Any], prefix: str) -> None:
        async with self.save_lock:
            self.results.append(detail)
            if self.save_every and len(self.results) - self.partial_checkpoint >= self.save_every:
                self.partial_checkpoint = len(self.results)
                await self.export_orchestrator.export_partial(self.results, prefix)

    # ── procesamiento de un contrato (con retry y timeout) ────────────────────

    async def _process_contract(
        self, url: str, estado: str, prefix: str, sede: str, index: int, total: int
    ) -> None:
        print(f'  {CYAN}→ Procesando contrato {index}/{total}{RESET}: {url}')

        async def extract_action() -> Optional[Dict[str, Any]]:
            return await self.extract_contract_page(url, estado, sede)

        try:
            detail = await retry_async(
                extract_action,
                RetryPolicy(retries=self.max_retries, base_delay=1.0, max_delay=30.0,
                            jitter=0.1, timing_factor=self.timing_factor),
                retry_if=lambda exc, attempt: attempt < self.max_retries,
                on_retry=lambda exc, attempt: self.logger.error(
                    f'retry_extract={attempt}/{self.max_retries} | sitio={self.current_site}'
                    f' | estado={estado} | url={url} | mensaje={exc}'
                ),
            )
            if detail:
                detail['sitio'] = self.current_site
                await self._append_result(detail, prefix)
                self.stats['extracted'] += 1
                self.concurrency_ctrl.on_success()
                self._print_contract_result(url, estado, sede, True)
            else:
                self.stats['skips'] += 1
                self.logger.skip(f'sitio={self.current_site} | estado={estado} | url={url} | motivo=sin datos útiles')
                self._print_contract_result(url, estado, sede, False, 'sin datos útiles')
        except Exception as exc:
            msg = str(exc)
            self.logger.error(f'extract_failed={self.current_site} | estado={estado} | url={url} | mensaje={msg}')
            self.concurrency_ctrl.on_error(msg)
            self.stats['errors'] += 1
            self._print_contract_result(url, estado, sede, False, msg)
        finally:
            self.stats['processed'] += 1

    async def _process_contract_with_timeout(
        self, url: str, estado: str, prefix: str, sede: str, index: int, total: int
    ) -> None:
        timeout_s = max(180.0, PAGE_NAVIGATION_TIMEOUT / 1000 * 4)
        task = asyncio.create_task(
            self._process_contract(url, estado, prefix, sede, index, total)
        )
        try:
            await asyncio.wait_for(task, timeout=timeout_s)
        except asyncio.TimeoutError:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
            msg = f'timeout_extract={int(timeout_s)}s'
            self.logger.error(f'{msg} | sitio={self.current_site} | estado={estado} | url={url}')
            self.concurrency_ctrl.on_error(msg)
            self.stats['errors'] += 1
            self.stats['processed'] += 1
            self._print_contract_result(url, estado, sede, False, msg)
        except Exception:
            if not task.done():
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass
            raise

    # ── procesamiento de un estado completo ───────────────────────────────────

    async def process_state(
        self, estado: str, filtros: Dict[str, Any], limit: int = 0
    ) -> List[Dict[str, Any]]:
        await self._goto(self.main_page, f"{self.base_url}{URLS['contratos']}")
        await self._wait(1)

        filter_manager = FilterManager(selectors=SELECTORS, base_url=self.base_url)
        await filter_manager.apply_filters(self.main_page, filtros, estado)

        urls = await filter_manager.collect_contract_urls(
            self.main_page, estado, self.output_dir, debug=DEBUG
        )
        if limit and len(urls) > limit:
            print(f'  ⚠ Límite aplicado: {limit} de {len(urls)} contratos')
            urls = urls[:limit]

        if not urls:
            print(f'  ℹ No se encontraron contratos para {estado}')
            return []

        total = len(urls)
        print(f'→ Extrayendo detalle de {total} contratos...')
        prefix = f'{self.current_site}_{estado}'.replace(' ', '_')
        sede = filtros.get('sede', '')

        pending = list(enumerate(urls, start=1))
        while pending:
            batch_size = max(1, self.concurrency)
            batch, pending = pending[:batch_size], pending[batch_size:]

            results = await asyncio.gather(
                *[asyncio.create_task(
                    self._process_contract_with_timeout(url, estado, prefix, sede, idx, total)
                  ) for idx, url in batch],
                return_exceptions=True,
            )
            for r in results:
                if isinstance(r, Exception):
                    self.logger.error(
                        f'unhandled_contract_task_exception={r} | sitio={self.current_site} | estado={estado}'
                    )

            if self.concurrency_ctrl.error_streak >= self.concurrency_ctrl.error_threshold and pending:
                self.logger.error(f'batch_error_threshold_reached | sitio={self.current_site}')
                try:
                    await self._recreate_browser_context()
                except Exception as exc:
                    self.logger.error(f'recreate_on_batch_error_failed={exc}')
                await asyncio.sleep(self._calculate_delay(2.0))

        self.progress.print_final(self.stats['processed'], total)
        return self.results

    # ── exportación (delegada al orquestador) ────────────────────────────────

    async def export_site_reports(
        self,
        sitio: Dict[str, Any],
        mode: str = 'todos',
        sede_override: str = '',
        rows: Optional[List[Dict[str, Any]]] = None,
        export_csv: Optional[bool] = None,
        export_xlsx: Optional[bool] = None,
    ) -> None:
        await self.export_orchestrator.export_site_reports(
            sitio=sitio,
            rows=rows if rows is not None else self.results,
            mode=mode,
            sede_override=sede_override,
            export_csv=EXPORT_CSV if export_csv is None else export_csv,
            export_xlsx=EXPORT_XLSX if export_xlsx is None else export_xlsx,
        )

    # ── utilidades de presentación ────────────────────────────────────────────

    def print_dashboard(
        self, mode: str, contract_url: str, estado: str, sede: str,
        export_csv: bool, export_xlsx: bool
    ) -> None:
        border = f"{CYAN}{'=' * 62}{RESET}"
        export_label = (
            'CSV + XLSX' if export_csv and export_xlsx
            else 'CSV' if export_csv
            else 'XLSX' if export_xlsx
            else '[ninguno]'
        )
        print(border)
        print(f'{BOLD}{MAGENTA}WORLD CLASS SCRAPER - DASHBOARD DE EJECUCIÓN{RESET}')
        print(f'{GREEN}  Modo       : {RESET}{mode}')
        print(f'{GREEN}  Sede       : {RESET}{sede or "[default]"}')
        print(f'{GREEN}  Estado     : {RESET}{estado or "[todos]"}')
        print(f'{GREEN}  Export     : {RESET}{export_label}')
        print(f'{GREEN}  Output     : {RESET}{self.output_dir}')
        print(f'{GREEN}  Logs       : {RESET}{self.log_dir}')
        if contract_url:
            print(f'{GREEN}  Contract   : {RESET}{contract_url}')
        print(border)

    def _print_contract_result(self, url: str, estado: str, sede: str, success: bool, error: str = '') -> None:
        label = f'{GREEN}OK{RESET}' if success else f'{RED}ERROR{RESET}'
        location = f' [{sede}]' if sede else ''
        msg = f'[{label}] {url}{location} (estado={estado})'
        if error:
            msg += f' - {error}'
        print(msg)

    async def check_server_online(self, url: Optional[str] = None) -> bool:
        target = url or self.base_url
        if not target:
            print('[WARN] Check-server omitido: no hay URL de sitio definida aún.')
            return False
        try:
            page = await self.browser_manager.new_page()
            await page.goto(target, timeout=PAGE_NAVIGATION_TIMEOUT, wait_until='domcontentloaded')
            await self._wait_for_page_ready(page)
            print(f'[OK] Servidor online: {target}')
            await page.close()
            return True
        except Exception as exc:
            print(f'[WARN] Servidor no responde: {target} ({exc})')
            return False


# ── función main (punto de entrada programático) ──────────────────────────────

async def main(
    mode: str = MODO,
    headless: bool = HEADLESS,
    timing_factor: float = TIMING_FACTOR,
    log_dir: str = LOG_DIR,
    output_dir: str = OUTPUT_DIR,
    contract_url: str = '',
    estado: str = '',
    sede: str = '',
    export_csv: Optional[bool] = None,
    export_xlsx: Optional[bool] = None,
    check_server: bool = False,
    limit: int = 0,
) -> None:
    print('WORLD CLASS SCRAPER - Extracción de Contratos')

    if export_csv is None and export_xlsx is None:
        export_csv = EXPORT_CSV
        export_xlsx = EXPORT_XLSX
    else:
        export_csv = bool(export_csv)
        export_xlsx = bool(export_xlsx)

    summary_logger = ScraperLogger(log_dir)
    summary_logger.summary(
        f'START | modo={mode} | contract_url={contract_url}'
        f' | export_csv={export_csv} | export_xlsx={export_xlsx}'
        f' | limit={limit if limit else "todos"}'
    )

    scraper = AsyncWorldClassScraper(
        base_url='',
        email=EMAIL,
        password=PASSWORD,
        headless=headless,
        timing_factor=timing_factor,
        log_dir=log_dir,
        output_dir=output_dir,
    )
    scraper.print_dashboard(mode, contract_url, estado, sede, export_csv, export_xlsx)
    await scraper.start()

    if check_server:
        sitio_cfg = next((s for s in SITIOS if s['nombre'] == mode), None)
        if sitio_cfg:
            scraper.base_url = sitio_cfg['base_url']
            if not await scraper.check_server_online(scraper.base_url):
                print('[WARN] El servidor no respondió, el scraper intentará continuar de todas formas.')
        else:
            print('[WARN] Check-server omitido: modo no encontrado en SITIOS.')
    else:
        print('[INFO] Check-server deshabilitado, iniciando sin verificación de servidor.')

    datos_globales: List[Dict[str, Any]] = []

    try:
        if contract_url:
            sitio_cfg = next((s for s in SITIOS if s['nombre'] == mode), None)
            if sitio_cfg is None:
                print(f"✗ Sitio '{mode}' no encontrado en SITIOS. Verifica config.py.")
                return

            scraper.current_site = sitio_cfg['nombre']
            scraper.base_url = sitio_cfg['base_url']
            print(f'=== {scraper.current_site.upper()} (URL directa) ===')
            print('[PASO 1] Login...')
            if not await scraper.login():
                scraper.logger.error(f'sitio={scraper.current_site} | motivo=login fallido')
                return

            effective_sede = sede or sitio_cfg['filtros'].get('sede', '')
            detail = await scraper.extract_contract_page(contract_url, estado, effective_sede)
            if detail:
                datos_globales.append(detail)
                await scraper.export_site_reports(
                    sitio_cfg, mode=mode, sede_override=effective_sede,
                    rows=datos_globales, export_csv=export_csv, export_xlsx=export_xlsx,
                )
            else:
                print('✗ No se extrajeron datos del contrato directo.')
            return

        sitios_a_procesar = (
            SITIOS if mode == 'todos' else [s for s in SITIOS if s['nombre'] == mode]
        )
        if not sitios_a_procesar:
            print(f"✗ Sitio '{mode}' no encontrado en SITIOS. Verifica config.py.")
            return

        for sitio_cfg in sitios_a_procesar:
            scraper.current_site = sitio_cfg['nombre']
            scraper.base_url = sitio_cfg['base_url']
            scraper.concurrency_ctrl.site_name = sitio_cfg['nombre']
            print(f'=== {scraper.current_site.upper()} ===')
            print('[PASO 1] Login...')
            if not await scraper.login():
                scraper.logger.error(f'sitio={scraper.current_site} | motivo=login fallido')
                continue

            site_filters = sitio_cfg['filtros'].copy()
            if sede:
                site_filters['sede'] = sede

            estados_a_procesar = [estado] if estado else site_filters.get('estados', sitio_cfg.get('estados', []))

            for estado_item in estados_a_procesar:
                print(f'→ Estado: {estado_item}')
                await scraper.process_state(estado_item, site_filters, limit=limit)

            datos_globales.extend(scraper.results)

            if scraper.results:
                await scraper.export_site_reports(
                    sitio_cfg, mode=mode,
                    sede_override=site_filters.get('sede', ''),
                    export_csv=export_csv, export_xlsx=export_xlsx,
                )

        if mode == 'todos' and datos_globales:
            saved = await scraper.export_orchestrator.export_combined(
                rows=datos_globales,
                mode=mode,
                filename=EXCEL_COMBINADO_FILENAME,
                export_csv=export_csv,
                export_xlsx=export_xlsx and EXCEL_COMBINADO,
            )
            if saved:
                summary_logger.summary(f"combined_exports={' '.join(saved)} | registros={len(datos_globales)}")

    finally:
        await scraper.stop()
        summary_logger.summary(
            f"END | modo={mode} | extraidos={scraper.stats['extracted']}"
            f" | errores={scraper.stats['errors']} | skips={scraper.stats['skips']}"
        )
        export_label = (
            'CSV + XLSX' if export_csv and export_xlsx
            else 'CSV' if export_csv
            else 'XLSX' if export_xlsx
            else '[ninguno]'
        )
        print('=' * 62)
        print('EJECUCIÓN FINALIZADA')
        print(f"  Modo      : {mode}")
        print(f"  Extraídos : {scraper.stats['extracted']}")
        print(f"  Errores   : {scraper.stats['errors']}")
        print(f"  Skips     : {scraper.stats['skips']}")
        print(f"  Export    : {export_label}")
        print(f"  Output    : {scraper.output_dir}")
        print(f"  Logs      : {scraper.log_dir}")
        print('=' * 62)
