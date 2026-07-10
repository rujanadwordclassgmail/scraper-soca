git rm --ignore-unmatch 

uv run python main.py --mode worldclass --no-headless --log-dir logs --output-dir output

uv run python main.py --mode worldclass --no-headless --timing-factor 0.7 --output-dir output/smoke --log-dir logs/smoke


Aquí tienes el texto de las opciones desplegables de ambos combo box:


Worldclass
### 1. Estado de Contrato (Primera imagen)
* CASH
* PROCE
* CERO
* GASTO LEGAL
* SEPARACION
* PEDDING

### 2. Sede (Segunda imagen)
* WC - Santo domingo
* WC- - Guayaquil
* WCG - GUAYAQUIL
* WN - worldclass norte
* OCN - NASELLORIL
* WCS - OCT HOTELS
* WCQ - Los cuates
* WCU - RESTAURANTE

Discovery
### 1. Estado de Contrato (Primera imagen)
* CASH
* PROCE
* CERO
* GASTO LEGAL
* SEPARACION
* PEDDING

### 2. Sede (Segunda imagen)
* DC - Moreria
* PR - PRUEBA
* PPR - RAPIVISA

## Santo Domingo
uv run python main.py --mode worldclass --sede "WC - Santo domingo" --estado CASH --csv --check-server
uv run python main.py --mode worldclass --sede "WC - Santo domingo" --estado PROCE --csv --check-server
uv run python main.py --mode worldclass --sede "WC - Santo domingo" --estado CERO --csv --check-server
uv run python main.py --mode worldclass --sede "WC - Santo domingo" --estado "GASTO LEGAL" --csv --check-server --timing-factor 0.8
uv run python main.py --mode worldclass --sede "WC - Santo domingo" --estado PEDDING --csv --check-server


