# Validation — 0.1.0-experimental

Local validation uses Python 3.12 (standard library only):

```sh
python -m unittest discover -s tests -v
python -m py_compile callout_bridge.py
python callout_bridge.py tests/fixtures/converter/simple.converter.md --dry-run --map info=NOTE
```

22 unittest methods passed, including independently authored adversarial reviewer regressions with additional subcases. Tested: supported conversions, explicit mappings, converter-level fixture fidelity, preservation of unsupported islands, malformed syntax, nested markup, literal Markdown contexts, unusual separators, CRLF/surrounding bytes, idempotence, UTF-8 failure, no-overwrite and symlink refusal. The simple pinned-converter fixture converts one block with explicit info→NOTE mapping and zero preserved warnings. The eight-type fixture with info→NOTE and warn→WARNING converts two and preserves six.

GitHub Actions matrix is prepared for Python 3.10/3.12/3.13; remote CI has **not run**. No publishing, repository push, or live Notesnook application/export verification occurred. This is a reviewable experimental CLI, not a guarantee against every malformed HTML or Markdown dialect input. The tool does not sanitize unsafe HTML left in preserved input.

Source provenance and optional reproduction harness: `proof/`. Tests do not execute npm or need external packages. Upstream `<precode>` missing-content evidence is described there; postprocessing cannot recover absent code.
