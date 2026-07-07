import importlib
import os
import unittest

from config import ENV_FILE


class EnvConfigTests(unittest.TestCase):
    def test_env_file_path_is_defined(self):
        self.assertEqual(ENV_FILE, '.env')

    def test_site_credentials_are_loaded_from_environment(self):
        os.environ['WORLDCLASS_EMAIL'] = 'worldclass@example.com'
        os.environ['WORLDCLASS_PASSWORD'] = 'worldclass-pass'
        os.environ['DISCOVERY_EMAIL'] = 'discovery@example.com'
        os.environ['DISCOVERY_PASSWORD'] = 'discovery-pass'

        import config
        config = importlib.reload(config)

        self.assertEqual(config.SITIOS[0]['email'], 'worldclass@example.com')
        self.assertEqual(config.SITIOS[0]['password'], 'worldclass-pass')
        self.assertEqual(config.SITIOS[1]['email'], 'discovery@example.com')
        self.assertEqual(config.SITIOS[1]['password'], 'discovery-pass')


if __name__ == '__main__':
    unittest.main()
