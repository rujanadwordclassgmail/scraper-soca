"""Utilidades compartidas: constantes ANSI, slugify."""
import re
import unicodedata

# ── Colores ANSI ────────────────────────────────────────────────────────────
RESET = '\033[0m'
BOLD = '\033[1m'
GREEN = '\033[32m'
YELLOW = '\033[33m'
CYAN = '\033[36m'
MAGENTA = '\033[35m'
RED = '\033[31m'


def slugify(value: str) -> str:
    """Convierte un texto arbitrario en un slug seguro para nombres de archivo."""
    if not value:
        return 'sin-sede'
    value = unicodedata.normalize('NFKD', str(value))
    value = value.encode('ascii', 'ignore').decode('ascii')
    value = value.strip().lower()
    value = re.sub(r'[^a-z0-9]+', '-', value)
    value = re.sub(r'-{2,}', '-', value)
    return value.strip('-') or 'sin-sede'
