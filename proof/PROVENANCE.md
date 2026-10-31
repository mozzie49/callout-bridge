# Notesnook converter-level proof (not app-export evidence)

Generated 2026-10-31 in isolated Node v24.22.1 / npm 11.9.0 environment.

## Scope and limits
These are synthetic, original HTML test inputs following the publicly documented editor serialization shape. Their `.converter.md` counterparts are genuine outputs of the exact pinned conversion library and flavor used by Notesnook. No Notesnook UI, account, full app export, attachment rewrite, internal-link rewrite, archive generation, browser DOM, or user data was exercised. The DOM implementation is linkedom 0.14.26 (a Notesnook core locked dependency), not a verified browser runtime. This is converter-level compatibility evidence, not a real Notesnook app-export fixture.

The motivating issue https://github.com/streetwriters/notesnook/issues/10023 is open, has no comments or exported attachments at inspection. It reports raw HTML callouts in Markdown. No authentic user-export attachment was located in that issue.

## Pinned upstream sources
Repository streetwriters/notesnook commit `e1bf280a75bb4c4bb55372b34e1cb2e4f35f2188`:
- https://github.com/streetwriters/notesnook/blob/e1bf280a75bb4c4bb55372b34e1cb2e4f35f2188/packages/editor/src/extensions/callout/callout.ts : div.callout, data-callout-type, content heading block*, default heading level 4; collapsed is additional class.
- https://github.com/streetwriters/notesnook/blob/e1bf280a75bb4c4bb55372b34e1cb2e4f35f2188/packages/core/src/content-types/tiptap.ts : sets showdown.helper.document to getDummyDocument(), new Converter(), setFlavor('original'), makeMarkdown(this.data).
- https://github.com/streetwriters/notesnook/blob/e1bf280a75bb4c4bb55372b34e1cb2e4f35f2188/packages/core/src/utils/html-parser.ts : dummy document created via DOMParser with wrapped HTML.
- https://github.com/streetwriters/notesnook/blob/e1bf280a75bb4c4bb55372b34e1cb2e4f35f2188/packages/core/package-lock.json : exact versions/integrities retained in upstream-lock-excerpt.json.
- https://github.com/streetwriters/notesnook/blob/e1bf280a75bb4c4bb55372b34e1cb2e4f35f2188/packages/common/src/utils/export-notes.ts : export entry-point context, previously traced by parent agent.

## Reproduction
```sh
cd proof
npm ci --ignore-scripts --no-audit --no-fund
node reproduce.cjs
sha256sum -c SHA256SUMS
```
Run these commands from the project root; the optional harness creates `proof/fixtures/`. The shipped regression copies are in `tests/fixtures/converter/`. Installing the optional research dependencies requires network access and appropriate authorization; the Python CLI and tests need neither.

## Results
All four cases execute successfully:
- simple: surrounding paragraphs become Markdown; callout and its inline markup remain raw HTML.
- types: all eight issue-mentioned callout types remain raw HTML.
- nested: nesting, collapsed class, custom title, and list remain HTML. This is intentionally outside the MVP conversion subset.
- code: converter substitutes `<precode language="js" precodenum="0"></precode>` inside raw callout; original code is absent from Markdown. This is preexisting converter-level data loss, not recoverable by an exported-Markdown postprocessor. Preserve and warn; never invent the code.

The substitution happens before outerHTML fallback in installed showdown dist/showdown.js; fallback serializes the whole div without resolving nested precode placeholders. Assertions verify this observed behavior.

## Licensing
Notesnook inspected source is GPL-3.0-or-later, copyright Streetwriters. No full Notesnook source is copied into the deliverable. The original harness calls public APIs; synthetic fixture text is newly authored here. @streetwriters/showdown 3.0.9-alpha reports MIT, linkedom 0.14.26 ISC; their installed package license files remain in node_modules. The package lock records transitive dependency versions. Do not bundle node_modules merely to distribute these fixtures. Attribution and this limitation statement should accompany any copied fixtures.
