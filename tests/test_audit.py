"""Tests para worldclass_scraper.modules.audit."""
import pytest
from pathlib import Path

from worldclass_scraper.modules.audit import (
    read_log,
    classify_line,
    summarize_log,
    audit_logs,
    format_report,
)


# ── fixtures con líneas reales de los logs ────────────────────────────────────

ERRORS_LOG_LINES = [
    "[2026-07-09 20:08:08] ERROR | retry_goto=1/3 | url=https://example.com/1205 | mensaje=Page.goto: Timeout",
    "[2026-07-09 20:08:08] ERROR | retry_goto=1/3 | url=https://example.com/1132 | mensaje=Page.goto: Target page, context or browser has been closed",
    "[2026-07-09 20:08:09] ERROR | retry_extract=1/2 | sitio=worldclass | estado=GASTO LEGAL | url=https://example.com/1176 | mensaje=Locator.text_content: Target page",
    "[2026-07-09 20:22:35] ERROR | extract_failed=worldclass | estado=GASTO LEGAL | url=https://example.com/1891 | mensaje=Locator.text_content: Target page",
    "[2026-07-09 20:22:45] ERROR | timeout_extract=120s | sitio=worldclass | estado=GASTO LEGAL | url=https://example.com/1876",
    "[2026-07-09 20:22:45] ERROR | timeout_extract=120s | sitio=worldclass | estado=GASTO LEGAL | url=https://example.com/1798",
    "[2026-07-09 21:45:18] ERROR | context_closed_detected | attempting_recreate | url=https://example.com/2292",
    "[2026-07-09 21:45:18] ERROR | new_page_failed=BrowserContext.new_page: Protocol error | recreating browser context",
    "[2026-07-09 21:45:18] ERROR | new_page_failed=BrowserContext.new_page: Protocol error | recreating browser context",
    "[2026-07-09 21:46:12] ERROR | recovery_failed=Locator.text_content: Target page | url=https://example.com/2292",
]

SUMMARY_LOG_LINES = [
    "[2026-07-09 21:00:01] SUMMARY | auto_recovery_concurrency from=3 to=4 | stable_streak=20 | sitio=worldclass",
    "[2026-07-09 21:00:41] SUMMARY | auto_reduce_concurrency from=4 to=3 | sitio=worldclass",
    "[2026-07-09 21:00:41] SUMMARY | auto_reduce_concurrency from=3 to=2 | sitio=worldclass",
    "[2026-07-09 21:00:41] SUMMARY | auto_reduce_concurrency from=2 to=1 | sitio=worldclass",
    "[2026-07-09 21:00:41] SUMMARY | report_saved=csv_saved=output/... | registros=17",
    "[2026-07-09 21:00:42] SUMMARY | END | modo=worldclass | extraidos=17 | errores=95 | skips=0",
    "[2026-07-09 21:27:37] SUMMARY | recreated_browser_context_due_errors | sitio=worldclass",
]


# ── read_log ──────────────────────────────────────────────────────────────────

def test_read_log_returns_empty_for_missing_file(tmp_path):
    result = read_log(tmp_path / 'nonexistent.log')
    assert result == []


def test_read_log_returns_lines(tmp_path):
    log_file = tmp_path / 'test.log'
    log_file.write_text('line1\nline2\nline3', encoding='utf-8')
    result = read_log(log_file)
    assert result == ['line1', 'line2', 'line3']


def test_read_log_handles_empty_file(tmp_path):
    log_file = tmp_path / 'empty.log'
    log_file.write_text('', encoding='utf-8')
    result = read_log(log_file)
    assert result == []


# ── classify_line ─────────────────────────────────────────────────────────────

class TestClassifyLine:
    def test_retry_goto(self):
        line = "[2026-07-09] ERROR | retry_goto=1/3 | url=https://example.com"
        assert classify_line(line) == 'retry_goto'

    def test_retry_goto_second_attempt(self):
        line = "[2026-07-09] ERROR | retry_goto=2/3 | url=https://example.com"
        assert classify_line(line) == 'retry_goto'

    def test_retry_extract(self):
        line = "[2026-07-09] ERROR | retry_extract=1/2 | sitio=worldclass | url=https://example.com"
        assert classify_line(line) == 'retry_extract'

    def test_extract_failed(self):
        line = "[2026-07-09] ERROR | extract_failed=worldclass | estado=CASH | url=https://example.com"
        assert classify_line(line) == 'extract_failed'

    def test_timeout_extract(self):
        line = "[2026-07-09] ERROR | timeout_extract=120s | sitio=worldclass | url=https://example.com"
        assert classify_line(line) == 'timeout_extract'

    def test_timeout_extract_different_seconds(self):
        line = "[2026-07-09] ERROR | timeout_extract=225s | sitio=worldclass | url=https://example.com"
        assert classify_line(line) == 'timeout_extract'

    def test_context_closed_detected(self):
        line = "[2026-07-09] ERROR | context_closed_detected | attempting_recreate | url=https://example.com"
        assert classify_line(line) == 'context_closed'

    def test_target_closed_error(self):
        line = "[2026-07-09] ERROR | retry_goto=1/3 | mensaje=TargetClosedError: browser closed"
        assert classify_line(line) == 'retry_goto'  # retry_goto tiene prioridad por estar primero

    def test_new_page_failed(self):
        line = "[2026-07-09] ERROR | new_page_failed=BrowserContext.new_page: Protocol error | recreating"
        assert classify_line(line) == 'new_page_failed'

    def test_concurrency_reduced_in_summary(self):
        line = "[2026-07-09] SUMMARY | auto_reduce_concurrency from=4 to=3 | sitio=worldclass"
        assert classify_line(line) == 'concurrency_reduced'

    def test_concurrency_recovered_in_summary(self):
        line = "[2026-07-09] SUMMARY | auto_recovery_concurrency from=3 to=4 | stable_streak=20"
        assert classify_line(line) == 'concurrency_recovered'

    def test_other_error_unclassified(self):
        line = "[2026-07-09] ERROR | recovery_failed=some weird error | url=https://example.com"
        assert classify_line(line) == 'other_errors'

    def test_regular_summary_line_ignored(self):
        line = "[2026-07-09] SUMMARY | END | modo=worldclass | extraidos=17 | errores=95 | skips=0"
        assert classify_line(line) is None

    def test_report_saved_line_ignored(self):
        line = "[2026-07-09] SUMMARY | report_saved=csv_saved=output/... | registros=17"
        assert classify_line(line) is None

    def test_non_log_line_ignored(self):
        assert classify_line("just some random text") is None

    def test_empty_line_ignored(self):
        assert classify_line("") is None


# ── summarize_log ─────────────────────────────────────────────────────────────

class TestSummarizeLog:
    def test_counts_retry_goto_correctly(self):
        result = summarize_log(ERRORS_LOG_LINES)
        assert result.get('retry_goto') == 2

    def test_counts_retry_extract_correctly(self):
        result = summarize_log(ERRORS_LOG_LINES)
        assert result.get('retry_extract') == 1

    def test_counts_extract_failed_correctly(self):
        result = summarize_log(ERRORS_LOG_LINES)
        assert result.get('extract_failed') == 1

    def test_counts_timeout_extract_correctly(self):
        result = summarize_log(ERRORS_LOG_LINES)
        assert result.get('timeout_extract') == 2

    def test_counts_context_closed_correctly(self):
        result = summarize_log(ERRORS_LOG_LINES)
        assert result.get('context_closed') == 1

    def test_counts_new_page_failed_correctly(self):
        result = summarize_log(ERRORS_LOG_LINES)
        assert result.get('new_page_failed') == 2

    def test_counts_other_errors(self):
        result = summarize_log(ERRORS_LOG_LINES)
        assert result.get('other_errors') == 1

    def test_empty_lines_returns_empty_dict(self):
        result = summarize_log([])
        assert result == {}

    def test_summary_log_concurrency_events(self):
        result = summarize_log(SUMMARY_LOG_LINES)
        assert result.get('concurrency_reduced') == 3
        assert result.get('concurrency_recovered') == 1

    def test_summary_log_ignores_non_events(self):
        result = summarize_log(SUMMARY_LOG_LINES)
        # report_saved y END no deben aparecer
        assert 'report_saved' not in result
        assert 'end' not in result


# ── audit_logs ────────────────────────────────────────────────────────────────

class TestAuditLogs:
    def _write_logs(self, tmp_path, errors=None, summary=None):
        if errors is not None:
            (tmp_path / 'errors.log').write_text('\n'.join(errors), encoding='utf-8')
        if summary is not None:
            (tmp_path / 'run_summary.log').write_text('\n'.join(summary), encoding='utf-8')

    def test_returns_all_sections(self, tmp_path):
        self._write_logs(tmp_path, errors=ERRORS_LOG_LINES, summary=SUMMARY_LOG_LINES)
        report = audit_logs(str(tmp_path))
        assert 'errors' in report
        assert 'run_summary' in report
        assert 'totals' in report

    def test_totals_sum_all_error_categories(self, tmp_path):
        self._write_logs(tmp_path, errors=ERRORS_LOG_LINES, summary=[])
        report = audit_logs(str(tmp_path))
        # 2 retry_goto + 1 retry_extract + 1 extract_failed + 2 timeout_extract
        # + 1 context_closed + 2 new_page_failed + 1 other_errors = 10
        assert report['totals']['total_errors'] == 10

    def test_totals_retries_is_goto_plus_extract(self, tmp_path):
        self._write_logs(tmp_path, errors=ERRORS_LOG_LINES, summary=[])
        report = audit_logs(str(tmp_path))
        # 2 retry_goto + 1 retry_extract = 3
        assert report['totals']['total_retries'] == 3

    def test_missing_files_return_empty_sections(self, tmp_path):
        report = audit_logs(str(tmp_path))
        assert report['errors'] == {}
        assert report['run_summary'] == {}
        assert report['totals']['total_errors'] == 0

    def test_real_log_patterns_recognized(self, tmp_path):
        """Verifica con líneas exactas tomadas de los logs reales de producción."""
        real_errors = [
            "[2026-07-09 20:08:08] ERROR | retry_goto=1/3 | url=https://worldclass.systemsoca.com/vercontrato/1205 | mensaje=Page.goto: Timeout 40000ms exceeded.",
            "[2026-07-09 20:08:09] ERROR | retry_extract=1/2 | sitio=worldclass | estado=GASTO LEGAL | url=https://worldclass.systemsoca.com/vercontrato/1176 | mensaje=Locator.text_content: Target page, context or browser has been closed",
            "[2026-07-09 20:22:35] ERROR | extract_failed=worldclass | estado=GASTO LEGAL | url=https://worldclass.systemsoca.com/vercontrato/1891 | mensaje=Locator.text_content: Target page, context or browser has been closed",
            "[2026-07-09 20:22:45] ERROR | timeout_extract=120s | sitio=worldclass | estado=GASTO LEGAL | url=https://worldclass.systemsoca.com/vercontrato/1876",
            "[2026-07-09 21:45:18] ERROR | context_closed_detected | attempting_recreate | url=https://worldclass.systemsoca.com/vercontrato/2292",
            "[2026-07-09 21:45:18] ERROR | new_page_failed=BrowserContext.new_page: Protocol error (Target.createTarget): browserContextId | recreating browser context",
        ]
        real_summary = [
            "[2026-07-09 21:00:01] SUMMARY | auto_recovery_concurrency from=3 to=4 | stable_streak=20 | sitio=worldclass",
            "[2026-07-09 21:00:41] SUMMARY | auto_reduce_concurrency from=4 to=3 | sitio=worldclass",
        ]
        self._write_logs(tmp_path, errors=real_errors, summary=real_summary)
        report = audit_logs(str(tmp_path))

        assert report['errors']['retry_goto'] == 1
        assert report['errors']['retry_extract'] == 1
        assert report['errors']['extract_failed'] == 1
        assert report['errors']['timeout_extract'] == 1
        assert report['errors']['context_closed'] == 1
        assert report['errors']['new_page_failed'] == 1
        assert report['run_summary']['concurrency_recovered'] == 1
        assert report['run_summary']['concurrency_reduced'] == 1


# ── format_report ─────────────────────────────────────────────────────────────

class TestFormatReport:
    def test_output_contains_section_headers(self, tmp_path):
        report = {
            'errors': {'retry_goto': 5, 'timeout_extract': 3},
            'run_summary': {'concurrency_reduced': 2},
            'totals': {'total_errors': 8, 'total_retries': 5},
        }
        output = format_report(report)
        assert '[ERRORS]' in output
        assert '[RUN_SUMMARY]' in output
        assert '[TOTALS]' in output

    def test_output_contains_counts(self):
        report = {
            'errors': {'retry_goto': 12},
            'run_summary': {},
            'totals': {'total_errors': 12, 'total_retries': 12},
        }
        output = format_report(report)
        assert 'retry_goto' in output
        assert '12' in output

    def test_empty_sections_omitted(self):
        report = {
            'errors': {},
            'run_summary': {'concurrency_reduced': 1},
            'totals': {'total_errors': 0, 'total_retries': 0},
        }
        output = format_report(report)
        assert '[ERRORS]' not in output
        assert '[RUN_SUMMARY]' in output

    def test_entries_sorted_by_count_descending(self):
        report = {
            'errors': {'timeout_extract': 50, 'retry_goto': 5, 'extract_failed': 1},
            'run_summary': {},
            'totals': {},
        }
        output = format_report(report)
        # timeout_extract (50) debe aparecer antes que retry_goto (5)
        assert output.index('timeout_extract') < output.index('retry_goto')
        assert output.index('retry_goto') < output.index('extract_failed')
