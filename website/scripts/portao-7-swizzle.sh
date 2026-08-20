#!/usr/bin/env bash
#
# Portão 7 — a superfície de swizzle congelada, e `src/theme/` conferido contra ela.
#
# Cadência: UPGRADE. É o único portão da segunda cadência do repositório, e é por
# isso que ele não entra em `npm run portoes` — rodá-lo a cada commit custaria
# dez segundos de `swizzle --list` para conferir uma coisa que só muda quando o
# `@docusaurus/theme-classic` muda de versão.
#
# TRANSPLANTADO de `panlabs-tech/shinydoc-docusaurus`. O número 7 veio com ele:
# renumerar para 4 aqui não compraria nada e quebraria a leitura cruzada com o
# gabarito, que é de onde o mecanismo veio. Este site tem QUATRO portões — 1, 2,
# 3 e 7 —, e o buraco na numeração é deliberado.
#
# O mecanismo, e o que só ele enxerga: a doc do Docusaurus diz que um componente
# renomeado no upstream faz o arquivo swizzlado ser **completamente ignorado**,
# sem erro. Nenhum build reprova, porque não há nada errado a reprovar — a
# customização simplesmente para de existir. Congelar a lista e diffá-la é o
# único jeito de ver isso acontecer.
#
# A regra escrita que este portão cobra: `.claude/rules/swizzle-theme.md`.
# https://github.com/ThiagoPanini/overpower/issues/130

set -uo pipefail

echo "Portão 7 — a superfície de swizzle"
echo

if ! node scripts/swizzle-list.mjs --verificar; then
  echo
  echo "Portão 7 REPROVOU."
  exit 1
fi
