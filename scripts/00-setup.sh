#!/usr/bin/env bash
# =============================================================
# 00-setup.sh - Prepara e CONGELA o ambiente ZAP para o estudo.
# Rode UMA VEZ. Depois disso, nao atualize mais nada ate o fim
# do experimento, ou as varreduras deixam de ser comparaveis.
#
# Usa Dockerfile (e nao docker commit) para preservar o entrypoint
# original da imagem oficial e gerar um artefato reproduzivel.
# =============================================================
set -euo pipefail

IMAGEM="zaproxy/zap-stable"
IMG_LOCAL="zap-pesquisa:congelado"
RAIZ="$(cd "$(dirname "$0")" && pwd)"
OUT="$RAIZ/out"
mkdir -p "$OUT"

# ascanrulesBeta  -> SQLi por SGBD e time-based (injecao cega)
# ascanrulesAlpha -> regras experimentais adicionais
# ajaxSpider      -> descoberta de superficie em SPAs
# accessControl   -> teste semi-automatizado de controle de acesso (IDOR)
# jwt             -> alg:none, chave fraca, assinatura nao verificada (A07)
# reports         -> templates, inclui traditional-json-plus
ADDONS=(ascanrulesBeta ascanrulesAlpha spiderAjax accessControl jwt reports automation)
echo ">> [1/5] Baixando imagem base..."
docker pull "$IMAGEM"

echo ">> [2/5] Testando acesso ao marketplace do ZAP..."
# Se o marketplace estiver bloqueado, os add-ons nao instalam e o
# experimento roda com um conjunto de regras diferente do planejado.
if ! docker run --rm "$IMAGEM" \
     curl -sS -o /dev/null -m 30 https://bitbucket.org 2>/dev/null; then
  echo "!! AVISO: sem acesso a bitbucket.org de dentro do container."
  echo "!! O download de add-ons provavelmente vai falhar."
  echo "!! Se voce usa proxy ou VPN, configure o Docker antes de seguir."
  read -rp ">> ENTER para tentar mesmo assim, Ctrl-C para abortar: " _
fi

echo ">> [3/5] Construindo imagem com os add-ons..."
DOCKERFILE="$RAIZ/Dockerfile.zap"
{
  echo "FROM ${IMAGEM}"
  echo "# Add-ons congelados para o experimento"
  printf 'RUN zap.sh -cmd -addonupdate'
  for a in "${ADDONS[@]}"; do printf ' \\\n    -addoninstall %s' "$a"; done
  echo
} > "$DOCKERFILE"

docker build -t "$IMG_LOCAL" -f "$DOCKERFILE" "$RAIZ"

echo ">> [4/5] Validando a imagem..."
VER=$(docker run --rm "$IMG_LOCAL" zap.sh -cmd -version 2>&1 | tail -1)
if [[ ! "$VER" =~ ^[0-9]+\.[0-9]+ ]]; then
  echo "ERRO: a imagem nao executa o zap.sh. Saida obtida:"
  docker run --rm "$IMG_LOCAL" zap.sh -cmd -version 2>&1 | tail -20
  exit 1
fi
echo "   ZAP $VER OK."

# Confere que os add-ons REALMENTE entraram. O -addoninstall retorna 0
# mesmo quando o download falha, entao a checagem tem de ser explicita.
LISTA=$(docker run --rm "$IMG_LOCAL" zap.sh -cmd -addonlist 2>/dev/null)
FALTANDO=()
for a in "${ADDONS[@]}"; do
  grep -qi "$a" <<< "$LISTA" || FALTANDO+=("$a")
done

if [[ ${#FALTANDO[@]} -gt 0 ]]; then
  echo
  echo "!! ADD-ONS AUSENTES: ${FALTANDO[*]}"
  echo "!! Sem eles a varredura roda com um conjunto de regras diferente"
  echo "!! do planejado. Causa mais provavel: rede bloqueando o marketplace."
  echo "!! Alternativa: baixe os .zap manualmente em"
  echo "!!   https://github.com/zaproxy/zap-extensions/releases"
  echo "!! e adicione ao Dockerfile.zap:"
  echo "!!   COPY addons/*.zap /home/zap/.ZAP/plugin/"
  exit 1
fi
echo "   Todos os ${#ADDONS[@]} add-ons presentes."

echo ">> [5/5] Registrando versoes para a Secao 3.3.1 do artigo..."
{
  echo "# Ambiente congelado em: $(date -Is)"
  echo "# Imagem local: $IMG_LOCAL"
  echo "# Imagem base:  $IMAGEM"
  docker image inspect "$IMAGEM" --format '# Digest base: {{index .RepoDigests 0}}' 2>/dev/null || true
  echo
  echo "## Versao do ZAP"
  echo "$VER"
  echo
  echo "## Add-ons instalados"
  echo "$LISTA"
} > "$OUT/ambiente.txt"

echo
echo "OK. Imagem '$IMG_LOCAL' pronta."
echo "Versoes em out/ambiente.txt  |  Dockerfile.zap = artefato do artigo."
