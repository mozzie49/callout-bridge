"""Independent adversarial preservation checks (synthetic unless stated)."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from callout_bridge import convert


def block(body='ok'):
    return '<div class="callout" data-callout-type="note"><h4>NOTE</h4><p>'+body+'</p></div>'


class PreservationReview(unittest.TestCase):
    def preserved(self, source):
        result, report = convert(source)
        self.assertEqual(result.encode('utf-8'), source.encode('utf-8'))
        self.assertFalse(report['changed'])

    def test_unknown_markup_and_malformed_tags(self):
        for source in [block('a<![CDATA[hidden]]>b'), block().replace('</p>', '</p junk>'),
                       block().replace('<p>', '<p/ >'), block().replace('\" data-callout-type', '\"data-callout-type'), block('<a href="https://a"><a href="https://b">B</a></a>'),
                       block('<strong>a</strong><strong>b</strong>')]:
            with self.subTest(source=source): self.preserved(source)

    def test_indented_unknown_html_context(self):
        for indent in [' ', '  ', '   ']:
            for tag in ['section', 'script', 'style', 'pre', 'textarea']:
                source=indent+'<'+tag+'>\n\n'+block()+'\n\n</'+tag+'>'
                with self.subTest(source=source): self.preserved(source)

    def test_declaration_context(self):
        for opening, closing in [('<![CDATA[',']]>'), ('<?xml','?>'), ('<!DOCTYPE html [',']>')]:
            source=opening+'\n\n'+block()+'\n\n'+closing
            with self.subTest(source=source): self.preserved(source)

    def test_delimiter_ambiguity_preserved(self):
        self.preserved(block('a<strong>!</strong>b'))
        self.preserved(block('a<em>!</em>b'))

    def test_unknown_attributes_entities_and_whitespace(self):
        for body in ['<em title="x">x</em>', '<a href="https://x" target="_blank">x</a>',
                     '&unknown;', 'a\tb', '<img src="x">', '<!--hidden-->ok']:
            with self.subTest(body=body): self.preserved(block(body))

    def test_surrounding_bytes_and_second_pass(self):
        prefix='\ufeff序言\r\n\r\n'; suffix='\r\n\r\n尾声\t  \r\n'
        source=prefix+block()+suffix
        result, report=convert(source)
        self.assertEqual(report['converted'],1)
        self.assertTrue(result.startswith(prefix)); self.assertTrue(result.endswith(suffix))
        self.assertEqual(convert(result)[0], result)

    def test_unusual_line_separators_do_not_corrupt_source(self):
        for sep in ['\v', '\f', '\x85', '\u2028', '\u2029', '\r']:
            source=block().replace('</h4>', '</h4>'+sep*3)+'\n\nTAIL'
            result, report=convert(source)
            with self.subTest(separator=repr(sep)):
                self.assertTrue(result == source or result == '> [!NOTE]\n> ok\n\nTAIL')

    def test_output_symlinks_and_invalid_utf8(self):
        script=Path(__file__).resolve().parents[1]/'callout_bridge.py'
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); source=root/'source.md'; target=root/'target.md'; dangling=root/'dangling.md'
            original=block().encode(); source.write_bytes(original)
            target.symlink_to(source); dangling.symlink_to(root/'missing.md')
            for output in [source,target,dangling]:
                proc=subprocess.run([sys.executable,str(script),str(source),'-o',str(output)],capture_output=True)
                self.assertEqual(proc.returncode,2); self.assertEqual(source.read_bytes(),original)
            self.assertFalse((root/'missing.md').exists())
            source.write_bytes(b'\xff')
            fresh=root/'fresh.md'
            proc=subprocess.run([sys.executable,str(script),str(source),'-o',str(fresh)],capture_output=True)
            self.assertEqual(proc.returncode,2); self.assertFalse(fresh.exists())

if __name__=='__main__': unittest.main()
