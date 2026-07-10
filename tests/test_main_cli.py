from worldclass_scraper.cli import build_parser as build_argument_parser


def test_parser_defaults():
    parser = build_argument_parser()
    args = parser.parse_args([])
    assert args.mode == 'todos'
    assert args.headless
    assert args.timing_factor == 1.0
    assert args.log_dir == 'logs'
    assert args.output_dir == 'output'
    assert args.contract_url == ''
    assert args.estado == ''
    assert args.sede == ''
    assert args.csv is None
    assert args.xlsx is None
    assert args.limit == 0


def test_parser_csv_xlsx_flags():
    parser = build_argument_parser()
    args = parser.parse_args(['--csv'])
    assert args.csv is True
    assert args.xlsx is None

    args = parser.parse_args(['--xlsx'])
    assert args.csv is None
    assert args.xlsx is True

    args = parser.parse_args(['--csv', '--xlsx'])
    assert args.csv is True
    assert args.xlsx is True


def test_parser_limit_flag():
    parser = build_argument_parser()
    args = parser.parse_args(['--limit', '500'])
    assert args.limit == 500

    args = parser.parse_args([])
    assert args.limit == 0
