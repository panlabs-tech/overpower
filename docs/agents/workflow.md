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

> **Estado em 2026-08-07: o ruleset está ativo** (`main: PR obrigatorio e gate verde`), e a ordem obrigatória do [#24](https://github.com/panlabs-tech/overpower/issues/24) foi cumprida na sequência que ela exige — *público → `ci.yml` e teste, com a run acontecendo uma vez → só então o ruleset*. Esta seção deixou de descrever o alvo e passou a descrever o repo.
>
> **A trava foi observada, não inferida:** um `git push origin main` do próprio dono, com o ruleset ligado, é recusado com `Required status check "gate" is expected` e `push declined due to repository rule violations`. A lista de bypass está vazia de verdade.

**Nada entra na `main` sem PR.** Não é convenção: é ruleset, exigindo PR e status checks, com **zero aprovações** — o GitHub não deixa o autor aprovar o próprio PR, e exigir uma travaria um repo de um mantenedor só — e com a **lista de bypass vazia, inclusive para o dono**. Em modo autônomo o agente empurra com a credencial do dev, então bypass com o nome dele é bypass para o agente, e a regra viraria decoração.

Isso é o que deixa o `release.yml` continuar sem rodar lint nem teste antes de publicar: toda tag sai de um commit que passou pelo portão, por mecanismo e não por disciplina.

**Publicar é mergear.** Um merge na `main` que mude a versão do `pyproject.toml` cria a tag e dispara o `release.yml`; um merge que não mude não publica nada. O disparo é `gh workflow run release.yml --ref v$X`, e não o push da tag — **tag criada com `GITHUB_TOKEN` não dispara workflow nenhum**, e `workflow_dispatch` é a exceção documentada. Decidido em [Portões do repositório](https://github.com/panlabs-tech/overpower/issues/24).

**E mover a versão não é disciplina, é portão.** O `release-ready` — segundo required check, ao lado do `gate` — reprova o PR que muda o wheel sem bumpar, e **imprime na falha o nível calculado e os dois comandos**. Nenhum workflow escreve na branch: push com `GITHUB_TOKEN` não dispara CI, então um bot deixaria o SHA novo sem check e o PR travaria para sempre. Decidido em [Publicação automática](https://github.com/panlabs-tech/overpower/issues/62) e registrado na [ADR 0012](../adr/0012-o-bump-e-ato-do-autor-e-o-portao-o-ensina.md).

> **Isto substitui um estado que durou três merges.** Depois da `v0.1.0`, os PRs [#59](https://github.com/panlabs-tech/overpower/issues/59), [#60](https://github.com/panlabs-tech/overpower/issues/60) e [#61](https://github.com/panlabs-tech/overpower/issues/61) entraram sem bumpar; o `tag.yml` viu a tag existente, escreveu `::notice::` e **saiu verde** nas três. Nada publicado, nenhum erro em lugar nenhum. O `tag.yml` agora tem três ramos, e o terceiro — tag existente apontando para outro commit — é `::error::` com `exit 1`.

## Modo de implementação autônoma

Disparado por "implementa as issues" ou equivalente:

1. Colete as issues `ready-for-agent` abertas, sem bloqueio pendente.
2. Um **git worktree por issue**, aninhado no próprio repo.
3. `/tdd`: RED → GREEN → refactor.
4. Commit (Conventional Commits, subject minúsculo — o `commit-msg` cobra) e push.
5. **Abra o PR como `--draft` já no primeiro push.** Vários pushes não criam vários PRs: `gh pr create` não é idempotente, então a guarda é `gh pr list --head "$BRANCH" --state open`.
6. Ao terminar, escreva o corpo do PR e rode `gh pr ready`. O corpo é escrito **no fim, por quem tem o ticket na mão** — não no começo, por quem só tem o diff.
7. **Feche o release junto com o trabalho**, se o PR muda o wheel. Não decore o nível: o `release-ready` vermelho já o calculou e imprimiu os dois comandos — `uv version --bump <nível>` e `uv run towncrier build --version "$(uv version --short)"`. Bumpar antes de ver o vermelho é permitido, e errar para cima também; errar para baixo reprova.
8. **Mergeie no verde** e encadeie até as issues acabarem. Com ruleset, `gh pr merge --auto` é nativo: o auto-merge do GitHub só é oferecido em PR bloqueado por required check.

## Portões

Decididos em [Portões do repositório: CI de PR, hooks locais e a política de branch](https://github.com/panlabs-tech/overpower/issues/24) — o detalhe e as medições moram lá; aqui fica o que um agente precisa para trabalhar.

**Local, por `lefthook`.** `ruff check`, `ruff format --check` e **P1** sobre `{staged_files}` via `uv run` — a versão vem do `uv.lock`, a mesma que a CI usa, e é isso que impede um segundo caminho local —, mais `gitleaks` sobre o staged e `commitlint` no `commit-msg`. Arma-se com `lefthook install` **uma vez por clone**, e os worktrees herdam, porque compartilham o `.git/hooks` do repo principal.

O hook local **não é o portão, é o atalho**: ele pega barato o erro barato. `--no-verify` não abre buraco nenhum, porque quem barra é o ruleset, e ruleset não tem `--no-verify`.

**Na CI, no PR.** Três jobs, e o critério de repartição é que só o `pytest` varia com SO e versão:

| job | conteúdo |
|---|---|
| `static` | `ruff check` · `ruff format --check` · `pyright` · **P1** · **P2** — ubuntu, um Python |
| `test` | `pytest`, matriz de 3 SOs × 3 versões de Python |
| `gate` | `needs: [static, test]` com `if: always()` e asserção dos dois resultados |
| `release-ready` | versão movida, `CHANGELOG.md` fechado, `changelog.d/` vazio e nível ≥ o que os fragmentos pedem — só quando o PR muda o wheel |

**São dois os nomes exigidos pelo ruleset**, `gate` e `release-ready`, e eles não se fundem de propósito: `gate` quer dizer *"o código está são"*, `release-ready` quer dizer *"mergear isto publica"*. As duas falhas têm remédios diferentes, e um nome por remédio é o que faz um agente acertar na primeira leitura. O `release-ready` **não** entra no `needs` do `gate`: são checks irmãos, não etapas.

> **Ordem obrigatória ao mexer nisso**, e é a mesma lição do [#24](https://github.com/panlabs-tech/overpower/issues/24): um required check tem de **existir e ter reportado** antes de entrar no ruleset. Nome no ruleset sem job que o publique trava todo PR em *"Expected — waiting for status to be reported"*, para sempre.

Todos bloqueantes: portão que não bloqueia é documentação. O `gate` existe por mecânica e não por elegância — required check some **por nome**, e nome de célula de matriz carrega os valores dela, então sem ele mudar a matriz travaria todo PR em *"Expected — waiting for status to be reported"*.

**O `gate` não pode ser o job vazio que o [#24](https://github.com/panlabs-tech/overpower/issues/24) desenhou**, e isso apareceu ao implementá-lo. Job que é pulado porque a dependência falhou reporta como **skipped**, e o GitHub trata required check skipped como sucesso: o job ficaria verde exatamente quando tivesse algo a dizer. Daí o `if: always()` mais a leitura explícita de `needs.<job>.result`. Observado nas duas rodadas do [#33](https://github.com/panlabs-tech/overpower/pull/33) — vermelho quando o Windows quebrou, verde depois.

Três armadilhas medidas, que quem mexer nos portões precisa conhecer: **P1 passa por vacuidade** se `src/overpower/content/` não existir (sai `exit=0` com saída vazia); **`pytest` sem nenhum teste sai 5**, o que sob ruleset é deadlock de merge e não feiura; e a do `gate` acima. As duas primeiras eram previstas, a terceira não.

> **Estado em 2026-08-07: a raiz de conteúdo existe** ([#45](https://github.com/panlabs-tech/overpower/issues/45)), e com ela a guarda do P1 inverteu de sentido. Enquanto não havia conteúdo, `test -d` transformava a vacuidade num aviso e num `exit 0`; agora que a árvore é rastreada, sujeito vazio é **regressão**, e os dois P1 — o da CI e o do `lefthook` — falham em vez de passar. O P2 também deixou de comparar dois conjuntos vazios: são **82 caminhos** dos dois lados.

**A matriz 3×3 pagou na primeira rodada.** `WindowsPath("/home/dev").is_absolute()` é `False` — falta letra de unidade —, e 79 dos 257 testes falhavam só nas três células Windows. O produto estava certo e os fixtures é que eram POSIX-only. É exatamente a classe que a [doutrina de teste](testing.md) previu que passaria verde numa célula só.

**O que deliberadamente não é portão.** O job `windows-latest` prova o caminho *com* privilégio e não cobre o caso sem ele, porque o runner liga Developer Mode ([#19](https://github.com/panlabs-tech/overpower/issues/19)); a frescura da tabela de runtimes é **ato de curadoria, não automação**; e — quarta ocorrência da mesma classe — **nenhum teste toca o GitHub de verdade em job nenhum**, nem no PR nem no release, decidido em [Doutrina de teste](https://github.com/panlabs-tech/overpower/issues/30). A regra que sai disso: **portão bloqueia o que este repo controla; o que depende de terceiro se verifica na curadoria.**

## Referência de padrão Python

O `panlabs-python-standards` é a régua de forma de código consultada aqui. Onde ele e uma decisão do mapa divergirem, vence o mapa — e a divergência vira ADR em `docs/adr/`.

**O eixo de testes já foi adjudicado inteiro**, posição por posição, em [`testing.md`](testing.md): o que é dublê, o que roda de verdade, como a saída visual é asseverada e onde cada arquivo de teste mora. Resultado da adjudicação: **zero divergências** — onde a resposta daqui parece contrariar a régua, é a condição declarada da própria régua que a redireciona. A única posição que precisou de ADR foi a que um leitor da régua tentaria desfazer: [ADR 0010](../adr/0010-nao-existe-duble-de-sistema-de-arquivos.md), não existe dublê de sistema de arquivos.
