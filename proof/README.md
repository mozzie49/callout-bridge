# Optional converter-level proof

The Python CLI/tests need no npm dependencies. These research files reproduce the converter-generated synthetic fixtures, not a live app export.

From this directory, in an isolated workspace with network/install authorization:

```sh
npm ci --ignore-scripts --no-audit --no-fund
node reproduce.cjs
sha256sum -c SHA256SUMS
```

The harness creates `fixtures/`; compare with `../tests/fixtures/converter/`. See PROVENANCE.md for the original execution environment, upstream pins, license attribution, and missing-code observation. No node_modules are bundled. Running this optional research harness is not necessary to use CalloutBridge.
