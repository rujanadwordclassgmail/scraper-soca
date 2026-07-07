import unittest

from main import build_argument_parser


class MainCliTests(unittest.TestCase):
    def test_parser_defaults(self):
        parser = build_argument_parser()
        args = parser.parse_args([])
        self.assertEqual(args.mode, 'todos')
        self.assertTrue(args.headless)
        self.assertEqual(args.timing_factor, 1.0)
        self.assertEqual(args.log_dir, 'logs')


if __name__ == '__main__':
    unittest.main()
