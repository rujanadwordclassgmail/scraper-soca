import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from worldclass_scraper.config import TIMING_FACTOR
from worldclass_scraper.scraper import AsyncWorldClassScraper


def test_calculate_delay_uses_timing_factor():
    scraper = AsyncWorldClassScraper("https://example.com", "user", "pass", timing_factor=TIMING_FACTOR)
    assert scraper._calculate_delay(1.0) == 1.0 * TIMING_FACTOR


def test_calculate_delay_never_negative():
    scraper = AsyncWorldClassScraper("https://example.com", "user", "pass", timing_factor=TIMING_FACTOR)
    assert scraper._calculate_delay(-0.5) == 0.0
