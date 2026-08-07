# Fluxo de desenvolvimento

## Do problema à execução

```
/wayfinder  →  /to-spec  →  /to-tickets  →  /tdd  →  worktree  →  PR  →  merge no verde
```

Uma decisão grande demais para uma sessão vira **mapa** de wayfinding, resolvido um ticket de decisão por vez. Um mapa fechado vira **spec**. Uma spec vira **tickets** com arestas de bloqueio declaradas.

## O mapa da v0.1.0 carrega execução

O mapa que originou este repo declara, nas suas Notes, um **override do padrão do wayfinder**: ele não só decide, ele constrói. O destino dele é a **v0.1.0 publicada no PyPI**, validada por `uvx overpower@latest` a partir do PyPI público.

O caminho do índice Artifactory corporativo **saiu do critério de fechamento** em [Reservar o nome no PyPI e provar o pipeline ponta a ponta](https://github.com/panlabs-tech/overpower/issues/13): a metade técnica já estava provada no [#3](https://github.com/panlabs-tech/overpower/issues/3), e a metade que sobrou — Curation, allow-list por licença, WAF — é decisão de admin corporativo e nunca foi engenharia nossa.

Isso vale **para este mapa**. Mapas futuros voltam ao padrão: decidem, não executam.

## Política de branch

**Nada entra na `main` sem PR.** Não é convenção: é ruleset, exigindo PR e status checks, com **zero aprovações** — o GitHub não deixa o autor aprovar o próprio PR, e exigir uma travaria um repo de um mantenedor só — e com a **lista de bypass vazia, inclusive para o dono**. Em modo autônomo o agente empurra com a credencial do dev, então bypass com o nome dele é bypass para o agente, e a regra viraria decoração.

Isso é o que deixa o `release.yml` continuar sem rodar lint nem teste antes de publicar: toda tag sai de um commit que passou pelo portão, por mecanismo e não por disciplina.

**Publicar é mergear.** Um merge na `main` que mude a versão do `pyproject.toml` cria a tag e dispara o `release.yml`; um merge que não mude não publica nada. O disparo é `gh workflow run release.yml --ref v$X`, e não o push da tag — **tag criada com `GITHUB_TOKEN` não dispara workflow nenhum**, e `workflow_dispatch` é a exceção documentada. Decidido em [Portões do repositório](https://github.com/panlabs-tech/overpower/issues/24).

## Modo de implementação autônoma

Disparado por "implementa as issues" ou equivalente:

1. Colete as issues `ready-for-agent` abertas, sem bloqueio pendente.
2. Um **git worktree por issue**, aninhado no próprio repo.
3. `/tdd`: RED → GREEN → refactor.
4. Commit (Conventional Commits, subject minúsculo — o `commit-msg` cobra) e push.
5. **Abra o PR como `--draft` já no primeiro push.** Vários pushes não criam vários PRs: `gh pr create` não é idempotente, então a guarda é `gh pr list --head "$BRANCH" --state open`.
6. Ao terminar, escreva o corpo do PR e rode `gh pr ready`. O corpo é escrito **no fim, por quem tem o ticket na mão** — não no começo, por quem só tem o diff.
7. **Mergeie no verde** e encadeie até as issues acabarem. Com ruleset, `gh pr merge --auto` é nativo: o auto-merge do GitHub só é oferecido em PR bloqueado por required check.

## Portões

Decididos em [Portões do repositório: CI de PR, hooks locais e a política de branch](https://github.com/panlabs-tech/overpower/issues/24) — o detalhe e as medições moram lá; aqui fica o que um agente precisa para trabalhar.

**Local, por `lefthook`.** `ruff check`, `ruff format --check` e **P1** sobre `{staged_files}` via `uv run` — a versão vem do `uv.lock`, a mesma que a CI usa, e é isso que impede um segundo caminho local —, mais `gitleaks` sobre o staged e `commitlint` no `commit-msg`. Arma-se com `lefthook install` **uma vez por clone**, e os worktrees herdam, porque compartilham o `.git/hooks` do repo principal.

O hook local **não é o portão, é o atalho**: ele pega barato o erro barato. `--no-verify` não abre buraco nenhum, porque quem barra é o ruleset, e ruleset não tem `--no-verify`.

**Na CI, no PR.** Três jobs, e o critério de repartição é que só o `pytest` varia com SO e versão:

| job | conteúdo |
|---|---|
| `static` | `ruff check` · `ruff format --check` · `pyright` · **P1** · **P2** — ubuntu, um Python |
| `test` | `pytest`, matriz de 3 SOs × 3 versões de Python |
| `gate` | job vazio, `needs: [static, test]` — **é este o nome exigido pelo ruleset** |

Todos bloqueantes: portão que não bloqueia é documentação. O `gate` existe por mecânica e não por elegância — required check some **por nome**, e nome de célula de matriz carrega os valores dela, então sem ele mudar a matriz travaria todo PR em *"Expected — waiting for status to be reported"*.

Duas armadilhas medidas, que quem mexer nos portões precisa conhecer: **P1 passa por vacuidade** se `src/overpower/content/` não existir (sai `exit=0` com saída vazia), então ele vem guardado por `test -d`; e **`pytest` sem nenhum teste sai 5**, o que sob ruleset é deadlock de merge e não feiura.

**O que deliberadamente não é portão.** O job `windows-latest` prova o caminho *com* privilégio e não cobre o caso sem ele, porque o runner liga Developer Mode ([#19](https://github.com/panlabs-tech/overpower/issues/19)); e a frescura da tabela de runtimes é **ato de curadoria, não automação**. A regra que sai da terceira ocorrência da mesma classe: **portão bloqueia o que este repo controla; o que depende de terceiro se verifica na curadoria.**

## Referência de padrão Python

O `panlabs-python-standards` é a régua de forma de código consultada aqui. Onde ele e uma decisão do mapa divergirem, vence o mapa — e a divergência vira ADR em `docs/adr/`.
