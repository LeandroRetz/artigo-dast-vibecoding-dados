# Apêndice C — Configuração do OWASP ZAP

Toda a instrumentação da varredura dinâmica. Os valores abaixo foram **idênticos
nas oito execuções** (quatro modelos × dois perfis de acesso); alterá-los entre
modelos invalidaria a comparação.

## C.1 Ambiente

| item | valor |
|---|---|
| OWASP ZAP | 2.17.0 |
| imagem base | `zaproxy/zap-stable` |
| digest da base | `sha256:781a2bdaea47324e7bab583e2263f21d257b0aee61ed51521a5be45f5f5081ef` |
| imagem congelada | `zap-pesquisa:congelado` |
| runtime | Java 17.0.20, heap 5.951 MB |

A imagem foi construída e congelada **antes da primeira varredura** e não foi
reconstruída em nenhum momento, de modo que as oito varreduras compartilham
exatamente o mesmo conjunto de regras. O `Dockerfile.zap` (em `scripts/`) é o
artefato de reprodutibilidade; `metodologia/ambiente.txt` registra o inventário
completo colhido no momento da execução.

## C.2 Add-ons

| add-on | versão | canal | função no experimento |
|---|---|---|---|
| `ascanrules` | 83.0.0 | release | regras ativas de referência |
| `ascanrulesBeta` | 66.0.0 | beta | injeção SQL por SGBD e *time-based* |
| `ascanrulesAlpha` | 58.0.0 | alpha | regras experimentais adicionais |
| `spiderAjax` | 23.32.0 | release | descoberta de superfície em SPA |
| `accessControl` | 13.0.0 | alpha | apoio ao teste de controle de acesso |
| `jwt` | 1.0.3 | alpha | `alg:none`, chave fraca, assinatura não verificada |
| `reports` | 0.46.0 | release | template `traditional-json-plus` |
| `automation` | 0.60.0 | beta | execução declarativa dos planos |

O uso de add-ons em canal *alpha* e *beta* é deliberado: as regras de injeção SQL
específicas por SGBD e o suporte a JWT residem nesses canais. O congelamento de
versão preserva a consistência entre as oito varreduras, mas **não** elimina a
limitação de maturidade declarada — ver as ameaças à validade no artigo.

## C.3 Parâmetros de varredura

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

## C.4 Política de varredura explícita

Declara-se uma política nomeada (`policy-dast-vibecoding`) em vez de usar a
*Default Policy*, para que os ajustes finos de sensibilidade sejam auditáveis.

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

`threshold: low` nas regras de injeção SQL **aumenta deliberadamente a
sensibilidade** — e, com ela, a taxa de falsos positivos — por serem a classe de
maior severidade sob investigação. Essa assimetria é declarada no artigo porque
afeta a leitura de H1 e H2.

As demais regras instaladas permanecem ativas nos valores padrão: a política
ajusta, não restringe.

Um identificador obsoleto (`90018`), inexistente no ZAP 2.17.0, foi removido do
template depois que o scanner encerrou com `Unrecognised active scan rule ID` e
código de saída 2. A cobertura de injeção SQL segue garantida por 40018–40024.

## C.5 Sequência de jobs executada

Cada uma das oito varreduras executou o mesmo plano declarativo, nesta ordem:

1. **`replacer`** — injeta em todo *request* o cookie de sessão obtido por login
   fora do scanner (justificativa em C.6);
2. **`passiveScan-config`** — `scanOnlyInScope: true`, `maxAlertsPerRule: 0`;
3. **`activeScan-policy`** — declara `policy-dast-vibecoding` (C.4);
4. **`spider`** — rastreamento tradicional, 5 min, profundidade 10;
5. **`spiderAjax`** — rastreamento por navegador (`firefox-headless`), 5 min,
   necessário por serem as quatro aplicações SPA;
6. **`passiveScan-wait`** — drena a fila do scanner passivo antes de prosseguir;
7. **`activeScan`** — payloads ativos, 10 min por regra, 90 min por varredura,
   5 threads por host;
8. **`report`** — `traditional-json-plus` (carrega as tags OWASP/CWE por alerta)
   e `traditional-html` para inspeção humana.

O contexto inclui apenas a origem da aplicação (`localhost:5173`) e **exclui**:

- as rotas de *logout* — sem isso o scanner derruba a própria sessão no meio do
  active scan;
- os domínios do Stripe — serviço externo, fora do escopo do experimento.

Os oito planos concretos, como executados, estão em `planos/`.

## C.6 Sessão autenticada: por que o cookie é injetado

**Este é o desvio mais consequente em relação a uma configuração ingênua do ZAP.**

Três das quatro aplicações marcam o cookie de sessão como `Secure` quando
`NODE_ENV=production`. A política de cookies do ZAP não retransmite um cookie
`Secure` sobre HTTP. Em consequência, a verificação de sessão por *polling*
retornava 401, o ZAP concluía que a sessão havia expirado e reautenticava a cada
requisição, travando a exploração.

Medição em `fable5`, mesmo plano, variando **apenas** o mecanismo de sessão:

| configuração | URLs descobertas pelo spider AJAX |
|---|---|
| anônima | 169 |
| autenticação nativa do ZAP | **11** |
| cookie injetado via `replacer` | **908** |

A autenticação nativa produzia cobertura **inferior à anônima** — resultado que,
se não detectado, teria produzido oito varreduras essencialmente desautenticadas
sem qualquer erro visível no log.

Adotou-se: autenticação executada fora do scanner (`curl`), captura do cookie de
sessão e injeção via regra `replacer` no cabeçalho `Cookie` de todas as
requisições. O `01-varrer.sh` valida o cookie contra `/api/users/me` antes de
iniciar cada passagem e aborta o perfil caso não obtenha 200.

**A aplicação não foi alterada.** O atributo `Secure` continua sendo emitido nas
respostas e continua sendo detectado e reportado pelo scanner passivo,
preservando-o como achado. O que se contorna é uma limitação do cliente HTTP do
scanner sobre conexão em texto claro, não uma propriedade do código gerado.

Alternativa não adotada: servir as aplicações sobre TLS. Exigiria um terminador
reverso, que introduz um salto adicional capaz de alterar cabeçalhos de resposta
— justamente uma das variáveis medidas.

## C.7 Verificação pós-varredura

Para cada `relatorios-zap/<modelo>-<perfil>-log.txt` foi verificado:

- `Job activeScan finished` sem `Unexpected error`;
- ausência de `Unrecognised parameter` / `Unrecognised element`;
- `Job spiderAjax found N URLs` com N na ordem de milhares;
- `.json` e `.html` dos dois perfis presentes e não vazios;
- a passagem como `admin` alcançou rotas que a de `user_comum` não alcançou.

**Critério de aborto:** alertas concentrados apenas em `/` e `/login` indicariam
autenticação não funcional. Nenhuma das oito varreduras acionou o critério.

`dados/_fingerprints.txt` contém oito linhas. As duas linhas de um mesmo modelo
apresentam o mesmo hash — é a mesma aplicação nos dois perfis; linhas de modelos
distintos apresentam hashes diferentes — a aplicação foi efetivamente trocada.
