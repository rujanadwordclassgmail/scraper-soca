Estrategia de reportes — WorldClass
=================================

Resumen
------
Archivo por sede: un solo Excel por sede con hojas por estado + hojas auxiliares.

Nombre de archivo sugerido
-------------------------
output/<modo>/reports/worldclass_<SEDE>_<YYYYmmdd>.xlsx
Ejemplo: output/worldclass/reports/worldclass_WCG_20260708.xlsx

Estructura interna del Excel
---------------------------
- Hoja por estado (una hoja para cada status: `PROCE`, `CASH`, `CERO`, `GASTO LEGAL`, `SEPARACION`, `PEDDING`).
- `combined`: todas las filas con columna `estado` (útil para ETL/consultas) y campos normalizados como `Sede` y `Estado_Contrato`.
- `summary`: métricas y pivots (conteos por estado, montos por mes, KPIs).
- `failed`: filas que fallaron + ruta a `raw/` (HTML/screenshot) para auditoría.
- `meta`: metadata del run (`scrape_ts`, `modo`, `sede`, `total_extracted`, `total_errors`, paths de archivos).

Columnas principales exportadas
------------------------------
- `Sede`: sede normalizada por contrato
- `Estado_Contrato`: estado normalizado
- `Numero_Contrato`: identificador del contrato
- `Fecha_Creacion`
- `Nombre_Titular`, `Apellido_Titular`, `Cedula_Titular`, `Celular_Titular`, `Email_Titular`
- `Nombre_Cotitular`, `Apellido_Cotitular`, `Cedula_Cotitular`, `Celular_Cotitular`, `Email_Cotitular`
- `Valor_Contrato`, `Cuota_Inicial`, `Pago_Inicial`
- `Cuotas_Saldo_Inicial`, `Fecha_Primer_Pago_Inicial`, `Cuotas_Saldo_Restante`, `Fecha_Primer_Pago_Restante`
- `Comentario`
- `url`

Flujo de extracción y guardado
------------------------------
1. Iterar por `sede` (ej. `WCG`).
2. Para cada `sede`, iterar por `estado` (los 6): `PROCE`, `CASH`, `CERO`, `GASTO LEGAL`, `SEPARACION`, `PEDDING`.
3. Al terminar cada `estado`, guardar parcial:
   - output/<modo>/partial_<SEDE>_<ESTADO>_<YYYYmmdd_HHMMSS>.xlsx
   - Mantener raw en: output/<modo>/raw/<SEDE>/ (HTML + capturas de pantallas de fallos)
4. Cuando se completan todos los estados de la sede, combinar parciales y crear el Excel final por sede con las hojas descritas arriba:
   - output/<modo>/reports/worldclass_<SEDE>_<YYYYmmdd>.xlsx
5. Si `mode==todos`, generar un Excel combinado adicional:
   - output/<modo>/reports/contratos_todos_<YYYYmmdd>.xlsx

Política de guardado y reanudación
---------------------------------
- Guardar parciales cada vez que se completa un `estado` o cada N filas (configurable).
- En caso de fallo, reintentar solo los parciales que fallaron.
- Mantener un `failed_rows.xlsx` por sede con detalles para reprocesos.

Auditoría y logs
----------------
- Registrar en `run_summary.log`:
  - inicio/fin, `sede`, `estado`, filas extraídas, errores, paths de parciales y final.
- Guardar `auth_session.json` y marcar expiración.

Reportes y hojas útiles para stakeholders
----------------------------------------
- `summary`: tabla con conteo de contratos por estado y montos por sede/mes.
- `pending_alerts`: contratos en `PEDDING` o `GASTO LEGAL` para revisión manual.
- `combined`: para cargas a BI o SQL.

Comandos de ejemplo (prueba corta)
---------------------------------
```bash
export MAX_CONTRATOS=50
uv run python main.py --mode worldclass --no-headless --output-dir output/report_test --log-dir logs/report_test
```

Rutas y convenciones
--------------------
- Parciales: output/<modo>/partial_<SEDE>_<ESTADO>_*.xlsx
- Raw/audit: output/<modo>/raw/<SEDE>/
- Reports finales: output/<modo>/reports/worldclass_<SEDE>_<YYYYmmdd>.xlsx

Siguientes pasos recomendados
----------------------------
- Implementar guardado parcial automático por `sede+estado`.
- Implementar combinador para generar el Excel por sede (hojas por estado + combined + summary + failed + meta).
- Añadir tests E2E con muestras HTML para validar normalización de `sede` y `estado`.

Notas
-----
- Mantener `raw_values` y `normalized_values` en cada fila para trazabilidad.
- Ajustar `MAX_CONTRATOS` y `SAVE_EVERY` en `src/worldclass_scraper/config.py` según necesidad.

Documento generado por la estrategia acordada.
