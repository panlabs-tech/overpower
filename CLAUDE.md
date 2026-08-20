# overpower

CLI Python, publicada no PyPI, que instala equipamento de agente curado num repositório ou na máquina — `list` diz o que há, `install` escreve, `doctor` diz se o que foi escrito continua sendo o que foi escrito.

## O reconhecimento sai da janela

A implementação começa **delegando o reconhecimento a um subagente `Explore`** e agindo sobre o **digest** que ele devolve. O digest é o orçamento de leitura: o que ele nomeia se lê em fatia estreita, o resto fica de fora. O schema e a ordem estão em `.claude/context-economy-protocol.md`.

Medido em 46 sessões deste repo: explorar dentro da própria janela leva o primeiro `Edit` a **152k tokens** — 50k de `Read` e `Bash` crus, 61k do raciocínio nos 63 turnos que os orquestram. Um digest custa **~4k** e substitui os dois.

## Onde perguntar antes de procurar

Estes documentos não se deduzem olhando a árvore. Leia a **seção**, não o arquivo — `domain.md` tem 26k e `testing.md` 23k.

| Pergunta | Onde |
| --- | --- |
| O que um termo significa aqui — artefato, AI Framework, bundle, receita, slot, grupo universal, procedência | `docs/agents/domain.md` § Vocabulário |
| O que o modelo permite, o que proíbe, o que admite no catálogo | `docs/agents/domain.md` § Regras do modelo, § Axiomas, § Critério de curadoria |
| Onde o conteúdo mora, e por que são duas raízes irmãs com invariantes opostas | `docs/agents/domain.md` § Onde o conteúdo mora |
| Como falar com o issue tracker, e as operações de wayfinding | `docs/agents/issue-tracker.md` |
| Como o trabalho anda, o que trava um merge, como se publica | `docs/agents/workflow.md` |
| O que é real, o que é dublê, o que vira snapshot | `docs/agents/testing.md` § Resumo executável |
| Por que uma decisão é o que é | `docs/adr/` |

**No código, o índice é o docstring.** Todo módulo de `src/overpower/` abre com uma linha que declara sua responsabilidade — `head` nelas localiza mais barato que `grep`.

## O código é em inglês

**Todo artefato de código aqui é inglês** — identificador, comentário, docstring, mensagem de log, nome de módulo e nome de arquivo. Idioma misto produz identificador híbrido (`parse_lancamento`), e aí a fronteira entre os dois idiomas deixa de morar numa camada e passa a morar em cada assinatura. É a regra 43 do padrão panlabs, e a medição que a dispensa de trava está em `src/overpower/content/pool/skills/panlabs-python-standards/references/06-regua-de-maquina.md` § 7 — **sem mecanismo: confere-se em review.**

Escapam duas coisas, e nenhuma delas é código deste repositório: **interface alheia, grafada como o dono a grafa** — `npm run pino -- --verificar` é script do `panlabs-docs` — e **copy dirigida a quem lê em outra língua** — o prompt que `scripts/overpower-docs-update.sh` manda para a skill em português do irmão. Cada uma carrega no lugar o comentário que diz por quê.

**Prosa não é código.** Mensagem de commit, ticket, ADR, este arquivo e `docs/agents/` são português — o `commitlint.config.mjs` já dizia isso, e é lá que a metade lintável da convenção mora. Os nomes dos arquivos de `docs/adr/` são a dívida conhecida da regra.

## Pegadinhas

- **Nada entra na `main` sem PR.** É ruleset, com a lista de bypass vazia inclusive para o dono; `gate` e `release-ready` são required checks.
- **Publicar é mergear.** Um merge que muda a versão do `pyproject.toml` cria a tag e dispara o release; um que não muda não publica nada.
- **`gh pr merge --delete-branch` falha aqui.** Ele troca o checkout para a `main`, que costuma estar ocupada por um worktree. Mergeie sem a flag e apague a branch remota por `gh api -X DELETE`.

## Agent skills

### Issue tracker

Issues no GitHub, repo `ThiagoPanini/overpower`. Ver `docs/agents/issue-tracker.md`.

### Domain docs

Single-context — o domínio mora em `docs/`. Ver `docs/agents/domain.md`.
