"""Punto de entrada del proyecto.

Solo responsabilidad: añadir src/ al path y delegar en cli.main().
No define parsers ni lógica propia — eso vive en worldclass_scraper.cli.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from worldclass_scraper.cli import main

if __name__ == '__main__':
    main()
