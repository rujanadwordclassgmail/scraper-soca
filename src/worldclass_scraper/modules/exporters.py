"""Exportación de resultados a Excel y CSV.

Contiene:
  - AbstractExporter: contrato de exportación (DIP — el scraper depende de esto,
    no de una implementación concreta).
  - ExcelExporter: implementación pandas/openpyxl.
  - ExportOrchestrator: coordina exportaciones parciales, por sede y combinadas.

Responsabilidades de este módulo:
  - Serializar filas de datos a archivos.
  - Agrupar filas por sede/estado para generar rutas de archivo.
  - Nada de Playwright, nada de lógica de negocio.
"""
from __future__ import annotations

import asyncio
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from worldclass_scraper.modules.utils import slugify


# ── Interfaz ─────────────────────────────────────────────────────────────────

class AbstractExporter(ABC):
    """Contrato mínimo que debe cumplir cualquier exportador."""

    @abstractmethod
    def export(
        self,
        rows: List[Dict[str, Any]],
        filepath: str,
        sheet_names: Optional[List[str]] = None,
        sheet_field: str = 'Estado_Contrato',
    ) -> str:
        """Exporta rows a filepath. Retorna la ruta final escrita."""

    @abstractmethod
    def export_csv(self, rows: List[Dict[str, Any]], filepath: str) -> str:
        """Exporta rows como CSV a filepath. Retorna la ruta final escrita."""


# ── Implementación concreta ───────────────────────────────────────────────────

class ExcelExporter(AbstractExporter):
    """Exporta a Excel (.xlsx) con hoja por estado + hoja 'combined', o CSV."""

    MAX_CELL_LENGTH = 32767

    def __init__(self, output_dir: str = 'output') -> None:
        self.output_dir = output_dir

    # ── AbstractExporter ────────────────────────────────────────────────────

    def export(
        self,
        rows: List[Dict[str, Any]],
        filepath: str,
        sheet_names: Optional[List[str]] = None,
        sheet_field: str = 'Estado_Contrato',
    ) -> str:
        df = pd.DataFrame(rows)
        output_path = self._resolve_path(filepath)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if not sheet_names:
            df = self._truncate_dataframe(df if not df.empty else pd.DataFrame([{}]))
            df.to_excel(output_path, index=False)
            return output_path

        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            for sheet in sheet_names:
                group = df[df[sheet_field] == sheet].copy() if sheet_field in df.columns else pd.DataFrame(columns=df.columns)
                self._truncate_dataframe(group).to_excel(
                    writer, sheet_name=self._sanitize_sheet_name(sheet), index=False
                )
            self._truncate_dataframe(df.copy()).to_excel(writer, sheet_name='combined', index=False)

        return output_path

    def export_csv(self, rows: List[Dict[str, Any]], filepath: str) -> str:
        df = pd.DataFrame(rows)
        output_path = self._resolve_path(filepath)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        return output_path

    # ── privados ─────────────────────────────────────────────────────────────

    def _resolve_path(self, filepath: str) -> str:
        if os.path.isabs(filepath) or os.path.dirname(filepath):
            return filepath
        return os.path.join(self.output_dir, filepath)

    @staticmethod
    def _sanitize_sheet_name(name: str) -> str:
        sanitized = str(name).strip()
        for ch in ['\\', '/', '*', '?', ':', '[', ']']:
            sanitized = sanitized.replace(ch, '')
        return sanitized[:31] or 'sheet'

    def _truncate_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        for col in df.select_dtypes(include='str').columns:
            df[col] = df[col].apply(self._truncate_value)
        return df

    @classmethod
    def _truncate_value(cls, value: Any) -> Any:
        if isinstance(value, str) and len(value) > cls.MAX_CELL_LENGTH:
            return value[: cls.MAX_CELL_LENGTH - 3] + '...'
        return value


# ── Orquestador de exportaciones ──────────────────────────────────────────────

class ExportOrchestrator:
    """Coordina exportaciones parciales, por sede/estado y combinadas.

    Desacopla al scraper de toda decisión sobre dónde y cómo escribir archivos.
    """

    def __init__(
        self,
        exporter: AbstractExporter,
        output_dir: str,
        logger=None,
        partial_export: bool = False,
        partial_format: str = 'csv',
        save_every: int = 0,
    ) -> None:
        self.exporter = exporter
        self.output_dir = output_dir
        self._logger = logger
        self.partial_export = partial_export
        self.partial_format = partial_format if partial_format in ('csv', 'xlsx') else 'csv'
        self.save_every = save_every

    # ── exportación parcial (checkpoints) ────────────────────────────────────

    async def export_partial(self, rows: List[Dict[str, Any]], prefix: str) -> None:
        """Guarda un checkpoint si `partial_export` está activo."""
        if not self.partial_export or not self.save_every or not rows:
            return
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        stem = f'partial_{prefix}_{len(rows)}_{ts}'
        if self.partial_format == 'csv':
            path = os.path.join(self.output_dir, f'{stem}.csv')
            await asyncio.to_thread(self.exporter.export_csv, rows, path)
            self._log(f'partial_csv_saved={path} | registros={len(rows)}')
        else:
            path = os.path.join(self.output_dir, f'{stem}.xlsx')
            await asyncio.to_thread(self.exporter.export, rows, path)
            self._log(f'partial_xlsx_saved={path} | registros={len(rows)}')

    # ── exportación por sede/estado ───────────────────────────────────────────

    async def export_site_reports(
        self,
        sitio: Dict[str, Any],
        rows: List[Dict[str, Any]],
        mode: str,
        sede_override: str = '',
        export_csv: bool = True,
        export_xlsx: bool = False,
    ) -> None:
        """Agrupa rows por (Sede, Estado) y escribe un archivo por grupo."""
        if not rows:
            return

        groups: Dict[tuple, List[Dict[str, Any]]] = {}
        for row in rows:
            sede = row.get('Sede') or sede_override or sitio.get('filtros', {}).get('sede', '') or 'SIN_SEDE'
            estado = row.get('Estado_Contrato') or 'NO_ESTADO'
            groups.setdefault((sede, estado), []).append(row)

        date_suffix = datetime.now().strftime('%Y%m%d')
        template = sitio.get('excel_template', 'contratos_{SEDE}_{ESTADO}.xlsx')
        sheet_names = sitio.get('sheet_names')

        for (sede_name, estado_name), group_rows in groups.items():
            sede_slug = slugify(sede_name)
            estado_slug = slugify(estado_name)
            reports_dir = os.path.join(self.output_dir, mode, sede_slug, 'reports')
            os.makedirs(reports_dir, exist_ok=True)

            base = template.replace('{SEDE}', sede_slug)
            base = base.replace('{ESTADO}', estado_slug) if '{ESTADO}' in base else (
                os.path.splitext(base)[0] + f'_{estado_slug}.xlsx'
            )
            stem = os.path.splitext(base)[0]
            saved: List[str] = []

            if export_csv:
                path = os.path.join(reports_dir, f'{stem}_{date_suffix}.csv')
                await asyncio.to_thread(self.exporter.export_csv, group_rows, path)
                saved.append(f'csv_saved={path}')

            if export_xlsx:
                path = os.path.join(reports_dir, f'{stem}_{date_suffix}.xlsx')
                await asyncio.to_thread(self.exporter.export, group_rows, path, sheet_names, 'Estado_Contrato')
                saved.append(f'xlsx_saved={path}')

            self._log(
                f"report_saved={' '.join(saved)} | sitio={sitio.get('nombre')}"
                f' | sede={sede_name} | estado={estado_name} | registros={len(group_rows)}'
            )

    # ── exportación combinada ────────────────────────────────────────────────

    async def export_combined(
        self,
        rows: List[Dict[str, Any]],
        mode: str,
        filename: str,
        export_csv: bool = True,
        export_xlsx: bool = False,
    ) -> List[str]:
        """Escribe el archivo combinado de todos los sitios bajo output/<mode>/reports/."""
        if not rows:
            return []

        reports_dir = os.path.join(self.output_dir, mode, 'reports')
        os.makedirs(reports_dir, exist_ok=True)
        saved: List[str] = []

        if export_csv:
            csv_name = filename.replace('.xlsx', '.csv')
            path = os.path.join(reports_dir, csv_name)
            await asyncio.to_thread(self.exporter.export_csv, rows, path)
            saved.append(path)
            print(f'✓ CSV combinado guardado: {path}')

        if export_xlsx:
            path = os.path.join(reports_dir, filename)
            await asyncio.to_thread(self.exporter.export, rows, path)
            saved.append(path)
            print(f'✓ Excel combinado guardado: {path}')

        return saved

    # ── privado ──────────────────────────────────────────────────────────────

    def _log(self, message: str) -> None:
        if self._logger:
            self._logger.summary(message)
