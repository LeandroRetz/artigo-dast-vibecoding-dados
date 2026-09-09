#!/usr/bin/env bash
# Wrapper para RESTAURAR_CMD do 01-varrer.sh: recebe so o modelo.
exec "$(dirname "$0")/04-preparar.sh" "$1" restaurar
