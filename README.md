# World Class Scraper

Automatiza la extracción de contratos desde las plataformas World Class y Discovery y los exporta a CSV o Excel.

## Inicio rápido

```bash
uv sync
uv run playwright install
cp .env.example .env   # rellena tus credenciales
uv run python main.py
```

## Estructura del proyecto

```
scrapping/
├── main.py                          # Punto de entrada (thin wrapper sobre cli)
├── scripts/
│   └── explore_site.py              # Herramienta de diagnóstico / exploración
├── src/worldclass_scraper/
│   ├── cli.py                       # Parser de argumentos CLI
│   ├── config.py                    # Configuración leída desde .env
│   ├── scraper.py                   # Orquestador principal
│   └── modules/
│       ├── auth.py                  # Login y gestión de sesión
│       ├── browser.py               # Ciclo de vida del navegador Playwright
│       ├── concurrency.py           # Control adaptativo de concurrencia
│       ├── exporters.py             # AbstractExporter, ExcelExporter, ExportOrchestrator
│       ├── extractors.py            # Extracción de campos de cada contrato
│       ├── filters.py               # Aplicación de filtros y paginación
│       ├── logging.py               # Logger estructurado a archivo
│       ├── progress.py              # Barra de progreso en consola
│       ├── retry.py                 # Política de reintentos con backoff exponencial
│       ├── audit.py                 # Análisis post-ejecución de logs
│       └── utils.py                 # Utilidades: slugify, constantes ANSI
├── tests/                           # Suite de pruebas unitarias (183 tests)
└── docs/                            # Documentación adicional
```

## Configuración

La única fuente de verdad para parámetros de entorno es `.env`. Copia el ejemplo y edítalo:

```bash
cp .env.example .env
```

Parámetros de credenciales (obligatorios):

```env
WORLDCLASS_EMAIL=tu_email@ejemplo.com
WORLDCLASS_PASSWORD=tu_password
DISCOVERY_EMAIL=tu_email@ejemplo.com
DISCOVERY_PASSWORD=tu_password
```

Parámetros de entorno/infraestructura (opcionales, con defaults razonables):

```env
CONCURRENCY=4                  # workers paralelos
PAGE_NAVIGATION_TIMEOUT=40000  # ms
PAGE_ACTION_TIMEOUT=20000      # ms
PAGE_READY_STATE_TIMEOUT=15000 # ms
TIMING_FACTOR=1.0              # multiplica todos los delays
EXPORT_CSV=true
EXPORT_XLSX=false
AUTO_REDUCE_ON_ERRORS=true     # reduce concurrencia al detectar errores
AUTO_RECOVERY=true             # recupera concurrencia cuando se estabiliza
```

> Los parámetros de comportamiento por ejecución (qué extraer, cuántos contratos) van en CLI, no en `.env`.

## CLI — flags disponibles

```
--mode          worldclass | discovery | todos  (default: todos)
--sede          Sede a procesar (default: la configurada en .env)
--estado        Estado a extraer. Sin valor: procesa todos
--limit N       Máximo de contratos por estado. 0 = todos (default: 0)
--csv           Exportar a CSV
--xlsx          Exportar a Excel
--timing-factor Float que multiplica los delays solo para esta ejecución
--no-headless   Mostrar el navegador (útil para depurar)
--check-server  Verificar si el servidor responde antes de arrancar
--contract-url  URL de un contrato específico para extracción directa
--output-dir    Directorio de salida (default: output/<mode>)
--log-dir       Directorio de logs  (default: logs/<mode>)
```

## Ejemplos de uso

```bash
# Extracción completa de WorldClass
uv run python main.py --mode worldclass

# Solo una sede y estado, con límite
uv run python main.py --mode worldclass --sede 'WCG - GUAYAQUIL' --estado CASH --limit 500

# Exportar a CSV y Excel, navegador visible
uv run python main.py --mode worldclass --csv --xlsx --no-headless

# Extraer un contrato directamente
uv run python main.py --mode worldclass --contract-url https://worldclass.systemsoca.com/vercontrato/1234

# Ajustar velocidad de navegación
uv run python main.py --mode worldclass --timing-factor 0.8
```

## Salidas

- CSV / Excel en `output/<mode>/<sede-slug>/reports/`
- Logs en `logs/<mode>/errors.log` y `logs/<mode>/run_summary.log`
- Capturas de depuración en `output/<mode>/debug/` y `output/<mode>/screenshots/`

## Esquema de columnas exportadas

| Columna | Descripción |
|---|---|
| `Sede` | Sede canónica normalizada (`WCG - GUAYAQUIL`, etc.) |
| `Estado_Contrato` | Estado normalizado (`PROCE`, `CASH`, `CERO`, `GASTO LEGAL`, `SEPARACION`, `PEDDING`) |
| `Numero_Contrato` | Identificador del contrato |
| `Fecha_Creacion` | Fecha de creación |
| `Nombre_Titular`, `Apellido_Titular`, `Cedula_Titular`, `Celular_Titular`, `Email_Titular` | Datos del titular |
| `Nombre_Cotitular`, `Apellido_Cotitular`, `Cedula_Cotitular`, `Celular_Cotitular`, `Email_Cotitular` | Datos del cotitular |
| `Valor_Contrato`, `Cuota_Inicial`, `Pago_Inicial` | Valores económicos |
| `Cuotas_Saldo_Inicial`, `Fecha_Primer_Pago_Inicial` | Saldo inicial |
| `Cuotas_Saldo_Restante`, `Fecha_Primer_Pago_Restante` | Saldo restante |
| `Comentario` | Texto de comentario extraído |

## Análisis de logs

```python
from worldclass_scraper.modules.audit import audit_logs, format_report

report = audit_logs('logs/worldclass')
print(format_report(report))
```

Ejemplo de salida:

```
=== AUDIT REPORT ===

[ERRORS]
  timeout_extract             : 95
  retry_goto                  : 12
  retry_extract               : 8
  context_closed              : 3
  extract_failed              : 2

[RUN_SUMMARY]
  concurrency_reduced         : 4
  concurrency_recovered       : 2

[TOTALS]
  total_errors                : 120
  total_retries               : 20
```

## Tests

```bash
uv run pytest -q
```

183 tests unitarios cubriendo todos los módulos del paquete.

## Dependencias

Gestionadas exclusivamente con `uv`. No editar `requirements.txt` manualmente — `pyproject.toml` es la fuente de verdad.

```bash
uv sync                         # instalar dependencias
uv run playwright install       # instalar Chromium
uv lock --no-update             # actualizar lockfile sin subir versiones
```

## Documentación adicional

- [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md)
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)
