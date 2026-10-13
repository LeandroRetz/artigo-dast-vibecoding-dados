# Appendix B — execution-enabling changes

No security remediation was performed after generation. Authentication/authorisation middleware, validation, CORS, response headers and secrets were retained for evaluation.

| Legacy identifier | Source change | Reason |
|---|---|---|
| `deepseek-mini-v4` | Add one `"build": "tsc"` entry to `backend/package.json` | Only backend lacking a compilation script; its existing tsconfig already defines source/output directories |
| `opus` | Add five lines of `/api` proxy configuration to `frontend/vite.config.js` | Make the API reachable at the common scanned origin instead of obtaining zero API coverage |
| `qwen-3.8-8b` | None | Existing source supports preparation |
| `fable5` | None | Existing source supports preparation |

All four additionally received a separate `docker-compose.dast.yml` override, leaving the original Compose files unchanged. The override serves compiled backend code with `NODE_ENV=production` and the frontend through `vite build`/`vite preview`, avoiding development-server resources such as `/@vite/client` and `/node_modules/.vite/deps/`.

For Opus, the API base URL was set to the scanned origin and `/api` was proxied to the backend. This is a scan-topology intervention and a threat to strict non-intervention. Scanning only backend ports would exclude SPA resources; scanning both origins could duplicate findings in implementations already using a proxy. The chosen change does not modify security middleware or validation.

Before scanning, dedicated volumes were cleared; experiment accounts were registered through the public API, and the administrative role was set in the database. A cart item, paid test-mode order and review were prepared per account. The resulting database snapshot was restored between profiles. Original seed records and application-specific hashes/commits remain the authoritative provenance.

The supplementary horizontal tests use copies of the retained backends and separate databases. They do not modify application source and do not repeat the original production scan.
