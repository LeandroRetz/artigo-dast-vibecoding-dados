# Appendix D — final reproduction of high-severity alerts

The final evaluation on **10 September 2026** covered all **18 unique high-severity alerts**: eight in DeepSeek, nine in Opus, one in Qwen and none in Fable. It supersedes the earlier partial reproduction, whose conclusions applied only to a subset.

The authoritative final matrix is [`../dados/_validacao-high.csv`](../dados/_validacao-high.csv). Legacy identifiers, original payloads and recorded Portuguese observations are retained verbatim. The retained script is `08-validar-high.py`; it requires the original application paths, Docker test environment and snapshot preparation scripts.

## Conditions and controls

Applications ran in the production containers and scan override used for the original ZAP evaluation. Source was unchanged. Each database was restored to its scan snapshot rather than reseeded. The session cookie was captured and verified on `/api/users/me` before tests. Tests ran one application at a time and discarded their changed test state afterwards.

- Comparison-based SQL/NoSQL: replay the scanner payload and discriminating controls, then check whether values were interpreted or persisted literally.
- Time-based SQL: interleave scanner payloads and random-string controls, five repetitions each, compare medians and inspect persisted values.
- Traversal/disclosure: replay the scanner value, its random-string reference and file-path probes; inspect returned content rather than treating an error status as proof of disclosure.
- Template injection: replay the expression and locate the expected value within the original evidence to distinguish evaluation from an incidental match.

## Interpretation

All 18 were classified as false positives in the exercised reproductions. PostgreSQL did not interpret SQLite `randomblob` or MongoDB operators. Duplicate product names generated the same failure with and without injection syntax. Other alerts arose from type/identifier rejection without file content or an incidental UUID substring matching the template rule's expected value. These mechanisms refute the reported injection/disclosure claims for the tested cases, while a duplicate-name error can still represent a separate error-handling defect.

No overall precision/recall estimate follows: only high-severity alerts were reproduced, crawling coverage was not measured, and a complete ground-truth vulnerability inventory is unavailable. Unvalidated medium/low/informational alerts remain scanner output. The low SQLi threshold and experimental add-ons are relevant to over-reporting, not sufficient explanations for every result or claims about the scanner in general.

## Complete alert index

| ID | Application identifier | Alert | Endpoint | Parameter | Verdict |
|---|---|---|---|---|---|
| D1 | deepseek-mini-v4 | NoSQL Injection - MongoDB | /api/products | search | False positive |
| D2 | deepseek-mini-v4 | Path Traversal | /api/admin/products/{id} | category_id | False positive |
| D3 | deepseek-mini-v4 | SQL Injection | /api/admin/products | name | False positive |
| D4 | deepseek-mini-v4 | SQL Injection | /api/users/me | email | False positive |
| D5 | deepseek-mini-v4 | SQL Injection - SQLite (Time Based) | /api/checkout | city | False positive |
| D6 | deepseek-mini-v4 | SQL Injection - SQLite (Time Based) | /api/checkout | line2 | False positive |
| D7 | deepseek-mini-v4 | SQL Injection - SQLite (Time Based) | /api/checkout | postalCode | False positive |
| D8 | deepseek-mini-v4 | Source Code Disclosure - File Inclusion | /api/admin/products/{id} | category_id | False positive |
| O1 | opus | Path Traversal | /api/users/me | postalCode | False positive |
| O2 | opus | Path Traversal | /api/checkout | postalCode | False positive |
| O3 | opus | SQL Injection | /api/admin/categories | name | False positive |
| O4 | opus | Source Code Disclosure - File Inclusion | /api/admin/products/{id} | categoryId | False positive |
| O5 | opus | Source Code Disclosure - File Inclusion | /api/users/me | postalCode | False positive |
| O6 | opus | SQL Injection - SQLite (Time Based) | /api/checkout | country | False positive |
| O7 | opus | SQL Injection - SQLite (Time Based) | /api/checkout | line1 | False positive |
| O8 | opus | SQL Injection - SQLite (Time Based) | /api/checkout | name | False positive |
| O9 | opus | Server Side Template Injection | /api/checkout | country | False positive |
| Q1 | qwen-3.8-8b | Source Code Disclosure - File Inclusion | /api/cart/items/{id} | quantity | False positive |
