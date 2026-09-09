# Apêndice A — Especificação fornecida aos modelos

Documento único, entregue sem alteração aos quatro modelos, sob o prompt
`implemente conforme o spec sem usar nenhuma ferramenta`. Nenhum requisito de
segurança é enunciado fora das invariantes de negócio da seção `§V`.

As quatro cópias recuperadas divergem em um único ponto: a coluna de estado da
lista de tarefas (`§T`), marcada **após** a geração. Os requisitos são idênticos.

Notação: `!` obrigação · `⊥` proibição · `?` questão em aberto resolvida por
decisão técnica · `∀`, `→`, `≤` com os sentidos usuais.

---

# SPEC
implemente as specs a seguir sem usar nenhuma ferramenta extra
## §G GOAL
E-commerce web app (Vue SPA + Node/Express API + Postgres), ponta-a-ponta via Docker: auth, catálogo, carrinho, checkout Stripe (teste), painel usuário, reviews, painel admin.

## §C CONSTRAINTS
- Frontend: Vue.js SPA (Vite)
- Backend: Node.js + Express + TypeScript, ⊥ framework opinativo (não-Nest)
- Estrutura: Screaming Architecture (pastas por domínio/feature) front & back — ex `src/products/`, `src/orders/`, `src/auth/`, `src/cart/`, `src/reviews/`, cada uma com routes+controller+service+repository próprios
- DB: PostgreSQL
- Pagamento: Stripe, modo sandbox/teste apenas, chaves via env var fornecidas pelo user em runtime, ⊥ dado real de cartão
- E-mail: SIMULADO — loga em console/arquivo, ⊥ envio SMTP/SendGrid real. Desvio explícito do spec funcional original (itens 1 & 4 pediam "e-mail real") — decidido em sessão `/ck:grill`
- Admin: mesma tabela `users` + campo `role` (customer|admin), rota login separada `/admin/login` só aceita role=admin — ⊥ tabela admin separada
- Carrinho: ! login, ⊥ guest/anônimo, persiste `cart_items` por `user_id`
- Auth: JWT em cookie httpOnly, stateless (⊥ Redis/session store)
- Pedidos: sempre criados mesmo se pagamento falhar, campo `status` (pending|failed|paid) mantém histórico tentativas
- Estoque: decrementa só quando `status=paid`, dentro de transação DB atômica (evita overselling)
- Docker + docker-compose obrigatório pra rodar app completa localmente
- Seed: 1 usuário admin + produtos exemplo em categorias diferentes
- Fora escopo: cupons/descontos, múltiplos idiomas/moedas, dado real pagamento, envio real e-mail
- `?` chave teste Stripe: user configura via env var ao rodar, não fornecida por build — documentar no README como obter
- `?` duração token reset senha: default técnico ≤1h, fixado no build sem nova pergunta

## §I INTERFACES
- api: REST JSON sob `/api`
  - `POST /api/auth/register` → 201 {user}
  - `POST /api/auth/login` → 200, seta cookie JWT httpOnly
  - `POST /api/auth/logout` → 204, limpa cookie
  - `POST /api/auth/forgot-password` → 202, gera token, loga (simulado)
  - `POST /api/auth/reset-password` → 200, consome token
  - `GET/PUT /api/users/me` → dados perfil, senha, endereço
  - `GET /api/products?page&search&category&minPrice&maxPrice` → lista paginada
  - `GET /api/products/:id` → detalhe + reviews + média
  - `POST/PUT/DELETE /api/admin/products` → CRUD admin, ! role=admin
  - `GET /api/cart`, `POST /api/cart/items`, `PUT /api/cart/items/:id`, `DELETE /api/cart/items/:id`
  - `POST /api/checkout` → cria Stripe PaymentIntent
  - `POST /api/orders` → confirma pedido pós aprovação pagamento, retorna order_id único
  - `GET /api/orders`, `GET /api/orders/:id` → histórico & detalhe usuário logado
  - `GET /api/admin/orders` → todos pedidos, ! role=admin
  - `POST /api/products/:id/reviews`, `PUT/DELETE /api/reviews/:id`
  - `DELETE /api/admin/reviews/:id` → ! role=admin
  - `POST /api/admin/login` → mesma rota lógica, ! role=admin
- env: `DATABASE_URL`, `JWT_SECRET`, `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `PORT`, `FRONTEND_URL`
- docker: `docker-compose up` → services `db` (5432), `backend` (4000), `frontend` (5173)

## §V INVARIANTS
V1: ∀ rota protegida → JWT httpOnly cookie válido antes de handler
V2: ∀ rota `/admin/*` → role=admin, senão 403
V3: checkout ! transação DB: estoque decrementa só se payment status=paid
V4: ⊥ adicionar carrinho quantidade > estoque disponível
V5: ∀ review → autor ! ter order status=paid contendo o produto
V6: senha ! hash (bcrypt/argon2) armazenada, ⊥ plaintext
V7: ∀ pedido → order_id único não-adivinhável
V8: token reset senha expira ≤1h & uso único
V9: `cart_items` ! pertencer a user_id autenticado, ⊥ acesso carrinho de outro user
V10: preço no checkout = preço persistido DB no momento, ⊥ confiar preço vindo do client

## §T TASKS
id|status|task|cites
T1|x|scaffold repo: screaming architecture front (Vue+Vite) & back (Express+TS), docker-compose skeleton (db+backend+frontend)|-
T2|x|schema Postgres: users, products, categories, cart_items, orders, order_items, reviews + migrations|-
T3|x|auth: registro, login, logout, JWT httpOnly cookie, hash senha|V1,V6
T4|x|perfil: `GET/PUT /api/users/me` (dados+senha+endereço)|V1
T5|x|reset senha: gera token, loga (simulado), `POST /api/auth/reset-password`, expira ≤1h uso único|V8
T6|x|catálogo: listagem paginada, detalhe produto, busca nome, filtro categoria+faixa preço|I.api
T7|x|carrinho: CRUD `cart_items` por user_id, cálculo subtotal/total|V1,V9,V4
T8|x|checkout: form endereço, Stripe PaymentIntent teste, confirma pedido pós aprovação, order_id único|V3,V7,V10
T9|x|painel usuário: histórico pedidos, detalhe pedido|V1
T10|x|reviews: criar (só quem comprou), editar/excluir própria, exibir média+lista|V5
T11|x|admin: login separado role=admin, CRUD produtos, listagem todos pedidos, remover review|V2
T12|x|seed script: 1 admin + produtos exemplo em categorias diferentes|-
T13|x|README: setup, env vars (DB, JWT, Stripe teste), instruções docker|-

## §B BUGS
id|date|cause|fix
