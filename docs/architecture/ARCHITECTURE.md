# Arquitectura del proyecto

## Objetivo

Automatizar la extracción de contratos desde las plataformas World Class y Discovery y exportar los resultados a CSV / Excel.

## Estructura de módulos

```
src/worldclass_scraper/
├── config.py                  # Configuración leída desde .env
├── cli.py                     # Parser de argumentos de línea de comandos
├── scraper.py                 # Orquestador principal
└── modules/
    ├── auth.py                # Login y gestión de sesión Playwright
    ├── browser.py             # Ciclo de vida del navegador (start/close/new_page)
    ├── concurrency.py         # Control adaptativo de workers
    ├── exporters.py           # AbstractExporter, ExcelExporter, ExportOrchestrator
    ├── extractors.py          # Extracción de campos del detalle de contrato
    ├── filters.py             # Aplicación de filtros web y paginación
    ├── logging.py             # Logger estructurado a archivo
    ├── progress.py            # Barra de progreso en consola
    ├── retry.py               # RetryPolicy con backoff exponencial + jitter
    ├── audit.py               # Análisis post-ejecución de logs
    └── utils.py               # slugify, constantes ANSI
```

## Responsabilidades por módulo

### config.py
Lee variables de entorno desde `.env`. Define credenciales, URLs, filtros, timeouts, sedes, estados y flags de exportación. Es la **única** fuente de verdad para parámetros de entorno.

### cli.py
Define y parsea los argumentos de línea de comandos. No contiene lógica de negocio. Delega completamente en `scraper.main()`.

### scraper.py / `AsyncWorldClassScraper`
Orquestador. Coordina el ciclo: login → filtros → recolección de URLs → extracción concurrente → exportación. Instancia y coordina todos los módulos. No implementa lógica propia de ninguna capa.

### modules/auth.py / `AsyncAuthManager`
- Carga y guarda `storage_state` de sesión en disco
- Ejecuta el flujo de login: navegar, detectar campos con fallbacks, rellenar, verificar
- No conoce nada de contratos ni de exportación

### modules/browser.py / `AsyncBrowserManager`
- Arranca y cierra Playwright + Chromium
- Crea nuevas páginas con timeouts configurados
- Detecta contextos cerrados y los marca como `None` para que el orquestador los recree

### modules/concurrency.py / `AdaptiveConcurrencyController`
- Recibe señales de éxito (`on_success`) y error (`on_error`)
- Reduce `concurrency` al alcanzar `error_threshold` de errores transientes consecutivos
- Recupera `concurrency` gradualmente al alcanzar `stable_threshold` de éxitos
- No conoce Playwright ni contratos — solo un entero y dos contadores

### modules/extractors.py / `ContractExtractor`
- Extrae todos los campos del HTML de un contrato individual
- Normaliza sede y estado a valores canónicos
- Extrae comentarios de textarea o de tabla según la estructura de la página

### modules/exporters.py
- `AbstractExporter`: interfaz de exportación (DIP)
- `ExcelExporter`: implementación con pandas/openpyxl — CSV y XLSX con hojas por estado
- `ExportOrchestrator`: coordina checkpoints parciales, exportaciones por sede/estado y archivo combinado

### modules/filters.py / `FilterManager`
- Aplica sede, fechas y estado en el formulario web
- Maneja la paginación y recolecta todas las URLs de contratos

### modules/retry.py / `RetryPolicy` + `retry_async`
- Backoff exponencial con jitter y `timing_factor`
- Predicado configurable `retry_if(exc, attempt) -> bool`
- Callback opcional `on_retry(exc, attempt)`

### modules/audit.py
- Lee `errors.log` y `run_summary.log` post-ejecución
- Clasifica líneas por categoría: `retry_goto`, `timeout_extract`, `context_closed`, etc.
- Produce un reporte estructurado con conteos y totales

### modules/logging.py / `ScraperLogger`
- Escribe líneas con timestamp a `errors.log`, `skipped_contracts.log` y `run_summary.log`

### modules/progress.py / `ProgressRenderer`
- Renderiza y imprime barras de progreso ASCII con colores ANSI

### modules/utils.py
- `slugify()`: convierte texto arbitrario en slug seguro para nombres de archivo
- Constantes de color ANSI reutilizadas en varios módulos

## Flujo de ejecución

```
CLI (cli.py)
  └─► scraper.main()
        ├─► AsyncWorldClassScraper.start()
        │     ├─► AsyncBrowserManager.start()
        │     └─► AsyncAuthManager.load_session()  (si existe)
        │
        ├─► AsyncAuthManager.login()               (si no había sesión)
        │
        └─► para cada estado:
              ├─► FilterManager.apply_filters()
              ├─► FilterManager.collect_contract_urls()
              └─► para cada batch de URLs:
                    ├─► extract_contract_page()     (con RetryPolicy)
                    ├─► AdaptiveConcurrencyController.on_success/on_error()
                    └─► ExportOrchestrator.export_partial()  (checkpoint)
        │
        └─► ExportOrchestrator.export_site_reports()
              └─► ExportOrchestrator.export_combined()  (modo todos)
```

## Principios de diseño aplicados

| Principio | Aplicación |
|---|---|
| **SRP** | Cada clase/módulo tiene una sola razón para cambiar |
| **OCP** | `AbstractExporter` permite añadir exportadores sin tocar el orquestador |
| **DIP** | `ExportOrchestrator` depende de `AbstractExporter`, no de `ExcelExporter` directamente |
| **Única fuente de verdad** | Parámetros de entorno solo en `.env`; parámetros de ejecución solo en CLI |

## Tests

183 tests unitarios en `tests/`. Cada módulo tiene su archivo de test correspondiente. Los módulos que dependen de Playwright se testean con `MagicMock` (para métodos síncronos como `page.locator()`) y `AsyncMock` (para métodos async).
