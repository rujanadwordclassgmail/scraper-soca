import os
from datetime import datetime


class ScraperLogger:
    """Ayuda a registrar eventos y errores del scraper en archivos de texto."""

    def __init__(self, log_dir):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)

    def write(self, filename, message):
        path = os.path.join(self.log_dir, filename)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(path, 'a', encoding='utf-8') as fh:
            fh.write(f'[{timestamp}] {message}\n')

    def error(self, message):
        self.write('errors.log', f'ERROR | {message}')

    def skip(self, message):
        self.write('skipped_contracts.log', f'SKIP | {message}')

    def summary(self, message):
        self.write('run_summary.log', f'SUMMARY | {message}')
