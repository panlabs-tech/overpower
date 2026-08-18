#!/usr/bin/env bash
#
# Portão 1 — literal fora do arquivo de tokens.
#
# Cadência: commit.
#
# TRANSPLANTADO de `panlabs-tech/shinydoc-docusaurus`, junto com o tema que ele
# guarda. O racional abaixo é o de lá e continua valendo aqui porque o CSS é o
# mesmo — os números de issue citados na prosa são do gabarito, não deste repo.
# A regra escrita que este portão cobra mora em `.claude/rules/css-tokens.md`.
# https://github.com/panlabs-tech/overpower/issues/130
#
# Cor, comprimento, tempo e curva nascem em `src/css/tokens.css` e em nenhum
# outro lugar. Este portão não depende de ninguém lembrar da regra: depende de a
# varredura passar.
#
# Escopo deliberado nas quatro categorias que carregam desenho. `0`, número sem
# unidade, `%`, `fr`, `ch`, `lh` e `auto` ficam de fora: são layout, e flagrá-los
# transformaria o portão em ruído, que é como portão morre.
#
# `lh` entrou na lista no slice do catálogo do gabarito, e entrou por decisão em vez de por
# omissão. Ele é a altura da linha do próprio elemento — uma REFERÊNCIA ao que a
# escala de tipografia já decidiu, como `%` é referência ao contêiner. Quem
# escreve `calc((1lh - var(--sd-space-4)) / 2)` para centrar um ícone na primeira
# linha não escolheu um número: pediu o que a entrelinha der. Cravar o mesmo
# recuo em `px` é que seria literal, e esse o portão pega.
#
# ---------------------------------------------------------------------------
# A SEGUNDA PERNA — e ela nasceu de um limite que a primeira redação previu
#
# Media query não lê custom property, e o limiar dela é um comprimento. A
# redação original deste portão escreveu, em voz alta: *"o dia em que um CSS
# Module precisar do limiar é o dia de reabrir esta linha — e não de afrouxar o
# portão em silêncio."* O slice 2 é esse dia: `chrome.css` e `foco.css` têm o
# limiar do estreito, e `foco.css` tem `(pointer: coarse)` e `(hover: none)`.
#
# Reabrir em voz alta significa trocar uma regra por outra mais forte, não
# abrir uma exceção. O prelúdio de `@media` sai da varredura de literal E entra
# numa varredura própria, que exigia que **todo limiar de comprimento do
# projeto fosse 996px ou 997px** — os literais compilados do Infima.
#
# O portão cobrava o que a spec decidira: um limiar só no projeto inteiro, e
# não os 1024 da âncora brigando com os 996/997 do framework. Um
# `@media (min-width: 1024px)` novo reprovava aqui, e reprovava onde
# precisava — CONTINUA reprovando: a #96 do gabarito mediu que o limiar de 1024 da âncora
# (esconder a sidebar) não é alcançável sem reabrir `windowSize` do React, que
# é `unsafe` fora do alcance de qualquer CSS. Essa parte da premissa original SOBREVIVE inteira.
#
# ---------------------------------------------------------------------------
# A REABERTURA DA #96 DO GABARITO — em voz alta, como o parágrafo acima pediu
#
# O TOC tem limiar PRÓPRIO agora, 1280, e ele não briga com o do framework
# pelo motivo oposto ao da sidebar: esconder `.col--3` é decisão NOSSA sobre
# um `<div>` que o CSS já controla por inteiro — não há `windowSize` do React
# no caminho, porque `DocItemTOCDesktop` já está montado em toda a faixa
# `windowSize === 'desktop'`, que cobre de 997 a infinito. 1280 é só onde a
# ÂNCORA muda de ideia visualmente, e o React nunca precisa saber.
#
# A lista fechada cresce de um valor para dois: **996/997 (o par do Infima,
# um limiar semântico) e 1280 (o do TOC)**. Continua sendo
# exatamente o que o parágrafo do slice 2 previu: trocar uma regra por outra
# mais forte, não abrir uma exceção silenciosa.
# ---------------------------------------------------------------------------

set -uo pipefail

ARQUIVO_DE_TOKENS='src/css/tokens.css'
PADRAO='#[0-9a-fA-F]{3,8}\b|[0-9.]+(px|rem|em|ms|s)\b|cubic-bezier|oklch\(|rgb\(|hsl\('
LIMIARES_FECHADOS='(99[67]|1280)px'

# A varredura cobre DECLARAÇÃO, não prosa: comentário sai antes, com o número de
# linha preservado. Ver `scripts/css-sem-comentario.awk`.
codigo() { find src -name '*.css' -exec awk -f scripts/css-sem-comentario.awk {} +; }

# --- perna 1: literal de desenho fora do arquivo de tokens -------------------
# O prelúdio de `@media` é excluído aqui e cobrado na perna 2.
achados=$(codigo \
  | grep -E "$PADRAO" \
  | grep -v "^${ARQUIVO_DE_TOKENS}:" \
  | grep -vE '^[^:]+:[0-9]+:[[:space:]]*@media') || true

if [ -n "$achados" ]; then
  echo "Portão 1 REPROVOU — literal de cor, comprimento, tempo ou curva fora de ${ARQUIVO_DE_TOKENS}:"
  echo
  echo "$achados"
  echo
  echo "O valor precisa nascer como token em ${ARQUIVO_DE_TOKENS} e ser citado por nome."
  exit 1
fi

# --- perna 2: lista fechada de limiares de media query -----------------------
# Toda media query com comprimento precisa usar um dos limiares fechados. As
# que não têm comprimento — `hover`, `pointer`, `prefers-reduced-motion` —
# passam livres.
limiares=$(codigo \
  | grep -E '^[^:]+:[0-9]+:[[:space:]]*@media' \
  | grep -E '[0-9.]+(px|rem|em)' \
  | grep -vE "$LIMIARES_FECHADOS") || true

if [ -n "$limiares" ]; then
  echo "Portão 1 REPROVOU — limiar de media query fora da lista fechada (996/997px, 1280px):"
  echo
  echo "$limiares"
  echo
  echo "O projeto tem DOIS limiares, e cada um responde por um eixo que não briga com"
  echo "o outro: 996/997 é o literal compilado do Infima — mostra e esconde a sidebar,"
  echo "dobra o gutter, monta a faixa —, e 1280 é só do TOC, puro CSS, sem estado de"
  echo "React no caminho. Um terceiro limiar aqui é a mesma briga que a redação"
  echo "original recusou — ver o comentário no topo do arquivo."
  exit 1
fi

echo "Portão 1 passou — nenhum literal de desenho fora de ${ARQUIVO_DE_TOKENS}, e limiares na lista fechada."
