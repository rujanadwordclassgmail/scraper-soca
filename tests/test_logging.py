import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from worldclass_scraper.modules.logging import ScraperLogger


def test_write_log_line_creates_file_and_writes_message():
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = ScraperLogger(tmpdir)
        logger.write("errors.log", "hello world")

        log_path = os.path.join(tmpdir, "errors.log")
        assert os.path.exists(log_path)
        with open(log_path, "r", encoding="utf-8") as fh:
            content = fh.read()
        assert "hello world" in content
