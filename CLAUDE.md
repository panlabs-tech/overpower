# overpower

CLI Python, publicada no PyPI, que instala equipamento de agente curado num
repositório ou na máquina. Invocação canônica: `uvx overpower@latest <comando>`.
Três comandos — `list` diz o que há, `install` escreve, `doctor` diz se o que foi
escrito continua sendo o que foi escrito.

Código em `src/overpower/`, suíte em `tests/`. Duas raízes irmãs de conteúdo com
invariantes opostas: `src/overpower/content/` **100% aterrissa**,
`src/overpower/catalog/` **0% aterrissa**.

## O reconhecimento sai da janela

A implementação começa **delegando o reconhecimento a um subagente `Explore`** e
agindo sobre o **digest** que ele devolve. O digest é o orçamento de leitura: o
que ele nomeia se lê em fatia estreita, o resto fica de fora.
`.claude/context-economy-protocol.md` carrega o schema e a ordem.

Medido neste repo, 45 sessões: explorar dentro da própria janela leva o primeiro
`Edit` a **152k tokens** — 50k de resultado cru de `Read`+`Bash` e 61k do
raciocínio ao redor deles. Um digest de subagente custa **~4k** e substitui os
dois.

## Onde perguntar antes de procurar

Cada resposta mora num lugar só. Leia a **seção**, não o arquivo — `domain.md`
tem 26k e `testing.md` 23k.

| Pergunta | Onde |
| --- | --- |
| O que um termo significa aqui — artefato, AI Framework, bundle, receita, slot, grupo universal, procedência | `docs/agents/domain.md` § Vocabulário |
| O que o modelo permite e proíbe | `docs/agents/domain.md` § Regras do modelo, § Axiomas |
| O que entra no catálogo | `docs/agents/domain.md` § Critério de curadoria |
| Como o trabalho anda, do problema à execução | `docs/agents/workflow.md` § Do problema à execução |
| O que trava um merge, e como se publica | `docs/agents/workflow.md` § Política de branch, § Portões |
| Como rodar o modo autônomo | `docs/agents/workflow.md` § Modo de implementação autônoma |
| O que é real, o que é dublê, o que vira snapshot | `docs/agents/testing.md` § Resumo executável, depois a posição citada |
| Como falar com o tracker, e as operações de wayfinding | `docs/agents/issue-tracker.md` |
| Por que uma decisão é o que é | `docs/adr/` |

## O que já é portão

**Nada entra na `main` sem PR** — é ruleset, com a lista de bypass vazia
inclusive para o dono, e `gate` e `release-ready` são required checks. **Publicar
é mergear**: um merge que muda a versão do `pyproject.toml` dispara o release.
Localmente, `lefthook` cobra ruff, gitleaks, commitlint e P1 no commit. O detalhe
mora em `docs/agents/workflow.md` § Portões.

## Agent skills

### Issue tracker

Issues no GitHub, repo `panlabs-tech/overpower`. Ver `docs/agents/issue-tracker.md`.

### Domain docs

Single-context — o domínio mora em `docs/`. Ver `docs/agents/domain.md`.
