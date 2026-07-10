import argparse
import asyncio
import os
from worldclass_scraper.scraper import main as scraper_main

DEFAULT_OUTPUT_DIR = 'output'
DEFAULT_LOG_DIR = 'logs'


def build_parser():
    parser = argparse.ArgumentParser(description='Scraper de contratos World Class')
    parser.add_argument('--mode', default='todos', choices=['todos', 'worldclass', 'discovery'], help='Modo de ejecución')
    parser.add_argument('--timing-factor', type=float, default=1.0, help='Factor de espera para el scraper')
    parser.add_argument('--headless', action='store_true', help='Ejecutar en modo headless')
    parser.add_argument('--no-headless', dest='headless', action='store_false', help='Mostrar navegador')
    parser.set_defaults(headless=True)
    parser.add_argument('--log-dir', default=DEFAULT_LOG_DIR, help='Directorio de archivos de log')
    parser.add_argument('--output-dir', default=DEFAULT_OUTPUT_DIR, help='Directorio de salida')
    parser.add_argument('--contract-url', default='', help='URL de contrato directo para extraer un solo contrato')
    parser.add_argument('--estado', default='', help='Estado a extraer en el modo normal; deja vacío para procesar todos los estados')
    parser.add_argument('--sede', default='', help='Sede a usar para el scrapping completo; deja vacío para usar la sede del config')
    parser.add_argument('--csv', action='store_true', default=None, help='Exportar resultado a CSV')
    parser.add_argument('--xlsx', action='store_true', default=None, help='Exportar resultado a Excel')
    parser.add_argument('--check-server', action='store_true', default=False, help='Verificar si el servidor está online antes de empezar')
    parser.add_argument('--limit', type=int, default=0, metavar='N', help='Máximo de contratos a procesar por estado. Por defecto 0 (todos).')
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    log_dir = args.log_dir
    output_dir = args.output_dir
    if log_dir == DEFAULT_LOG_DIR:
        log_dir = os.path.join(log_dir, args.mode)
    if output_dir == DEFAULT_OUTPUT_DIR:
        output_dir = os.path.join(output_dir, args.mode)

    asyncio.run(
        scraper_main(
            mode=args.mode,
            headless=args.headless,
            timing_factor=args.timing_factor,
            log_dir=log_dir,
            output_dir=output_dir,
            contract_url=args.contract_url,
            estado=args.estado,
            sede=args.sede,
            export_csv=args.csv,
            export_xlsx=args.xlsx,
            check_server=args.check_server,
            limit=args.limit,
        )
    )


if __name__ == '__main__':
    main()
