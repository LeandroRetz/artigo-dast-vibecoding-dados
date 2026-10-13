# Apêndice D — Validação manual dos achados de severidade alta

Um scanner DAST reporta injeção por **inferência**: diferença no corpo da
resposta, ou diferença no tempo de resposta. Nenhuma das duas prova que a
consulta é construída por concatenação de entrada. Este apêndice registra a
reprodução manual de quatro achados de severidade alta, buscando prova direta.

Critério aplicado a cada um:

1. o operador foi **interpretado** pela camada de dados, ou tratado como string?
2. o *payload* temporal produziu **atraso mensurável**?
3. o *payload* chegou ao banco como **dado literal**?

Dados brutos em [`dados/_validacao.csv`](../dados/_validacao.csv).
Reprodução em [`scripts/08-validar.sh`](../scripts/08-validar.sh).

---

## D.1 Injeção NoSQL em MongoDB — `deepseek-mini-v4`

`GET /api/products`, parâmetro `search`, confiança *High*, CWE-943.
*Payload*: `search[$regex]=.*`

| requisição | resultados |
|---|---:|
| sem `search` | 9 |
| com `search[$regex]=.*` | **0** |
| `search=zzzznaoexiste` (literal inexistente) | 0 |

O *payload* devolve **zero**, idêntico a uma busca por literal inexistente.
Fosse o operador interpretado, `.*` casaria todo o catálogo. O Express expande
`search[$regex]` em um objeto, que a aplicação trata como valor de string.

A consulta correspondente é uma comparação parametrizada sobre PostgreSQL:

```sql
p.name ILIKE '%' || $1 || '%'
```

Não há MongoDB em nenhuma camada da aplicação.

**Veredito: falso positivo.**

## D.2 Injeção SQL em SQLite por tempo — `deepseek-mini-v4` e `opus`

`POST /api/checkout`, parâmetros de endereço, confiança *Medium*, CWE-89.
*Payload*: `case randomblob(1000000000) when not null then 1 else 1 end`

| aplicação | sem *payload* | com *payload* |
|---|---|---|
| `deepseek-mini-v4` (campo `city`) | 0,951 · 0,345 · 0,331 s | 0,339 · 0,409 · 0,331 s |
| `opus` (campo `country`) | 0,842 · 0,471 · 0,330 s | 0,325 · 0,423 · 0,359 s |

Em SQLite, `randomblob(1000000000)` alocaria um gigabyte e travaria a resposta
por segundos. Não houve atraso mensurável em nenhuma das três repetições por
aplicação. E o valor foi persistido **verbatim**, como dado:

```
deepseek-mini-v4 → orders.city        = case randomblob(1000000000) when not null then 1 else 1 end
opus             → orders.ship_country = ' | case randomblob(10000000) when not null then "" else "" end | '
```

Vale notar o que a tabela mostra: nas duas aplicações, **a resposta mais lenta
observada foi de uma requisição sem *payload*** — o primeiro disparo de cada
série. O *endpoint* de *checkout* das quatro aplicações emite uma chamada de
rede à API do Stripe (`stripe.paymentIntents.create`), e sua latência é
dominada por esse trajeto externo, cujo primeiro estabelecimento de conexão é
mais caro. É exatamente o sinal que uma regra baseada em tempo interpreta como
evidência de injeção.

**Veredito: falso positivo** nas duas aplicações.

## D.3 Injeção SQL genérica — `deepseek-mini-v4`

`POST /api/admin/products`, parâmetro `name`, confiança *Low*, CWE-89.
Evidência registrada pelo scanner: `HTTP/1.1 500 Internal Server Error`.

| requisição | resposta |
|---|---|
| `name` normal | 201 |
| `name = '` (*payload* do scanner) | **201**, gravado literalmente como `'` |
| repetir `name = '` | **500** |
| repetir o `name` normal | **500** |
| `name = x' OR 1=1--` | **201**, gravado literalmente |

O 500 não decorre da aspa: decorre de **nome duplicado**. A tabela `products`
tem restrição de unicidade em `name`, e a violação não é tratada — reproduz-se
com qualquer nome repetido. O scanner observou 500 porque já havia enviado
aquele mesmo valor antes na varredura.

O `INSERT` correspondente é parametrizado:

```sql
INSERT INTO products (name, description, price_cents, stock, category_id, image_url)
VALUES ($1, $2, $3, $4, $5, $6) RETURNING *
```

**Veredito: falso positivo para CWE-89.** A reprodução expõe, porém, um defeito
real de menor severidade: violação de unicidade devolve 500 onde 409 seria a
resposta apropriada.

---

## D.4 Cobertura e o que permanece aberto

A reprodução cobre **cinco dos oito** achados de severidade alta de
`deepseek-mini-v4` e **três dos nove** de `opus`.

Permanecem **não reproduzidos**, como reportados pelo scanner: *path traversal*,
divulgação de código-fonte por inclusão de arquivo, injeção de *template* no
servidor e uma segunda ocorrência de injeção SQL.

O resultado é coerente com uma decisão declarada de instrumentação: as regras de
injeção SQL operam com `threshold: low` (Apêndice C.4), o que eleva
deliberadamente a sensibilidade e, com ela, a taxa esperada de falsos positivos,
por serem a classe de maior severidade sob investigação. As contagens brutas de
severidade alta devem, portanto, ser lidas como limite superior — e o fator de
superestimação **não é uniforme entre modelos**.
