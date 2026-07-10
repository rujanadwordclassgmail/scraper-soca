import importlib
import os

from worldclass_scraper.config import ENV_FILE


def test_env_file_path_is_defined():
    assert ENV_FILE == '.env'


def test_site_credentials_are_loaded_from_environment():
    os.environ['WORLDCLASS_EMAIL'] = 'worldclass@example.com'
    os.environ['WORLDCLASS_PASSWORD'] = 'worldclass-pass'
    os.environ['DISCOVERY_EMAIL'] = 'discovery@example.com'
    os.environ['DISCOVERY_PASSWORD'] = 'discovery-pass'

    import worldclass_scraper.config as config
    config = importlib.reload(config)

    assert config.SITIOS[0]['email'] == 'worldclass@example.com'
    assert config.SITIOS[0]['password'] == 'worldclass-pass'
    assert config.SITIOS[1]['email'] == 'discovery@example.com'
    assert config.SITIOS[1]['password'] == 'discovery-pass'


def test_src_package_can_be_imported():
    module = importlib.import_module('worldclass_scraper.config')
    assert hasattr(module, 'ENV_FILE')


