# Prototype — overpower terminal experience

Throwaway. Built to resolve
[Prototipo da experiencia de terminal](https://github.com/panlabs-tech/overpower/issues/12).
**Not production code**, and it does not get promoted — the decision it settled gets
rebuilt properly under the repo's own gates.

It exists as a primary source: the three variants are the evidence for why one of them
won, and a later reader who disagrees can run them instead of arguing from prose.

## Run it

One command, no setup — PEP 723 inline metadata, so `uv` resolves the stack itself.

```bash
uv run op.py all                 # every screen, variant C, English — the decision
uv run op.py -V a all            # variant A, Painel
uv run op.py -V b all            # variant B, Linha
uv run op.py --lang pt all       # the pt-BR copy that lost
uv run op.py install             # the wizard, needs a TTY
```

Degradation checks the ticket asked for:

```bash
uv run op.py all | cat           # under a pipe
NO_COLOR=1 uv run op.py all
COLUMNS=60 uv run op.py all
python3 drive.py c               # drives the wizard through a real PTY
```

## The three variants

| | bet | catalog | whole run | @60 columns |
| --- | --- | --- | --- | --- |
| **A** Painel | frames everywhere, rich maximalist | 42 lines | 12.1 KB | description squeezes to ~18 chars, 5 lines per item |
| **B** Linha | no boxes, one line per thing, cargo-shaped errors | 12 lines | 2.8 KB | truncates description, keeps tag + name + size |
| **C** Documento | rules and indentation as structure | 45 lines | 5.8 KB | **rewraps, loses nothing** |

C won. The reasoning is in the resolution comment on the issue.

## What the data is

- Framework numbers are **measured**: 22 skills / 68 files / 196,849 bytes, from
  [#15](https://github.com/panlabs-tech/overpower/issues/15).
- Pool sizes are **measured** from `~/.agents/skills` on the dev's machine.
- Bundle composition is **illustrative** — no ticket has decided it yet.

## Captures

`captures/` holds the rendered output at 80 columns, at 60 columns, and under a pipe,
with ANSI stripped. They are what the decision was made against.
