# Apêndice B — Intervenções realizadas para execução

Registro exigido pelo princípio de não-intervenção do protocolo: toda alteração
feita numa aplicação gerada, com arquivo, o que mudou e por que era necessário
para executar.

**Nenhuma vulnerabilidade foi corrigida.** Middleware de segurança, validação de
entrada, autenticação, autorização, política de CORS, cabeçalhos de resposta e
segredos permanecem exatamente como cada modelo os gerou — são a variável que o
experimento mede.

## Resumo

| aplicação | intervenção | natureza |
|---|---|---|
| `deepseek-mini-v4` | +1 linha: script `"build": "tsc"` | único *backend* sem script de compilação |
| `opus` | +5 linhas: proxy `/api` no Vite | única aplicação sem proxy para a API |
| `fable5` | nenhuma | — |
| `qwen-3.8-8b` | nenhuma | — |

Nas quatro foi acrescentado um `docker-compose.dast.yml` (arquivo novo, o
original não foi modificado) para servir o *build* de produção em vez do servidor
de desenvolvimento.

---

## Alterações — deepseek-mini-v4

Registro exigido pela Regra Central do CLAUDE.md: toda alteração feita
numa aplicação gerada, com arquivo, o que mudou e por que era necessário
para executar.

Repositório privado: https://github.com/LeandroRetz/artigo-dast-deepseek-mini-v4
- commit `baseline`: saída do modelo, sem modificações
- commit `dast`: as alterações listadas abaixo

### Nenhuma correção de segurança foi feita

Middleware, validação de entrada, autenticação, autorização, política de
CORS, headers de resposta e segredos permanecem exatamente como o modelo
gerou. São a variável medida pelo experimento.

### Alterações

#### `backend/package.json` — adicionado `"build": "tsc"`

Necessário para executar: era o único dos quatro backends sem script de
build. Só existia `"start": "tsx src/index.ts"`, que roda o TypeScript
direto do fonte. O runbook fixa `NODE_ENV=production` servindo o build
como parâmetro idêntico entre modelos, então sem esse script a aplicação
não podia ser tratada como as outras três.

O `tsconfig.json` já trazia `outDir: dist` e `rootDir: src` corretos; só
o script foi adicionado. `npx tsc` compila sem erro.

**Divergência a declarar no artigo:** este é o único modelo cujo backend
não produziu script de build. É observação sobre a saída do modelo, não
defeito de execução.

#### `docker-compose.dast.yml` — novo arquivo (override)

O `docker-compose.yml` original sobe dev server (`npm run dev` no backend
e no frontend). O override roda migrate + seed + build e sobe
`node dist/index.js` com `NODE_ENV=production`; no frontend, `vite build`
+ `vite preview`. O compose original não foi modificado.

Necessário porque varrer o dev server expõe `/@vite/client` e
`/node_modules/.vite/deps/*`, que inflam a superfície medida e não
existem em produção. O runbook proíbe explicitamente varrer o dev server.

### Estado do banco antes da varredura

- `docker compose down -v` antes de subir (banco zerado)
- `user@test.com` e `admin@test.com` criados via `POST /api/auth/register`
- `admin@test.com` promovido por SQL (`UPDATE users SET role='admin'`),
  porque nenhuma das aplicações expõe rota para isso
- para CADA um dos dois usuários: item de carrinho, pedido pago
  (PaymentIntent confirmado no Stripe em modo teste com `pm_card_visa`)
  e avaliação. IDs em `out/seed-deepseek-mini-v4.md`.

---

## Alterações — qwen-3.8-8b

Registro exigido pela Regra Central do CLAUDE.md: toda alteração feita
numa aplicação gerada, com arquivo, o que mudou e por que era necessário
para executar.

Repositório privado: https://github.com/LeandroRetz/artigo-dast-qwen-3.8-8b
- commit `baseline`: saída do modelo, sem modificações
- commit `dast`: as alterações listadas abaixo

### Nenhuma correção de segurança foi feita

Middleware, validação de entrada, autenticação, autorização, política de
CORS, headers de resposta e segredos permanecem exatamente como o modelo
gerou. São a variável medida pelo experimento.

### Alterações

#### `docker-compose.dast.yml` — novo arquivo (override)

Única alteração. Nenhum arquivo da aplicação foi tocado.

O backend já roda `node dist/...` pelo Dockerfile; o override apenas
acrescenta `NODE_ENV=production`. O frontend passa a rodar
`vite build` + `vite preview` em vez do dev server. O
`docker-compose.yml` original não foi modificado.

Necessário porque varrer o dev server expõe `/@vite/client` e
`/node_modules/.vite/deps/*`, que inflam a superfície medida e não
existem em produção. O runbook proíbe explicitamente varrer o dev server.

### Estado do banco antes da varredura

- `docker compose down -v` antes de subir (banco zerado)
- `user@test.com` e `admin@test.com` criados via `POST /api/auth/register`
- `admin@test.com` promovido por SQL (`UPDATE users SET role='admin'`),
  porque nenhuma das aplicações expõe rota para isso
- para CADA um dos dois usuários: item de carrinho, pedido pago
  (PaymentIntent confirmado no Stripe em modo teste com `pm_card_visa`)
  e avaliação. IDs em `out/seed-qwen-3.8-8b.md`.

---

## Alterações — fable5

Registro exigido pela Regra Central do CLAUDE.md: toda alteração feita
numa aplicação gerada, com arquivo, o que mudou e por que era necessário
para executar.

Repositório privado: https://github.com/LeandroRetz/artigo-dast-fable5
- commit `baseline`: saída do modelo, sem modificações
- commit `dast`: as alterações listadas abaixo

### Nenhuma correção de segurança foi feita

Middleware, validação de entrada, autenticação, autorização, política de
CORS, headers de resposta e segredos permanecem exatamente como o modelo
gerou. São a variável medida pelo experimento.

### Alterações

#### `docker-compose.dast.yml` — novo arquivo (override)

Única alteração. Nenhum arquivo da aplicação foi tocado.

O backend já roda `node dist/...` pelo Dockerfile; o override apenas
acrescenta `NODE_ENV=production`. O frontend passa a rodar
`vite build` + `vite preview` em vez do dev server. O
`docker-compose.yml` original não foi modificado.

Necessário porque varrer o dev server expõe `/@vite/client` e
`/node_modules/.vite/deps/*`, que inflam a superfície medida e não
existem em produção. O runbook proíbe explicitamente varrer o dev server.

### Estado do banco antes da varredura

- `docker compose down -v` antes de subir (banco zerado)
- `user@test.com` e `admin@test.com` criados via `POST /api/auth/register`
- `admin@test.com` promovido por SQL (`UPDATE users SET role='admin'`),
  porque nenhuma das aplicações expõe rota para isso
- para CADA um dos dois usuários: item de carrinho, pedido pago
  (PaymentIntent confirmado no Stripe em modo teste com `pm_card_visa`)
  e avaliação. IDs em `out/seed-fable5.md`.

---

## Alterações — opus

Registro exigido pela Regra Central do CLAUDE.md: toda alteração feita
numa aplicação gerada, com arquivo, o que mudou e por que era necessário
para executar.

Repositório privado: https://github.com/LeandroRetz/artigo-dast-opus
- commit `baseline`: saída do modelo, sem modificações
- commit `dast`: as alterações listadas abaixo

### Nenhuma correção de segurança foi feita

Middleware, validação de entrada, autenticação, autorização, política de
CORS, headers de resposta e segredos permanecem exatamente como o modelo
gerou. São a variável medida pelo experimento.

### Alterações

#### `frontend/vite.config.js` — adicionado proxy de `/api`

**Esta é a alteração mais consequente do experimento e precisa ser
declarada no artigo.**

O ZAP varre uma única origem (`localhost:5173`). Nas outras três
aplicações o `vite.config` já faz proxy de `/api` para o backend, então
a API aparece nessa origem e é varrida. O opus era a exceção: sem proxy,
o frontend chamava `http://localhost:4000/api` direto.

Consequência se nada fosse feito: varredura de `localhost:5173` daria
ZERO cobertura de API no opus. Ele apareceria como o mais seguro dos
quatro por artefato de topologia, não por segurança — corrompendo H1, H2
e H3.

O proxy foi escrito na mesma forma dos outros três (alvo por variável de
ambiente, `changeOrigin: true`). O `preview` do Vite herda
`server.proxy` (`resolvePreviewOptions`: `proxy: preview?.proxy ??
server.proxy`), então vale também no build de produção.

`changeOrigin: true` reescreve apenas o header `Host`. O header `Origin`
segue intacto, então a política de CORS observada continua sendo a que o
modelo escreveu.

**Alternativas descartadas** (registrar na Seção de ameaças à validade):
varrer só a porta 4000 nos quatro perderia a superfície do SPA; varrer
5173 e 4000 nos quatro duplicaria achados nos que têm proxy.

#### `docker-compose.dast.yml` — novo arquivo (override)

`NODE_ENV=production` e `node dist/server.js` no backend (o compose
original sobrescreve com `npm run dev`); `vite build` + `vite preview` no
frontend. `VITE_API_URL` passa a apontar para `http://localhost:5173/api`
— a mesma origem varrida — em vez de `http://localhost:4000/api`. O
`docker-compose.yml` original não foi modificado.

### Estado do banco antes da varredura

- `docker compose down -v` antes de subir (banco zerado)
- `user@test.com` e `admin@test.com` criados via `POST /api/auth/register`
- `admin@test.com` promovido por SQL (`UPDATE users SET role='admin'`),
  porque nenhuma das aplicações expõe rota para isso
- para CADA um dos dois usuários: item de carrinho, pedido pago
  (PaymentIntent confirmado no Stripe em modo teste com `pm_card_visa`)
  e avaliação. IDs em `out/seed-opus.md`.

**Nota:** o seed original do opus é o único que cria um usuário comum
(`customer@shop.test`); os outros três criam só admin. Isso não foi
alterado — os usuários do experimento são adicionais.

---
