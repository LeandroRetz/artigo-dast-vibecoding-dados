# Appendix A — English reading copy of the specification

This translation is a reading aid. The original Portuguese `A-especificacao.md` remains the experimental input. Do not replace the original when reproducing the generation. Task states in the recovered copies were marked after generation; the requirements are identical.

Notation: `!` required; `⊥` prohibited; `?` open question settled by a technical decision; usual meanings for universal quantification, implication and bounds.

**Instruction:** implement the following specifications without using any extra tool.

## Goal

End-to-end e-commerce web application using Vue SPA, Node/Express API and PostgreSQL, runnable through Docker: authentication, catalogue, cart, Stripe test checkout, customer dashboard, reviews and administrator dashboard.

## Constraints

- Frontend: Vue.js SPA with Vite.
- Backend: Node.js, Express and TypeScript; no opinionated framework such as Nest.
- Frontend/backend structure: domain/feature folders (Screaming Architecture), such as products, orders, auth, cart and reviews, each with its own routes, controller, service and repository.
- Database: PostgreSQL.
- Payments: Stripe sandbox/test mode only; runtime environment keys supplied by the user; no real card data.
- Email: simulated through console/file logging; no actual SMTP/SendGrid delivery. This explicitly differs from an earlier functional specification requesting real email; the original records a decision in a `/ck:grill` session.
- Administrators: the same users table with a customer/admin role field; separate `/admin/login` accepting only administrators; no separate admin table.
- Cart: login required, no guest cart; cart_items persisted by user_id.
- Authentication: JWT in an HttpOnly cookie; stateless; no Redis/session store.
- Orders: retain attempts even when payment fails, using pending/failed/paid status.
- Stock: decrement only when paid, within an atomic database transaction to prevent overselling.
- Docker and Docker Compose required to run the complete app locally.
- Seed: one administrator and example products in different categories.
- Out of scope: discounts/coupons, multiple languages/currencies, real payment data and actual email delivery.
- Stripe test keys: user configures environment variables at runtime; document how to obtain them in README.
- Password reset lifetime: technical default no longer than one hour, fixed during build without further questions.

## Interfaces

REST JSON under `/api`:

| Endpoint | Required behaviour |
|---|---|
| POST /api/auth/register | 201 with user |
| POST /api/auth/login | 200, set HttpOnly JWT cookie |
| POST /api/auth/logout | 204, clear cookie |
| POST /api/auth/forgot-password | 202, generate and log simulated token |
| POST /api/auth/reset-password | 200, consume token |
| GET/PUT /api/users/me | Profile, password and address |
| GET /api/products | Pagination, search, category and price filters |
| GET /api/products/:id | Detail, reviews and average |
| POST/PUT/DELETE /api/admin/products | Administrator CRUD |
| GET /api/cart; POST /api/cart/items; PUT/DELETE /api/cart/items/:id | Customer cart operations |
| POST /api/checkout | Create Stripe PaymentIntent |
| POST /api/orders | Confirm after payment approval, return unique order_id |
| GET /api/orders; GET /api/orders/:id | Logged-in customer's history and detail |
| GET /api/admin/orders | All orders; administrator required |
| POST /api/products/:id/reviews; PUT/DELETE /api/reviews/:id | Review operations |
| DELETE /api/admin/reviews/:id | Administrator moderation |
| POST /api/admin/login | Same login logic with administrator role required |

Environment variables: DATABASE_URL, JWT_SECRET, STRIPE_SECRET_KEY, STRIPE_PUBLISHABLE_KEY, PORT and FRONTEND_URL. `docker-compose up` starts db (5432), backend (4000) and frontend (5173).

## Invariants

| ID | Requirement |
|---|---|
| V1 | Every protected route validates its HttpOnly JWT cookie before its handler |
| V2 | Every admin route requires role=admin, otherwise 403 |
| V3 | Checkout uses a database transaction; stock decreases only when payment is paid |
| V4 | Cart quantity must not exceed available stock |
| V5 | A review author must have a paid order containing the product |
| V6 | Store a bcrypt/argon2 password hash, never plaintext |
| V7 | Each order has a unique, unguessable order_id |
| V8 | Reset tokens expire within one hour and are single-use |
| V9 | Cart items belong to the authenticated user; access to another user's cart is prohibited |
| V10 | Checkout prices come from persisted database prices, never client-supplied prices |

## Tasks

T1 scaffold domains and Compose; T2 schema and migrations; T3 registration/login/logout and password hashing; T4 profile; T5 password reset; T6 catalogue; T7 cart; T8 test checkout and payment confirmation; T9 customer order dashboard; T10 create eligible reviews and edit/delete own reviews; T11 administrative login/product CRUD/orders/moderation; T12 seed; T13 README setup, environment variables and Docker instructions.

The original task table also records invariant/interface references and completion status. Its bug table has columns id, date, cause and fix.
