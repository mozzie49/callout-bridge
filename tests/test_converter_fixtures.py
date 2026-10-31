"""Synthetic inputs passed through pinned upstream converter, not live app exports."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from callout_bridge import convert

FIXTURES = Path(__file__).parent / 'fixtures' / 'converter'

class ConverterFixtures(unittest.TestCase):
    def fixture(self, name):
        return (FIXTURES / (name + '.converter.md')).read_bytes().decode('utf-8')

    def test_real_type_requires_explicit_mapping(self):
        source = self.fixture('simple')
        self.assertEqual(convert(source)[0], source)
        output, report = convert(source, {'info': 'NOTE'})
        self.assertEqual(report['converted'], 1)
        self.assertIn('> [!NOTE]\n> **INFO**', output)
        self.assertEqual(report['events'][0]['mapping'], {'source': 'info', 'target': 'NOTE', 'explicit': True})
        self.assertTrue(output.startswith('Before callout.\n\n'))
        self.assertTrue(output.endswith('\n\nAfter callout.\n\n'))
        self.assertEqual(convert(output, {'info': 'NOTE'})[0], output)

    def test_two_declared_mappings_leave_six_untouched(self):
        source = self.fixture('types')
        output, report = convert(source, {'info': 'NOTE', 'warn': 'WARNING'})
        self.assertEqual((report['converted'], report['preserved']), (2, 6))
        self.assertIn('> **WARN**', output)
        for kind in ('abstract', 'hint', 'success', 'error', 'example', 'quote'):
            original = next(line for line in source.splitlines() if 'data-callout-type="' + kind + '"' in line)
            self.assertIn(original, output)

    def test_nested_and_precode_remain_untouched(self):
        for name in ('nested', 'code'):
            source = self.fixture(name)
            output, report = convert(source, {'info': 'NOTE', 'warn': 'WARNING'})
            self.assertEqual(output.encode(), source.encode())
            self.assertGreater(report['preserved'], 0)
        self.assertIn('precode', self.fixture('code'))
