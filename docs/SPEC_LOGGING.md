# Spec de logging y trazabilidad del scraper

## Objetivo
Agregar un sistema de logging simple, ordenado y útil para registrar:
- contratos que no pudieron procesarse,
- errores inesperados,
- eventos relevantes del flujo,
- y datos que puedan servir de soporte para el Excel o para auditoría.

## Requisitos

### 1. Logging en archivos separados
Crear una carpeta de logs con archivos independientes por tipo de evento:
- `logs/errors.log`: errores excepcionales del scraper.
- `logs/skipped_contracts.log`: contratos no procesados o sin datos útiles.
- `logs/run_summary.log`: resumen de cada ejecución.

### 2. Estructura de cada archivo

#### `errors.log`
Registrar:
- timestamp
- sitio
- estado
- URL del contrato
- mensaje de error
- stack trace breve si aplica

Formato sugerido:
```text
[2026-07-07 10:00:00] ERROR | sitio=worldclass | estado=PROCE | url=https://... | mensaje=Timeout al abrir contrato
```

#### `skipped_contracts.log`
Registrar:
- timestamp
- sitio
- estado
- URL del contrato
- motivo de omisión

Formato sugerido:
```text
[2026-07-07 10:00:05] SKIP | sitio=worldclass | estado=PROCE | url=https://... | motivo=Sin datos útiles
```

#### `run_summary.log`
Registrar:
- inicio de ejecución
- fin de ejecución
- sitio procesado
- cantidad de contratos encontrados
- cantidad de contratos extraídos
- cantidad de errores
- cantidad de skips
- tiempo total aproximado

Formato sugerido:
```text
[2026-07-07 10:00:00] START | sitio=worldclass
[2026-07-07 10:15:00] END | sitio=worldclass | extraidos=120 | errores=5 | skips=10
```

### 3. Datos relevantes para el Excel
Además de los datos extraídos, el scraper podría registrar una tabla secundaria o un archivo aparte con:
- contratos fallidos,
- contratos omitidos,
- razones de fallo,
- y estado del proceso.

Esto puede ser útil para análisis posterior sin saturar la hoja principal del Excel.

### 4. Comportamiento esperado
- Si un contrato falla, no debe detener todo el proceso.
- Si un contrato no trae datos útiles, debe registrarse y seguir con el siguiente.
- El archivo de logs debe ser legible y fácil de revisar manualmente.
- El Excel debe recibir solo los registros válidos.

### 5. Configuración recomendada
Agregar en el archivo de configuración valores como:
- `LOG_DIR = 'logs'`
- `LOG_LEVEL = 'INFO'`
- `SAVE_FAILED_ROWS = True`

### 6. Alcance del spec
- Se implementará el sistema de logging en archivos separados.
- No se cambiará la lógica de extracción de datos.
- No se cambiará la estructura principal del Excel salvo lo necesario para incluir un registro de errores si se decide.

## Orden recomendado
1. Crear la carpeta `logs`.
2. Implementar escritura de `errors.log`.
3. Implementar escritura de `skipped_contracts.log`.
4. Implementar escritura de `run_summary.log`.
5. Añadir la configuración del logging.
