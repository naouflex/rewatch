# API docs static assets

These files are vendored to keep `/api/docs/` Content-Security-Policy friendly:
no inline scripts, no external CDN fetches.

## Files

| File                    | Purpose                                                                   |
| ----------------------- | ------------------------------------------------------------------------- |
| `scalar.standalone.js`  | Scalar API Reference standalone bundle that mounts `<script id="api-reference">` automatically. |

## Bumping `scalar.standalone.js`

```bash
SCALAR_VERSION=1.55.1   # bump as needed
curl -sSL \
  "https://cdn.jsdelivr.net/npm/@scalar/api-reference@${SCALAR_VERSION}/dist/browser/standalone.js" \
  -o redash/handlers/api_docs_static/scalar.standalone.js
sha256sum redash/handlers/api_docs_static/scalar.standalone.js
```

Then update the `Vendored Scalar version` table below.

| Vendored Scalar version | SHA-256                                                            |
| ----------------------- | ------------------------------------------------------------------ |
| `1.55.1`                | `4ce2b8b11c4c4a95ecce9014dfdf3ba272c30795bfea4103a2f7203432ab51fe` |

## Why vendored, not CDN?

1. CSP: loading from a CDN would force `script-src` to allow that origin.
2. Reproducibility: airgapped / offline docker builds keep working.
3. Auditability: the file is in git, so version bumps are reviewable.
