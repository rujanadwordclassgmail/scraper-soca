import argparse

from scraper import main as run_scraper


def build_argument_parser():
    parser = argparse.ArgumentParser(description='World Class scraper')
    parser.add_argument('--mode', default='todos', choices=['todos', 'worldclass', 'discovery'], help='Modo de ejecución')
    parser.add_argument('--headless', action='store_true', default=True, help='Ejecutar en modo headless')
    parser.add_argument('--no-headless', dest='headless', action='store_false', help='Mostrar navegador')
    parser.add_argument('--timing-factor', type=float, default=1.0, help='Factor de timing para controlar la velocidad')
    parser.add_argument('--log-dir', default='logs', help='Directorio de archivos de log')
    return parser


def main():
    parser = build_argument_parser()
    args = parser.parse_args()
    run_scraper(mode=args.mode, headless=args.headless, timing_factor=args.timing_factor, log_dir=args.log_dir)


if __name__ == "__main__":
    main()
