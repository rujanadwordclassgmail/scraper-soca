import os

try:
    from dotenv import load_dotenv
    load_dotenv('.env')
except ImportError:
    pass

def _normalize_list(value, sep=','):
    return [item.strip() for item in str(value).split(sep) if item.strip()]

def _env_bool(name, default=False):
    value = os.getenv(name, str(default))
    return str(value).strip().lower() in ('1', 'true', 'yes', 'on')

def _env_int(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default

def _env_float(name, default):
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default

ENV_FILE = '.env'
WORLDCLASS_EMAIL = os.getenv('WORLDCLASS_EMAIL', '')
WORLDCLASS_PASSWORD = os.getenv('WORLDCLASS_PASSWORD', '')
DISCOVERY_EMAIL = os.getenv('DISCOVERY_EMAIL', '')
DISCOVERY_PASSWORD = os.getenv('DISCOVERY_PASSWORD', '')
WORLDCLASS_BASE_URL = os.getenv('WORLDCLASS_BASE_URL', 'https://worldclass.systemsoca.com')
DISCOVERY_BASE_URL = os.getenv('DISCOVERY_BASE_URL', 'https://discovery.systemsoca.com')
LOGIN_PATH = os.getenv('LOGIN_PATH', '/login')
CONTRATOS_PATH = os.getenv('CONTRATOS_PATH', '/contratos')
WORLDCLASS_SEDE = os.getenv('WORLDCLASS_SEDE', 'WCG - GUAYAQUIL')
WORLDCLASS_FECHA_INICIAL = os.getenv('WORLDCLASS_FECHA_INICIAL', '2023-01-01')
WORLDCLASS_FECHA_FINAL = os.getenv('WORLDCLASS_FECHA_FINAL', '2026-07-08')
DISCOVERY_FECHA_INICIAL = os.getenv('DISCOVERY_FECHA_INICIAL', '2023-01-01')
DISCOVERY_FECHA_FINAL = os.getenv('DISCOVERY_FECHA_FINAL', '2026-07-08')
WORLDCLASS_ESTADOS = _normalize_list(os.getenv('WORLDCLASS_ESTADOS', 'CASH,PROCE,CERO,GASTO LEGAL,SEPARACION,PEDDING'))
WORLDCLASS_SEDES = _normalize_list(os.getenv('WORLDCLASS_SEDES', 'WC - Santo domingo,WC- - Guayaquil,WCG - GUAYAQUIL,WN - worldclass norte,OCN - NASELLORIL,WCS - OCT HOTELS,WCQ - Los cuates,WCU - RESTAURANTE'))
WORLDCLASS_SEDE = os.getenv('WORLDCLASS_SEDE', 'WCG - GUAYAQUIL')
DISCOVERY_ESTADOS = _normalize_list(os.getenv('DISCOVERY_ESTADOS', 'CASH,PROCE,CERO,GASTO LEGAL,SEPARACION,PEDDING'))
DISCOVERY_SEDES = _normalize_list(os.getenv('DISCOVERY_SEDES', 'DC - Moreria,PR - PRUEBA,PPR - RAPIVISA'))

SELECTOR_EMAIL = os.getenv('SELECTOR_EMAIL', 'input[type="email"], input#email')
SELECTOR_PASSWORD = os.getenv('SELECTOR_PASSWORD', 'input[type="password"], input#password')
SELECTOR_SUBMIT = os.getenv('SELECTOR_SUBMIT', 'button[type="submit"], input[type="submit"]')
SELECTOR_SEDE = os.getenv('SELECTOR_SEDE', 'select#bus_sede')
SELECTOR_FECHA_INICIAL = os.getenv('SELECTOR_FECHA_INICIAL', 'input#bus_f1')
SELECTOR_FECHA_FINAL = os.getenv('SELECTOR_FECHA_FINAL', 'input#bus_f2')
SELECTOR_ESTADO = os.getenv('SELECTOR_ESTADO', 'select#bus_estado')
SELECTOR_BUSCAR = os.getenv('SELECTOR_BUSCAR', 'button[onclick*="buscarXcs"]')
SELECTOR_CONTRATO_LINK = os.getenv('SELECTOR_CONTRATO_LINK', 'a[href*="/vercontrato/"]')

PAGE_NAVIGATION_TIMEOUT = _env_int('PAGE_NAVIGATION_TIMEOUT', 60000)
PAGE_ACTION_TIMEOUT = _env_int('PAGE_ACTION_TIMEOUT', 30000)
PAGE_READY_STATE_TIMEOUT = _env_int('PAGE_READY_STATE_TIMEOUT', 15000)
RETRY_BASE_DELAY = _env_float('RETRY_BASE_DELAY', 2.0)
RETRY_MAX_DELAY = _env_float('RETRY_MAX_DELAY', 30.0)
RETRY_JITTER = _env_float('RETRY_JITTER', 0.25)

LOG_DIR = os.getenv('LOG_DIR', 'logs')
OUTPUT_DIR = os.getenv('OUTPUT_DIR', 'output')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
SAVE_FAILED_ROWS = _env_bool('SAVE_FAILED_ROWS', True)
TIMING_FACTOR = _env_float('TIMING_FACTOR', 1.0)
SAVE_EVERY = _env_int('SAVE_EVERY', 50)
MAX_RETRIES = _env_int('MAX_RETRIES', 2)
CONCURRENCY = _env_int('CONCURRENCY', 2)
HEADLESS = _env_bool('HEADLESS', True)
DEBUG = _env_bool('DEBUG', False)
MODO = os.getenv('MODO', 'todos')
EXPORT_CSV = _env_bool('EXPORT_CSV', True)
EXPORT_XLSX = _env_bool('EXPORT_XLSX', False)
PARTIAL_EXPORT = _env_bool('PARTIAL_EXPORT', False)
PARTIAL_FORMAT = os.getenv('PARTIAL_FORMAT', 'csv').strip().lower()
EXCEL_COMBINADO = _env_bool('EXCEL_COMBINADO', True)
EXCEL_COMBINADO_FILENAME = os.getenv('EXCEL_COMBINADO_FILENAME', 'contratos_todos.xlsx')

# Auto-adaptive runtime controls for instability handling
AUTO_REDUCE_ON_ERRORS = _env_bool('AUTO_REDUCE_ON_ERRORS', True)
ERROR_THRESHOLD = _env_int('ERROR_THRESHOLD', 10)
MIN_CONCURRENCY = _env_int('MIN_CONCURRENCY', 1)
CONCURRENCY_REDUCTION_STEP = _env_int('CONCURRENCY_REDUCTION_STEP', 1)

# Dynamic backoff recovery: gradually increase concurrency when stable
AUTO_RECOVERY = _env_bool('AUTO_RECOVERY', True)
STABLE_THRESHOLD = _env_int('STABLE_THRESHOLD', 20)
RECOVERY_STEP = _env_int('RECOVERY_STEP', 1)
MAX_CONCURRENCY = _env_int('MAX_CONCURRENCY', 8)

EMAIL = WORLDCLASS_EMAIL
PASSWORD = WORLDCLASS_PASSWORD

SITIOS = [
    {
        'nombre': 'worldclass',
        'base_url': WORLDCLASS_BASE_URL,
        'email': EMAIL,
        'password': PASSWORD,
        'excel_template': 'contratos_worldclass_{SEDE}_{ESTADO}.xlsx',
        'sheet_names': WORLDCLASS_ESTADOS,
        'estados': WORLDCLASS_ESTADOS,
        'sedes': WORLDCLASS_SEDES,
        'filtros': {
            'sede': WORLDCLASS_SEDE,
            'fecha_inicial': WORLDCLASS_FECHA_INICIAL,
            'fecha_final': WORLDCLASS_FECHA_FINAL,
            'estados': WORLDCLASS_ESTADOS,
        }
    },
    {
        'nombre': 'discovery',
        'base_url': DISCOVERY_BASE_URL,
        'email': DISCOVERY_EMAIL,
        'password': DISCOVERY_PASSWORD,
        'excel_template': 'contratos_discovery_{SEDE}_{ESTADO}.xlsx',
        'sheet_names': DISCOVERY_ESTADOS,
        'estados': DISCOVERY_ESTADOS,
        'filtros': {
            'sede': DISCOVERY_SEDES[0] if DISCOVERY_SEDES else '',
            'fecha_inicial': DISCOVERY_FECHA_INICIAL,
            'fecha_final': DISCOVERY_FECHA_FINAL,
            'estados': DISCOVERY_ESTADOS,
        }
    },
]

URLS = {
    'login': LOGIN_PATH,
    'contratos': CONTRATOS_PATH,
}

SELECTORS = {
    'email': SELECTOR_EMAIL,
    'password': SELECTOR_PASSWORD,
    'submit': SELECTOR_SUBMIT,
    'sede': SELECTOR_SEDE,
    'fecha_inicial': SELECTOR_FECHA_INICIAL,
    'fecha_final': SELECTOR_FECHA_FINAL,
    'estado': SELECTOR_ESTADO,
    'buscar': SELECTOR_BUSCAR,
    'contrato_link': SELECTOR_CONTRATO_LINK,
}
