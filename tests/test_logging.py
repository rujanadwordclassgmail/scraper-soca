import os
import tempfile
import unittest

from scraper import WorldClassScraper


class LoggingTests(unittest.TestCase):
    def test_write_log_line_creates_file_and_writes_message(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            scraper = WorldClassScraper("https://example.com", "user", "pass", log_dir=tmpdir)
            scraper._write_log_line("errors.log", "hello world")

            log_path = os.path.join(tmpdir, "errors.log")
            self.assertTrue(os.path.exists(log_path))
            with open(log_path, "r", encoding="utf-8") as fh:
                content = fh.read()
            self.assertIn("hello world", content)


if __name__ == "__main__":
    unittest.main()
