# World Class Scraper - Extractor de Contratos

Script automatizado para extraer datos de contratos desde el sistema World Class y exportarlos a Excel.

## Requisitos

- Python 3.8 o superior
- Conexión a internet
- Credenciales de acceso al sistema World Class

## Instalación

1. Instalar las dependencias:
```bash
pip install -r requirements.txt
```

2. Instalar los navegadores de Playwright:
```bash
playwright install
```

## Configuración

Edita el archivo `config.py` para ajustar los parámetros:

### Credenciales
```python
EMAIL = 'admin@cronleads.com'
PASSWORD = '0CWC.2023'
```

### Modo de Navegador
```python
HEADLESS = True   # True = modo oculto (automático)
                  # False = ver navegador en tiempo real
```

- **HEADLESS = True**: El script aplica todos los filtros automáticamente sin mostrar el navegador
- **HEADLESS = False**: Muestra el navegador y espera a que apliques los filtros manualmente

### Filtros de Búsqueda
```python
FILTROS = {
    'sede': 'WCG - GUAYAQUIL',
    'fecha_inicial': '2024-01-01',  # Formato: YYYY-MM-DD
    'fecha_final': '2026-03-22',
    'estados': [
        'PROCE',
        'CERO',
        'GASTO LEGAL',
        'SEPACACION',
        'PEDDING'
    ]
}
```

### Archivo de Salida
```python
EXCEL_FILENAME = 'contratos_worldclass.xlsx'
```

Si el archivo está abierto, se creará uno nuevo con timestamp: `contratos_worldclass_YYYYMMDD_HHMMSS.xlsx`

## Uso

### Ejecución Básica

```bash
python scraper.py
```

### Proceso de Extracción

El script realiza los siguientes pasos:

1. **Inicio de sesión**: Conecta al sistema con las credenciales configuradas
2. **Navegación**: Accede a la página de contratos
3. **Aplicación de filtros**: 
   - Modo automático (HEADLESS=True): Aplica todos los filtros configurados
   - Modo manual (HEADLESS=False): Espera a que apliques los filtros
4. **Extracción de datos**: Procesa cada contrato y extrae todos los campos
5. **Exportación**: Guarda los datos en Excel

## Datos Extraídos

El script extrae los siguientes campos de cada contrato:

### Información General
- **Numero_Contrato**: Código del contrato (ej: WCG4394)
- **Fecha_Creacion**: Fecha en formato dd/mm/aa
- **Estado_Contrato**: Estado actual (PROCE, CERO, etc.)

### Datos del Titular
- **Nombre_Titular**
- **Apellido_Titular**
- **Cedula_Titular**
- **Celular_Titular**
- **Email_Titular**

### Datos del Cotitular
- **Nombre_Cotitular**
- **Apellido_Cotitular**
- **Cedula_Cotitular**
- **Celular_Cotitular**
- **Email_Cotitular**

### Detalles Financieros
- **Valor_Contrato**: Valor total del contrato
- **Cuota_Inicial**: Monto de la cuota inicial
- **Pago_Inicial**: Total del pago inicial
- **Cuotas_Saldo_Inicial**: Número de cuotas para financiar saldo inicial
- **Cuotas_Saldo_Restante**: Número de cuotas para financiar saldo restante

### Adicional
- **url**: URL del detalle del contrato

## Salida

El script genera:

- **Excel principal**: `contratos_worldclass.xlsx` (o con timestamp si está en uso)
- **Archivos de debug**:
  - `contratos_sin_filtros.html`: HTML de la página sin filtros
  - `contratos_sin_filtros.png`: Screenshot de la página sin filtros
  - `contratos_con_filtros.html`: HTML después de aplicar filtros (modo manual)
  - `contratos_con_filtros.png`: Screenshot después de filtros (modo manual)

## Ejemplos de Uso

### Extracción Automática Completa
```python
# En config.py
HEADLESS = True
FILTROS = {
    'sede': 'WCG - GUAYAQUIL',
    'fecha_inicial': '2024-01-01',
    'fecha_final': '2026-03-22',
    'estados': ['PROCE', 'CERO', 'GASTO LEGAL', 'SEPACACION', 'PEDDING']
}
```
```bash
python scraper.py
```

### Extracción Manual (con visualización)
```python
# En config.py
HEADLESS = False
```
```bash
python scraper.py
# El navegador se abrirá y esperará a que apliques los filtros manualmente
# Presiona ENTER en la consola cuando hayas terminado
```

### Extracción de un Solo Estado
```python
# En config.py
FILTROS = {
    'sede': 'WCG - GUAYAQUIL',
    'fecha_inicial': '2024-01-01',
    'fecha_final': '2026-03-22',
    'estados': ['PROCE']  # Solo un estado
}
```

## Solución de Problemas

### El script no inicia
- Verifica que Playwright esté instalado: `playwright install`
- Verifica las dependencias: `pip install -r requirements.txt`

### Error de credenciales
- Verifica EMAIL y PASSWORD en `config.py`
- Asegúrate de tener acceso al sistema

### No se extraen datos
- Revisa los archivos HTML y PNG generados para debug
- Verifica que los filtros sean correctos
- Intenta con HEADLESS=False para ver qué sucede

### El archivo Excel no se guarda
- Cierra el archivo Excel si está abierto
- El script creará uno nuevo con timestamp automáticamente

### El proceso es muy lento
- Es normal, el script procesa cada contrato individualmente
- Para muchos contratos, puede tomar varios minutos

## Notas Importantes

- El script respeta los tiempos de carga de la página para evitar errores
- Si un contrato falla, continúa con el siguiente
- Los datos se guardan al final del proceso completo
- Puedes interrumpir el script con Ctrl+C si es necesario

## Soporte

Para problemas o dudas, revisa:
1. Los archivos de debug generados (HTML y PNG)
2. Los mensajes en la consola durante la ejecución
3. La configuración en `config.py`
