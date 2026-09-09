#!/usr/bin/env bash
# =============================================================
# 04-preparar.sh - Prepara UMA aplicacao para a varredura.
#
#   ./04-preparar.sh <modelo> subir      # down -v, up producao, semear, promover, snapshot
#   ./04-preparar.sh <modelo> restaurar  # volta o banco ao snapshot (entre perfis)
#   ./04-preparar.sh <modelo> derrubar
#
# O snapshot e o estado inicial canonico do modelo: e ele que precisa
# valer para os DOIS perfis, senao admin e user_comum varrem bancos
# diferentes e a comparacao entre perfis perde sentido.
# =============================================================
set -euo pipefail

MODELO="${1:?uso: 04-preparar.sh <modelo> subir|restaurar|derrubar}"
ACAO="${2:?uso: 04-preparar.sh <modelo> subir|restaurar|derrubar}"
RAIZ="$(cd "$(dirname "$0")" && pwd)"
OUT="$RAIZ/out"; mkdir -p "$OUT"

# modelo -> diretorio da aplicacao, usuario e nome do banco
case "$MODELO" in
  deepseek-mini-v4) DIR="/home/leandro/Desktop/artigo deepseek"; PGUSER=app;      PGDB=shop ;;
  qwen-3.8-8b)      DIR="/home/leandro/Desktop/artigo gwen";     PGUSER=app;      PGDB=shop ;;
  fable5)           DIR="/home/leandro/Desktop/artigo fable";    PGUSER=shop;     PGDB=shop ;;
  opus)             DIR="/home/leandro/Desktop/artigo opus";     PGUSER=postgres; PGDB=ecommerce ;;
  *) echo "modelo desconhecido: $MODELO"; exit 1 ;;
esac

DC=(docker compose -f "$DIR/docker-compose.yml" -f "$DIR/docker-compose.dast.yml")
SNAP="$OUT/_snapshot-${MODELO}.sql"

esperar() {
  echo -n "   aguardando aplicacao"
  for _ in $(seq 1 60); do
    if curl -sf -o /dev/null -m 3 http://localhost:5173/ \
       && curl -sf -o /dev/null -m 3 http://localhost:5173/api/products; then
      echo " OK"; return 0
    fi
    echo -n "."; sleep 3
  done
  echo; echo "!! aplicacao nao respondeu em 180s"; "${DC[@]}" logs --tail 40; return 1
}

verificar() {
  # Round-trip completo do cookie. Nao basta o login devolver 200: tres das
  # quatro aplicacoes marcam o cookie como Secure quando NODE_ENV=production,
  # e um cookie Secure pode nao voltar sobre HTTP. Se isso acontecer, o ZAP
  # varreria tudo deslogado sem nenhum erro visivel.
  local anon logi prot jar rc=0
  jar=$(mktemp)
  anon=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:5173/api/users/me)
  logi=$(curl -s -o /dev/null -w '%{http_code}' -c "$jar" -X POST http://localhost:5173/api/auth/login \
         -H 'Content-Type: application/json' \
         -d '{"email":"user@test.com","password":"Test1234!"}')
  prot=$(curl -s -o /dev/null -w '%{http_code}' -b "$jar" http://localhost:5173/api/users/me)
  echo "   anonimo=$anon (401) | login=$logi (200) | com cookie=$prot (200)"
  [[ "$anon" == "401" ]] || { echo "!! /api/users/me nao devolve 401 anonimo"; rc=1; }
  [[ "$logi" == "200" ]] || { echo "!! login nao devolve 200"; rc=1; }
  [[ "$prot" == "200" ]] || { echo "!! COOKIE NAO FAZ ROUND-TRIP: a varredura rodaria deslogada"; rc=1; }

  # Os dois perfis precisam enxergar superficies diferentes, senao o login
  # como admin nao esta funcionando e a segunda passagem seria redundante.
  local jara adm_u adm_a
  jara=$(mktemp)
  curl -s -o /dev/null -c "$jara" -X POST http://localhost:5173/api/auth/login \
       -H 'Content-Type: application/json' \
       -d '{"email":"admin@test.com","password":"Test1234!"}'
  adm_u=$(curl -s -o /dev/null -w '%{http_code}' -b "$jar"  http://localhost:5173/api/admin/orders)
  adm_a=$(curl -s -o /dev/null -w '%{http_code}' -b "$jara" http://localhost:5173/api/admin/orders)
  echo "   /api/admin/orders: user_comum=$adm_u | admin=$adm_a"
  [[ "$adm_a" == "200" ]] || { echo "!! admin@test.com nao alcanca rota administrativa"; rc=1; }
  [[ "$adm_u" != "200" ]] || echo "!! ATENCAO: user_comum tambem alcanca /api/admin (possivel falha de autorizacao - NAO corrigir, e dado)"
  rm -f "$jar" "$jara"
  return $rc
}

case "$ACAO" in
  subir)
    # Derruba os QUATRO stacks, nao so o do modelo alvo: todos publicam nas
    # mesmas portas (5173, 4000, 5432) e um stack esquecido de pe faz o
    # proximo falhar com "port is already allocated". Os modelos rodam um
    # por vez por desenho do experimento.
    echo ">> [$MODELO] derrubando todos os stacks..."
    for OUTRO in "/home/leandro/Desktop/artigo deepseek" "/home/leandro/Desktop/artigo gwen" \
                 "/home/leandro/Desktop/artigo fable" "/home/leandro/Desktop/artigo opus"; do
      docker compose -f "$OUTRO/docker-compose.yml" -f "$OUTRO/docker-compose.dast.yml" \
        down -v >/dev/null 2>&1 || true
    done
    # Confirma que as portas ficaram livres antes de subir.
    for _ in $(seq 1 20); do
      ss -ltn 2>/dev/null | grep -qE ':(5173|4000|5432)\s' || break
      sleep 1
    done
    if ss -ltn 2>/dev/null | grep -qE ':(5173|4000|5432)\s'; then
      echo "!! portas 5173/4000/5432 ainda ocupadas por algo fora do experimento:"
      ss -ltnp 2>/dev/null | grep -E ':(5173|4000|5432)\s'
      exit 1
    fi
    echo ">> [$MODELO] zerando o banco e subindo..."
    echo ">> [$MODELO] subindo build de producao..."
    "${DC[@]}" up -d >/dev/null
    esperar
    echo ">> [$MODELO] semeando dados por usuario..."
    STRIPE_ENV_FILE="$DIR/.env" python3 "$RAIZ/03-semear.py" "$MODELO" >"$OUT/seed-${MODELO}.log" 2>&1 \
      || { echo "!! seed falhou, veja $OUT/seed-${MODELO}.log"; tail -20 "$OUT/seed-${MODELO}.log"; exit 1; }
    grep -E "^  (OK|FALHA|pedido|avaliacao|register|login)" "$OUT/seed-${MODELO}.log" | sed 's/^/   /' || true
    echo ">> [$MODELO] promovendo admin@test.com..."
    "${DC[@]}" exec -T db psql -U "$PGUSER" -d "$PGDB" \
      -c "UPDATE users SET role='admin' WHERE email='admin@test.com';"
    verificar
    echo ">> [$MODELO] snapshot do estado inicial..."
    "${DC[@]}" exec -T db pg_dump -U "$PGUSER" -d "$PGDB" --clean --if-exists > "$SNAP"
    echo "   $(wc -l < "$SNAP") linhas em $(basename "$SNAP")"
    echo ">> [$MODELO] pronto para varrer."
    ;;

  restaurar)
    [[ -f "$SNAP" ]] || { echo "!! sem snapshot para $MODELO"; exit 1; }
    echo ">> [$MODELO] restaurando o banco ao estado inicial..."
    "${DC[@]}" exec -T db psql -q -U "$PGUSER" -d "$PGDB" < "$SNAP" >/dev/null
    # O backend mantem pool de conexoes; reiniciar evita estado em cache.
    "${DC[@]}" restart backend >/dev/null
    esperar
    verificar
    echo ">> [$MODELO] banco restaurado."
    ;;

  derrubar)
    "${DC[@]}" down -v >/dev/null 2>&1 || true
    echo ">> [$MODELO] derrubado."
    ;;

  *) echo "acao invalida: $ACAO"; exit 1 ;;
esac
