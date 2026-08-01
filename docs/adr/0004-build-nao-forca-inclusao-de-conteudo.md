# O build não força inclusão de conteúdo

O `pyproject.toml` do overpower não tem `force-include`, não tem `artifacts`, não tem `ignore-vcs` e não tem `packages`. O conteúdo vendorizado entra no wheel pela travessia default do `hatchling`, sem uma linha de configuração de build.

O artefato desta decisão é uma **ausência**, e por isso ela precisa estar escrita: quem ler a [pesquisa de empacotamento](https://github.com/panlabs-tech/overpower/issues/3) — que recomenda `hatchling` justamente por ele ter `force-include` — e abrir o `pyproject.toml` vai achar que faltou alguém escrever a configuração.

## Considered Options

O problema real existe. O `.gitignore` do repo tem **88 padrões que casam em qualquer profundidade** — `build/`, `lib/`, `dist/`, `var/`, `env/`, `*.spec`, `*.log` — e o `hatchling` respeita esse arquivo. Medido: cinco arquivos de conteúdo dentro do pacote, dois deles em pastas chamadas `build/` e `lib/`; `git add -A`, `uv build`; **o build saiu 0 e o wheel foi publicado com 1 dos 5**, sem aviso do git, do build ou do wheel. É a mesma classe do `hatch-vcs` sob clone raso registrada no [#2](https://github.com/panlabs-tech/overpower/issues/2): sucesso com conteúdo errado.

Quatro saídas foram construídas e medidas.

**`.gitignore` aninhado com `!*` na raiz do conteúdo.** Recupera **5 de 5 no git** e **1 de 5 no wheel**. O `hatchling` lê *"the first `.gitignore` found in your project's root directory or parent directories"* — não lê o aninhado. É a pior das quatro: o `git status` fica limpo, os arquivos estão no repo, e o wheel sai errado sem sinal em lugar nenhum.

**`ignore-vcs = true`.** Recupera 5 de 5, e **vazou um `.env` e `node_modules/` para o sdist publicado**. O `hatchling` exclui `.venv/` e `.ruff_cache/` por default; `.env` não.

**`artifacts` nos dois alvos (sdist e wheel).** Recupera 5 de 5 e é a que parece certa — foi a recomendação inicial do agente na sabatina. Medido depois, **ela é a mais perigosa**:

| build | wheel |
| --- | --- |
| local, com o arquivo ignorado presente no disco | **2 de 2** |
| CI, a partir de `git clone` limpo | **1 de 2** |

O `artifacts` fura o filtro do `.gitignore` para o *build*, mas o arquivo continua invisível para o *git*. O `actions/checkout` traz só o que o git rastreia, então o arquivo não existe no CI. O resultado é divergência silenciosa entre o wheel que o dev testa e o wheel que é publicado — **o mecanismo mascara a falha exatamente onde se olha e não salva onde importa**.

**Nada, mais um portão no git.** Medido com o conteúdo real — 194 arquivos, clone limpo, `pyproject.toml` só com `[project]` e `hatchling`: **194 de 194 no wheel, 419.965 bytes**. A travessia default do target `wheel` é por diretório e não por extensão, então Markdown e JSON dentro de `src/overpower/` entram sozinhos.

Foi essa. A condição que a torna suficiente é o portão **P1**, que roda antes de qualquer build:

```
git ls-files --others --ignored --exclude-standard -- src/overpower/content/
```

Vazio, sempre. Um arquivo de conteúdo que o `.gitignore` engoliria aparece aí — offline, instantâneo, antes de existir wheel. Somado ao **P2**, que compara a lista sob `overpower/content/` no wheel construído com `git ls-files src/overpower/content`, os dois modos de falha silenciosos ficam cobertos: P1 pega arquivo no disco invisível para o git, que o P2 não pega porque some dos dois lados da comparação; P2 pega arquivo no git ausente do wheel.

## Consequences

**A escolha de backend segue `hatchling`, por um motivo novo.** O motivo do #3 — só ele tem `force-include` para conteúdo fora da árvore do pacote — deixou de valer quando todo o conteúdo passou a morar em `src/overpower/`. Medido, o `uv_build` também entrega 194 de 194 e também suporta PEP 639, e é o default do `uv init` desde a 0.12.0. Ele perde porque **ignora o `.gitignore`**: recria a mesma divergência do `artifacts`, passando no build local e quebrando no de CI. O `hatchling` erra junto com o CI, e por isso a falha é visível antes de publicar. Custa também 5,8% de tamanho — 444.469 contra 419.965 bytes, por gravar 119 entradas de diretório.

**Configuração de build vira sinal.** Qualquer `force-include`, `artifacts` ou `ignore-vcs` que apareça no `pyproject.toml` deste projeto é regressão até prova em contrário, e a prova tem de vir com o build de CI a partir de clone limpo, não com o build local.

**Se um dia conteúdo precisar vir de fora de `src/overpower/`** — gerado no build, submodule, diretório irmão — o `force-include` volta, e volta com a medição local×CI refeita. É a escotilha que o `uv_build` não teria.
