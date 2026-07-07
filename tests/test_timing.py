import unittest

from scraper import WorldClassScraper
from config import TIMING_FACTOR


class TimingTests(unittest.TestCase):
    def test_calculate_delay_uses_timing_factor(self):
        scraper = WorldClassScraper("https://example.com", "user", "pass")
        self.assertEqual(scraper._calculate_delay(1.0), 1.0 * TIMING_FACTOR)

    def test_calculate_delay_never_negative(self):
        scraper = WorldClassScraper("https://example.com", "user", "pass")
        self.assertEqual(scraper._calculate_delay(-0.5), 0.0)


if __name__ == "__main__":
    unittest.main()
