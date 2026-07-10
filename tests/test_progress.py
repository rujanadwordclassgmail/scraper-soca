"""Tests para worldclass_scraper.modules.progress — ProgressRenderer."""
import pytest
from worldclass_scraper.modules.progress import ProgressRenderer


def test_render_returns_empty_when_total_zero():
    r = ProgressRenderer()
    assert r.render(0, 0) == ''


def test_render_returns_empty_when_total_negative():
    r = ProgressRenderer()
    assert r.render(5, -1) == ''


def test_render_0_percent():
    r = ProgressRenderer(width=10)
    result = r.render(0, 100)
    # 0% → 0 bloques rellenos, 10 espacios
    assert '  0%' in result
    assert '█' not in result.replace('\033[32m', '').replace('\033[0m', '')


def test_render_100_percent():
    r = ProgressRenderer(width=10)
    result = r.render(100, 100)
    assert '100%' in result


def test_render_50_percent_has_filled_and_empty():
    r = ProgressRenderer(width=10)
    result = r.render(50, 100)
    assert ' 50%' in result
    # debe contener tanto bloques como espacios en la parte de la barra
    # quitamos los códigos ANSI para contar caracteres visibles
    import re
    clean = re.sub(r'\033\[[0-9;]+m', '', result)
    assert '█' in clean
    assert ' ' in clean


def test_render_current_exceeds_total_clamps_to_100():
    r = ProgressRenderer(width=10)
    result = r.render(200, 100)
    assert '100%' in result


def test_render_width_respected():
    width = 20
    r = ProgressRenderer(width=width)
    result = r.render(50, 100)
    import re
    clean = re.sub(r'\033\[[0-9;]+m', '', result)
    # la barra está entre '[' y ']'
    bar_content = clean[clean.index('[') + 1: clean.index(']')]
    assert len(bar_content) == width


def test_print_final_writes_to_stdout(capsys):
    r = ProgressRenderer(width=10)
    r.print_final(42, 100)
    captured = capsys.readouterr()
    assert 'Procesados: 42/100' in captured.out
