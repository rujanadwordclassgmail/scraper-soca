import os
import tempfile
import unittest

from scraper import WorldClassScraper


class OutputStructureTests(unittest.TestCase):
    def test_export_to_excel_uses_output_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            scraper = WorldClassScraper('https://example.com', 'user', 'pass', output_dir=tmpdir)
            data = [{'Numero_Contrato': 'WCG123', 'Estado_Contrato': 'PROCE'}]

            scraper.export_to_excel(data, 'contratos.xlsx')

            output_path = os.path.join(tmpdir, 'contratos.xlsx')
            self.assertTrue(os.path.exists(output_path))


if __name__ == '__main__':
    unittest.main()
