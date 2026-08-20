#!/bin/sh
# O gatilho da varredura de documentação. Ele NÃO varre: ele lança quem varre, e
# volta.
#
# A documentação deste projeto saiu daqui na #151 e vive em `panlabs-docs`. O
# que saiu junto foi o acoplamento: antes, mudar comportamento e mudar a página
# que o descreve era o mesmo PR. Este script repõe o acoplamento de fora, sem
# devolver a documentação para cá.
#
# ESTE SCRIPT NÃO É PORTÃO, E ISSO É REQUISITO. Ele não bloqueia commit, não
# bloqueia push, não bloqueia merge, e não entra em `needs` de job nenhum. Sai 0
# em todo caminho, inclusive nos de erro. Quem cobra é o portão do OUTRO
# repositório, sobre a `main` do outro repositório, e o `lefthook.yml` deste
# registra por que essa divisão é o desenho e não um afrouxamento.
#
# MARKER-GATED, na forma do `~/.claude/hooks/context-economy-injector.py`: sem
# o irmão no disco, sem a skill dentro dele, ou sem o `claude` no `PATH`, ele
# sai calado. Uma máquina que só tem este repositório não sente diferença, e o
# arquivo pode ser versionado sem impor nada a ninguém.
#
# A CONDIÇÃO DE DISPARO É O PINO, NÃO A VERSÃO. Este script não sabe comparar
# release, e não deve: ele pergunta ao `npm run pino -- --verificar` do outro
# repositório se há dívida. Isso o torna idempotente (pull que não traz nada
# não lança nada) e faz a varredura coalescer sozinha, porque o pino é cursor:
# três releases acumuladas viram uma varredura só.
#
# Códigos que o pino devolve, e eles são três de propósito:
#   0  em dia          nada a fazer
#   1  atrasado        lança
#   2  não deu para perguntar (rede)   NÃO lança; tenta no próximo pull

set -eu

IRMAO="${OVERPOWER_DOCS_REPO:-$(CDPATH= cd -- "$(dirname -- "$0")/../../panlabs-docs" 2>/dev/null && pwd || true)}"
[ -n "${IRMAO:-}" ] || exit 0
[ -d "$IRMAO/.git" ] || exit 0

SKILL="$IRMAO/.claude/skills/varredura-overpower/SKILL.md"
[ -f "$SKILL" ] || exit 0

command -v claude >/dev/null 2>&1 || exit 0
command -v npm    >/dev/null 2>&1 || exit 0

# O `post-merge` dispara em qualquer `git pull`, inclusive numa branch de
# trabalho. Só a `main` carrega release publicada.
[ "$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '')" = "main" ] || exit 0

# Uma varredura por vez. O outro repositório não aceita dois PRs abertos ao
# mesmo tempo: o portão 4 dele crava contagem de página, e dois PRs somando uma
# página cada passam sozinhos e quebram juntos depois do merge.
#
# `mkdir` é o lock atômico do POSIX; `-p` não serve, porque ele sucede quando o
# diretório já existe, que é exatamente o caso que precisa falhar.
LOCK="${XDG_STATE_HOME:-$HOME/.local/state}/overpower/varredura.lock"
mkdir -p "$(dirname "$LOCK")"
if ! mkdir "$LOCK" 2>/dev/null; then
  # Lock de sessão que morreu não pode travar o gatilho para sempre. Meia hora é
  # folgado para uma varredura e curto para uma pane.
  if [ -n "$(find "$LOCK" -maxdepth 0 -mmin +30 2>/dev/null)" ]; then
    rmdir "$LOCK" 2>/dev/null || true
    mkdir "$LOCK" 2>/dev/null || exit 0
  else
    exit 0
  fi
fi

# A PARTIR DAQUI TUDO É DESTACADO, E A ORDEM IMPORTA.
#
# A pergunta ao pino é uma chamada HTTP: até três tentativas de dez segundos,
# medidas em 1,05 s com o PyPI respondendo bem. Fazê-la aqui, antes de
# destacar, poria trinta segundos de rede dentro do `git pull` no pior caso.
# A regra deste repositório é que nada aqui trava, então quem pergunta é o
# processo de fora, não o hook.
#
# O que o hook faz de síncrono são só os guardas acima, todos locais: medidos em
# 0,00 s fora da `main` e sem o irmão.
#
# `--dangerously-skip-permissions` não é descuido: este processo é destacado e
# não tem terminal, então um pedido de permissão não teria a quem perguntar e
# ficaria pendurado para sempre. O que limita o estrago não é a permissão do
# agente, é o ruleset da `main` do outro repositório: `bypass_actors` vazio e o
# check `gate` obrigatório. Nada entra lá sem PR verde, inclusive vindo daqui.
#
# `setsid` solta o processo do grupo do `git`, para que fechar o terminal onde o
# `git pull` rodou não o mate junto. Sem `setsid` na máquina, `nohup` resolve o
# essencial.
LOG="${XDG_STATE_HOME:-$HOME/.local/state}/overpower/varredura.log"

LANCADOR="nohup"
command -v setsid >/dev/null 2>&1 && LANCADOR="setsid"

$LANCADOR sh -c '
  IRMAO="$1"; LOG="$2"; LOCK="$3"
  # O lock é solto em todo caminho de saída, inclusive nos de erro. Um lock
  # vazado calaria o gatilho por trinta minutos sem ninguém saber por quê.
  trap "rmdir \"$LOCK\" 2>/dev/null || true" EXIT INT TERM

  cd "$IRMAO" || exit 0

  PINO=0
  npm run --silent pino -- --verificar >/dev/null 2>&1 || PINO=$?

  # 0 em dia, 1 atrasado, 2 não deu para perguntar. Só o 1 manda varrer.
  [ "$PINO" -eq 1 ] || exit 0

  printf "\n=== %s — pino atrasado, varrendo ===\n" "$(date -Iseconds)" >> "$LOG"
  claude -p "varre a documentação do overpower" \
         --dangerously-skip-permissions >> "$LOG" 2>&1
  printf "=== %s — varredura terminou (código %s) ===\n" "$(date -Iseconds)" "$?" >> "$LOG"
' _ "$IRMAO" "$LOG" "$LOCK" >/dev/null 2>&1 &

exit 0
