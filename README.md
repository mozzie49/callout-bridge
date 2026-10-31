# CalloutBridge 0.1.0-experimental

Conservative Notesnook → GitHub alert repair.

A dependency-free Python 3.10+ CLI and agent skill. It repairs a **small, explicit subset** of raw HTML callouts in exported Markdown. This is not a generic HTML converter, sanitizer, or backup tool. Independently authored; no Notesnook GPL implementation copied.

## Quick start

```sh
python callout_bridge.py notes.md --dry-run --map info=NOTE --map warn=WARNING
python callout_bridge.py notes.md --check --map info=NOTE --map warn=WARNING
python callout_bridge.py notes.md --output repaired.md --map info=NOTE --map warn=WARNING
python -m unittest discover -s tests -v
```

All modes print JSON reports with changed/converted/preserved counts, per-candidate line numbers, and the source/target mapping for each conversion. Explicit mappings are user-selected semantic changes, not claimed lossless equivalences. `--check` exits 1 when conversion is available, 0 otherwise; preserved warnings do **not** imply clean compatibility. `--dry-run` exits 0 on successful inspection. I/O/UTF-8 errors exit 2. Output requires a new file; existing files (including input) are never overwritten. Review warnings and diff before adopting output. UTF-8 only; no recursive folders, network access, or package installation required.

### Explicit type mapping

Default conversion recognizes only `note`, `tip`, `important`, `warning`, `caution`, mapped to the corresponding GitHub label. Current Notesnook uses other names (including `info`, `warn`, `hint`, `abstract`, `success`, `error`, `example`, `quote`), so **real Notesnook-shaped input normally requires `--map`**. No semantic equivalence is assumed: choose only mappings appropriate for your notes, e.g. `--map info=NOTE`. Custom/default source titles are retained as bold text unless exactly equal to the target alert label. Unmapped types remain byte-for-byte intact with warnings.

### Narrow supported subset

- Standalone, column-zero `div` after a blank boundary (or start of document), followed by a blank boundary or EOF.
- Exactly quoted, whitespace-separated `class="callout"` and `data-callout-type` attributes; no other wrapper attributes.
- Plain-text `h4` title, followed by `p` blocks; text, simple `strong`/`em`, absolute HTTP(S) links with text-only labels, inline `code`, and `br`.
- HTML-sensitive Markdown punctuation is encoded as numeric entities so text does not become unintended formatting. Output favors conservative meaning over pretty Markdown source.
- Original content outside converted candidates is preserved, including CRLF. Unsupported candidates stay byte-for-byte unchanged, with a reason.

Collapsed state, nested callouts, unknown tags/attributes, lists, tables, images, raw code blocks, HTML comments/declarations, complex whitespace, formatted headings, nested or adjacent inline markup, and malformed structures are intentionally not converted. Fences, indented/inline examples, comments, frontmatter and enclosing HTML islands are skipped. Skipped non-candidate contexts are not counted as warnings. This is a deliberately conservative scanner, not a full CommonMark parser: preservation tests are evidence for covered cases, not a guarantee for every Markdown dialect.

## Evidence and limits

Demand: [Notesnook issue #10023](https://github.com/streetwriters/notesnook/issues/10023). Structural reference: [pinned callout serialization schema](https://github.com/streetwriters/notesnook/blob/e1bf280a75bb4c4bb55372b34e1cb2e4f35f2188/packages/editor/src/extensions/callout/callout.ts).

`examples/before.md` is a newly authored **source-derived fixture, not a real application export**. `tests/fixtures/converter/` contains synthetic inputs processed by the exact pinned Notesnook conversion library, with provenance. These are **converter-level outputs**, not live app/browser/full export verification. No real user exports were tested.

The converter-level code fixture exposes upstream `<precode>` placeholders where original code is missing. CalloutBridge preserves these and warns; it cannot recover data already absent from the input. Keep your original Notesnook data and backups.

## 中文说明

这是一个保守的 Notesnook Markdown 修复工具：仅把明确支持的原始 HTML 提示块转换为 GitHub Alerts。Python 3.10+，无需第三方依赖。

先运行 `--dry-run` 查看 JSON 报告，再用 `--output 新文件.md` 生成副本。工具不会覆盖任何已有文件。`--check` 在有可转换内容时返回 1；有保留警告并不代表完全兼容。

Notesnook 的 `info`、`warn` 等类型不会被默认猜测映射；需要显式提供 `--map info=NOTE --map warn=WARNING`，并人工确认语义。未映射类型、折叠块、嵌套、复杂 HTML 或格式异常全部保留原字节并报告原因。只支持独立顶层块、简单标题和段落，以及有限的加粗、斜体、链接、行内代码与换行。

测试素材包含自行编写的源码结构示例，以及固定版本转换库生成的合成输出；**不是用户真实导出，也未验证完整应用导出流程**。某些代码块在上游已变成 `<precode>` 占位符，本工具无法恢复丢失代码。请保留原笔记，检查差异和警告后再采用输出。
