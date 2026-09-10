#!/usr/bin/env bash
# =============================================================
# 08-validar.sh - Reproducao manual dos achados de severidade alta.
#
#   ./08-validar.sh deepseek-mini-v4
#   ./08-validar.sh opus
#
# Roda contra a aplicacao ATUALMENTE de pe em localhost:5173, com o banco
# restaurado ao snapshot da varredura (04-preparar.sh <modelo> restaurar).
#
# Um scanner DAST reporta injecao por inferencia: diferenca de resposta,
# ou diferenca de tempo. Nenhuma das duas prova que a consulta e
# construida por concatenacao. Este script busca a prova direta:
#   (a) o operador foi interpretado ou tratado como string?
#   (b) o payload temporal produziu atraso mensuravel?
#   (c) o payload chegou ao banco como dado literal?
# =============================================================
set -uo pipefail
MODELO="${1:?uso: 08-validar.sh <modelo>}"
BASE=http://localhost:5173

logar() { curl -si -X POST "$BASE/api/auth/login" -H 'Content-Type: application/json' \
          -d "{\"email\":\"$1\",\"password\":\"Test1234!\"}" \
          | grep -i '^set-cookie' | sed 's/.*: //;s/;.*//'; }

CK=$(logar user@test.com)
CKA=$(logar admin@test.com)
[[ -n "$CK" && -n "$CKA" ]] || { echo "!! login falhou"; exit 1; }

total() { python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('total','?'))"; }

if [[ "$MODELO" == "deepseek-mini-v4" ]]; then
  echo "== NoSQL Injection - MongoDB | GET /api/products?search"
  echo "   sem search .............. $(curl -s "$BASE/api/products?page=1&pageSize=3" | total)"
  echo "   search[\$regex]=.* ....... $(curl -s "$BASE/api/products?page=1&pageSize=3&search%5B%24regex%5D=.*" | total)"
  echo "   literal inexistente ..... $(curl -s "$BASE/api/products?page=1&pageSize=3&search=zzzznaoexiste" | total)"
  echo "   (operador interpretado casaria TODO o catalogo; igualar o literal = falso positivo)"

  echo
  echo "== SQL Injection | POST /api/admin/products, parametro name"
  novo() { curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/api/admin/products" \
           -H 'Content-Type: application/json' -b "$CKA" \
           -d "{\"name\":$1,\"description\":\"x\",\"price_cents\":1000,\"stock\":5,\"category_id\":1}"; }
  echo "   nome normal ............. $(novo '"Validacao A"')"
  echo "   name = aspa simples ..... $(novo "\"'\"")"
  echo "   repetir a aspa .......... $(novo "\"'\"")"
  echo "   repetir o nome normal ... $(novo '"Validacao A"')"
  echo "   name = x' OR 1=1-- ...... $(novo "\"x' OR 1=1--\"")"
  echo "   (500 nos REPETIDOS, e nao na aspa, indica violacao de UNIQUE, nao injecao)"
fi

echo
echo "== SQL Injection - SQLite (Time Based) | POST /api/checkout"
case "$MODELO" in
  opus) CAMPO=country; CORPO='{"shipping":{"name":"Usuario Comum","line1":"Rua Teste 100","city":"Porto Alegre","state":"RS","postalCode":"90000000","country":%s}}'; PROD_CAMPO=productId ;;
  *)    CAMPO=city;    CORPO='{"address":{"line1":"Rua Teste 100","city":%s,"state":"RS","postalCode":"90000000","country":"BR"}}'; PROD_CAMPO=product_id ;;
esac
PROD=$(curl -s "$BASE/api/products" | python3 -c "import json,sys; print(json.load(sys.stdin)['items'][0]['id'])")

medir() {
  for n in 1 2 3; do
    curl -s -o /dev/null -b "$CK" -X POST "$BASE/api/cart/items" -H 'Content-Type: application/json' \
         -d "{\"$PROD_CAMPO\":\"$PROD\",\"quantity\":1}"
    corpo=$(python3 -c "import json,sys; print(sys.argv[1] % json.dumps(sys.argv[2]))" "$CORPO" "$2")
    printf "   %-22s run%d  %ss\n" "$1" "$n" \
      "$(curl -s -o /dev/null -b "$CK" -w '%{time_total}' -X POST "$BASE/api/checkout" \
         -H 'Content-Type: application/json' -d "$corpo")"
  done
}
medir "sem payload" "Porto Alegre"
medir "com randomblob" 'case randomblob(1000000000) when not null then 1 else 1 end '
echo "   (randomblob em SQLite alocaria memoria por segundos; ausencia de atraso = falso positivo)"
echo "   (conferir no banco que o valor chegou como string literal na coluna de $CAMPO)"
