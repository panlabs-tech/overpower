# Handoff — o site de documentação do overpower

Este arquivo é o ponto de partida de uma sessão nova. Ele não é a spec: a spec inteira — as 12 decisões travadas, a árvore de 19 páginas com a fonte de fato de cada uma, e o inventário do que atravessa do gabarito — mora em [Spec: o site de documentacao do overpower](https://github.com/panlabs-tech/overpower/issues/129). **Leia a issue antes de tocar em qualquer arquivo.**

## O que foi decidido, em uma frase

Transplantar o tema de [`panlabs-tech/shinydoc-docusaurus`](https://github.com/panlabs-tech/shinydoc-docusaurus) para `website/` neste repositório, escrever documentação nova **em inglês** para as duas audiências que já existem — quem usa a CLI e quem contribui com ela — e publicar em `https://panlabs-tech.github.io/overpower/`.

O gabarito autoriza o transplante por escrito: o `README.md` dele declara que *o conteúdo é ficção descartável; o produto é a estrutura + a customização visual*.

## Os três tickets, em ordem

| Ticket | O que entrega | Bloqueado por |
| --- | --- | --- |
| [#130 — o site no ar, vazio](https://github.com/panlabs-tech/overpower/issues/130) | `website/` inteiro, deploy no Pages, portões, e as 19 páginas navegáveis com título, `description` e um parágrafo | nada — é a fronteira |
| [#131 — a sidebar `Guide` escrita](https://github.com/panlabs-tech/overpower/issues/131) | as 13 páginas de usuário | #130 |
| [#132 — a sidebar `Contributing` escrita e o README encolhe](https://github.com/panlabs-tech/overpower/issues/132) | as 6 páginas de contribuidor, o novo README, `[project.urls]` | #131 |

**#130 cabe numa sessão com folga.** #131 e #132 somam ~1.700 linhas de prosa em inglês, e prosa não paraleliza dentro de uma janela — são a sessão seguinte.

## As três coisas que mordem

1. **O Docusaurus mora em `website/`, nunca na raiz.** O gabarito põe React em `src/`; o `src/` daqui é o pacote Python, e o portão **P2** assere que o wheel carrega exatamente o que o git rastreia sob `src/`. Um arquivo versionado sob `src/` e ausente do wheel reprova o portão.

2. **`release-ready` só pode disparar no #132.** O gatilho é a tupla `WHEEL = ("src/", "README.md", "NOTICE", "LICENSE", "licenses/")` mais a tabela `[project]` do `pyproject.toml`. Editar o `README.md` ou acrescentar `Homepage`/`Documentation` a `[project.urls]` obriga bump de versão, fragment em `changelog.d/` e publicação no PyPI. Os tickets #130 e #131 foram desenhados para não encostar em nenhum dos dois.

3. **`description` no front matter é obrigatória.** O `MDXComponents` do gabarito a injeta como subtítulo abaixo do `<h1>` e **quebra o build** se ela faltar. O front matter é exatamente dois campos, `title` e `description`, e toda página escreve o próprio `# Título`.

## Armadilhas deste repo, medidas

- `gh pr merge --delete-branch` **falha aqui**: troca o checkout para a `main`, que costuma estar ocupada por um worktree. Mergeie sem a flag e apague a branch remota por `gh api -X DELETE`.
- **"Fecha #N" não fecha issue** — a keyword de auto-close do GitHub só existe em inglês. Feche à mão depois de cada merge.
- `uv version --short` **sai colorido**, e o ANSI entra no título do CHANGELOG fazendo o `release-ready` jurar que o towncrier não rodou.
- **Heredoc composto morre dentro de worktree.** Read+Edit resolve; script só dentro do worktree, em caminho ignorado.
- `.gitignore` **não tem `node_modules/`** hoje, e já ignora `/site` na linha 169 — mais um motivo para o diretório se chamar `website/`.
