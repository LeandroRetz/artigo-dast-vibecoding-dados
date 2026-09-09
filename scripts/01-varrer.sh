#!/usr/bin/env bash
# =============================================================
# 01-varrer.sh - Executa a varredura DAST em todos os modelos
# listados em modelos.conf, com configuracao IDENTICA.
#
# Uso:  ./01-varrer.sh            (todos)
#       ./01-varrer.sh fable5     (so um modelo)
# =============================================================
set -euo pipefail

# ----------------- PARAMETROS DO EXPERIMENTO -----------------
# Estes valores DEVEM ser identicos entre modelos e reportados
# na Secao 3.3.1 do artigo.
export STRENGTH="medium"     # payloads por parametro
export THRESHOLD="medium"    # criterio de confirmacao
export SPIDER_MIN=5          # minutos de spider (esforco fixo)
export RULE_MIN=10           # minutos maximos por regra
export SCAN_MIN=90           # minutos maximos de active scan

# Perfis de acesso varridos, na ordem. Uma varredura completa por perfil.
# Os nomes devem bater com o bloco "users" do plano.yaml.template.
PERFIS=(user_comum admin)

# ----------------- AUTENTICACAO ------------------------------
# Preencha conforme o DevTools da aplicacao. Assume-se que as
# quatro implementacoes seguem o mesmo spec, logo as mesmas rotas.
export AUTH_METHOD="json"                       # json | form | browser
export LOGIN_PATH="/login"
export LOGIN_REQUEST_PATH="/api/auth/login"
export LOGIN_BODY='{"email":"{%username%}","password":"{%password%}"}'
export POLL_PATH="/api/users/me"

# "headers" para JWT no Authorization; "cookie" para sessao classica
export SESSION_METHOD="cookie"
export JWT_FIELD="token"     # nome do campo do token na resposta do login

export USER_EMAIL="user@test.com"
export USER_PASS="Test1234!"
export ADMIN_EMAIL="admin@test.com"
export ADMIN_PASS="Test1234!"
# -------------------------------------------------------------

IMG_LOCAL="zap-pesquisa:congelado"
RAIZ="$(cd "$(dirname "$0")" && pwd)"
OUT="$RAIZ/out"
PLANOS="$RAIZ/planos"
mkdir -p "$OUT" "$PLANOS"

FILTRO="${1:-}"

docker image inspect "$IMG_LOCAL" >/dev/null 2>&1 || {
  echo "ERRO: imagem '$IMG_LOCAL' nao existe. Rode ./00-setup.sh primeiro."
  exit 1
}

# Host visto de dentro do container
if [[ "$(uname -s)" == "Linux" ]]; then
  REDE=(--network host); HOST_INTERNO="localhost"
else
  REDE=(); HOST_INTERNO="host.docker.internal"
fi

while read -r MODELO PORTA TIPO <&3; do
  [[ -z "${MODELO:-}" || "$MODELO" == \#* ]] && continue
  [[ -n "$FILTRO" && "$MODELO" != "$FILTRO" ]] && continue

  echo
  echo "============================================================"
  echo ">> MODELO: $MODELO  (porta $PORTA, $TIPO)"
  echo "============================================================"

  # --- 0. Pausa para trocar a aplicacao (modelos rodam um por vez) ---
  # Pule a pausa com PAUSAR=0 ./01-varrer.sh, ou quando ha filtro de modelo.
  if [[ "${PAUSAR:-1}" == "1" && -z "$FILTRO" ]]; then
    echo
    echo ">> Derrube a aplicacao anterior e suba a do modelo '$MODELO'"
    echo "   na porta $PORTA, com o banco em estado inicial."
    read -rp ">> ENTER para varrer, 'p' para pular este modelo: " RESP
    [[ "$RESP" == "p" ]] && { echo "   Pulado."; continue; }
  fi

  export MODELO
  export BASE_URL="http://${HOST_INTERNO}:${PORTA}"
  export GERADO_EM="$(date -Is)"
  export LOGIN_PAGE_URL="${BASE_URL}${LOGIN_PATH}"
  export LOGIN_REQUEST_URL="${BASE_URL}${LOGIN_REQUEST_PATH}"
  export POLL_URL="${BASE_URL}${POLL_PATH}"

  # --- 1. Sanidade: a aplicacao esta de pe? ---
  echo ">> Testando conectividade em $BASE_URL ..."
  if ! curl -sS -o /dev/null -m 10 "http://localhost:${PORTA}"; then
    echo "!! FALHA: nada respondendo na porta $PORTA. Pulando $MODELO."
    echo "   (varredura sem achados quase sempre e conexao recusada)"
    continue
  fi
  echo "   OK."

  # --- 1b. Impressao digital: confirma que trocou mesmo de aplicacao ---
  # Com todos os modelos na mesma porta, o risco real e varrer duas vezes
  # a mesma app achando que sao duas. Estes valores devem DIFERIR entre modelos.
  FP_SRV=$(curl -sSI -m 10 "http://localhost:${PORTA}" | tr -d '\r' \
           | grep -iE '^(server|x-powered-by):' | paste -sd'; ' - || true)
  FP_HASH=$(curl -sS -m 10 "http://localhost:${PORTA}" | md5sum | cut -c1-12)
  echo "   fingerprint: [${FP_SRV:-sem header}] body-md5=${FP_HASH}"

  # So conta como duplicata se a varredura anterior tiver CONCLUIDO.
  if [[ -f "$OUT/_fingerprints.txt" ]] && \
     grep -q "|${FP_HASH}$" "$OUT/_fingerprints.txt" && \
     ! grep -q "^${MODELO}-|${FP_HASH}$" "$OUT/_fingerprints.txt"; then
    ANTERIOR=$(grep "|${FP_HASH}$" "$OUT/_fingerprints.txt" | head -1 | cut -d'|' -f1)
    echo "!! ATENCAO: hash identico ao do modelo '${ANTERIOR}', ja varrido."
    echo "!! Voce pode nao ter trocado a aplicacao. Verifique antes de seguir."
    if [[ -n "${RESTAURAR_CMD:-}" ]]; then
      echo "!! Modo automatizado: ABORTANDO. Hash duplicado corrompe o dado."
      exit 1
    fi
    read -rp ">> ENTER para continuar mesmo assim, Ctrl-C para abortar: " _
  fi

  # ============================================================
  # Uma varredura POR PERFIL de acesso. Sem isto, as rotas que so
  # o admin alcanca (painel, gestao de usuarios) nunca sao exercidas
  # e ficam fora da comparacao entre modelos.
  # ============================================================
  for PERFIL in "${PERFIS[@]}"; do
  export PERFIL
  echo
  echo "   ---- perfil: $PERFIL ----"

  # Entre perfis o banco precisa voltar ao estado inicial: o active
  # scan anterior pode ter criado, alterado ou apagado registros.
  if [[ "$PERFIL" != "${PERFIS[0]}" ]]; then
    # RESTAURAR_CMD permite automatizar a restauracao (04-preparar.sh restaurar).
    # Sem ela, o comportamento original: pausa e espera o operador.
    if [[ -n "${RESTAURAR_CMD:-}" ]]; then
      echo "   >> Restaurando o banco: $RESTAURAR_CMD $MODELO"
      $RESTAURAR_CMD "$MODELO" || { echo "!! restauracao falhou; abortando"; exit 1; }
    else
      echo "   >> Restaure o banco ao estado inicial (seed) antes de seguir."
      read -rp "   >> ENTER quando o banco estiver semeado novamente: " _
    fi
  fi

  # --- 2. Monta os blocos variaveis do plano ---
  if [[ "$SESSION_METHOD" == "headers" ]]; then
    export SESSION_PARAMS="        parameters:
          Authorization: \"Bearer {%json:${JWT_FIELD}%}\""
  else
    export SESSION_PARAMS=""
  fi

  # --- 2b. Cookie de sessao do perfil, obtido fora do ZAP ---
  # Ver o comentario do job replacer no plano.yaml.template para o porque.
  if [[ "$PERFIL" == "admin" ]]; then
    EMAIL="$ADMIN_EMAIL"; SENHA="$ADMIN_PASS"
  else
    EMAIL="$USER_EMAIL"; SENHA="$USER_PASS"
  fi
  COOKIE_SESSAO=$(curl -sS -i -m 20 -X POST "http://localhost:${PORTA}${LOGIN_REQUEST_PATH}" \
    -H 'Content-Type: application/json' \
    -d "{\"email\":\"${EMAIL}\",\"password\":\"${SENHA}\"}" \
    | grep -i '^set-cookie:' | head -1 | sed -E 's/^[Ss]et-[Cc]ookie: *//' | cut -d';' -f1 || true)

  if [[ -z "$COOKIE_SESSAO" ]]; then
    echo "!! FALHA: login de ${EMAIL} nao devolveu Set-Cookie."
    echo "!! Varrer assim produziria dados de sessao anonima. Abortando ${MODELO}/${PERFIL}."
    continue
  fi
  echo "   sessao ${PERFIL}: cookie '${COOKIE_SESSAO%%=*}' obtido"

  # Confirma que o cookie realmente autentica antes de gastar 90 min.
  COD_AUTH=$(curl -sS -o /dev/null -w '%{http_code}' -m 20 \
    -H "Cookie: ${COOKIE_SESSAO}" "http://localhost:${PORTA}${POLL_PATH}")
  if [[ "$COD_AUTH" != "200" ]]; then
    echo "!! FALHA: ${POLL_PATH} devolveu ${COD_AUTH} com o cookie (esperado 200)."
    echo "!! Abortando ${MODELO}/${PERFIL} em vez de varrer deslogado."
    continue
  fi
  echo "   sessao ${PERFIL}: ${POLL_PATH} -> 200, autenticada"

  export JOB_REPLACER="  - type: \"replacer\"
    parameters:
      deleteAllRules: true
    rules:
      - description: \"cookie de sessao do perfil ${PERFIL}\"
        matchType: \"req_header\"
        matchString: \"Cookie\"
        replacementString: \"${COOKIE_SESSAO}\""

  if [[ "$TIPO" == "spa" ]]; then
    # Sem "user": quem autentica e o job replacer (cookie injetado).
    # Com "user", o ZAP reautentica a cada request nas aplicacoes que marcam
    # o cookie como Secure, e o crawl colapsa (11 URLs em vez de ~900).
    export JOB_AJAX="  - type: spiderAjax
    parameters:
      context: \"app\"
      url: \"${BASE_URL}\"
      maxDuration: ${SPIDER_MIN}
      browserId: \"firefox-headless\""
  else
    export JOB_AJAX=""
  fi

  # --- 3. Gera o plano concreto (fica no repo como evidencia) ---
  PLANO="$PLANOS/plano-${MODELO}-${PERFIL}.yaml"
  envsubst < "$RAIZ/plano.yaml.template" > "$PLANO"
  echo "   >> Plano gerado: planos/plano-${MODELO}-${PERFIL}.yaml"

  # --- 4. Executa ---
  LOG="$OUT/${MODELO}-${PERFIL}-log.txt"
  INICIO=$(date +%s)
  set +e
  docker run --rm "${REDE[@]}" \
    -v "$RAIZ":/zap/wrk/:rw \
    "$IMG_LOCAL" zap.sh -cmd \
    -config start.checkForUpdates=false \
    -autorun "/zap/wrk/planos/plano-${MODELO}-${PERFIL}.yaml" 2>&1 | tee "$LOG"
  STATUS=${PIPESTATUS[0]}
  set -e
  FIM=$(date +%s)

  echo ">> Duracao: $(( (FIM-INICIO)/60 )) min | exit=$STATUS" | tee -a "$LOG"

  # Registra a impressao digital so se a varredura concluiu.
  if [[ $STATUS -eq 0 ]]; then
    echo "${MODELO}-${PERFIL}|$(date -Is)|${FP_SRV}|${FP_HASH}" >> "$OUT/_fingerprints.txt"
  else
    echo "!! Varredura de ${MODELO}/${PERFIL} falhou (exit=$STATUS). Veja $LOG."
  fi

  # --- 5. Alerta se a sessao caiu (destroi a comparabilidade) ---
  if grep -qiE "authentication.*fail|user is not logged in|login failed" "$LOG"; then
    echo "!! ATENCAO: o log indica falha de autenticacao em ${MODELO}/${PERFIL}."
    echo "!! A cobertura de rotas protegidas pode estar comprometida."
  fi

  done   # fim do laco de perfis

done 3< "$RAIZ/modelos.conf"

echo
echo "Concluido. Relatorios em out/. Agora rode: python3 02-agregar.py"
