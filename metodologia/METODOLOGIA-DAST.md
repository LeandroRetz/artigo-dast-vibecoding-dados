# Procedimento de varredura dinâmica com OWASP ZAP

Documento de apoio ao artigo. Reúne (i) o procedimento operacional de
execução das varreduras e (ii) os dados de instrumentação necessários
para as seções de método e de ameaças à validade.

Redigido como rascunho técnico: os fatos e medições estão consolidados,
mas a redação final e a interpretação dos resultados cabem ao pesquisador.

---

## 1. Objeto e desenho

Comparam-se quatro aplicações web de comércio eletrônico geradas por
modelos de linguagem distintos a partir de uma mesma especificação
(`SPEC.md`). A variável independente é o modelo gerador; a variável
dependente é a superfície de vulnerabilidades observável por análise
dinâmica.

| identificador | modelo gerador | repositório privado |
|---|---|---|
| `deepseek-mini-v4` | DeepSeek Mini v4 | `artigo-dast-deepseek-mini-v4` |
| `qwen-3.8-8b` | Qwen 3.8 8B | `artigo-dast-qwen-3.8-8b` |
| `fable5` | Fable 5 | `artigo-dast-fable5` |
| `opus` | Opus | `artigo-dast-opus` |

A ordem acima é a ordem de execução e deve ser reportada, pois as
aplicações compartilham as mesmas portas e são executadas sequencialmente.

Cada aplicação é varrida **duas vezes**, uma por perfil de acesso
(`user_comum` e `admin`), totalizando oito varreduras. A segunda passagem
é necessária porque as rotas administrativas — painel, gestão de
usuários, relatórios — não são exercidas pelo perfil comum, e é nelas que
se concentram as operações destrutivas.

### 1.1 Princípio de não-intervenção

Nenhuma vulnerabilidade foi corrigida nas aplicações geradas. Segredos
embutidos, CORS permissivo, ausência de validação e demais achados
constituem o dado que o experimento mede; corrigi-los invalidaria o
resultado.

Alterações nas aplicações restringiram-se ao mínimo necessário para que
executassem, e estão registradas individualmente em
`out/alteracoes-<modelo>.md`. O total é de duas linhas de código-fonte em
duas das quatro aplicações (Seção 5.1).

---

## 2. Ambiente de execução

### 2.1 Instrumentação

| item | valor |
|---|---|
| OWASP ZAP | 2.17.0 |
| imagem base | `zaproxy/zap-stable` |
| digest da base | `sha256:781a2bdaea47324e7bab583e2263f21d257b0aee61ed51521a5be45f5f5081ef` |
| imagem congelada | `zap-pesquisa:congelado` (`sha256:5942e0601c95…`) |
| runtime | Java 17.0.20, heap 5.951 MB |

A imagem foi congelada antes da primeira varredura e não foi reconstruída
em nenhum momento, de modo que as oito varreduras compartilham
exatamente o mesmo conjunto de regras. O `Dockerfile.zap` é o artefato de
reprodutibilidade; `out/ambiente.txt` registra o inventário completo.

### 2.2 Add-ons

| add-on | versão | canal | função no experimento |
|---|---|---|---|
| `ascanrules` | 83.0.0 | release | regras ativas de referência |
| `ascanrulesBeta` | 66.0.0 | beta | injeção SQL por SGBD e time-based |
| `ascanrulesAlpha` | 58.0.0 | alpha | regras experimentais adicionais |
| `spiderAjax` | 23.32.0 | release | descoberta de superfície em SPA |
| `accessControl` | 13.0.0 | alpha | apoio ao teste de controle de acesso |
| `jwt` | 1.0.3 | alpha | `alg:none`, chave fraca, assinatura não verificada |
| `reports` | 0.46.0 | release | template `traditional-json-plus` |
| `automation` | 0.60.0 | beta | execução declarativa dos planos |

O uso de add-ons em canal *alpha* e *beta* é deliberado: as regras de
injeção SQL específicas por SGBD e o suporte a JWT residem nesses canais.
A versão exata está congelada, o que preserva a reprodutibilidade apesar
da maturidade declarada.

### 2.3 Parâmetros de varredura

Idênticos nas oito execuções. Alterá-los entre modelos invalidaria a
comparação.

| parâmetro | valor | significado |
|---|---|---|
| `defaultStrength` | `medium` | número de payloads por parâmetro |
| `defaultThreshold` | `medium` | critério de confirmação do achado |
| spider tradicional | 5 min, profundidade 10 | descoberta de links estáticos |
| spider AJAX | 5 min, `firefox-headless` | descoberta em SPA |
| duração máxima por regra | 10 min | limite por regra ativa |
| duração máxima do active scan | 90 min | limite por varredura |
| `threadPerHost` | 5 | concorrência |
| `scanOnlyInScope` | `true` | restringe ao contexto declarado |
| `maxAlertsPerRule` | 0 (sem limite) | evita truncamento de instâncias |

### 2.4 Política de varredura explícita

Declara-se uma política nomeada (`policy-dast-vibecoding`) em vez de usar
a *Default Policy*, para que os ajustes finos de sensibilidade sejam
auditáveis:

| regra | id | strength | threshold |
|---|---|---|---|
| SQL Injection (genérica) | 40018 | high | low |
| SQL Injection — MySQL | 40019 | high | low |
| SQL Injection — Hypersonic | 40020 | high | low |
| SQL Injection — Oracle | 40021 | high | low |
| SQL Injection — PostgreSQL | 40022 | high | low |
| SQL Injection — SQLite | 40024 | high | low |
| XSS refletido | 40012 | high | medium |
| XSS persistente | 40014 | high | medium |
| Server Side Include | 40009 | medium | medium |
| Server Side Code Injection | 90019 | medium | medium |
| Command Injection | 90020 | medium | medium |
| Path Traversal | 6 | medium | medium |
| Remote File Inclusion | 7 | medium | medium |

`threshold: low` nas regras de injeção SQL aumenta deliberadamente a
sensibilidade — e, com ela, a taxa de falsos positivos — por serem a
classe de maior severidade sob investigação. Essa assimetria deve ser
declarada, pois afeta a leitura de H1.

As demais regras instaladas permanecem ativas nos valores padrão; a
política ajusta, não restringe.

### 2.5 Parâmetros fixos das aplicações

| item | valor |
|---|---|
| porta varrida | 5173 |
| ambiente | `NODE_ENV=production`, servindo o build |
| usuário comum | `user@test.com` / `Test1234!` |
| administrador | `admin@test.com` / `Test1234!` |
| Stripe | mesmas chaves de teste nas quatro |
| banco | zerado e re-semeado antes de cada varredura |

Não foram padronizados — por constituírem o objeto de estudo — framework,
banco, ORM, biblioteca de autenticação, política de CORS, cabeçalhos,
segredos e validação de entrada.

---

## 3. Procedimento de execução

### 3.1 Preparação do ambiente (uma vez)

```bash
cd files
chmod +x *.sh *.py
./00-setup.sh          # constrói e congela zap-pesquisa:congelado
```

O script verifica explicitamente que todos os add-ons foram instalados: o
`-addoninstall` do ZAP retorna zero mesmo quando o download falha, de modo
que a checagem precisa ser feita à parte. Ausência de add-on interrompe a
execução, pois o conjunto de regras deixaria de corresponder ao declarado.

Produz `out/ambiente.txt` (Seção 2 deste documento).

### 3.2 Execução completa

```bash
./05-rodar-tudo.sh
```

Encadeia, para cada modelo na ordem fixa:

1. `04-preparar.sh <modelo> subir` — derruba os quatro *stacks*, confirma
   que as portas 5173, 4000 e 5432 estão livres, zera o banco
   (`docker compose down -v`), sobe o build de produção, semeia os dados,
   promove o administrador e captura um *snapshot* do estado inicial.
2. `01-varrer.sh <modelo>` — varre os dois perfis, restaurando o banco a
   partir do *snapshot* entre eles.
3. `04-preparar.sh <modelo> derrubar`.

Ao final executa `02-agregar.py`. O progresso é registrado em
`out/_execucao.log`.

Duração observada: aproximadamente 105 min por perfil, ~3,5 h por modelo,
~14 h no total.

### 3.3 Execução passo a passo

```bash
./04-preparar.sh deepseek-mini-v4 subir
RESTAURAR_CMD=./04-restaurar.sh ./01-varrer.sh deepseek-mini-v4
python3 02-agregar.py
```

Omitindo `RESTAURAR_CMD`, o script pausa entre os perfis e aguarda que o
operador restaure o banco manualmente.

### 3.4 Semeadura de dados

Cada aplicação precisa conter, antes da varredura, ao menos um registro de
cada recurso da especificação **pertencente a cada um dos dois usuários**.
Sem isso o spider não descobre as rotas de detalhe (`/pedidos/{id}`), o
active scan não as exercita, e a aplicação parece mais segura por
ausência de dados — não por propriedade do código.

`03-semear.py` executa, para cada usuário, exclusivamente pela API
pública: registro, inclusão de item no carrinho, *checkout*, confirmação
do pagamento junto ao Stripe em modo de teste (`pm_card_visa`) e criação
de avaliação. O pagamento efetivo é necessário porque três das quatro
implementações condicionam a criação de avaliações à existência de pedido
pago.

A promoção de `admin@test.com` ao papel administrativo é feita por SQL,
por nenhuma das aplicações expor rota para tal operação.

Os identificadores gerados ficam em `out/seed-<modelo>.md` e alimentam a
auditoria manual de IDOR.

### 3.5 Verificação obrigatória pós-varredura

Para cada `out/<modelo>-<perfil>-log.txt`:

- [ ] `Job activeScan finished` sem `Unexpected error`
- [ ] ausência de `Unrecognised parameter` / `Unrecognised element`
- [ ] `Job spiderAjax found N URLs` com N na ordem de milhares
- [ ] `.json` e `.html` dos dois perfis presentes e não vazios
- [ ] a passagem como `admin` alcançou rotas que a de `user_comum` não alcançou

**Critério de aborto.** Se os alertas se concentrarem apenas em `/` e
`/login`, a autenticação não funcionou; interromper e diagnosticar antes
de varrer os modelos restantes.

`out/_fingerprints.txt` deve conter oito linhas. As duas linhas de um
mesmo modelo devem apresentar o mesmo *hash*; linhas de modelos distintos
com *hash* idêntico indicam que a aplicação não foi trocada e que o dado
está corrompido.

---

## 4. Decisões de instrumentação

Esta seção documenta os desvios em relação a uma configuração ingênua do
ZAP. Cada um decorre de uma falha observada, e todos foram aplicados de
forma idêntica às quatro aplicações.

### 4.1 Build de produção, não servidor de desenvolvimento

Uma primeira varredura, posteriormente descartada, foi executada contra o
servidor de desenvolvimento do Vite. O relatório continha instâncias em
`/@vite/client` e `/node_modules/.vite/deps/*` — artefatos inexistentes em
produção que inflam artificialmente a superfície medida.

Os arquivos `docker-compose.yml` originais das quatro aplicações sobem o
servidor de desenvolvimento. Introduziu-se um `docker-compose.dast.yml`
por aplicação, que sobrepõe os comandos para executar `vite build` +
`vite preview` no *frontend* e o artefato compilado com
`NODE_ENV=production` no *backend*, sem modificar o arquivo original.

Material descartado preservado em `out/_descartado-devserver/` com
justificativa.

### 4.2 Sessão autenticada: injeção de cookie

**Este é o desvio mais consequente e precisa ser declarado no artigo.**

Três das quatro aplicações marcam o cookie de sessão com o atributo
`Secure` quando `NODE_ENV=production`. A política de cookies do ZAP não
retransmite um cookie `Secure` sobre HTTP. Em consequência, a verificação
de sessão por *polling* retornava 401, o ZAP concluía que a sessão havia
expirado e reautenticava a cada requisição, travando a exploração.

Medição em `fable5`, mesmo plano, variando apenas o mecanismo de sessão:

| configuração | URLs descobertas pelo spider AJAX |
|---|---|
| anônima | 169 |
| autenticação nativa do ZAP | **11** |
| cookie injetado via `replacer` | **908** |

A autenticação nativa produzia cobertura inferior à anônima — resultado
que, se não detectado, teria produzido oito varreduras essencialmente
desautenticadas sem qualquer erro visível no log.

Adotou-se: autenticação executada fora do scanner (`curl`), captura do
cookie de sessão e injeção via regra `replacer` no cabeçalho `Cookie` de
todas as requisições; os *jobs* de exploração e varredura não recebem o
parâmetro `user`. O `01-varrer.sh` valida o cookie contra `/api/users/me`
antes de iniciar cada passagem e aborta o perfil caso não obtenha 200.

**A aplicação não foi alterada.** O atributo `Secure` continua sendo
emitido nas respostas e continua sendo detectado e reportado pelo scanner
passivo, preservando-o como achado. O que se contorna é uma limitação do
cliente HTTP do scanner sobre conexão em texto claro, não uma propriedade
do código gerado.

Alternativa não adotada: servir as aplicações sobre TLS. Exigiria um
terminador reverso, que introduz um salto adicional capaz de alterar
cabeçalhos de resposta — justamente uma das variáveis medidas.

### 4.3 Assimetria de topologia da aplicação `opus`

O ZAP varre uma única origem (`localhost:5173`). Em três das aplicações, a
configuração do Vite faz *proxy* de `/api` para o *backend*, de modo que a
API é alcançável nessa origem. Em `opus` não havia *proxy*: o *frontend*
consumia `http://localhost:4000/api` diretamente.

Sem intervenção, a varredura de `opus` teria produzido cobertura nula da
API, e o modelo apareceria como o mais seguro dos quatro por artefato de
topologia — comprometendo H1, H2 e H3.

Adotou-se a adição do *proxy* `/api` em `opus`, na mesma forma dos outros
três (`changeOrigin: true`), igualando a topologia. `changeOrigin`
reescreve apenas o cabeçalho `Host`; o cabeçalho `Origin` permanece
íntegro, de modo que a política de CORS observada continua sendo a que o
modelo escreveu.

Alternativas descartadas: varrer somente a porta 4000 nas quatro
aplicações (perderia a superfície do SPA e a camada de *proxy*); varrer
5173 e 4000 simultaneamente (duplicaria achados nas três que possuem
*proxy*).

### 4.4 Correção de identificador de regra obsoleto

O plano declarava a regra 90018, inexistente no ZAP 2.17.0. O ZAP emitia
`Unrecognised active scan rule ID` e encerrava com código 2. A regra foi
removida do template. A cobertura de injeção SQL permanece garantida pelas
regras 40018–40024.

### 4.5 Comportamento de *fallback* das SPA

As quatro aplicações são *single-page applications* servidas por
`vite preview`, que retorna `index.html` com código 200 para qualquer
caminho não correspondente a um recurso estático. O scanner interpreta
esses 200 como recursos existentes, o que infla a contagem de URLs e pode
gerar achados espúrios da classe "arquivo oculto".

O comportamento é idêntico nas quatro aplicações, preservando a
comparabilidade, mas a contagem bruta de URLs **não** deve ser usada como
métrica de superfície. Recomenda-se normalizar os achados por *endpoint*
de API efetivo.

---

## 5. Divergências observadas entre as aplicações

Dados coletados por inspeção durante a preparação. Constituem material
para a caracterização das aplicações e, em parte, para os achados
complementares fora do escopo DAST.

### 5.1 Intervenções necessárias para execução

| aplicação | intervenção | natureza |
|---|---|---|
| `deepseek-mini-v4` | `+1` linha: script `"build": "tsc"` | único *backend* sem script de compilação |
| `opus` | `+5` linhas: *proxy* `/api` no Vite | única aplicação sem *proxy* para a API |
| `fable5` | nenhuma | — |
| `qwen-3.8-8b` | nenhuma | — |

Ausência de script de compilação e ausência de *proxy* são, elas próprias,
observações sobre a completude da saída de cada modelo.

### 5.2 Pilha tecnológica

Convergência alta: as quatro adotaram Vue 3 + Vite no *frontend* e
Express + PostgreSQL (`pg`, sem ORM) no *backend*, com `bcryptjs` e
`jsonwebtoken`.

Divergências:

| aspecto | deepseek | qwen | fable | opus |
|---|---|---|---|---|
| validação de esquema | — | — | — | `zod` |
| `cors` como dependência | ausente | presente | presente | presente |
| gerência de estado | `pinia` | ausente | `pinia` | `pinia` |
| script de build no backend | ausente | presente | presente | presente |

### 5.3 Sessão e autenticação

As quatro convergiram em JWT transportado por cookie `httpOnly`, com
`POST /api/auth/login` recebendo `{email, password}` e `GET /api/users/me`
como rota protegida — o que dispensou configuração por aplicação.

| aspecto | deepseek | qwen | fable | opus |
|---|---|---|---|---|
| nome do cookie | `auth_token` | `token` | `token` | `access_token` |
| `httpOnly` | sim | sim | sim | sim |
| `sameSite` | `lax` | `lax` | `lax` | `lax` |
| `secure` | **`false` fixo** | variável de ambiente | `NODE_ENV==='production'` | `NODE_ENV==='production'` |
| validade do token | 7 dias | 1 dia | 7 dias | configurável |

`deepseek-mini-v4` é a única que fixa `secure: false` no código,
independentemente do ambiente. `qwen-3.8-8b` é a única a adotar validade
de um dia; as demais mantêm sessão por sete dias.

### 5.4 Identificadores de recurso

| aplicação | produtos | pedidos | avaliações |
|---|---|---|---|
| `deepseek-mini-v4` | inteiro sequencial | inteiro sequencial | inteiro sequencial |
| `qwen-3.8-8b` | inteiro sequencial | UUID | inteiro sequencial |
| `fable5` | inteiro sequencial | UUID | inteiro sequencial |
| `opus` | UUID | UUID | UUID |

Relevante para a auditoria de IDOR: identificadores sequenciais são
enumeráveis, UUID não. `opus` é a única a adotar UUID uniformemente.

### 5.5 Superfície administrativa

Todas expõem `GET /api/admin/orders` sob verificação de papel. A extensão
difere: `fable5` expõe apenas listagem de pedidos sob `/api/admin`,
enquanto `opus` segmenta em quatro sub-roteadores
(`/api/admin/{categories,orders,products,reviews}`).

`fable5` e `opus` implementam rota de autenticação administrativa
separada (`POST /api/admin/login`); `deepseek-mini-v4` e `qwen-3.8-8b`
também a expõem, porém sem separação equivalente no *frontend*.

### 5.6 Dados de seed originais

| aplicação | credenciais semeadas |
|---|---|
| `deepseek-mini-v4` | `admin@example.com` / `admin123` (apenas administrador) |
| `qwen-3.8-8b` | `admin@example.com` / `Admin@123` (apenas administrador) |
| `fable5` | `admin@loja.dev` / `admin123` (apenas administrador) |
| `opus` | `admin@shop.test` / `Admin123!` e `customer@shop.test` / `Customer123!` |

Três das quatro não semeiam usuário não privilegiado, o que impediria o
exercício do fluxo de compra sem cadastro manual. Apenas `opus` produz
credenciais que satisfazem a política de senha que ela própria implementa.

### 5.7 Contratos de API

Divergências relevantes para reprodutibilidade, ainda que as rotas
coincidam:

- endereço de entrega: `line1`/`postalCode` (deepseek), `street`/`zip`
  (fable), `shipping.name` obrigatório (opus)
- confirmação de pedido: `{orderId, paymentIntentId}` (deepseek),
  `{payment_intent_id, address}` (fable), `{orderId}` (opus)
- item de carrinho: `product_id` (deepseek, fable, qwen) vs `productId` (opus)

`03-semear.py` tenta as variantes e registra em `out/seed-<modelo>.md`
qual foi aceita, servindo de documentação do contrato efetivo.

---

## 6. Ameaças à validade

**Sensibilidade assimétrica.** As regras de injeção SQL operam com
`threshold: low`, elevando a taxa de falsos positivos nessa classe
relativamente às demais (Seção 2.4).

**Add-ons em canal alpha/beta.** Regras de maturidade declarada inferior
podem apresentar comportamento instável. Mitigado pelo congelamento de
versão, que garante consistência entre as oito varreduras, mas não
elimina a limitação.

**Contagem de URLs inflada.** O *fallback* das SPA responde 200 a qualquer
caminho (Seção 4.5). Normalizar por *endpoint* de API.

**Sessão estática.** O cookie é capturado uma vez por passagem e não é
renovado. Caso o active scan invalide a sessão, as requisições seguintes
seriam desautenticadas. Mitigado pela exclusão das rotas de *logout* do
escopo e pela validade longa dos tokens (1 a 7 dias).

**Intervenção em `opus`.** A adição do *proxy* altera a topologia de rede
observada, ainda que não a lógica de segurança (Seção 4.3).

**Limite de duração.** O active scan é interrompido em 90 minutos. Se
alguma aplicação não concluir a varredura nesse limite, sua cobertura
será inferior à das demais. Verificar `Job activeScan finished` e a
duração registrada em cada log.

**Não determinismo do spider AJAX.** A exploração dirigida por navegador
não é perfeitamente reprodutível entre execuções. Contagens de URL entre
modelos devem ser tratadas como aproximações.

**Escopo do DAST.** Análise dinâmica não observa política de autorização,
armazenamento de token no cliente nem invalidação de sessão. Tratados
como achados complementares por auditoria manual (Seção 7.2).

---

## 7. Produtos e destino no artigo

### 7.1 Saídas automáticas

| arquivo | destino |
|---|---|
| `out/ambiente.txt` | Seção 3.3.1 — versões de ZAP e add-ons |
| `planos/plano-*.yaml` | apêndice de reprodutibilidade (8 planos) |
| `out/*-log.txt` | Subseção 3.1.2, item (iv) |
| `out/_fingerprints.txt` | verificação de integridade (8 linhas) |
| `out/_execucao.log` | registro cronológico da execução |
| `out/_tab_resumo.csv` | Seção 4.2 — H1 e H2 |
| `out/_tab_owasp.csv` | Seção 4.3 — H3 |
| `out/_tab_por_perfil.csv` | achados exclusivos de admin vs. usuário comum |
| `out/_tab_detalhado.csv` | Seção 4.4 |
| `out/_pendente_mapeamento.csv` | achados sem categoria OWASP automática |
| `out/alteracoes-<modelo>.md` | apêndice de intervenções |
| `out/seed-<modelo>.md` | insumo da auditoria de IDOR |

### 7.2 Achados complementares pendentes

Fora do alcance da varredura dinâmica, a executar manualmente:

**IDOR.** Para cada modelo, autenticar como `user@test.com` e requisitar
recurso pertencente ao administrador, usando os identificadores de
`out/seed-<modelo>.md`. Registrar em `out/_idor.csv`
(`modelo, endpoint, id_alvo, dono, requisitante, status, violacao`).
A Seção 5.4 é diretamente relevante: identificadores sequenciais são
enumeráveis.

**Gerência de sessão.** Registrar em `out/_sessao.csv`: local de
armazenamento do token no cliente, atributos do cookie, expiração,
invalidação no *logout*, segredo de assinatura versionado e algoritmo. A
Seção 5.3 já consolida parte desses dados por inspeção.

### 7.3 Métricas sugeridas

Dado o *fallback* das SPA (Seção 4.5), recomenda-se reportar:

- achados únicos por modelo, agregando os dois perfis
- achados por *endpoint* de API efetivo (métrica normalizada)
- distribuição por severidade
- achados exclusivos do perfil administrativo
- distribuição por categoria OWASP Top 10

---

## 8. Inventário de scripts

| script | função |
|---|---|
| `00-setup.sh` | constrói e congela a imagem do ZAP; valida add-ons |
| `01-varrer.sh` | gera o plano e executa as duas passagens por modelo |
| `02-agregar.py` | consolida os oito relatórios nas tabelas do artigo |
| `03-semear.py` | cria usuários e dados por usuário via API |
| `04-preparar.sh` | sobe, semeia e fotografa o estado inicial de um modelo |
| `04-restaurar.sh` | restaura o banco entre os perfis |
| `05-rodar-tudo.sh` | orquestra a execução completa |
| `plano.yaml.template` | modelo do plano de automação do ZAP |
| `modelos.conf` | modelos, portas e tipo (`spa`/`ssr`), na ordem de execução |
| `Dockerfile.zap` | artefato de reprodutibilidade do ambiente |
