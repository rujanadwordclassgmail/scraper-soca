# Optimización del scraper para 3000 registros

## Contexto

El scraper puede llegar a procesar alrededor de 3000 registros, lo que implica visitar el servidor muchas veces para:

- abrir la página del contrato,
- localizar los datos relevantes,
- extraer la información,
- y guardar el resultado.

Con ese volumen, el rendimiento ya no depende solo del código, sino también de la latencia de red, la capacidad del servidor y la forma en que se gestionan las peticiones.

## Problema principal

El mayor cuello de botella suele ser la espera por respuestas del servidor. En este tipo de flujo, el tiempo total está dominado por:

- carga de páginas,
- navegación entre pantallas,
- espera por elementos del DOM,
- y escritura de resultados.

## Recomendación general

Para 3000 registros, conviene diseñar el scraper con un enfoque más escalable:

1. Separar la recolección de URLs del procesamiento de detalle.
2. Procesar los contratos en lotes.
3. Limitar la concurrencia para evitar saturar el sitio.
4. Usar reintentos con pausas controladas.
5. Guardar resultados periódicamente para no perder progreso.

## Plan de concurrencia recomendado para el servidor

Dado que el equipo es un Dell PowerEdge T140 con 16 GB de RAM y un Xeon E-2224G/E-2226G, la estrategia más segura es usar concurrencia moderada y controlada, no un paralelismo agresivo.

### Parámetros recomendados

- Workers iniciales: 2 a 3.
- Máximo sugerido: 4 workers.
- Tiempo entre peticiones: 1 a 3 segundos, según la respuesta del sitio.
- Guardado intermedio: cada 50 a 100 contratos procesados.

### Motivo

En este tipo de scraping, la CPU no suele ser el cuello de botella principal. El tiempo se pierde mayormente esperando respuestas del servidor, cargando páginas y navegando por la interfaz. Por eso, un número pequeño de workers suele ser suficiente y más estable.

### Escalado progresivo

Se recomienda iniciar con:

- 2 workers para validar estabilidad,
- luego subir a 3 si el sitio responde bien,
- y solo pasar a 4 si no aparecen bloqueos ni errores frecuentes.

### Reglas de seguridad

- No abrir más navegadores de los que el servidor pueda sostener.
- No superar el número de peticiones simultáneas que el sitio acepte.
- Evitar correr varios procesos de scraping al mismo tiempo si ya se está usando mucha memoria o CPU.
- Monitorear errores de timeout, red o bloqueo temporal.

## Propuesta de arquitectura para este servidor

Una estructura razonable sería:

- Fase 1: recolectar las URLs o identificadores de contratos.
- Fase 2: encolar los contratos en una cola compartida.
- Fase 3: ejecutar 2 a 4 workers con concurrencia limitada.
- Fase 4: guardar resultados en un archivo intermedio y exportarlos al final.

## Recomendación final

Para este servidor, la mejor opción es un modelo de concurrencia moderada:

- 2 a 4 workers,
- pausas controladas,
- guardado incremental,
- y monitoreo de errores.

Eso permitirá procesar 3000 registros con mejor rendimiento sin poner en riesgo la estabilidad del scraper ni del sitio objetivo.

## Estrategias recomendadas

### 1. Concurrencia controlada

Para tareas donde el tiempo se pasa esperando respuestas del servidor, conviene usar concurrencia.

Opciones recomendadas:

- Threads: buenos para I/O-bound, cuando las operaciones esperan respuestas externas.
- Asyncio: útil si se quiere un modelo más moderno y eficiente para muchas peticiones.
- Multiprocessing: útil si luego hay procesamiento pesado de datos, pero no es la primera opción para el scraping por sí solo.

### 2. Evitar abrir un navegador por cada contrato

El navegador es un recurso costoso. Lo ideal es:

- abrir una sola sesión de navegador,
- reutilizarla para varios contratos,
- y cerrar solo al final del trabajo.

### 3. Control de velocidad

Con 3000 registros, conviene introducir pausas razonables entre peticiones para evitar:

- bloqueos por parte del servidor,
- captchas,
- o throttling por IP.

Un patrón útil es:

- retraso mínimo entre peticiones,
- reintentos exponenciales,
- y pausas adicionales si aparecen errores frecuentes.

### 4. Persistencia incremental

No conviene esperar a terminar todo para guardar resultados. Lo mejor es:

- escribir por lotes,
- guardar cada cierto número de contratos,
- y permitir reanudar la ejecución si falla.

### 5. Logging y monitoreo

Para procesos largos, es importante registrar:

- contratos procesados,
- errores por contrato,
- tiempos promedio,
- y progreso general.

## Propuesta de arquitectura

Una estructura razonable sería:

- Fase 1: recolectar todas las URLs o identificadores de contratos.
- Fase 2: encolar los contratos a procesar.
- Fase 3: ejecutar workers con concurrencia limitada.
- Fase 4: guardar resultados en un archivo intermedio o Excel.

## Recomendación final

Para este scraper, la mejor opción inicial no es simplemente “hacerlo más rápido”, sino hacer que sea más escalable y robusto.

La combinación más práctica sería:

- concurrencia limitada para las peticiones,
- reutilización del navegador,
- guardado incremental,
- y control de velocidad.

Eso permitirá manejar 3000 registros de forma más estable y con menos riesgo de fallos.
