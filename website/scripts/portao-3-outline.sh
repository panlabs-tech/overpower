#!/usr/bin/env bash
#
# Portão 3 — `outline` fora do arquivo de foco.
#
# Cadência: commit.
#
# TRANSPLANTADO de `panlabs-tech/shinydoc-docusaurus`, junto com o tema que ele
# guarda. O racional abaixo é o de lá e continua valendo aqui porque o CSS é o
# mesmo — os números de issue citados na prosa são do gabarito, não deste repo.
# A regra escrita que este portão cobra mora em `.claude/rules/css-tokens.md`.
# https://github.com/ThiagoPanini/overpower/issues/130
#
# O contrato de estado de entrada mora inteiro em `src/css/foco.css`. Nenhum
# outro arquivo do projeto escreve `outline`.
#
# O motivo é específico, e não é higiene. Este contrato não morre por alguém
# desenhar um anel ruim — morre por alguém escrever `outline: none` num botão
# para "limpar" o visual. É a linha de CSS mais comum do mundo, e ela apaga
# acessibilidade de teclado **sem sintoma visível para quem a escreveu**.
#
# A varredura cobre `src/` inteiro, inclusive CSS Module de componente. A regra
# universal de `:focus-visible` alcança todo focável do site; um componente que
# precise dizer qualquer coisa sobre foco além de *"herda"* está com o desenho
# errado, e é `foco.md` que decide, não o componente.
#
# Limite conhecido, escrito em voz alta: `grep` é orientado a linha, então uma
# declaração `outline` quebrada em várias linhas escapa. Hoje não há nenhuma, e
# o dia em que houver é o dia de normalizar espaço em branco na varredura — não
# de ignorar o achado.

set -uo pipefail

ARQUIVO_DE_FOCO='src/css/foco.css'
PADRAO='(^|[^-a-z])outline[a-z-]*[[:space:]]*:'

# Comentário sai antes da varredura: o portão cobra DECLARAÇÃO, não prosa. Ver
# `scripts/css-sem-comentario.awk`.
achados=$(find src -name '*.css' -exec awk -f scripts/css-sem-comentario.awk {} + \
  | grep -E "$PADRAO" \
  | grep -v "^${ARQUIVO_DE_FOCO}:") || true

if [ -n "$achados" ]; then
  echo "Portão 3 REPROVOU — \`outline\` fora de ${ARQUIVO_DE_FOCO}:"
  echo
  echo "$achados"
  echo
  echo "O contrato de estado de entrada é universal e mora num arquivo só."
  echo "Se o anel precisa mudar de dono, a regra vai para ${ARQUIVO_DE_FOCO} —"
  echo "ver \`.claude/rules/css-tokens.md\`."
  exit 1
fi

echo "Portão 3 passou — \`outline\` só existe em ${ARQUIVO_DE_FOCO}."
