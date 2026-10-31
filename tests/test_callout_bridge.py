import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from callout_bridge import convert


def block(body='<p>Keep <strong>backups</strong>.</p>', kind='warning', title='Before publishing', attrs=''):
    return f'<div class="callout" data-callout-type="{kind}"{attrs}><h4>{title}</h4>{body}</div>'


class Conversion(unittest.TestCase):
    def unchanged(self, source):
        actual, report = convert(source)
        self.assertEqual(source.encode(), actual.encode())
        return report

    def test_source_derived_warning(self):
        actual, report = convert(block())
        self.assertEqual(actual, '> [!WARNING]\n> **Before publishing**\n>\n> Keep **backups**&#46;')
        self.assertEqual(report['converted'], 1)

    def test_five_types_and_default_title(self):
        for kind in ('note', 'tip', 'important', 'warning', 'caution'):
            output, _ = convert(block(kind=kind, title=kind.upper()))
            self.assertTrue(output.startswith('> [!' + kind.upper() + ']\n> Keep'))

    def test_multiline_crlf_and_surrounding_bytes(self):
        source = '前言\r\n\r\n' + block().replace('><', '>\r\n<') + '\r\n\r\n尾声\r\n'
        actual, report = convert(source)
        self.assertEqual(report['converted'], 1)
        self.assertTrue(actual.startswith('前言\r\n\r\n>'))
        self.assertTrue(actual.endswith('\r\n\r\n尾声\r\n'))
        self.assertNotIn('\n', actual.replace('\r\n', ''))

    def test_code_and_links(self):
        actual, _ = convert(block('<p><a href="https://example.com/a?x=1&amp;y=2">Docs</a> <code>`x`</code></p>'))
        self.assertIn('[Docs](<https://example.com/a?x=1&amp;y=2>)', actual)
        self.assertIn('`` `x` ``', actual)

    def test_markdown_injection_is_text(self):
        actual, _ = convert(block('<p>[link](bad) &lt;script&gt; *not italic*</p>'))
        self.assertIn('&#91;link&#93;', actual)
        self.assertNotIn('<script>', actual)
        self.assertNotIn('*not italic*', actual)

    def test_unsupported_whole_candidate(self):
        for source in [block(kind='info'), block(attrs=' id="x"'), block().replace('class="callout"','class="callout collapsed"'),
                       block('<p><img src="x"></p>'), block('<table><tr><td>x</td></tr></table>'), block('<p><strong><em>x</em></strong></p>'),
                       block('<p>a  b</p>'), block('<p>a\nb</p>'), block('<p><a href="javascript:x">x</a></p>'),
                       block('<p title="x">x</p>'), block('<p>x</p><div>x</div>'), block('<p><!--x-->x</p>'),
                       block(title='<strong>Title</strong>'), block('<p>x</p>', attrs=' class="callout"'),
                       block('<p>x</p>').replace('</p>', '</p extra>')]:
            with self.subTest(source=source):
                self.assertEqual(self.unchanged(source)['preserved'], 1)

    def test_nested_entire_island_preserved(self):
        self.unchanged(block('<p>outer</p>' + block()))
        self.unchanged('<section>\n\n' + block() + '\n\n</section>')
        self.unchanged('<div>\n\n' + block() + '\n\n</div>')

    def test_literal_contexts(self):
        for source in ['```html\n' + block() + '\n```', '~~~~\n' + block() + '\n~~~~',
                       '   ```\n' + block() + '\n   ```', '    ' + block(), '`' + block() + '`',
                       '<!--\n\n' + block() + '\n\n-->', 'text <!--\n\n' + block() + '\n-->',
                       '---\nexample: |\n' + block() + '\n---', '> ' + block(), 'text\n' + block(),
                       '<script>\n\n' + block() + '\n</script>']:
            self.unchanged(source)

    def test_unterminated_and_malformed(self):
        for source in [block()[:-6], block().replace('</h4>', '</h3>'), block().replace('</p>', ''), block() + 'suffix', block() + '\ntext']:
            self.unchanged(source)

    def test_multiple_blocks_and_idempotent(self):
        source = block() + '\n\n' + block(kind='info') + '\n\n' + block(title='WARNING')
        actual, report = convert(source)
        self.assertEqual((report['converted'], report['preserved']), (2, 1))
        self.assertEqual(convert(actual)[0], actual)

    def test_cli_never_overwrites(self):
        script = str(Path(__file__).resolve().parents[1] / 'callout_bridge.py')
        with tempfile.TemporaryDirectory() as folder:
            source, target = Path(folder)/'in.md', Path(folder)/'out.md'
            source.write_text(block())
            def run(*args):
                return subprocess.run([sys.executable, script, str(source), *map(str,args)], capture_output=True, text=True)
            self.assertEqual(run().returncode, 2)
            checked = run('--check')
            self.assertEqual(checked.returncode, 1)
            self.assertTrue(json.loads(checked.stdout)['changed'])
            self.assertEqual(run('--dry-run').returncode, 0)
            self.assertEqual(run('-o', source).returncode, 2)
            self.assertEqual(source.read_text(), block())
            self.assertEqual(run('-o', target).returncode, 0)
            saved = target.read_bytes()
            self.assertEqual(run('-o', target).returncode, 2)
            self.assertEqual(target.read_bytes(), saved)
            source.write_bytes(b'\xff')
            self.assertEqual(run('--check').returncode, 2)

if __name__ == '__main__':
    unittest.main()
