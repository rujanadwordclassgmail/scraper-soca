"""Análisis post-ejecución de logs del scraper.

Lee los archivos de log generados por ScraperLogger y produce un resumen
estructurado con conteos por categoría de evento.

Categorías reconocidas (basadas en el formato real de logs):
  - retry_goto        : reintentos de navegación  (retry_goto=N/M)
  - retry_extract     : reintentos de extracción  (retry_extract=N/M)
  - extract_failed    : fallo final de extracción (extract_failed=)
  - timeout_extract   : timeout por contrato       (timeout_extract=Ns)
  - context_closed    : contexto Playwright cerrado (context_closed_detected | TargetClosedError)
  - concurrency_reduced  : reducción adaptativa de concurrencia (auto_reduce_concurrency)
  - concurrency_recovered: recuperación adaptativa  (auto_recovery_concurrency)
  - new_page_failed   : fallo al crear nueva página (new_page_failed=)
  - other_errors      : cualquier otra línea de ERROR no clasificada
"""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List


# ── tipos ──────────────────────────────────────────────────────────────────────

LogSummary = Dict[str, int]
AuditReport = Dict[str, LogSummary]


# ── lectura ────────────────────────────────────────────────────────────────────

def read_log(path: Path) -> List[str]:
    """Lee un archivo de log y devuelve sus líneas. Retorna [] si no existe."""
    if not path.exists():
        return []
    return path.read_text(encoding='utf-8').splitlines()


# ── clasificación ──────────────────────────────────────────────────────────────

# Orden importa: se aplica el primer patrón que coincida.
_PATTERNS: list[tuple[str, str]] = [
    ('retry_goto',            r'retry_goto=\d+/\d+'),
    ('retry_extract',         r'retry_extract=\d+/\d+'),
    ('extract_failed',        r'extract_failed='),
    ('timeout_extract',       r'timeout_extract=\d+s'),
    ('context_closed',        r'context_closed_detected|TargetClosedError'),
    ('concurrency_reduced',   r'auto_reduce_concurrency'),
    ('concurrency_recovered', r'auto_recovery_concurrency'),
    ('new_page_failed',       r'new_page_failed='),
]

_COMPILED = [(key, re.compile(pattern)) for key, pattern in _PATTERNS]


def classify_line(line: str) -> str | None:
    """Clasifica una línea de log y retorna la categoría, o None si no aplica.

    Solo procesa líneas que sean ERROR o SUMMARY relevantes.
    """
    is_error   = 'ERROR |' in line
    is_summary = 'SUMMARY |' in line and any(
        kw in line for kw in ('auto_reduce', 'auto_recovery', 'recreated_browser')
    )

    if not (is_error or is_summary):
        return None

    for key, pattern in _COMPILED:
        if pattern.search(line):
            return key

    # cualquier otra línea ERROR no clasificada
    if is_error:
        return 'other_errors'

    return None


def summarize_log(lines: List[str]) -> LogSummary:
    """Cuenta eventos por categoría en una lista de líneas de log."""
    counts: LogSummary = defaultdict(int)
    for line in lines:
        category = classify_line(line)
        if category:
            counts[category] += 1
    return dict(counts)


# ── API pública ────────────────────────────────────────────────────────────────

def audit_logs(log_dir: str) -> AuditReport:
    """Lee errors.log y run_summary.log de log_dir y devuelve un reporte completo.

    Ejemplo de salida::

        {
          'errors': {
              'retry_goto': 12,
              'retry_extract': 8,
              'timeout_extract': 45,
              'context_closed': 3,
              'extract_failed': 2,
              'other_errors': 1,
          },
          'run_summary': {
              'concurrency_reduced': 4,
              'concurrency_recovered': 2,
          },
          'totals': {
              'total_errors': 71,
              'total_retries': 20,
          }
        }
    """
    base = Path(log_dir)
    error_counts   = summarize_log(read_log(base / 'errors.log'))
    summary_counts = summarize_log(read_log(base / 'run_summary.log'))

    total_errors  = sum(error_counts.values())
    total_retries = (
        error_counts.get('retry_goto', 0)
        + error_counts.get('retry_extract', 0)
    )

    return {
        'errors':      error_counts,
        'run_summary': summary_counts,
        'totals': {
            'total_errors':  total_errors,
            'total_retries': total_retries,
        },
    }


def format_report(report: AuditReport) -> str:
    """Formatea un AuditReport como texto legible para CLI o logging."""
    lines: List[str] = ['=== AUDIT REPORT ===']

    for section, counts in report.items():
        if not counts:
            continue
        lines.append(f'\n[{section.upper()}]')
        for key, value in sorted(counts.items(), key=lambda x: -x[1]):
            lines.append(f'  {key:<28}: {value}')

    return '\n'.join(lines)
