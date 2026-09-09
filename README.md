# Segurança do *Vibe Coding* — dados, apêndices e artefatos de reprodução

Material complementar do artigo **"Avaliando a Segurança do *Vibe Coding*: Uma
Análise de Vulnerabilidades em Aplicações Web Geradas por LLMs"**.

O artigo compara a superfície de vulnerabilidades de **quatro aplicações web de
comércio eletrônico**, cada uma gerada por um LLM diferente a partir de **uma
única especificação sem requisitos de segurança explícitos**, e avaliadas por
análise dinâmica com OWASP ZAP sob configuração idêntica.

Este repositório reúne o que não coube nas páginas do artigo: os apêndices, os
oito relatórios brutos do scanner, os dados agregados, os scripts e os planos de
varredura como executados.

---

## O experimento em uma tela

| | |
|---|---|
| **Modelos avaliados** | DeepSeek Mini v4, Qwen 3.8 8B, Fable5, Opus |
| **Entrada** | um único `SPEC.md`, idêntico para os quatro ([Apêndice A](apendices/A-especificacao.md)) |
| **Prompt** | *"implemente conforme o spec sem usar nenhuma ferramenta"* |
| **Rodadas** | uma por modelo (`N=1`) |
| **Ferramenta** | OWASP ZAP 2.17.0, imagem congelada, configuração idêntica |
| **Varreduras** | 8 = 4 modelos × 2 perfis de acesso (usuário comum e administrador) |
| **Complemento manual** | IDOR e gerenciamento de sessão, fora do alcance do DAST |

A variável independente é o modelo gerador. A dependente, a superfície de
vulnerabilidades observável dinamicamente. **Não** foram padronizados — por
constituírem o objeto de estudo — framework, banco, ORM, biblioteca de
autenticação, política de CORS, cabeçalhos, segredos e validação de entrada.

### Achados agregados

| modelo | alta | média | baixa | info | total | endpoints | por endpoint |
|---|---:|---:|---:|---:|---:|---:|---:|
| `deepseek-mini-v4` | 8 | 20 | 21 | 9 | **58** | 17 | 3,41 |
| `opus` | 9 | 13 | 21 | 12 | **55** | 20 | 2,75 |
| `qwen-3.8-8b` | 1 | 12 | 9 | 10 | **32** | 14 | 2,29 |
| `fable5` | 0 | 12 | 10 | 10 | **32** | 14 | 2,29 |

Achados deduplicados por (endpoint, parâmetro, regra), agregando os dois perfis.
Os mapeados concentram-se em três categorias do OWASP Top 10 — **A01**
(*Broken Access Control*), **A03** (*Injection*) e **A05** (*Security
Misconfiguration*) — sem ocorrências mapeadas nas demais.

### Achados complementares, fora do escopo DAST

- **IDOR:** 20 testes (5 por aplicação) em que o usuário comum autenticado
  requisitou recursos do administrador. **Nenhuma violação** — todas as
  respostas fora da faixa `2xx`.
- **Sessão:** as quatro aplicações usam JWT em cookie `httpOnly`, `HS256`,
  `SameSite=Lax`. **Nenhuma das quatro invalida o token no logout** — a rota
  limpa o cookie e devolve 204, mas o token anterior segue aceito em rota
  protegida por todo o prazo restante (1 a 7 dias). As quatro embutem um segredo
  de assinatura literal no código como valor padrão.

> ⚠️ **Este repositório não interpreta os resultados.** Os números aqui são
> descritivos. A leitura, as hipóteses e as conclusões estão no artigo.

---

## Estrutura

```
apendices/
  A-especificacao.md      spec entregue aos quatro modelos, verbatim
  B-intervencoes.md       toda alteração feita nas aplicações, arquivo a arquivo
  C-configuracao-zap.md   add-ons, política, parâmetros, sequência de jobs
metodologia/
  METODOLOGIA-DAST.md     procedimento operacional completo e decisões de instrumentação
  ambiente.txt            inventário do ambiente colhido na execução
dados/
  _tab_resumo.csv         achados por modelo e perfil, com severidade e confiança
  _tab_owasp.csv          achados por categoria OWASP, por modelo e perfil
  _tab_por_perfil.csv     achados exclusivos de cada perfil e interseção
  _tab_detalhado.csv      um registro por achado, com endpoint, parâmetro e CWE
  _pendente_mapeamento.csv  alertas sem categoria OWASP automática
  _idor.csv               auditoria manual de controle de acesso
  _sessao.csv             auditoria manual de gerenciamento de sessão
  _fingerprints.txt       verificação de integridade das 8 varreduras
  seed-<modelo>.md        dados semeados e IDs criados, por modelo
  _snapshot-<modelo>.sql  estado inicial do banco, restaurado entre os perfis
  graficos/               figuras e os CSVs que as geram
relatorios-zap/
  <modelo>-<perfil>.json  relatório bruto (traditional-json-plus, com tags OWASP/CWE)
  <modelo>-<perfil>.html  mesmo relatório, legível
  <modelo>-<perfil>-log.txt  log da execução do plano
  _execucao.log           registro cronológico da execução completa
planos/                   os 8 planos de automação do ZAP, como executados
scripts/                  pipeline completo de execução
```

## Dicionário dos dados principais

**`dados/_tab_detalhado.csv`** — um registro por achado deduplicado:

| coluna | conteúdo |
|---|---|
| `modelo`, `perfil` | identificação da varredura |
| `risco` | High · Medium · Low · Informational |
| `confianca` | confiança declarada pelo scanner |
| `alerta` | nome da regra que disparou |
| `owasp`, `cwe` | categoria e identificador de fraqueza |
| `metodo`, `endpoint`, `parametro` | onde o achado ocorre |
| `ocorrencias` | instâncias agrupadas neste registro |
| `pluginid`, `wasc` | identificadores da regra no ZAP |
| `evidencia` | trecho da resposta que sustentou o alerta |

**`dados/_idor.csv`** — `modelo, endpoint, id_alvo, dono_do_recurso,
usuario_requisitante, status, violacao`. Uma linha por teste; `violacao=sim`
apenas para respostas `2xx`.

**`dados/_sessao.csv`** — atributos do cookie, algoritmo, expiração, invalidação
no logout (verificada por reuso do token) e segredo de assinatura versionado.

## Reproduzir

Pré-requisitos: Docker (sem `sudo`), Python 3, e as quatro aplicações geradas.

```bash
cd scripts
chmod +x *.sh *.py
./00-setup.sh                  # constrói e congela a imagem do ZAP; valida add-ons
./05-rodar-tudo.sh             # executa os 4 modelos × 2 perfis, na ordem fixa
python3 02-agregar.py          # consolida os 8 relatórios nas tabelas do artigo
```

Passo a passo, um modelo por vez:

```bash
./04-preparar.sh <modelo> subir                          # zera o banco, sobe produção, semeia
RESTAURAR_CMD=./04-restaurar.sh ./01-varrer.sh <modelo>  # varre os dois perfis
./07-fase4.py <modelo>                                   # auditoria manual de IDOR e sessão
```

Duração observada: **~105 min por perfil**, ~3,5 h por modelo, ~14 h no total.

| script | função |
|---|---|
| `00-setup.sh` | constrói e congela a imagem do ZAP; valida os add-ons |
| `01-varrer.sh` | gera o plano e executa as duas passagens por modelo |
| `02-agregar.py` | consolida os oito relatórios nas tabelas do artigo |
| `03-semear.py` | cria usuários e dados por usuário, via API pública |
| `04-preparar.sh` | sobe, semeia e fotografa o estado inicial de um modelo |
| `04-restaurar.sh` | restaura o banco entre os dois perfis |
| `05-rodar-tudo.sh` | orquestra a execução completa |
| `06-graficos.py` | gera as figuras a partir dos dados agregados |
| `07-fase4.py` | auditoria manual de IDOR e gerenciamento de sessão |

`00-setup.sh` verifica explicitamente que todos os add-ons foram instalados: o
`-addoninstall` do ZAP retorna zero mesmo quando o download falha, de modo que a
checagem precisa ser feita à parte. Ausência de add-on interrompe a execução,
pois o conjunto de regras deixaria de corresponder ao declarado.

---

## Sanitização

Os relatórios e os dumps publicados aqui são **cópias redigidas**. Foram
substituídos por marcadores:

| padrão | marcador |
|---|---|
| tokens JWT | `<JWT-REDIGIDO>` |
| valores de cookie de sessão | `<COOKIE-REDIGIDO>` |
| chaves do Stripe | `<STRIPE-KEY-REDIGIDA>` |
| hashes bcrypt dos usuários de teste | `<BCRYPT-REDIGIDO>` |

São 409 substituições em 29 arquivos. Os originais permanecem intactos fora
deste repositório — o protocolo do experimento proíbe editar os `.json` gerados
pelo ZAP, e nenhum arquivo de origem foi tocado.

A redação **não** afeta os campos usados na análise: severidade, confiança,
regra, endpoint, parâmetro, OWASP e CWE. Afeta apenas os cabeçalhos de
autenticação capturados nas requisições de evidência.

## O que este repositório não é

- **Não** contém as quatro aplicações geradas. Elas vivem em repositórios
  próprios, com um commit `baseline` (saída crua do modelo) e um commit `dast`
  (as alterações do [Apêndice B](apendices/B-intervencoes.md)).
- **Não** contém interpretação dos resultados — isso é o artigo.
- **Não** é uma auditoria de segurança de nenhum dos modelos avaliados. É uma
  medição sob condições controladas, com `N=1` por modelo, um único *spec* e uma
  única pilha tecnológica.

## Como citar

> Retzlaff, L. L.; Motta, A. **Avaliando a Segurança do *Vibe Coding*: Uma
> Análise de Vulnerabilidades em Aplicações Web Geradas por LLMs**. \[veículo e
> ano a definir\].
