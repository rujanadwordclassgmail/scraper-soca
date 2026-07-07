import os
from dotenv import load_dotenv

load_dotenv('.env')

HEADLESS = True

# ── Logging ─────────────────────────────────────────────────────────────────
LOG_DIR = 'logs'
OUTPUT_DIR = 'output'
LOG_LEVEL = 'INFO'
SAVE_FAILED_ROWS = True

# ── Environment ────────────────────────────────────────────────────────────
ENV_FILE = '.env'

# ── Credenciales desde variables de entorno ────────────────────────────────
EMAIL = os.getenv('WORLDCLASS_EMAIL', '')
PASSWORD = os.getenv('WORLDCLASS_PASSWORD', '')
DISCOVERY_EMAIL = os.getenv('DISCOVERY_EMAIL', '')
DISCOVERY_PASSWORD = os.getenv('DISCOVERY_PASSWORD', '')

# ── Timing global ───────────────────────────────────────────────────────────
# Ajusta los tiempos del scraper manualmente.
# Valores menores a 1.0 lo hacen más rápido; mayores a 1.0 lo hacen más lento.
TIMING_FACTOR = 1.0

# ── Debug ────────────────────────────────────────────────────────────────────
# True  → guarda archivos HTML cuando no se encuentra el número de contrato
# False → no genera ningún archivo de debug
DEBUG = False

# ── Modo de ejecución ───────────────────────────────────────────────────────
# 'todos'       → procesa todos los sitios y genera Excel por sitio + combinado
# 'worldclass'  → procesa solo el sitio worldclass
# 'discovery'   → procesa solo el sitio discovery
MODO = 'todos'

# ── Excel combinado (solo aplica cuando MODO = 'todos') ─────────────────────
EXCEL_COMBINADO = True
EXCEL_COMBINADO_FILENAME = 'contratos_todos.xlsx'

# ── Sitios ──────────────────────────────────────────────────────────────────
SITIOS = [
    {
        'nombre': 'worldclass',
        'base_url': 'https://worldclass.systemsoca.com',
        'email': EMAIL or os.getenv('WORLDCLASS_EMAIL', ''),
        'password': PASSWORD or os.getenv('WORLDCLASS_PASSWORD', ''),
        'excel': 'contratos_worldclass.xlsx',
        'filtros': {
            'sede': 'WCG - GUAYAQUIL',
            'fecha_inicial': '2023-01-01',
            'fecha_final': '2026-05-16',
            'estados': ['PROCE', 'CERO', 'GASTO LEGAL', 'SEPARACION', 'PEDDING']
        }
    },
    {
        'nombre': 'discovery',
        'base_url': 'https://discovery.systemsoca.com',
        'email': DISCOVERY_EMAIL or os.getenv('DISCOVERY_EMAIL', ''),
        'password': DISCOVERY_PASSWORD or os.getenv('DISCOVERY_PASSWORD', ''),
        'excel': 'contratos_discovery.xlsx',
        'filtros': {
            'sede': '',          # dejar vacío para no filtrar por sede
            'fecha_inicial': '2025-01-01',
            'fecha_final': '2026-05-07',
            'estados': ['PROCE', 'CERO', 'GASTO LEGAL', 'SEPARACION', 'PEDDING']
        }
    },
]

URLS = {
    'login': '/login',
    'contratos': '/contratos'
}
