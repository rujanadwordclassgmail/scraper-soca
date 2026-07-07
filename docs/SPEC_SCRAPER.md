# Spec de refactorización del scraper

## Objetivo
Preparar el scraper para procesar cargas grandes de contratos de forma más estable, controlable y segura.

## Flujo actual esperado del scraper
1. Inicio del navegador.
2. Login en la plataforma.
3. Navegación a la vista de contratos.
4. Aplicación de filtros por sitio y estado.
5. Recolección de enlaces de contratos.
6. Apertura de cada contrato.
7. Extracción de datos.
8. Acumulación en memoria.
9. Exportación final a Excel.

## Problemas a cubrir en la siguiente fase
- Procesos largos pueden fallar o interrumpirse.
- Una falla en un contrato puede detener el flujo completo.
- No existe un control fino de velocidad.
- No existe una estrategia de guardado parcial.
- El proceso actual es muy dependiente de la estabilidad de la página.

## Cambios recomendados

### 1. Configuración de ejecución
Agregar parámetros configurables en el archivo de configuración:
- `TIMING_FACTOR`: controla la velocidad del scraper.
- `MAX_CONTRATOS`: limita cuántos contratos procesar por corrida.
- `SAVE_EVERY`: define cada cuántos registros se guarda progreso parcial.
- `MAX_RETRIES`: número de reintentos por contrato fallido.

### 2. Flujo recomendado
1. Inicializar navegador.
2. Hacer login.
3. Por cada estado y sitio:
   - aplicar filtros,
   - recolectar URLs,
   - procesar contratos uno por uno,
   - guardar cada `SAVE_EVERY` registros.
4. Al finalizar, exportar el Excel final.

### 3. Estrategia de resiliencia
- Si un contrato falla, registrar el error y continuar.
- Reintentar el contrato un número limitado de veces.
- Guardar resultados intermedios para evitar perder trabajo.
- Si el proceso se interrumpe, poder reanudar desde la última exportación parcial.

### 4. Recomendación de settings iniciales
Propuesta conservadora:
- `TIMING_FACTOR = 0.8`
- `MAX_CONTRATOS = 300`
- `SAVE_EVERY = 50`
- `MAX_RETRIES = 2`

### 5. Logging recomendado
- Mostrar solo resumen por estado y por bloque de contratos.
- Registrar errores por contrato.
- Mantener un log simple y legible.

## Plan de recuperación si algo falla
Si el scraper se estrella:
1. Revisar el último bloque guardado.
2. Ajustar `TIMING_FACTOR` si el sitio está respondiendo lento.
3. Reducir `MAX_CONTRATOS` para validar una corrida pequeña.
4. Reintentar con `SAVE_EVERY` más bajo si se desea mayor seguridad.
5. Mantener el archivo Excel parcial como respaldo.

## Nota
Este documento sirve como base para refactorizar el flujo de forma ordenada y con un punto claro de recuperación ante fallos.
