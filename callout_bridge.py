#!/usr/bin/env python3
"""Conservative, independently written Notesnook callout repair (Python 3.10+)."""
import argparse
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys

TYPES = {x: x.upper() for x in ('note', 'tip', 'important', 'warning', 'caution')}
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

class Unsupported(ValueError):
    pass

class Island(HTMLParser):
    """Locate the closing tag of a top-level HTML island, without rewriting it."""
    def __init__(self, source):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.lines = [0] + [m.end() for m in re.finditer('\n', source)]
        self.stack = []
        self.end = None
        self.bad = False
    def source_offset(self):
        line, col = self.getpos()
        return self.lines[line - 1] + col
    def handle_starttag(self, tag, attrs):
        if self.end is None and tag not in VOID:
            self.stack.append(tag)
    def handle_startendtag(self, tag, attrs):
        if not self.stack and self.end is None:
            self.end = self.source_offset() + len(self.get_starttag_text())
    def handle_endtag(self, tag):
        if self.end is not None:
            return
        if not self.stack or self.stack[-1] != tag:
            self.bad = True
            return
        self.stack.pop()
        if not self.stack:
            self.end = self.source.find('>', self.source_offset()) + 1

class Tree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.root = ['ROOT', {}, []]
        self.stack = [self.root]
    def handle_starttag(self, tag, attrs):
        if not re.fullmatch(r'''<[A-Za-z][A-Za-z0-9]*(?:\s+[A-Za-z_:][\w:.-]*\s*=\s*(?:"[^"]*"|'[^']*'))*\s*/?>''', self.get_starttag_text()):
            raise Unsupported('unsupported or malformed start-tag syntax')
        if re.search(r'/\s+>', self.get_starttag_text()):
            raise Unsupported('malformed self-closing syntax')
        if tag not in {'div', 'h4', 'p', 'strong', 'em', 'a', 'code', 'br'}:
            raise Unsupported('unsupported HTML tag: ' + tag)
        if len(dict(attrs)) != len(attrs):
            raise Unsupported('duplicate attributes')
        if self.get_starttag_text() != self.get_starttag_text().strip():
            raise Unsupported('invalid tag')
        node = [tag, dict(attrs), []]
        self.stack[-1][2].append(node)
        if tag != 'br':
            self.stack.append(node)
    def handle_startendtag(self, tag, attrs):
        if tag != 'br':
            raise Unsupported('unsupported self-closing tag')
        self.handle_starttag(tag, attrs)
    def handle_endtag(self, tag):
        if len(self.stack) == 1 or self.stack[-1][0] != tag:
            raise Unsupported('unbalanced HTML')
        self.stack.pop()
    def handle_data(self, data):
        if '<' in data:
            raise Unsupported('ambiguous HTML text')
        self.stack[-1][2].append(data)
    def handle_entityref(self, name):
        raw = '&' + name + ';'
        if html.unescape(raw) == raw:
            raise Unsupported('unknown HTML entity')
        self.stack[-1][2].append(html.unescape(raw))
    def handle_charref(self, name):
        self.stack[-1][2].append(html.unescape('&#' + name + ';'))
    def handle_comment(self, data):
        raise Unsupported('HTML comments inside callout')
    def handle_decl(self, data):
        raise Unsupported('HTML declaration')
    def unknown_decl(self, data):
        raise Unsupported("unknown HTML declaration")
    def handle_pi(self, data):
        raise Unsupported('processing instruction')


def escape(text):
    # Encode punctuation: prevent HTML text from becoming Markdown syntax.
    return ''.join('&#%d;' % ord(c) if c in '&<>\\`*_{}[]()#+-.!|~' else c for c in text)


def inline(children):
    out = []
    previous_markup = False
    for node_index, node in enumerate(children):
        if not isinstance(node, str) and previous_markup:
            raise Unsupported("adjacent inline markup")
        previous_markup = not isinstance(node, str)
        if isinstance(node, str):
            if re.search(r'[\x00-\x1f\x7f\x85\u2028\u2029]', node) or '\n' in node or '\r' in node or '\t' in node or '  ' in node:
                raise Unsupported('whitespace requiring HTML layout semantics')
            out.append(escape(node))
            continue
        tag, attrs, kids = node
        if tag == 'a':
            if set(attrs) != {'href'} or not re.fullmatch(r'https?://[^\s<>"\\]+', attrs['href'] or ''):
                raise Unsupported('unsupported link attributes or destination')
            if any(not isinstance(k, str) for k in kids):
                raise Unsupported('formatted link label')
            target = attrs['href'].replace('&', '&amp;')
            out.append('[' + inline(kids) + '](<' + target + '>)')
        elif attrs:
            raise Unsupported('unsupported inline attributes')
        elif tag in {'strong', 'em'}:
            before = children[node_index - 1] if node_index else ''
            after = children[node_index + 1] if node_index + 1 < len(children) else ''
            if (isinstance(before, str) and before and before[-1].isalnum()) or (isinstance(after, str) and after and after[0].isalnum()):
                raise Unsupported('ambiguous emphasis boundaries')
            if any(not isinstance(k, str) for k in kids):
                raise Unsupported('nested emphasis markup')
            value = inline(kids)
            if not value or value != value.strip():
                raise Unsupported('ambiguous emphasis spacing')
            mark = '**' if tag == 'strong' else '*'
            out.append(mark + value + mark)
        elif tag == 'code':
            if any(not isinstance(k, str) for k in kids):
                raise Unsupported('nested markup in code')
            value = ''.join(kids)
            if not value or re.search(r'[\x00-\x1f\x7f\x85\u2028\u2029]', value) or '  ' in value or value != value.strip():
                raise Unsupported('unsupported code whitespace')
            ticks = '`' * (max([len(x) for x in re.findall(r'`+', value)] or [0]) + 1)
            pad = ' ' if value.startswith('`') or value.endswith('`') else ''
            out.append(ticks + pad + value + pad + ticks)
        elif tag == 'br' and not kids:
            out.append('  \n')
        else:
            raise Unsupported('unsupported inline nesting: ' + tag)
    return ''.join(out)


def render(raw, newline, mappings):
    if re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\x85\u2028\u2029]', raw):
        raise Unsupported('unsupported control or line separator')
    if re.search(r'</[^>]*>', raw) and any(not re.fullmatch(r'</[A-Za-z][A-Za-z0-9]*\s*>', t) for t in re.findall(r'</[^>]*>', raw)):
        raise Unsupported('malformed closing tag')
    parser = Tree()
    parser.feed(raw)
    parser.close()
    if len(parser.stack) != 1 or len(parser.root[2]) != 1:
        raise Unsupported('malformed HTML')
    tag, attrs, kids = parser.root[2][0]
    if tag != 'div' or set(attrs) != {'class', 'data-callout-type'} or attrs['class'] != 'callout':
        raise Unsupported('unsupported wrapper attributes or collapsed callout')
    kind = attrs['data-callout-type']
    if kind not in mappings:
        raise Unsupported('unsupported or lossy callout type: ' + str(kind))
    blocks = [k for k in kids if not (isinstance(k, str) and not k.strip())]
    if not blocks or isinstance(blocks[0], str) or blocks[0][0] != 'h4':
        raise Unsupported('missing h4 title')
    rendered = []
    for index, node in enumerate(blocks):
        if isinstance(node, str) or node[1] or node[0] != ('h4' if index == 0 else 'p'):
            raise Unsupported('unsupported block body or attributes')
        if index == 0 and any(not isinstance(k, str) for k in node[2]):
            raise Unsupported('formatted title')
        value = inline(node[2])
        if not value or value != value.strip():
            raise Unsupported('empty or padded block')
        if index == 0:
            if value == mappings[kind]:
                continue
            value = '**' + value + '**'
        rendered.append(value)
    if not rendered:
        raise Unsupported('empty callout body')
    body = '\n\n'.join(rendered)
    return ('> [!' + mappings[kind] + ']\n' + '\n'.join('> ' + line if line else '>' for line in body.split('\n'))).replace('\n', newline)


def convert(source, mappings=None):
    explicit_mappings = set(mappings or {})
    if mappings and any(not re.fullmatch('[a-z][a-z0-9_-]*', k) or v not in TYPES.values() for k, v in mappings.items()):
        raise ValueError('invalid explicit callout mapping')
    mappings = dict(TYPES) if mappings is None else {**TYPES, **mappings}
    lines = re.findall(r'[^\n]*\n|[^\n]+$', source)
    out, events = [], []
    i = 0
    fence = None
    frontmatter = bool(lines and lines[0].strip() == '---')
    while i < len(lines):
        line = lines[i]
        if frontmatter:
            out.append(line)
            if i > 0 and line.strip() in {'---', '...'}:
                frontmatter = False
            i += 1
            continue
        match = re.match(r' {0,3}(`{3,}|~{3,})(.*)', line)
        if fence:
            out.append(line)
            if re.fullmatch(r' {0,3}' + re.escape(fence[0]) + '{' + str(fence[1]) + r',}[ \t]*(?:\r?\n)?', line):
                fence = None
            i += 1
            continue
        if match and not (match[1][0] == '`' and '`' in match[2]):
            fence = (match[1][0], len(match[1]))
            out.append(line)
            i += 1
            continue
        # Only standalone column-zero HTML islands after a blank boundary.
        if re.match(r' {0,3}<', line) or '<!--' in line:
            remainder = ''.join(lines[i:])
            if '<!--' in line:
                end = remainder.find('-->')
                end = len(remainder) if end < 0 else end + 3
            elif re.match(r' {0,3}<', line) and line.lstrip().startswith(('<!', '<?')):
                # Unsupported declarations can contain arbitrary markup; preserve remainder.
                end = len(remainder)
            elif re.match(r' {0,3}<[A-Za-z][\w-]*(?:\s|>)', line):
                island = Island(remainder)
                try:
                    island.feed(remainder)
                except Exception:
                    island.bad = True
                end = island.end or len(remainder)
            else:
                end = len(line)
            n = remainder[:end].count('\n') + (not remainder[:end].endswith('\n'))
            n = max(n, 1)
            chunk = ''.join(lines[i:i + n])
            candidate = bool(re.match(r'<div\b', line, re.I) and re.search(r'\bcallout\b', remainder.split('>', 1)[0]))
            if candidate:
                reason = None
                try:
                    if (i > 0 and lines[i - 1].strip()) or chunk[end:].strip() or (i + n < len(lines) and lines[i + n].strip()):
                        raise Unsupported('callout is not an isolated block')
                    raw = remainder[:end]
                    newline = '\r\n' if '\r\n' in raw or line.endswith('\r\n') else '\n'
                    replacement = render(raw, newline, mappings) + chunk[end:]
                except (Unsupported, ValueError, RecursionError) as exc:
                    reason = str(exc)
                    replacement = chunk
                mapping_info = None
                if not reason:
                    parsed = Tree()
                    parsed.feed(raw)
                    source_type = parsed.root[2][0][1]['data-callout-type']
                    mapping_info = {'source': source_type, 'target': mappings[source_type], 'explicit': source_type in explicit_mappings}
                events.append({'mapping': mapping_info, 'line': i + 1, 'status': 'preserved' if reason else 'converted', 'reason': reason})
                out.append(replacement)
            else:
                out.append(chunk)
            i += n
            continue
        out.append(line)
        i += 1
    result = ''.join(out)
    return result, {'changed': result != source, 'converted': sum(e['status'] == 'converted' for e in events), 'preserved': sum(e['status'] == 'preserved' for e in events), 'events': events}


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('input', type=Path)
    mode = cli.add_mutually_exclusive_group(required=True)
    mode.add_argument('-o', '--output', type=Path, help='create a new file; existing paths are never overwritten')
    mode.add_argument('--check', action='store_true', help='JSON report only; exit 1 if changes are available')
    mode.add_argument('--dry-run', action='store_true', help='JSON report only; exit 0 on successful inspection')
    cli.add_argument('--map', action='append', default=[], metavar='SOURCE=ALERT', help='explicit semantic mapping to NOTE/TIP/IMPORTANT/WARNING/CAUTION; repeatable')
    args = cli.parse_args(argv)
    mappings = {}
    for mapping in args.map:
        pair = mapping.split('=')
        if len(pair) != 2 or not re.fullmatch('[a-z][a-z0-9_-]*', pair[0]) or pair[1] not in TYPES.values() or pair[0] in mappings:
            cli.error('each --map must be a unique lowercase SOURCE=NOTE|TIP|IMPORTANT|WARNING|CAUTION')
        mappings[pair[0]] = pair[1]
    try:
        data = args.input.read_bytes()
        result, report = convert(data.decode('utf-8'), mappings)
        if args.output:
            with args.output.open('xb') as stream:
                stream.write(result.encode('utf-8'))
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1 if args.check and report['changed'] else 0
    except (OSError, UnicodeError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2

if __name__ == '__main__':
    sys.exit(main())
