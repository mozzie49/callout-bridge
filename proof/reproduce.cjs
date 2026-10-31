// Original research harness. Synthetic inputs; NOT an actual Notesnook app export.
const fs = require('node:fs');
const assert = require('node:assert/strict');
const showdown = require('@streetwriters/showdown');
const { DOMParser } = require('linkedom');
showdown.helper.document = new DOMParser().parseFromString('<!doctype html><html lang="en"><head><title>Document Fragment</title></head><body><div></div></body></html>', 'text/html');
const converter = new showdown.Converter();
converter.setFlavor('original');
const cases = {
  simple: '<p>Before callout.</p><div data-callout-type="info" class="callout"><h4>INFO</h4><p>A <strong>bold</strong> point with <a href="https://example.com">a link</a>.</p></div><p>After callout.</p>',
  types: ['abstract','hint','info','success','warn','error','example','quote'].map(type => `<div data-callout-type="${type}" class="callout"><h4>${type.toUpperCase()}</h4><p>Body for ${type}.</p></div>`).join(''),
  nested: '<div data-callout-type="warn" class="collapsed callout"><h4>Custom title</h4><p>Outer body.</p><div data-callout-type="hint" class="callout"><h4>HINT</h4><p>Inner body.</p></div><ul><li><p>First</p></li><li><p>Second</p></li></ul></div>',
  code: '<div data-callout-type="example" class="callout"><h4>EXAMPLE</h4><p>Code follows.</p><pre><code data-language="js">const n = 1;\nconsole.log(n);</code></pre></div>',
};
fs.mkdirSync('fixtures', {recursive:true});
for (const [name, html] of Object.entries(cases)) {
  const md = converter.makeMarkdown(html);
  fs.writeFileSync(`fixtures/${name}.input.html`, html);
  fs.writeFileSync(`fixtures/${name}.converter.md`, md);
  assert(md.includes('class="') && md.includes('callout'));
  console.log(name, JSON.stringify(md));
}
assert(fs.readFileSync('fixtures/simple.converter.md','utf8').includes('<strong>bold</strong>'));
assert(fs.readFileSync('fixtures/code.converter.md','utf8').includes('<precode'));
assert(!fs.readFileSync('fixtures/code.converter.md','utf8').includes('console.log'));
console.log('PASS: raw HTML fallback reproduced; upstream precode placeholder content loss reproduced.');
