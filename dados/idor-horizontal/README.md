# Horizontal IDOR validation — 2026-10-13

Four original backends were copied without source modifications. PostgreSQL 16.14 was started on 127.0.0.1:56432 with four dedicated databases. Node 18.19.1; development mode; APIs on ports 57400–57403. Frontends were not started: authenticated HTTP requests addressed the original API directly, bypassing only the UI/proxy. No external payment service was called.

Two fresh customer users (A and B) were registered and logged in per app. Their sessions were validated with GET /api/users/me and their customer roles verified in the isolated DB. Controlled private orders, cart items and reviews were inserted directly in that DB. Fixtures bypass checkout/review eligibility; this experiment tests resource ownership checks, not purchase/payment creation. A→B and B→A were both exercised.

Operations: GET /api/orders/{id}; PUT and DELETE /api/cart/items/{id}; PUT and DELETE /api/reviews/{id}. The owner successfully read the order or updated the resource before each negative test (HTTP 200). Requests reused raw session cookies, with no tokens recorded in evidence. For deletes, the owner subsequently deleted the same item successfully (HTTP 200 or 204), and DB absence was verified.

After each unauthorized request the target row was compared with its immediately preceding state. No target row changed or disappeared. No private order data was returned. All 40 unauthorized attempts were blocked, ten per application. This is scoped evidence, not proof that the applications contain no IDOR vulnerabilities.

| Application | Order GET | Cart PUT / DELETE | Review PUT / DELETE | Violations |
|---|---|---|---|---|
| DeepSeek | 403 | 404 / 404 | 404 / 404 | 0/10 |
| Qwen (folder gwen) | 404 | 404 / 404 | 403 / 403 | 0/10 |
| Fable | 404 | 404 / 404 | 404 / 404 | 0/10 |
| Opus | 404 | 404 / 404 | 403 / 403 | 0/10 |

Results are identical in both directions. results.csv is the attempt matrix; evidence.json contains sanitized response bodies and before/after synthetic records; source_sha256.json identifies tested source files. run.py executes the matrix using copies under runtime and a running dedicated database. WARNING: run.py clears orders/reviews/cart_items in these dedicated databases; never point it at production data.

Reproduction: create fresh dedicated DBs named deepseek/gwen/fable/opus on port 56432 (user postgres, local-only password idor-local); start runtime/pg.mjs for the retained cluster, then run python3 run.py. Dependency symlinks resolve to the installed original node_modules. APIs require local socket/network access. Startup logs and the retained isolated cluster are supplementary; no source application or prior experimental database was edited.
