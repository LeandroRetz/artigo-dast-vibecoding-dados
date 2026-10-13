# Appendix C — OWASP ZAP configuration

The same frozen image, add-ons and automation plan were used for four applications and two access profiles (eight runs).

## Environment

| Item | Recorded value |
|---|---|
| ZAP | 2.17.0 |
| Base image | `zaproxy/zap-stable` |
| Base digest | `sha256:781a2bdaea47324e7bab583e2263f21d257b0aee61ed51521a5be45f5f5081ef` |
| Frozen image | `zap-pesquisa:congelado` |
| Runtime | Java 17.0.20; recorded heap 5,951 MB |

The image was frozen before the first scan. The retained Dockerfile and environment inventory provide reproduction detail.

## Add-ons

| Add-on | Version | Channel |
|---|---|---|
| ascanrules | 83.0.0 | release |
| ascanrulesBeta | 66.0.0 | beta |
| ascanrulesAlpha | 58.0.0 | alpha |
| spiderAjax | 23.32.0 | release |
| accessControl | 13.0.0 | alpha |
| jwt | 1.0.3 | alpha |
| reports | 0.46.0 | release |
| automation | 0.60.0 | beta |

Freezing versions ensures common rules, not their correctness. Alpha/beta maturity is an explicit limitation. Installing an add-on does not prove that each contextual vulnerability class was exercised.

## Parameters

| Parameter | Value |
|---|---|
| Default strength / threshold | medium / medium |
| Traditional spider | 5 minutes, depth 10 |
| AJAX spider | 5 minutes, firefox-headless |
| Maximum active scan | 90 minutes |
| Maximum per rule | 10 minutes |
| Threads per host | 5 |
| scanOnlyInScope | true |
| maxAlertsPerRule | 0, unlimited |

SQLi rules 40018, 40019, 40020, 40021, 40022 and 40024 use high strength / low threshold. Reflected and persistent XSS rules 40012 and 40014 use high / medium. Rules 40009, 90019, 90020, 6 and 7 use medium / medium. Other installed rules remain enabled at defaults. Lower SQLi thresholds favour sensitivity and require careful false-positive validation. An obsolete rule ID 90018 was removed after ZAP rejected it.

## Job sequence and authentication

1. Inject an externally obtained session cookie using `replacer`.
2. Configure passive scanning and the dedicated active policy.
3. Run the traditional spider and then AJAX spider.
4. Wait for the passive queue.
5. Run active tests.
6. Export `traditional-json-plus` and `traditional-html`.

The context is the application origin, `localhost:5173`. Stripe domains and logout routes are excluded. Logout exclusion preserves the scan session and means post-logout token replay is outside this automated workflow.

Login is performed before the scan; the raw cookie is injected into requests and validated against `/api/users/me`. This permits authenticated testing over the local HTTP transport even where Secure cookies would not normally be replayed by the client. Cookie attributes in application responses remain unchanged. The session audit records Secure for Fable and Opus; an earlier prose count of three applications should not replace that recorded matrix.

After each run, confirm successful active-scan completion, valid recognised parameters, nonempty reports, authenticated discovery and consistency of served-code fingerprints across both profiles. URL discovery counts are diagnostic, not a measured percentage of reachable coverage.
