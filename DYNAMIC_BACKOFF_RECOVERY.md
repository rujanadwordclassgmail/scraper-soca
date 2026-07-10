# Control Adaptativo de Concurrencia

La lógica de backoff dinámico vive en `src/worldclass_scraper/modules/concurrency.py` — clase `AdaptiveConcurrencyController`.

## Cómo funciona

El controlador recibe señales externas del scraper y ajusta el número de workers en consecuencia:

```
Error transiente detectado
  └─► error_streak += 1
      si error_streak >= error_threshold:
          concurrency = max(min_concurrency, concurrency - reduction_step)
          error_streak = 0

Extracción exitosa
  └─► stable_streak += 1
      si stable_streak >= stable_threshold:
          concurrency = min(max_concurrency, concurrency + recovery_step)
          stable_streak = 0
```

Errores que cuentan como transientes (los demás resetean el streak sin acumular):
- `Target page, context or browser has been closed`
- `TargetClosedError`
- `Page.goto: Timeout`
- `timeout_extract`
- `Locator.text_content: Target page`

## Configuración

Todos los parámetros se controlan desde `.env`:

| Variable | Default | Descripción |
|---|---|---|
| `AUTO_REDUCE_ON_ERRORS` | `true` | Habilitar reducción automática |
| `ERROR_THRESHOLD` | `10` | Errores transientes antes de reducir |
| `MIN_CONCURRENCY` | `1` | Mínimo permitido |
| `CONCURRENCY_REDUCTION_STEP` | `1` | Cuánto reducir por evento |
| `AUTO_RECOVERY` | `true` | Habilitar recuperación gradual |
| `STABLE_THRESHOLD` | `20` | Éxitos consecutivos antes de aumentar |
| `RECOVERY_STEP` | `1` | Cuánto aumentar por periodo estable |
| `MAX_CONCURRENCY` | `8` | Máximo permitido |

## Perfiles recomendados

**Sitio lento o inestable (>40s de carga):**
```env
CONCURRENCY=1
ERROR_THRESHOLD=5
STABLE_THRESHOLD=30
MAX_CONCURRENCY=3
```

**Sitio rápido y estable (<20s de carga):**
```env
CONCURRENCY=4
ERROR_THRESHOLD=15
STABLE_THRESHOLD=15
RECOVERY_STEP=2
MAX_CONCURRENCY=8
```

## Desactivar

```env
AUTO_REDUCE_ON_ERRORS=false
AUTO_RECOVERY=false
```

## Monitoreo

Los eventos quedan registrados en `logs/<modo>/run_summary.log`:

```
[2026-07-09 21:00:01] SUMMARY | auto_recovery_concurrency from=3 to=4 | stable_streak=20 | sitio=worldclass
[2026-07-09 21:00:41] SUMMARY | auto_reduce_concurrency from=4 to=3 | sitio=worldclass
```

Para analizar una ejecución completa:

```python
from worldclass_scraper.modules.audit import audit_logs, format_report
print(format_report(audit_logs('logs/worldclass')))
```
