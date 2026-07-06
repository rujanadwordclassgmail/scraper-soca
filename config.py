HEADLESS = True

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
        'email': 'admin@cronleads.com',
        'password': '0CWC.2023',
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
        'email': 'anyersonher_89@hotmail.com',
        'password': '@cartera1677',
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
