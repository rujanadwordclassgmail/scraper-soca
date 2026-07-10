# Guía de desarrollo

## Requisitos

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) como gestor de entorno y dependencias

## Configuración inicial

```bash
uv sync                    # crea .venv e instala dependencias
uv run playwright install  # descarga Chromium
cp .env.example .env       # copia el ejemplo y rellena tus credenciales
```

No usar `pip` directamente en este proyecto — `uv` es el gestor oficial. La fuente de verdad es `pyproject.toml`.

## Ejecutar el scraper

```bash
uv run python main.py --mode worldclass
```

Ver todos los flags disponibles:

```bash
uv run python main.py --help
```

## Ejecutar tests

```bash
uv run pytest -q           # suite completa (rápida, ~0.7s)
uv run pytest -v           # con nombres detallados
uv run pytest tests/test_concurrency.py -v   # módulo específico
```

## Estructura de tests

Cada módulo en `src/worldclass_scraper/modules/` tiene su test en `tests/test_<módulo>.py`.

Regla clave para tests con Playwright: `page.locator()` es **síncrono** en Playwright — usar `MagicMock` para `page`, y `AsyncMock` solo para los métodos del locator (`.count()`, `.all()`, etc.).

```python
# Correcto
page = MagicMock()
locator = MagicMock()
locator.count = AsyncMock(return_value=1)
page.locator.return_value = locator

# Incorrecto — convierte locator() en coroutine
page = AsyncMock()
```

## Agregar una dependencia

```bash
uv add nombre-paquete              # runtime
uv add --dev nombre-paquete        # solo desarrollo
```

## Estilo y convenciones

- Una responsabilidad por clase/módulo (SRP)
- Parámetros de entorno solo en `.env` — nunca hardcodeados ni en CLI
- Parámetros de ejecución (qué extraer, cuántos) solo en flags CLI
- Nombres en snake_case para variables/funciones, PascalCase para clases
- Type hints en firmas públicas

## Flujo de trabajo

1. Crear rama: `git checkout -b feature/descripcion`
2. Implementar cambios
3. Pasar tests: `uv run pytest -q`
4. Actualizar documentación si cambia la API pública o el comportamiento
5. Commit y PR

## Checklist antes de un PR

- [ ] `uv run pytest -q` pasa sin errores
- [ ] Módulo nuevo tiene su `test_<módulo>.py`
- [ ] `.env.example` actualizado si se añadió variable de entorno nueva
- [ ] Documentación actualizada si cambió comportamiento externo

## Análisis de una ejecución

```python
from worldclass_scraper.modules.audit import audit_logs, format_report

report = audit_logs('logs/worldclass')
print(format_report(report))
```

## Archivos de referencia

| Archivo | Propósito |
|---|---|
| `pyproject.toml` | Dependencias y configuración de pytest |
| `.env.example` | Plantilla de variables de entorno |
| `docs/architecture/ARCHITECTURE.md` | Diseño de módulos y flujo |
| `scripts/explore_site.py` | Herramienta de exploración/diagnóstico del sitio |
