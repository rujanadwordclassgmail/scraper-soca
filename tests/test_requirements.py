import os
import re
import unittest


class RequirementsTests(unittest.TestCase):
    def test_required_packages_are_declared(self):
        root = os.path.dirname(os.path.dirname(__file__))
        requirements_path = os.path.join(root, 'requirements.txt')

        self.assertTrue(os.path.exists(requirements_path), 'requirements.txt no encontrado')

        with open(requirements_path, 'r', encoding='utf-8') as fh:
            content = fh.read().lower()

        required_packages = ['playwright', 'pandas', 'openpyxl', 'beautifulsoup4']
        for package in required_packages:
            self.assertTrue(
                any(re.match(rf'^{re.escape(package)}([<>=!~].*)?$', line.strip()) for line in content.splitlines()),
                f'El paquete {package} no está declarado en requirements.txt'
            )


if __name__ == '__main__':
    unittest.main()
