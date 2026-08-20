#!/usr/bin/env bash
#
# Portão 2 — duas pernas: duração ou curva cravada numa transição, e transição
# de cor sobre o documento.
#
# Cadência: commit.
#
# TRANSPLANTADO de `panlabs-tech/shinydoc-docusaurus`, junto com o tema que ele
# guarda. O racional abaixo é o de lá e continua valendo aqui porque o CSS é o
# mesmo — os números de issue citados na prosa são do gabarito, não deste repo.
# A regra escrita que este portão cobra mora em `.claude/rules/css-tokens.md`.
# https://github.com/ThiagoPanini/overpower/issues/130
#
# Nenhum CSS do projeto escreve duração ou curva fora dos seis movimentos
# nomeados. Não é higiene: é o que faz `prefers-reduced-motion` alcançar o
# Infima e o theme-classic, que nós não escrevemos. Movimento que compõe da
# escala herda a redefinição; movimento com número cravado, não.
#
# A varredura cobre `src/` INTEIRO, inclusive o arquivo de tokens — e isso não é
# mais estrito por acaso. O bloco de vocabulário sobrevive porque ele declara
# TOKENS (`--sd-dur-*`, `--sd-ease-*`, `--sd-move-*`), não declarações
# `transition:` ou `animation:`. "Fora do bloco de vocabulário" e "em toda
# parte" coincidem por construção, e um `transition: color 200ms` escrito dentro
# do próprio arquivo de tokens reprova como qualquer outro.
#
# Limite conhecido, escrito em voz alta: `grep` é orientado a linha, então uma
# declaração `transition:` cujo valor quebre em várias linhas escapa. Fora do
# arquivo de tokens isso não importa — o portão 1 pega o literal de tempo em
# qualquer posição. Dentro dele, este é o único guarda, e hoje não há nenhuma
# declaração de transição multilinha lá. O dia em que houver é o dia de trocar a
# varredura por uma que normalize espaço em branco — não de ignorar o achado.

set -uo pipefail

PADRAO='(transition|animation)[a-z-]*:[^;{}]*([0-9.]+m?s\b|cubic-bezier)'

# Comentário sai antes da varredura: o portão cobra DECLARAÇÃO, não prosa. Ver
# `scripts/css-sem-comentario.awk`.
achados=$(find src -name '*.css' -exec awk -f scripts/css-sem-comentario.awk {} + \
  | grep -E "$PADRAO") || true

if [ -n "$achados" ]; then
  echo "Portão 2 REPROVOU — duração ou curva cravada numa transição/animação:"
  echo
  echo "$achados"
  echo
  echo "Use um dos seis movimentos: --sd-move-{state,enter,expand,showcase,reveal,ambient}."
  exit 1
fi

# --- segunda perna: transição de cor sobre o documento -----------------------
#
# a doutrina de motion fecha a lista do que nunca anima com "a superfície não anima":
# proibição de `transition` em `background-color` ou `color` no `:root`, no
# `html` e no `body`. Ela carregava a nota *"verificado na implementação"* desde
# o slice 1, e ninguém a verificava desde então — a auditoria S9-1 achou a
# afirmação de pé e a régua ausente.
#
# A primeira perna não a pega, e a razão é que a violação seria LEGÍTIMA por
# ela: `transition: color var(--sd-move-state)` no `:root` compõe do vocabulário
# certinho e passaria. O que reprova aqui é o SELETOR, não o valor.
#
# A varredura é de duas passadas porque a declaração e o seletor estão em linhas
# diferentes: `awk` guarda o último seletor visto e só olha as declarações de
# transição debaixo dele. O comentário já saiu na passada de cima.
#
# A ARMADILHA que custou uma rodada: `css-sem-comentario.awk` emite
# `arquivo:linha:código`, e um seletor `:root` vira `src/css/tokens.css:12::root`.
# Uma âncora `^` no regex do seletor nunca casa nesse texto, e o portão passa
# verde com a violação escrita — que é o pior modo de falhar que um portão tem.
# O prefixo sai antes da comparação, e o endereço é guardado à parte para o
# relatório continuar apontando onde está.
#
# LIMITE CONHECIDO, e ele é a letra da regra e não um descuido: a doutrina de motion
# proíbe `background-color` e `color`, e é isso que esta perna cobra. Um
# `transition: border-color` no `:root` passa — e animaria a troca de tema do
# mesmo jeito. Alargar a varredura seria alargar a REGRA, que não é o que um
# portão faz; o dia em que a linha do §4 disser `border-color` é o dia de
# acrescentar o termo aqui.
#
# `*` e `*, *::before` NÃO entram na lista: o reset global do bloco `reduce` é
# exatamente uma transição sobre tudo, e é ele que faz `prefers-reduced-motion`
# alcançar o upstream (§3). A regra é sobre a SUPERFÍCIE da página, não sobre
# quantos elementos um seletor alcança.
documento=$(find src -name '*.css' -exec awk -f scripts/css-sem-comentario.awk {} + \
  | awk '
      {
        corpo = $0
        onde = ""
        if (match(corpo, /^[^ \t]+\.css:[0-9]+:/)) {
          onde = substr(corpo, 1, RLENGTH)
          corpo = substr(corpo, RLENGTH + 1)
        }
      }
      corpo ~ /\{/ {
        seletor = corpo
        sub(/\{.*/, "", seletor)
        gsub(/^[ \t]+|[ \t]+$/, "", seletor)
      }
      corpo ~ /transition(-property)?[ \t]*:/ {
        if (seletor ~ /(^|,)[ \t]*(html|body|:root)[ \t]*(,|$)/ &&
            corpo ~ /(background-color|[^-a-z]color|transition[ \t]*:[ \t]*all)/) {
          print onde seletor " {" corpo "}"
        }
      }') || true

if [ -n "$documento" ]; then
  echo "Portão 2 REPROVOU — transição de cor sobre o documento:"
  echo
  echo "$documento"
  echo
  echo "A superfície não anima. Mova a transição para o controle —"
  echo "ver \`.claude/rules/css-tokens.md\`."
  exit 1
fi

echo "Portão 2 passou — toda transição compõe do vocabulário de motion,"
echo "e nenhuma transição de cor toca \`html\`, \`body\` ou \`:root\`."
