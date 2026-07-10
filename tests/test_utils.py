"""Tests para worldclass_scraper.modules.utils — slugify."""
import pytest
from worldclass_scraper.modules.utils import slugify


def test_slugify_empty_string():
    assert slugify('') == 'sin-sede'


def test_slugify_none_equivalent():
    # None no es str pero el contrato dice que si value es falsy devuelve 'sin-sede'
    assert slugify(None) == 'sin-sede'  # type: ignore[arg-type]


def test_slugify_simple_ascii():
    assert slugify('CASH') == 'cash'


def test_slugify_spaces_become_hyphens():
    assert slugify('WCG - GUAYAQUIL') == 'wcg-guayaquil'


def test_slugify_tildes_stripped():
    assert slugify('Separación') == 'separacion'


def test_slugify_multiple_special_chars():
    assert slugify('WC - Santo domingo') == 'wc-santo-domingo'


def test_slugify_double_hyphens_collapsed():
    assert slugify('a--b') == 'a-b'


def test_slugify_leading_trailing_hyphens_stripped():
    assert slugify('--hola--') == 'hola'


def test_slugify_mixed_case_and_accents():
    assert slugify('Gasto Legal') == 'gasto-legal'


def test_slugify_only_special_chars_returns_fallback():
    # todos los caracteres se eliminan → strip('-') devuelve '' → fallback
    assert slugify('---') == 'sin-sede'


def test_slugify_numbers_preserved():
    assert slugify('WCG123') == 'wcg123'


def test_slugify_unicode_non_latin():
    # caracteres chinos no tienen equivalente ASCII → se eliminan → fallback
    result = slugify('北京')
    assert result == 'sin-sede'
