#!/usr/bin/env bash
# =============================================================
# 05-rodar-tudo.sh - Varredura completa dos 4 modelos, 2 perfis cada.
#
# Para cada modelo, na ordem fixa de modelos.conf:
#   1. 04-preparar.sh subir     (down -v, build de producao, seed, snapshot)
#   2. 01-varrer.sh <modelo>    (user_comum e admin; restaura o banco entre eles)
#   3. 04-preparar.sh derrubar
# No fim: 02-agregar.py
# =============================================================
set -uo pipefail
RAIZ="$(cd "$(dirname "$0")" && pwd)"
cd "$RAIZ"
OUT="$RAIZ/out"; mkdir -p "$OUT"
DIARIO="$OUT/_execucao.log"

registrar() { echo "[$(date -Is)] $*" | tee -a "$DIARIO"; }

registrar "===== INICIO DA VARREDURA COMPLETA ====="
registrar "parametros: STRENGTH/THRESHOLD medium, SPIDER 5min, RULE 10min, SCAN 90min"

MODELOS=()
while read -r m _ _; do
  [[ -z "${m:-}" || "$m" == \#* ]] && continue
  MODELOS+=("$m")
done < modelos.conf
registrar "modelos na ordem: ${MODELOS[*]}"

for MODELO in "${MODELOS[@]}"; do
  registrar ">>> [$MODELO] preparando"
  if ! ./04-preparar.sh "$MODELO" subir >>"$DIARIO" 2>&1; then
    # Falha de preparacao costuma ser sistemica (porta ocupada, imagem, rede)
    # e atingiria os modelos seguintes tambem. Abortar deixa o problema
    # visivel em vez de entregar 3 de 4 varreduras silenciosamente.
    registrar "!!! [$MODELO] preparacao FALHOU - ABORTANDO a execucao"
    registrar "!!! ultimas linhas do erro:"
    tail -15 "$DIARIO" | sed 's/^/!!!   /' | tee -a "$DIARIO" >/dev/null
    ./04-preparar.sh "$MODELO" derrubar >/dev/null 2>&1
    exit 1
  fi
  registrar ">>> [$MODELO] preparado; iniciando varredura dos 2 perfis"

  INICIO=$(date +%s)
  RESTAURAR_CMD="$RAIZ/04-restaurar.sh" PAUSAR=0 ./01-varrer.sh "$MODELO" >>"$DIARIO" 2>&1
  ST=$?
  FIM=$(date +%s)
  registrar ">>> [$MODELO] varredura terminou em $(( (FIM-INICIO)/60 )) min (exit=$ST)"

  for P in user_comum admin; do
    F="$OUT/${MODELO}-${P}.json"
    if [[ -s "$F" ]]; then
      registrar "    OK  ${MODELO}-${P}.json ($(du -h "$F" | cut -f1))"
    else
      registrar "    !!! FALTANDO ${MODELO}-${P}.json"
    fi
  done

  ./04-preparar.sh "$MODELO" derrubar >>"$DIARIO" 2>&1
done

registrar ">>> agregando"
python3 02-agregar.py >>"$DIARIO" 2>&1 && registrar ">>> agregacao OK" || registrar "!!! agregacao FALHOU"
registrar "===== FIM ====="
