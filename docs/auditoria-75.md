# Auditoria pós-entrega da spec #75 — o enxerto de MCP

Auditoria de conformidade da issue **#75** (*"Spec: o enxerto de MCP — `install --mcp`, a receita
federada e a segunda operação de escrita"*), construída por 16 tickets fechados e mergeados:
`#76 #77 #78 #79 #80 #81 #82 #83 #84 #85 #86 #87 #97 #98 #99 #100`.

Nenhum arquivo de `src/` ou `tests/` foi editado durante a auditoria.

> **Estado, 2026-08-17: os 13 achados estão fechados.** Este documento é o relatório da auditoria
> como ela foi feita, contra a base nomeada na § 0 — não é uma lista de pendências. Os consertos
> saíram em cinco PRs, e o raciocínio de cada um mora no corpo do PR, não aqui:
> [#114](https://github.com/ThiagoPanini/overpower/pull/114) (`S0-1`, `S1-1`, `S1-2`),
> [#118](https://github.com/ThiagoPanini/overpower/pull/118) (`S1-3`, `S1-5`, `S9-2`, `S10-1`),
> [#121](https://github.com/ThiagoPanini/overpower/pull/121) (`S4-3`, `C2-1`),
> [#124](https://github.com/ThiagoPanini/overpower/pull/124) (`S1-4`, `C3-01`) e
> [#127](https://github.com/ThiagoPanini/overpower/pull/127) (`S4-1`, `S4-2`).
> Onde a medição do conserto discordou da auditoria, quem vale é o PR — o desempate do `S4-3` não
> desempatava, o `S9-2` tinha três trechos e não dois, e o conserto proposto para o `S4-2` não
> alcançava o dado.
>
> **Estado, 2026-08-19: três das nove dúvidas da § 7 fecharam, ao encerrar a spec.** As **6** e
> **9** viraram conserto — a contagem do `doctor` passou a somar as duas classes de aterrissagem,
> e o documento sem JSON nenhum é recusado nas palavras deste produto em vez das do parser. A **7**
> virou emenda no corpo da própria #75, com ponteiro para o
> [#100](https://github.com/ThiagoPanini/overpower/issues/100). Nenhuma virou ticket: foram
> aplicadas direto, por decisão do dono, no PR que fechou as três specs abertas. As outras seis
> continuam abertas, e a **2** deixou de estar travada — ver a nota ao pé da § 7.

---

## 0. A base auditada, e uma correção de método

A auditoria foi lançada no worktree `issue-87-devin-measure`, em `37850c5` (v0.19.1). **Esse worktree
está 4 commits atrás da `main`.** Como os 16 tickets foram *mergeados*, o artefato entregue é a
`main`, e é ela que vale:

```
$ git log --oneline HEAD..origin/main
4fb2250 Merge pull request #110 from panlabs-tech/worktree-issue-86-doctor-knows-mcp
4f32cd4 Merge remote-tracking branch 'origin/main' into worktree-issue-86-doctor-knows-mcp
76981d8 feat: o doctor conhece enxerto, o inerte e o clone que sumiu (#86)
11c0c35 Merge pull request #109 from panlabs-tech/worktree-issue-87-devin-measure

$ git diff --stat HEAD origin/main
 src/overpower/inspection.py | 399 +++++++++++++++++++++++++++++++-
 src/overpower/screens.py    |  41 ++++-
 tests/test_inspection.py    | 142 +++++++++++-
 tests/test_screens.py       |   9 +-
 CHANGELOG.md · pyproject.toml · uv.lock
```

O impacto é cirúrgico: **o ticket #86 — as quatro checagens do `doctor` — não existe no worktree
velho.** Tudo o mais (`recipes.py`, `rendering.py`, `grafting.py`, `planning.py`, `writing.py`,
`runtimes.py`, `remote.py`, `wizard.py`, `cli.py`) é byte-idêntico nas duas bases.

**Consequência para quem ler outra auditoria deste mesmo escopo:** um auditor que rode contra o
worktree velho reportará as histórias 60–64 como `AUSENTE`. É fantasma de base velha, não achado.
Toda a seção de `doctor` deste relatório foi refeita contra um worktree em `origin/main` (`4fb2250`),
criado em `/home/paninit/.claude/jobs/114165b6/tmp/main-audit`.

---

## 1. Veredito

> **A spec #75 está entregue.** Das 68 histórias: **57 `PROVADO`**, **7 `PARCIAL`**, **1 `SEM-PROVA`**,
> **2 `AUSENTE`** e **1 `SUPERSEDIDA`** por ADR posterior. Os sete portões passam. As garantias
> centrais — o diff aditivo, o segredo que nunca toca o disco, a identidade de três vias estendida
> com as duas metades, e a recusa antes do primeiro byte — foram **atacadas** e resistiram.

O que sustenta o veredito, e foi medido e não inferido:

- **A matriz de 12 fragmentos está inteira e correta.** As 4 receitas × 3 alvos renderizadas de
  verdade: três chaves raiz, três grafias de slot sem contaminação cruzada, header
  `Authorization: Bearer` montado a partir do papel (a palavra não aparece na receita), `inputs[]`
  com `password: true` **só** onde há segredo, `[server.env]` literal, nenhum default inventado — e
  **zero ocorrências de `${VAR:-default}`** nos doze, que é a armadilha medida na Problem Statement.
- **A história 36 foi atacada e resistiu.** 24 instalações reais (4 receitas × 3 alvos × 2 escopos)
  com valores-sentinela exportados no ambiente; `grep` no `$HOME`, no `$TMPDIR`, nos 24 stdouts e nos
  três arquivos de projeto devolve **zero ocorrências**. Só `${VAR}` / `${env:VAR}` / `${input:…}`.
- **A identidade de três vias estendida existe com as duas metades**, que era a pergunta que a spec
  fez com mais ênfase: `tests/test_writing.py:503`, linha 537 (`named <= after`) e linha **538**
  (`after - before <= named`) — a segunda é a que pega a armadilha de exit 0 com enxerto sumido.
  Sem `skipif`, sem marca, rodando nas 9 células.
- **O diff aditivo se sustenta** em indentação de 2, 4 e tab, em CRLF, em 9 comentários JSONC, em
  `$schema` e chave raiz inventada, e num `~/.claude.json` realista cujo `projects` — com histórico
  e `allowedTools` — chega byte-idêntico. `json.dumps` aparece uma vez em `src/`, sobre um escalar.
- **Recusa antes do primeiro byte em 100%** dos casos de exit 2 e 3, inclusive em linha que mistura
  classes: a recusa do MCP não deixa a skill escrita.
- **A raiz irmã se comporta**: 83 arquivos aterrissados numa instalação de tudo, **zero `.toml`** —
  a receita nunca aterrissa, que é a invariante que a separou da raiz de conteúdo.
- **O leitor de receita é total**: as 5 combinações incoerentes de (transporte × papel × campo)
  são recusadas com erro nomeado. Nenhuma produz fragmento sem sentido.

Os **3 achados B** são estreitos e nenhum contradiz o desenho: dois são casos de borda de inserção
em `grafting.py` (chave duplicada; comentário de fim de linha), e o terceiro é a única história
genuinamente não entregue — a **história 3**, os slots na tela de avaliação.

---

## 2. Saída dos portões

Rodados contra `origin/main` (`4fb2250`), a base entregue. **São sete, não quatro:** os required
checks deste repo são dois nomes — `gate` (que agrega o job `static` mais a matriz `test`) e
`release-ready` —, e dentro de `static` moram ruff e pyright **junto com P1, P2 e P3**, que o mapa
do briefing não listava. O crítico de cobertura os encontrou e os rodou.

| portão | saída verbatim | exit |
| --- | --- | --- |
| `uv run ruff format --check .` | `37 files already formatted` | 0 |
| `uv run ruff check .` | `All checks passed!` | 0 |
| `uv run --group typecheck pyright` | `0 errors, 0 warnings, 0 informations` | 0 |
| `uv run pytest` | `937 passed, 6 skipped in 38.33s` | 0 |
| **P1** — invariante da raiz de conteúdo | `P1 ok: 82 tracked path(s)` | 0 |
| **P2** — o wheel carrega o que a árvore declara | `P2 ok: 82 path(s) in dist/overpower-0.20.0-py3-none-any.whl` | 0 |
| **P3** — o sdist declara o que carrega (ADR `0013-o-sdist-…`) | `P3 ok: 111 file(s) in dist/overpower-0.20.0.tar.gz` | 0 |

**Os sete portões passam.**

### A ressalva do `/tmp/.git`, medida

No worktree velho, `uv run pytest` sem argumento sai **1**, com `4 failed, 928 passed, 6 skipped`:

```
FAILED tests/test_cli.py::test_outside_a_git_repository_no_scope_exits_two_and_writes_nothing - assert 0 == 2
FAILED tests/test_cli.py::test_outside_a_git_repository_a_graft_exits_two_as_well - assert 0 == 2
FAILED tests/test_scope.py::test_outside_any_repository_is_none - AssertionError: assert PosixPath('/tmp') is None
FAILED tests/test_wizard.py::test_ask_scope_outside_a_repository_has_one_answer_and_asks_nothing
```

As quatro são a poluição conhecida desta máquina — `/tmp/.git` faz `/tmp` ser detectado como
repositório. Com `--basetemp` fora de `/tmp`, as quatro passam.

**Uma segunda armadilha, descoberta durante esta auditoria e que vale registrar:** um `--basetemp`
*mais longo* que o default derruba **outros quatro** testes, com sintoma `assert '.mcp.json' in
'╭─ error …'`. Não é defeito de produto — é o teste assertando substring contra um painel Rich que
reembrulha por largura, e o caminho longo quebra a linha no meio do nome do arquivo. Reproduzi na
porta da frente, com um caminho de projeto profundo, e o produto **nomeia o arquivo corretamente**:

```
$ overpower install --mcp cloudflare --runtime claude-code   # em .../um-diretorio-de-projeto-bastante-profundo/com-mais-um-nivel
EXIT: 3
│  /home/…/um-diretorio-de-projeto-basta                                      │
│  nte-profundo/com-mais-um-nivel/.mcp.json is not ours to repair, and it is   │
│  broken: There were multiple errors parsing the JSON5 document.              │
CONTEM '.mcp.json' CONTIGUO: True
```

Quem for reproduzir a suíte fora de `/tmp`: use um basetemp **curto** (`--basetemp=/home/<user>/pt`).

---

## 3. Achados

29 achados, ordenados por severidade e, dentro dela, por custo de conserto crescente.
Todo **B** e **D** passou por um cético instruído a refutá-lo; **6 morreram** e estão na § 6.

| id | sev | título | onde | custo |
| --- | --- | --- | --- | --- |
| **S1-4** | **B** | comentário de fim de linha reancorado no servidor novo — o diff deixa de ser aditivo | `grafting.py:424-428` | ~5 linhas + 1 param de teste |
| **S4-1** | **B** | chave duplicada faz o enxerto cair na ocorrência sombreada — exit 0, e o runtime lê o valor antigo | `grafting.py:499-504` | ~6 linhas + 1 param de teste |
| **S1-1** | **B** | a tela de avaliação nunca mostra os slots que a receita exige | `screens.py:594` | ~10 linhas + 1 teste + 1 fixture |
| **S4-3** | D | conta `2 writes` para o par servidor + `inputs[]` que a spec define como uma escrita só | `planning.py:1063-1074` | 1 linha |
| **C3-01** | D | config de usuário ilegível cai no handler de "bug do overpower" | `grafting.py:146-157` | 1 linha + 1 teste |
| **S1-3** | D | a tela diz `scopes project, global` para receita que o install recusa em projeto | `rendering.py:279` | 1 linha + 1 teste |
| **S0-1** | D | nenhuma receita embutida declara precondição, e as duas stdio sobem por `npx` | `hostinger-vps.toml:19`, `coolify.toml:21` | 6 linhas de TOML |
| **C2-1** | D | a tela conta um arquivo por MCP selecionado, não por documento escrito | `writing.py:130-143` | 6 linhas + 1 teste |
| **S10-1** | D | dois slots de nomes distintos colapsam num `${input:id}` só — o segundo sobrescreve | `rendering.py:563-570` | ~6 linhas + 1 teste |
| **S1-5** | D | a linha que `list --mcp X --from URL` manda copiar não instala — o `--from` some | `screens.py:575` | ~6 linhas + 1 teste |
| **S1-2** | D | a tela de avaliação nunca mostra as precondições declaradas | `screens.py:594` | ~8 linhas + 1 teste |
| **S4-2** | D | vírgula sobrando em `.mcp.json` estrito não é recusada — exit 0 sobre arquivo que o alvo não lê | `grafting.py:245` | ~8 linhas + 1 param |
| **S9-2** | D | `runtimes.py` ainda afirma que a linha do Devin é doc do fornecedor "e não uma medição" | `runtimes.py:778-782,881-885` | ~8 linhas de comentário |
| **P-1** … **P-11** | P | 11 comportamentos corretos sem rede de proteção — detalhados na § 4 | vários | 1 teste cada |
| **O-1** … **O-5** | O | 5 otimizações, cada uma com o número que a justifica — detalhadas na § 4 | vários | ver tabela |

---

## 4. Detalhe dos achados

Todo achado **B** e **D** abaixo passou por um subagente cético instruído a refutá-lo, com a ordem
*"na dúvida, refute"*. Os que morreram estão na § 6.

### B — bloqueia

```yaml
- id: S1-4
  severidade: B
  titulo: comentário de fim de linha é reancorado no servidor recém-escrito, e o diff deixa de ser aditivo
  historia: 14 e 18 (ADR 0016)
  onde: src/overpower/grafting.py:424-428 (`_appended`)
  esperado: |
    #75 história 14 — "o resto do documento chegue **byte a byte igual**".
    ADR 0016 — "o `git diff` mostra só as linhas que o overpower escreveu".
  observado: |
    `_appended` move o `wsc_after` inteiro do último par para o valor novo. Quando esse
    `wsc_after` contém um comentário de fim de linha, o comentário sai da entrada que ele
    anotava e passa a anotar o servidor que o overpower escreveu.
  prova: |
    antes (.mcp.json):
      "antigo": {"command": "node"} // meu comentario sobre o antigo
    $ overpower install --mcp cloudflare --runtime claude-code --yes   → exit 0
    depois:
        "antigo": {"command": "node"},
        "cloudflare": { "type": "http", "url": "https://mcp.cloudflare.com/mcp" }
        // meu comentario sobre o antigo
    O critério executável do próprio produto reprova: `lost_lines` (tests/test_writing.py:475),
    que admite **uma vírgula** como única exceção, devolve
      ['    "antigo": {"command": "node"} // meu comentario sobre o antigo']
    e o `diff -u` mostra **1 linha removida** e 5 adicionadas. Reproduzido também em
    .vscode/mcp.json. O fixture existente (test_writing.py:620) põe o comentário em linha
    própria, onde mover é correto — o caso de mesma linha não tem cobertura.
  conserto: |
    Em grafting.py:424, mover só o rabo de whitespace **posterior ao último comentário**
    (`_indent_of` já sabe achar a última corrida de whitespace); o que vem antes fica com
    o par que já o tinha.
  custo: ~5 linhas em grafting.py + 1 caso na parametrização de test_writing.py:620
  nota: |
    O cético graduou **D**. Promovi para **B** porque a escada de severidade desta auditoria
    lista "diff não aditivo" explicitamente sob B, e a prova é executada: `lost_lines` não
    vazio e uma linha removida no diff.

- id: S4-1
  severidade: B
  titulo: chave duplicada no arquivo do usuário faz o enxerto aterrissar na ocorrência sombreada — exit 0, e o runtime lê o valor antigo
  historia: 67 + a identidade de três vias (#75 linha 250)
  onde: src/overpower/grafting.py:499-504 (`_index_of` devolve o primeiro match), usado por `refuse_if_broken` (:188) e por `_set` (:307)
  esperado: |
    #75 linha 250 — "toda chave que o plano nomeou existe no documento depois da execução".
    ADR 0013:27 — o plano nomear a chave é "a única defesa que sobra" contra a sobrescrita
    incondicional.
  observado: |
    Todo parser JSON resolve chave duplicada pela **última** ocorrência; o overpower escreve
    na **primeira**. Sai 0, imprime `1 write · 1 file`, o plano nomeia
    `.mcp.json › mcpServers.cloudflare` — e depois da execução essa chave, para quem lê o
    arquivo, ainda vale o valor do usuário. Reproduzido nos **três** dialetos.
  prova: |
    # entrada: {"mcpServers": {"cloudflare": {"command":"VELHO-A"}, "cloudflare": {"command":"VELHO-B"}}}
    $ overpower install --mcp cloudflare --runtime claude-code --yes ; echo $?
    0
    $ python3 -c "import json;print(json.load(open('.mcp.json'))['mcpServers']['cloudflare'])"
    {'command': 'VELHO-B'}     # o enxerto está no arquivo e é invisível ao runtime

    # raiz duplicada: {"mcpServers": {...}, "mcpServers": {...}}  →  exit 0
    $ python3 -c "import json;print(sorted(json.load(open('.mcp.json'))['mcpServers']))"
    ['outro']                  # `cloudflare` sumiu do significado do arquivo

    # e a checagem da história 67 é EVADIDA por esta via:
    # {"mcpServers": "not a table"} sozinho sai 3; escondido atrás de uma raiz
    # duplicada sai **0**, porque refuse_if_broken só tipa a primeira ocorrência.
  conserto: |
    Recusar, não escrever na última: a RFC 8259 §4 promete comportamento *unpredictable*,
    e escrever o valor certo num documento ambíguo deixa o documento ambíguo. Em
    `refuse_if_broken` (grafting.py:172), contar as ocorrências da chave raiz e do nome do
    servidor e levantar `MalformedDocumentError` quando > 1.
  custo: ~6 linhas em grafting.py + 1 param novo em BROKEN (tests/test_writing.py:1148)
  nota: |
    A ressalva honesta do cético: isto **alarga** "quebrado" além do texto literal da
    história 67 (chave duplicada é JSON válido pela RFC). É emenda à ADR 0013, cuja
    cláusula de reabertura (0013:31) já mira território vizinho.

- id: S1-1
  severidade: B
  titulo: a tela de avaliação de um MCP nunca mostra os slots que a receita exige
  historia: 3
  onde: src/overpower/screens.py:594 (`_recipe_facts`)
  esperado: |
    #75 história 3 — "quero ver **quais slots ele exige e o papel de cada um**, para saber
    que segredos vou precisar ter antes de instalar, e não descobrir isso num 401 depois."
  observado: |
    `_recipe_facts` devolve `(*_declared(recipe.server), *_target_facts(targets))`;
    `recipe.slots` não é lido em lugar nenhum de `screens.py` (as duas ocorrências de "slot"
    são docstring). A linha `env` da tela contém **só literais de `[server.env]`**, nunca slots.
  prova: |
    $ overpower list --mcp coolify          # a 80 e a 120 colunas, contra origin/main
    │    env      COOLIFY_BASE_URL  https://vps.panlabs.tech                       │
    │    targets  claude-code, vscode, devin                                       │
    │    scopes   project, global                                                  │
    # o slot COOLIFY_ACCESS_TOKEN (catalog/mcps/coolify.toml:27-29) não aparece.
    # Pior em hostinger-vps: não tem [server.env], então a tela não tem linha `env`
    # nenhuma — nada sugere que HOSTINGER_API_TOKEN existe.
    $ grep -rln "slot" tests/snapshots/   →  vazio
    # os 4 snapshots MCP aprovados registram a ausência.
  conserto: |
    Uma linha `slots  <NOME>  <papel>` em `_recipe_facts` (screens.py:594), entre
    `_declared` e `_target_facts`, com um `_stacked` como o de `_pairs`.
  custo: |
    ~10 linhas em screens.py + 1 teste. As fixtures `recorded_recipe`/`recorded_stdio_recipe`
    não declaram slot, então os 4 snapshots `list-mcp*` não se movem sem uma fixture nova.
  nota: |
    O `--dry-run` do install imprime `not set here COOLIFY_ACCESS_TOKEN` — mas (a) está sob o
    verbo `install`, e a história 3 vive em § Descobrir; (b) é condicional a a variável estar
    unset (`cli.py:906-907`), então quem já exportou não vê nada; (c) **nunca mostra o papel**,
    que é metade literal da história.
```

### D — defeito

```yaml
- id: S4-3
  severidade: D
  titulo: o relatório conta "2 writes" para o par servidor + `inputs[]` que a spec define como uma escrita só
  historia: "#75 linha 227"
  onde: src/overpower/planning.py:1063-1074 (`_graft_landing`) e :302 (`Plan.writes`)
  esperado: |
    "Um MCP no VS Code é dois enxertos no mesmo documento — o servidor e o append em
    `inputs[]` —, e os dois são **uma escrita só do ponto de vista do plano**, porque
    aterrissam no mesmo lugar."
  observado: |
    `_graft_landing` colapsa só `files`; `landing.writes` carrega **duas** entradas.
  prova: |
    $ overpower install --mcp github --runtime vscode --yes | grep write
    │  2 writes · 1 file                                                           │
    $ overpower install --mcp cloudflare --runtime claude-code --yes | grep write
    │  1 write · 1 file                                                            │

    # o desempate: o caso federado (clone + enxerto), que a #75 linha 219 chama de
    # "duas escritas, ambas no plano", imprime exatamente 2 —
    # logo "escrita" = objeto `Write` do plano, a unidade que a própria spec escolheu:
    RUNTIME=claude-code writes=2 files=3 landings=2 modes=['CLONE', 'GRAFT']
    RUNTIME=vscode      writes=2 files=3 landings=2 modes=['CLONE', 'GRAFT']

    # nenhum snapshot fixa `2 writes · 1 file`:
    # tests/snapshots/installed-graft-80.txt:6 aprova `1 write · 1 file`
    # (claude-code, servidor sem inputs[]).
  conserto: contar escritas de enxerto por documento no sumário (o mesmo `1 if index == 0 else 0` que `files` já usa) — ou emendar a linha 227 da #75
  custo: 1 linha em planning.py — ou 1 parágrafo de spec
  nota: |
    Não é cosmético de tela: o `--dry-run` e o relatório de falha parcial ("wrote 14 of 22")
    contam as duas.

- id: S1-3
  severidade: D
  titulo: a tela diz `scopes project, global` para uma receita que o install recusa em escopo de projeto
  historia: 4 e 28 (ADR 0015)
  onde: src/overpower/rendering.py:279 (`targets_of` filtra só por transporte)
  esperado: |
    ADR 0015 § Consequences — "o conjunto de escopos é função da receita, e o wizard não
    oferece projeto para uma receita com `[source]`" e "a tela não oferece o que o passo
    seguinte recusaria".
  observado: |
    `targets_of` devolve todo par (runtime, scope) cujo documento expressa o transporte;
    não olha `recipe.source`. O wizard **já** obedece a ADR (`wizard.py:304-318`,
    `if sourced: return Scope.GLOBAL`); a tela de `list` não.
  prova: |
    $ overpower list --mcp acme --from <url>
    │    scopes   project, global                                                  │
    $ overpower install --mcp acme --from <url> --runtime claude-code --yes
    `acme`: brings its own source code, which lands on this machine and not in the
    repository; install with --global instead                              (exit 3)

    src/overpower/rendering.py:279-283:
      return tuple(Target(runtime=runtime, scope=scope)
                   for (runtime, scope), document in documents.items()
                   if recipe.transport in _transports(document.dialect))
    # e `Target` É o par (runtime, scope) — tests/test_screens.py:244.
    # Nenhum teste fixa a saída para receita com fonte: recorded_recipe() é HTTP sem [source].
  conserto: '`and (recipe.source is None or scope is Scope.MACHINE)` no generator de `targets_of` — a mesma regra que planning.py:391 já aplica'
  custo: 1 linha em rendering.py + 1 teste em test_rendering.py

- id: S9-2
  severidade: D
  titulo: runtimes.py ainda afirma que a linha do Devin é doc do fornecedor "e não uma medição", com o binário "ausente da máquina"
  historia: "#75 § Further Notes — 'as docstrings passam a citar medição em vez de inferência'"
  onde: src/overpower/runtimes.py:778-782 e :881-885
  esperado: |
    Depois da #87 (`devin 3000.4.25` em sandbox), `docs/research/mcp-config-formats.md:603,623`
    marcam **medido**, e `src/overpower/rendering.py:399` já diz "measured, not just inferred
    by analogy". A #75 linha 300 lista a propagação como entregável.
  observado: |
    runtimes.py:778-782 — "Vendor documentation and **not** a measurement, in …/issues/80:
      `.devin/mcp_config.json` at the root of the project, `mcpServers`, and no approval gate
      documented anywhere — so `born_pending` stays false…"
    runtimes.py:881-885 — "the Devin row was read off the vendor's documentation **with the
      binary absent from the machine** (…/issues/80)"
  prova: |
    $ git show --stat 01de393
    mcp-config-formats.md · rendering.py · test_cli.py · test_rendering.py
    # o commit da medição não tocou runtimes.py.
    contra docs/research/mcp-config-formats.md:623:
      "`devin mcp list`, `devin mcp get <nome>` e `devin mcp add` leem e escrevem
       `.devin/mcp_config.json` … sem exigir login e sem qualquer prompt de confiança"
  conserto: |
    Reescrever os dois trechos citando a § "Medição 2026-08-14". Atenção ao meio-termo que o
    cético isolou: a cláusula que **decide comportamento** — "no approval gate documented
    anywhere, so `born_pending` stays false" — **continua correta**, porque a #87 deixou o
    portão de *uso* atrás do login e achou `--respect-workspace-trust` de alcance não
    confirmado. O que envelheceu é o qualificador de abertura, que cobre exatamente os dois
    fatos que a #87 mediu.
  custo: ~8 linhas de comentário/docstring, nenhuma mudança de comportamento

- id: S1-2
  severidade: D
  titulo: a tela de avaliação de um MCP nunca mostra as precondições declaradas
  historia: 5
  onde: src/overpower/screens.py:594 (mesma função de S1-1)
  esperado: '#75 história 5 — "quero ver as **precondições** que ele declara, para saber que ferramental minha máquina precisa ter"'
  observado: '`recipe.preconditions` não aparece em screens.py; a única superfície é a recusa de install (planning.py:697), que é exatamente o "descobrir depois" que a história pede para evitar'
  prova: |
    $ grep -n "precondition" src/overpower/screens.py   →  nada
    # o schema suporta (recipes.py:76,337,544,697) e o leitor lê.
  conserto: 'uma linha `needs  <check> <value>` em `_recipe_facts` (screens.py:594)'
  custo: ~8 linhas em screens.py + 1 teste
  nota: |
    **Rebaixado de B para D pelo cético, e ele estava certo**: `grep -rn "precondition"
    src/overpower/catalog/` devolve **zero** — nenhuma receita embutida declara precondição,
    então o defeito é hoje inobservável para todo artefato que o produto entrega. Só morde
    receita federada via `--from`. É lacuna latente que vira defeito quando nascer a primeira
    receita com `[[preconditions]]` — ver S0-1, que é o outro lado do mesmo fato.

- id: S1-5
  severidade: D
  titulo: a linha que `list --mcp X --from URL` manda copiar não instala — o `--from` some
  historia: "- (invariante interna do produto)"
  onde: src/overpower/screens.py:575 — `commands=(_install(MCP_FLAG, recipe.name),)`
  esperado: |
    O produto testa por nome que a linha impressa instala quando colada de volta:
    `test_the_mcp_line_the_list_prints_installs_when_it_is_pasted_back` (test_cli.py:2246) e
    `test_the_lines_to_copy_survive_a_pipe` (test_cli.py:565).
  observado: '`cli.py:434-435` chama `_listed(...)` igual ao caminho sem `--from`; `from_` nunca chega à tela'
  prova: |
    $ overpower list --mcp acme --from https://github.com/acme/servers
    │      overpower install --mcp acme                                            │
    $ overpower install --mcp acme --runtime claude-code --yes
    no MCP server named `acme` (the catalog has: cloudflare, coolify, github,
    hostinger-vps)                                                          (exit 2)
    # test_cli.py:2246 roda `list --mcp cloudflare` SEM --from; não afirma nada sobre o federado.
  conserto: 'passar a origem para `mcp_screen` e emitir `overpower install --mcp <slug> --from <url>` quando ela existir (screens.py:549/575; a chamada é cli.py:490)'
  custo: ~6 linhas entre cli.py e screens.py + 1 teste
  nota: |
    **D fraco.** Nenhuma história da #75 exige a linha de cópia para o caso federado — a
    história 6 só pede "ler a receita sem instalar nada". É violação de invariante interna,
    não da spec. Pré-existente e byte-idêntico em `origin/main`, não é regressão deste corte.

- id: S4-2
  severidade: D
  titulo: vírgula sobrando num `.mcp.json` estrito não é recusada — sai 0 sobre um arquivo que o Claude Code não lê
  historia: 67
  onde: src/overpower/grafting.py:245 (`_document` lê tudo com o parser JSON5, tolerante) vs src/overpower/runtimes.py:760-767 (o produto documenta `.mcp.json` como estrito)
  esperado: |
    #75 história 67 — "quero que o overpower **recuse e não repare**".
    ADR 0016:58 reafirma: "`claude mcp add` e `codex mcp add` **recusam e não reparam**".
  observado: |
    O leitor é JSON5 para os dois dialetos. Num `.vscode/mcp.json` (JSONC) vírgula sobrando é
    legal; num `.mcp.json` ela é "arquivo já quebrado". O overpower não repara (a vírgula
    sobrevive — a segunda metade da história está cumprida) mas também não recusa.
  prova: |
    $ python3 -c "import json;json.load(open('.mcp.json'))"   # antes
    JSONDecodeError: Expecting property name enclosed in double quotes: line 4 column 3
    $ overpower install --mcp cloudflare --runtime claude-code --yes ; echo $?
    0        # + "Done!" e "pending approval — Claude Code asks the next time it starts"
    $ python3 -c "import json;json.load(open('.mcp.json'))"   # depois
    JSONDecodeError: ...

    # a medição do próprio repo confirma a premissa:
    docs/research/mcp-config-formats.md:61   JSONC = "comentários + vírgula final"
    docs/research/mcp-config-formats.md:167  Claude Code lendo .mcp.json:  JSONC | ❌ estrito
    docs/research/mcp-config-formats.md:178  arquivo inválido: "reporta, mas exit 0 em mcp list"
  conserto: |
    `refuse_if_broken` (grafting.py:172) já recebe o `path`; passar também o `Dialect` e,
    quando o documento é estrito, revalidar o texto com `json.loads` antes de aceitar.
    `McpDocument.dialect` já separa os dois (runtimes.py:765, :808) — falta o dado chegar ao
    leitor (`grep -c Dialect src/overpower/grafting.py` = 0). É um portão, não feature nova.
  custo: ~8 linhas em grafting.py + a passagem do dialeto em planning.py:653; 1 param em BROKEN
  nota: |
    `tests/test_writing.py:996` (`test_a_trailing_comma_keeps_the_entry_it_terminates`) roda
    sobre `VSCODE_JSON`, onde a vírgula é JSONC legal — é o caso oposto, não a rede que falta.
```

```yaml
- id: C3-01
  severidade: D
  titulo: arquivo de configuração de usuário ilegível cai no handler de "bug do overpower"
  historia: "- (modelo de erro; a régua de saída da #75, linhas 231-240)"
  onde: src/overpower/grafting.py:146-157 (`read_document`, `path.open()` na :156) — sem guarda de `OSError`; escapa até o catch-all `except Exception` em src/overpower/cli.py:1054
  esperado: |
    Erro nomeado de ambiente, como os dois vizinhos do mesmo arquivo já têm.
  observado: |
    exit 1 com o painel de erro interno:
      "PermissionError: [Errno 13] Permission denied: .../.claude.json"
      "This is a bug in the overpower, not in what you typed."
    A falha é na **leitura**, antes de qualquer escrita, e o produto se autoacusa por uma
    permissão que o usuário pôs.
  prova: |
    # com HOME isolado:
    $ chmod 000 $HOME/.claude.json
    $ overpower install --mcp github --runtime claude-code --global --yes
    → exit 1, painel "This is a bug in the overpower"

    # a assimetria, tripla, no mesmo arquivo e no mesmo comando:
    | ~/.claude.json malformado   | MalformedDocumentError nomeado (grafting.py:251) |
    | ~/.claude.json não gravável | WriteFailedError nomeado (writing.py:95 / :135)  |
    | ~/.claude.json NÃO LEGÍVEL  | painel de bug                                    |
    # PermissionError é subclasse de OSError, e writing.py:135 já captura OSError.
  conserto: guardar `read_document` com `except OSError` e um erro nomeado, como os dois vizinhos
  custo: 1 linha em grafting.py + 1 teste
  nota: |
    **D de banda baixa.** O ponto fraco é o realismo — `chmod 000` no próprio arquivo é
    artificial —, mas `.claude.json` criado por `sudo`/root em container, volume montado e ACL
    corporativa produzem a mesma leitura negada. Não há perda de dado, a parada é segura e
    anterior a qualquer escrita, e o exit code não engana pipeline: o achado é **só** sobre a
    mensagem. Mas não é redação — a flag `unexpected=True` existe para afirmar de quem é a
    culpa, e manda abrir bug por uma condição de ambiente que o produto não pode consertar.
    Não há ADR sustentando "toda exceção não modelada é bug por decisão": o catch-all é
    catch-all, não doutrina.

- id: C2-1
  severidade: D
  titulo: a tela de fecho conta um arquivo por MCP selecionado, não por documento escrito
  historia: "- (contrato declarado no próprio código, planning.py:163-171)"
  onde: src/overpower/planning.py:1072 (soma final em src/overpower/writing.py:130-143)
  esperado: |
    planning.py:170-171, literal — "**Zero for a second graft into the same one** — a VS Code
    slot lands the server and its prompt as two keys, and the report at the end counts what
    landed on disk, where one file did."  "the same one" é o mesmo **documento**.
  observado: |
    `files = 1 if index == 0 else 0` é enumerado *dentro de uma seleção* (`_graft_landing`, um
    por MCP). Três MCPs no mesmo `.vscode/mcp.json` são exatamente "second graft into the same
    one", e o `index == 0` reinicia por MCP: o contador dá 3 onde 1 arquivo aterrissou.
  prova: |
    $ overpower install --mcp github,coolify,hostinger-vps --runtime vscode -y
      6 writes · 3 files
    $ git status --porcelain
      ?? .vscode/mcp.json          # um arquivo
    # correto quando os documentos são mesmo distintos:
    $ overpower install --mcp github --runtime claude-code,vscode -y   →  2 arquivos, 2 landam
    # nenhum snapshot fixa o contador multi-MCP:
    #   tests/snapshots/installed-graft-80.txt:6  →  "1 write · 1 file" (um MCP, um enxerto)
    #   grep "github,\|,coolify" tests/  →  zero. Nenhum caso multi-MCP existe na suíte.
  conserto: |
    Em `writing.py:132-142`, contar caminho distinto para `WriteMode.GRAFT` em vez de somar
    `write.files`. A dedup precisa ser plan-wide e `_graft_landing` não enxerga as outras
    seleções — por isso o conserto é no escritor, não no plano.
  custo: 6 linhas em writing.py + 1 teste
  nota: |
    Metade da acusação original **caiu** na verificação: reinstalar num documento pré-existente
    imprime `1 file` tendo criado zero arquivos, e isso é **contrato cumprido** — a frase diz
    "One for the first graft into a document", sem distinguir criar de tocar. Só o caso
    multi-MCP viola. **Distinto de S4-3**, e um conserto não fecha os dois: aplicar só o de
    S4-3 dá `3 writes · 3 files` (o `3 files` sobrevive); aplicar só este deixa `6 writes`.
    A raiz de forma é comum: **os dois contadores são calculados por seleção/landing e nunca
    reconciliados contra o caminho do documento.**

- id: S10-1
  severidade: D
  titulo: dois slots de nomes distintos que normalizam para o mesmo `${input:id}` viram um prompt — o segundo sobrescreve o primeiro, exit 0
  historia: "- (a invariante que a própria recipes.py:604-611 declara)"
  onde: src/overpower/rendering.py:563-570 (`_input_id`), sem contraparte em src/overpower/recipes.py:632-653 (`_filled`)
  esperado: |
    recipes.py:604-611 — "dois `bearer` slots carregam variáveis diferentes e preenchem o
    *mesmo* header, então um renderizador montando uma tabela guardaria um deles e largaria o
    outro no exit 0 — um segredo sumido de um arquivo que ninguém relê."
  observado: |
    `_input_id(name) = name.lower().replace("_", "-")` não é injetiva. O leitor guarda o
    **lugar** (nome cru, case-sensitive — correto para variável POSIX); o renderizador colapsa
    o **nome**. O graft `Inputs` carrega `identity="id"` e `grafting._set_element`
    (grafting.py:339-360) substitui o elemento de mesma identidade.
  prova: |
    # CLI real, receita HTTP com dois headers DISTINTOS e slots API_KEY / API-KEY:
    EXIT: 0     "2 writes · 1 file"
    .vscode/mcp.json:
      "headers": {"X-One": "${input:api-key}", "X-Two": "${input:api-key}"}
      "inputs": [{"type":"promptString","id":"api-key","description":"API-KEY","password":true}]
    # X-One recebe calado o segredo que o usuário digitou para API-KEY.
    # E o caso env, também pela CLI: dois slots, um prompt, `description` do segundo.
  conserto: mover `_input_id` para `recipes.py` e somar `_input_id(name)` à comparação de `_slots`, levantando o `CollidingSlotError` que já existe
  custo: ~6 linhas em recipes.py + 1 teste
  nota: |
    **D e não B**, por dois motivos que o cético fixou. (i) O gatilho exige nomes que difiram
    **só** em caixa ou `_`/`-`; headers distintos dão nomes distintos, e headers que normalizam
    iguais já são recusados por `_filled` (recipes.py:648). Nenhuma receita embutida tem o par.
    (ii) Quem escreve `API_KEY` + `API-KEY` está, na prática, declarando o **mesmo** segredo.
    O dano real é de **segunda ordem**: a mesma receita **diverge entre alvos** — o VS Code pede
    um valor e enche os dois headers, enquanto Claude e Devin (`${VAR}`/`${env:VAR}`, sem
    normalização) pedem duas variáveis, uma delas (`API-KEY`) não setável por `export` POSIX.
    Uma versão anterior deste achado foi **refutada** (ver § 6, S3-1); esta é outra coisa, e o
    cético que a avaliou explicitou a distinção.

- id: S0-1
  severidade: D
  titulo: nenhuma receita embutida declara precondição, embora a tabela de receitas de prova da #75 atribua `command_exists` a duas delas — e as duas sobem por `npx`
  historia: 5 e 31 (critério de curadoria, #75 linha 304)
  onde: src/overpower/catalog/mcps/hostinger-vps.toml:19 e coolify.toml:21
  esperado: |
    #75 § "As receitas de prova, e elas são reais" (linhas 268-273) tem uma coluna `precondição`,
    e nela `command_exists` para `hostinger-vps` e para `coolify`.
    #75 linha 304 — "O que continua reprovando é exigência **não declarada**."
    docs/agents/domain.md:127 amarra a leitura ao mecanismo: "o que reprovava não era exigir
    ferramental — era exigir **sem declarar**", dito ao anunciar `[[preconditions]]` (#82).
  observado: |
    $ grep -rn "precondition" src/overpower/catalog/mcps/   →  zero (exit 1)
    hostinger-vps.toml:19  command = "npx"
    coolify.toml:21        command = "npx"
  prova: |
    As 4 receitas lidas inteiras (14, 29, 23, 24 linhas): nenhuma tem `[[preconditions]]`.
    Instalar qualquer uma numa máquina sem Node sai 0 e escreve config para um servidor que não
    sobe — que é o dano que a história 31 nomeia: "para que quem instala descubra a falta
    **antes** da escrita e não num erro obscuro do agente". A maquinaria existe
    (planning.py:697/720, exit 3) e o catálogo embarcado nunca a exercita.
  conserto: acrescentar `[[preconditions]] check = "command_exists" / value = "npx"` às duas receitas
  custo: 6 linhas de TOML — e nada na #75 precisa ser emendado, porque a tabela dela já as prevê
  nota: |
    O cético pesou o eixo mais forte — "a coluna é descritiva do servidor, não exigência de
    conteúdo" — e ele não fecha: o valor escrito é `command_exists`, que é literalmente um dos
    três `check` do schema (recipes.py:199); descrição livre teria dito "precisa de Node".
    É defeito de **curadoria**, não de implementação. E é o outro lado do S1-2: enquanto
    nenhuma receita declarar precondição, a lacuna da tela permanece inobservável.
```

### P — prova ausente

O comportamento existe e está correto; **nada o prova**. Cada linha diz qual comportamento
observável ficaria sem rede se uma regressão o quebrasse.

| id | comportamento sem rede | onde | conserto | custo |
| --- | --- | --- | --- | --- |
| **P-1** | **a primeira linha da tabela de exit 3** — runtime sem renderizador → exit 3, nada escrito. Apagar o `elif carries_mcp` de `planning.py:615-616` passa a suíte inteira verde e troca exit 3 por exit 0 com o servidor em lugar nenhum. `grep -rn "NoMcpDocumentError\|no MCP document" tests/` → **zero** | `planning.py:459,859` | 1 teste em `test_planning.py`, molde em `:169` | 1 teste |
| **P-2** | **as 4 receitas embutidas nunca são renderizadas por teste nenhum.** `test_rendering.py` só usa dublês inline; `test_catalog.py` carrega o catálogo real e nunca chama `render`. O caminho **literal** de `[server.env]` — exatamente onde a armadilha `${VAR:-default}` mora nos dois arquivos versionados da organização — não tem asserção: editar `coolify.toml` para `COOLIFY_BASE_URL = "${COOLIFY_BASE_URL:-https://…}"` entra **verde** | `tests/test_rendering.py` (nenhum `load_catalog`) | um teste que renderiza as 4 × 3 alvos, afirma 12 fragmentos e `":-" not in` nos doze | 1 teste (~15 linhas) |
| **P-3** | **o ramo HTTP do allowlist de `[server]`** — `[server.env]` sob `transport = "http"` é recusado; sem a guarda ele seria lido e sumiria calado do fragmento. Provado por **mutação**: trocar `_HTTP_KEYS` para aceitar `env`/`command` deixa **141 testes passando** | `recipes.py:593`; o único teste do eixo (`test_recipes.py:158`) exercita só o ramo stdio | parametrizar `test_recipes.py:158` com o par http | 1 teste (2 params) |
| **P-4** | **quatro recusas do leitor de receita**: `slots`/`preconditions` que não são lista, `args` que não é lista, item de `args` não-string | `recipes.py:614,700,758,761` | 4 casos parametrizados em `test_recipes.py` | 1 teste parametrizado |
| **P-5** | **a linha exit 1 é a única sem par (dry-run, real).** O espelho está asseverado para 0, 2 e 3; uma regressão em que o dry-run engolisse `ObtentionError` e devolvesse 0 passaria verde nas 9 células — e é o portão de CI que a história 57 existe para servir | `tests/test_cli.py:2459` roda só o caminho real | cópia de `:2459` com `--dry-run`, assertando `dry == real == 1` | 1 teste (~14 linhas) |
| **P-6** | **receita federada reprovada na validação parando a linha na CLI**: transporte proibido → exit 3 e disco intacto. Trocar `ForbiddenTransportError(RefusedError)` por `(OverpowerError)` muda o exit de 3 para 1 com a suíte verde | `recipes.py:566`; provado só no nível de `read_recipe` | 1 teste de CLI com `--from` sobre remoto local, molde `test_cli.py:2407` | 1 teste |
| **P-7** | **os desvios de `inputs[]` mal-formado no enxerto** (`"inputs": ["x"]`, `"inputs": [{}]`) — arquivos de usuário plausíveis. A idempotência é *load-bearing* por medição: `grafting.py:202-215` diz que o VS Code confia por `TrustedOnNonce` sobre o hash do lançamento, então duplicar a cada run faria o usuário reaprovar tudo sempre | `grafting.py:377,380` | 2 casos em `test_writing.py` | 1 teste parametrizado |
| **P-8** | **as 4 renderizações novas do bloco de integridade do `doctor`** (`pending approval`, `clone is gone`, `` `VAR` not set here ``, `clone not referenced by any config`) não têm snapshot nem asserção estrutural. As duas fixtures do doctor têm `notices=()`, então o teste de largura também nunca as vê. Fica sem rede: a dobra do caminho a 60 colunas, o recuo sob a headline, o `/` final do órfão, e o `op.dim` que separa notice de finding | `tests/test_screens.py:1411-1495` | 3ª fixture `recorded_graft_diagnosis()` + 2 entradas nas listas + 2 snapshots | ~30 linhas + 2 snapshots |
| **P-9** | **`doctor` deixa de cobrar aprovação com `enableAllProjectMcpServers`** — medido ao vivo: com a flag no `.claude/settings.local.json`, as linhas de `approv` somem | `inspection.py:786-787`; `grep -rn enableAllProjectMcpServers tests/` → zero | um caso a mais em `test_inspection.py:543+` | 1 teste |
| **P-10** | **o braço Devin do check de slot do `doctor`** — `grep -rn 'devin' tests/test_inspection.py` → **zero**. Medido ao vivo: `doctor` reporta `UnsetSlot` para `${env:VAR}` do dialeto Devin, exit 0 | `inspection.py:893-894` | parametrizar `test_inspection.py:628` por dialeto | 1 parametrização |
| **P-11** | **`doctor` tolera documento MCP corrompido sem crashar** — `printf '{ this is not json' > .mcp.json; overpower doctor` → `no findings`, exit 0, sem traceback | `inspection.py:692-695` | 1 caso em `test_inspection.py` | 1 teste |

### O — otimização

Cada linha carrega o número que a justifica. Achado **O** sem número não entrou.

| id | o quê | número | onde |
| --- | --- | --- | --- |
| **O-1** | `_devin` reescreve a caminhada de `_server`, contra o que o docstring de `_server` proíbe em `rendering.py:342-345` (*"One walk of the fields for both dialects… Writing it twice would put the shape of a server in two places, and the second one is where a field goes missing the day a recipe grows one"*). O delta real entre as duas é **dois** campos. Consequência medida: `_reference(Dialect.DEVIN)` ficou **inalcançável** — nunca executa nas 929 provas, que incluem instalações devin | **−17 linhas** de lógica, **+8** de tabela (net ~−9), mais 2 linhas mortas | `rendering.py:392-426` e `334-364`; morto em `:386-387` |
| **O-2** | `refuse_broken_documents` lê e parseia o mesmo arquivo **uma vez por write**. O *check* por write é correto (`planning.py:665-667` o justifica); a leitura e o parse não | 3 MCPs num `.mcp.json` existente = **6 leituras + 6 parses**; agrupando por caminho → 4 e 4. Economia = N−1 de N grafts por documento | `planning.py:669-677` |
| **O-3** | dois docstrings de módulo deixaram de indexar o que o módulo carrega — e neste repo *"o índice é o docstring"*. `runtimes.py:1-21` diz *"where each AI runtime reads **skills** from"* e não menciona MCP nem enxerto uma vez sequer, enquanto o módulo carrega `Dialect` (:62), `McpDocument` (:111), `MCP_DOCUMENTS` (:871) e `document_for` (:935). `discovery.py:1-24` para em `content/pool/` e `content/frameworks/`, e o módulo anda a terceira raiz em `:274` | `awk 'NR<=21' runtimes.py \| grep -ci "mcp\|graft"` → **0** | `runtimes.py:1`, `discovery.py:1` |
| **O-4** | duas ADRs ocupam o número **0013** (`0013-a-chave-alheia-e-sobrescrita.md`, nascida em `de3d892`/#74, e `0013-o-sdist-declara-o-que-carrega.md`, em `147348b`/#73). Não há índice de ADRs para quebrar, e **nenhuma citação por número aponta para a ADR errada** — cada uma é desambiguada pelo contexto do arquivo | **8** citações por número puro (7 → chave-alheia, 1 → sdist) e 8 por slug. Renomear a do sdist para `0019-` custa **1 rename + 6 referências**; renomear a outra custaria 9 e quebraria o link que a #75 cita | `docs/adr/0013-*.md` |
| **O-5** | a suíte é sensível à **largura do terminal e ao comprimento do `tmp_path`**: 4 testes assertam substring (`'.mcp.json' in …`) contra um painel Rich que reembrulha, e quebram quando o caminho é longo ou `COLUMNS` é estreito. Confirmado por dois auditores independentes e por mim; com `COLUMNS=200` ou basetemp curto, os 4 passam. O CI **não fixa `COLUMNS`** | **4 testes**; conserto = 1 linha de env no workflow, ou assertar sobre texto não-reembrulhado | `tests/test_writing.py:1162`, `tests/test_cli.py:1680`; `.github/workflows/ci.yml` |

---

## 5. Matriz das 68 histórias

Classificação: `PROVADO` (comportamento existe **e** teste nomeado o exercita) · `SEM-PROVA`
(existe, nada prova) · `PARCIAL` (metade entregue) · `AUSENTE` (não existe) · `SUPERSEDIDA`
(revisada por ADR posterior — não é lacuna).

### Descobrir (1–8)

| nº | classificação | onde | prova |
| --- | --- | --- | --- |
| 1 | PROVADO | `screens.py:454` | `test_the_catalog_screen_gives_the_mcp_servers_a_block_of_their_own` (test_screens.py:1176) |
| 2 | PROVADO | `screens.py:549,597` | `test_the_mcp_screen_shows_the_description_whole` (:1195) + `…names_the_transport_and_the_url…` (:1211) |
| 3 | **AUSENTE** | `screens.py:594` — `_recipe_facts` nunca lê `recipe.slots` | — |
| 4 | PARCIAL | `screens.py:629`, `rendering.py:279` | `test_the_mcp_screen_names_which_targets_the_recipe_serves` (:1240) — runtimes certos, `scopes` mente para receita com fonte |
| 5 | **AUSENTE** | `screens.py:594` — nunca lê `recipe.preconditions` | — |
| 6 | PROVADO | `cli.py:434` | `test_list_mcp_from_shows_the_recipe_and_writes_nothing` (test_cli.py:2616) |
| 7 | PROVADO | `screens.py:549` | `test_no_rendered_line_of_an_mcp_screen_exceeds_the_terminal_width` (:1314) |
| 8 | PROVADO | `cli.py` (`_out`) | `test_piped_output_carries_no_ansi[list-mcp]` (test_cli.py:489) |

### Instalar um MCP de mercado (9–19)

| nº | classificação | onde | prova |
| --- | --- | --- | --- |
| 9 | PROVADO | `planning.py:981` | `test_the_plan_the_screen_and_the_document_name_the_same_keys` (test_writing.py:503) |
| 10 | PROVADO | `rendering.py:264` | `test_the_three_way_identity_of_a_graft_holds_in_machine_scope` (test_writing.py:1534) |
| 11 | PROVADO | `cli.py:591` | `test_a_line_that_mixes_a_skill_and_a_server_writes_both` (test_cli.py:1240) |
| 12 | PARCIAL | `cli.py:529,591` | vírgula: `test_two_servers_on_one_line_both_reach_the_same_document` (test_writing.py:736); **flag repetida sem teste próprio de `--mcp`** (executada e funciona) |
| 13 | PROVADO | `planning.py:981` | `test_the_graft_class_lands_in_a_document_and_the_planner_says_which_key` (test_planning.py:65) |
| 14 | PARCIAL | `grafting.py:424` | byte-a-byte provado (test_writing.py:544); **quebra com comentário de fim de linha** → achado |
| 15 | PROVADO | `grafting.py:305` | `test_a_server_of_the_same_name_is_overwritten_without_asking` (test_writing.py:569) |
| 16 | PROVADO | `planning.py:981` | `test_the_plan_the_screen_and_the_document_name_the_same_keys` (test_writing.py:503) |
| 17 | PROVADO | `writing.py` | `test_grafting_the_same_server_twice_writes_again_and_exits_zero` (test_writing.py:598) |
| 18 | PROVADO | `grafting.py:411` | `test_a_comment_in_the_vscode_document_survives_both_grafts` (test_writing.py:966) |
| 19 | PROVADO | `grafting.py:281` | `test_the_rest_of_the_document_arrives_byte_for_byte` (test_writing.py:544) |

### Instalar um MCP caseiro (20–35)

| nº | classificação | onde | prova |
| --- | --- | --- | --- |
| 20 | PROVADO | `remote.py:636` | `test_a_remote_search_reads_an_mcp_recipe_the_way_the_embedded_walk_does` (test_remote.py:558) |
| 21 | PROVADO | `remote.py:656` | idem (test_remote.py:558) |
| 22 | PROVADO | `remote.py:595` | `test_the_three_depths_of_url_install_the_same_mcp_recipe` (test_cli.py:2388) |
| 23 | PROVADO | `remote.py:304` | `test_branch_tag_and_a_full_sha_all_reach_the_same_tree` (test_remote.py:162) |
| 24 | PARCIAL | `remote.py:397` | fallback provado com skill (test_remote.py:278/230); **a composição fallback × MCP não é asseverada** |
| 25 | PROVADO | `rendering.py:286`, `planning.py:970` | `test_a_sourced_recipe_clones_to_the_machine_and_resolves_the_token` (test_cli.py:1276) |
| 26 | PROVADO | `planning.py:981` | `test_a_sourced_recipe_costs_a_clone_landing_alongside_its_graft` (test_planning.py:638) |
| 27 | PROVADO | `remote.py:355` | `test_reinstalling_a_sourced_recipe_re_clones_without_force` (test_cli.py:1374) |
| 28 | PROVADO | `planning.py:391` | `test_a_sourced_recipe_in_project_scope_is_refused_naming_the_fix` (test_cli.py:1306) |
| 29 | PROVADO | `planning.py:408` | idem (test_cli.py:1306) |
| 30 | PROVADO | `planning.py:727` (`shutil.which`); nenhum `subprocess` fora de `remote.py` | `test_a_malicious_precondition_value_is_never_executed` (test_cli.py:1786) |
| 31 | PROVADO | `recipes.py:697` | `test_a_precondition_is_read_as_a_check_and_a_value` (test_recipes.py:608) |
| 32 | PROVADO | `planning.py:697` | `test_a_failed_precondition_refuses_before_the_first_byte_naming_it` (test_cli.py:1626) |
| 33 | PROVADO | `cli.py:871` | `test_the_plan_prints_the_recipes_prose_instructions` (test_cli.py:1740) |
| 34 | PROVADO | `remote.py:650` | `test_an_mcp_recipe_that_is_not_found_remotely_exits_three…` (test_cli.py:2407) + `test_a_search_that_finds_nothing_does_not_fall_back` (:2427) |
| 35 | PROVADO | `remote.py:405` | `test_an_obtention_that_fails_on_both_paths_exits_one_carrying_the_transport_error` (test_cli.py:2459) |

### Segredo (36–43)

| nº | classificação | onde | prova |
| --- | --- | --- | --- |
| 36 | PROVADO | `rendering.py:429-455` | `test_a_slot_is_a_reference_and_never_the_value_behind_it` (test_rendering.py:343) + `:688` + `:706` |
| 37 | PROVADO | `rendering.py:498` | `test_an_env_slot_renders_as_the_reference_this_target_expands` (:228) |
| 38 | PROVADO | `rendering.py:586,290` | `test_a_slot_adds_the_input_that_puts_the_secret_in_the_operating_system_vault` (:393) |
| 39 | PROVADO | `rendering.py:613` | `test_a_devin_env_slot_renders_the_third_spelling_of_the_trio` (:578) |
| 40 | PROVADO | `recipes.py` + `rendering.py:498/586/613` | `test_no_role_ever_renders_a_default` (:320) — cobre 3 papéis × **1** alvo |
| 41 | PROVADO | `cli.py:886` | `test_a_slot_whose_variable_is_not_set_warns_and_still_exits_zero` (test_cli.py:1518) |
| 42 | PROVADO | `rendering.py:150,466` | `test_a_bearer_slot_assembles_the_authorization_header_out_of_the_role` (:263) |
| 43 | PROVADO | `rendering.py:429-448` | `test_a_literal_and_a_slot_share_the_environment_table_without_mixing` (:244) |

### Escopo e runtime (44–51)

| nº | classificação | onde | prova |
| --- | --- | --- | --- |
| 44 | PROVADO | `scope.py` + `cli.py` | `test_inside_a_git_repository_no_flag_lands_in_the_project` (test_cli.py:1816) |
| 45 | PROVADO | `cli.py` | `test_outside_a_git_repository_a_graft_exits_two_as_well` (test_cli.py:1852) |
| 46 | PROVADO | `planning.py` + `screens.py` | `test_the_graft_class_lands_in_a_document_and_the_planner_says_which_key` (test_planning.py:65) |
| 47 | **SEM-PROVA** | `planning.py:459,859` | — (comportamento correto, medido: exit 3, nada escrito) |
| 48 | **SUPERSEDIDA** | `planning.py:467-477`, `cli.py:955` | revisada por #100; ADR 0017:36 § Emenda. `test_a_runtime_with_no_mcp_document_still_receives_the_skill` (test_planning.py:193) prova o novo contrato |
| 49 | PROVADO | `wizard.py` | `test_mcp_runtime_choices_offer_only_mcp_documents_in_scope…` (test_wizard.py:586) |
| 50 | PROVADO | `wizard.py:304-318` | `test_ask_scope_with_a_sourced_recipe_has_one_answer_and_asks_nothing` (test_wizard.py:279) |
| 51 | PROVADO | `runtimes.py` | `test_a_machine_scope_graft_lands_in_the_personal_file_of_its_target` (test_cli.py:1092) |

### Ativação (52–55)

| nº | classificação | onde | prova |
| --- | --- | --- | --- |
| 52 | PROVADO | `cli.py:936` | `test_installing_an_mcp_warns_that_it_is_born_pending_approval` (test_cli.py:871) |
| 53 | PROVADO | `planning.py:742,835`, `runtimes.py:766` | `test_a_graft_into_vscode_says_nothing_about_approval` (:912) + `:1045` + `:1118` |
| 54 | PROVADO | nenhum caminho de escrita de aprovação | `test_a_machine_graft_touches_nothing_else_in_the_personal_file` (test_cli.py:1155) |
| 55 | PROVADO | `cli.py:936` | `test_installing_an_mcp_warns_that_it_is_born_pending_approval` (`assert code == 0`) |

### `--dry-run` (56–59)

| nº | classificação | onde | prova |
| --- | --- | --- | --- |
| 56 | PROVADO | `cli.py:812` | `test_the_dry_run_of_a_graft_names_the_key_and_writes_nothing` (test_cli.py:1186) |
| 57 | PARCIAL | `cli.py:809-812` | espelho provado para 0, 2 e 3; **exit 1 sem par (dry, real)** |
| 58 | PROVADO | `planning.py` + `remote.py` | `test_a_dry_run_resolves_the_remote_and_still_writes_nothing` (test_cli.py:2481) + `:1337` |
| 59 | PROVADO | `screens.py` | `test_the_dry_run_of_a_graft_names_the_key_and_writes_nothing` (:1186) + `:1563` |

### `doctor` (60–64) — verificado contra `origin/main`

| nº | classificação | onde | prova |
| --- | --- | --- | --- |
| 60 | PROVADO | `inspection.py:224,794` | `test_a_written_mcp_server_claude_code_has_not_approved_exits_three` (test_inspection.py:561) |
| 61 | PROVADO | `inspection.py:232,856` | `test_a_config_pointing_at_a_missing_clone_exits_three` (test_inspection.py:605) |
| 62 | PROVADO | `inspection.py:245,901,285` | `test_a_slot_not_set_in_this_environment_is_a_notice_not_a_failure` (test_inspection.py:628) |
| 63 | PROVADO | `inspection.py:254,925` | `test_a_clone_directory_no_config_references_is_named_and_not_removed` (test_inspection.py:651) |
| 64 | PROVADO | `inspection.py` — nenhuma chamada de remoção | mesmo teste (:651) |

### Recusas e integridade (65–68)

| nº | classificação | onde | prova |
| --- | --- | --- | --- |
| 65 | PARCIAL | `recipes.py` (conjunto fechado) | `test_a_transport_outside_the_closed_set_is_refused_naming_it[sse]/[ws]` (test_recipes.py:112) — **só no leitor, não pela CLI** |
| 66 | PROVADO | `recipes.py` | `test_a_malformed_recipe_names_the_file_and_the_field` (test_recipes.py:282) |
| 67 | PARCIAL | `grafting.py:143` | `test_a_configuration_file_that_is_already_broken_is_refused_and_not_repaired` (test_writing.py:1162) — **3 formas cobertas; vírgula sobrando e chave duplicada escapam** |
| 68 | PROVADO | `errors.py` | 2: test_cli.py:1852 · 3: test_cli.py:2407 · 1: test_cli.py:2459 |

### Contagem

| classificação | quantas | quais |
| --- | --- | --- |
| `PROVADO` | **57** | as demais |
| `PARCIAL` | **7** | 4, 12, 14, 24, 57, 65, 67 |
| `SEM-PROVA` | **1** | 47 |
| `AUSENTE` | **2** | 3, 5 |
| `SUPERSEDIDA` | **1** | 48 (por #100 / ADR 0017 § Emenda) |

Soma: 57 + 7 + 1 + 2 + 1 = **68**.

A história 40 fica `PROVADO` com ressalva: `test_no_role_ever_renders_a_default` cobre os três papéis
contra **um** alvo só (`CLAUDE_PROJECT`). A garantia forte está uma camada antes — `recipes.py` recusa
`default` como campo desconhecido —, então nenhuma receita chega ao renderizador com default para
inventar. Não virou achado.

---

## 6. Refutados — o que a Onda 2 matou

Esta seção é o que faz o resto ser confiável. **Seis achados morreram na verificação adversarial.**
Cada um tinha prova executada e redação plausível; nenhum sobreviveu ao cético.

| id | achado proposto | por que morreu |
| --- | --- | --- |
| **S3-1** | dois slots que diferem só por caixa (`GIT_TOKEN` / `git_token`) colapsam num `input` só no VS Code, e ambos recebem o mesmo segredo | o mecanismo existe, mas **o colapso é desenho declarado**: `docs/agents/domain.md:117` diz que duas receitas querendo `GITHUB_TOKEN` derivam o mesmo `id` e recebem **um** prompt. A invariante que o achado citava (`recipes.py:604-611`) é sobre **header** — case-insensitive por RFC 9110 —, não sobre nome de variável, que `recipes.py:646` preserva verbatim de propósito. Gatilho exige um par que nenhum autor plausível escreve; as três receitas com slot usam SCREAMING_SNAKE uniforme |
| **S2-2** | a história 48 foi revertida em código e o texto da #75 continua afirmando o contrário | **fechado por ADR.** `docs/adr/0017-…:36` traz a emenda literal: *"**Emenda (#100): numa linha mista, a recusa é por runtime, não mais pela linha inteira — e não precisa de recusa nova.**"* Spec estagnada depois de emenda por ADR é o processo funcionando |
| **S5-1** | linha mista cujo MCP não aterrissa em runtime nenhum sai exit 0 com zero servidores escritos | reproduzido (`EXIT=0`, `1 write · 8 files`, `no MCP destination cursor — took the skills, skipped the server`), mas é **o que a ADR decidiu**. A Nota da ADR 0009:69 quantifica por runtime **sem qualificador de cardinalidade**; o caso total é o degenerado do parcial, e a ADR 0017:36 prescreve exatamente o `SkippedClass` nomeado em exit 0, *"nunca em silêncio"* |
| **S5-2** | a recusa de receita federada nomeia um caminho de scratch já apagado | a história 66 pede recusa *"nomeando **o arquivo e o campo**"* — e a mensagem nomeia os dois (`bad-transport.toml`, `transport`) mais o conjunto aceito. Não pede caminho acionável; o autor edita `.overpower/mcp/<slug>.toml` no repositório dele, e esse tail está na mensagem. Prefixo de scratch é ruído, não desinformação |
| **S5-3** | `no recipe named X under owner/repo@ref` é a única recusa da família que não diz o que fazer | **premissa falsa**: `remote.py:189` (o irmão de skill, já shipado) tem forma idêntica e igualmente sem conserto. A história 29 é textualmente escopada ao caso *receita com fonte → escopo de projeto*; quem governa aqui é a 34, que pede só exit 3 e fallback que não roda. A assimetria com `AmbiguousRemoteRecipeError` é principiada — lá há candidatos a listar, aqui não há ação |
| **S9-3** | `domain.md:123` diz *"a evidência desta linha é doc do fornecedor, não medição"* e aponta para fontes que hoje dizem o contrário | `domain.md:123` é entrada **datada** de um chronicle **append-only**, cuja convenção o próprio arquivo demonstra na linha 119: supersede-se com entrada nova, não se reescreve a antiga. Como registro do que a #80 estabeleceu, a frase é história correta. O resíduo (não existe entrada de #87 no arquivo) é a **mesma causa raiz** do S9-2, não um segundo achado |

Além destes, **um fantasma meu**, morto antes de virar achado: os 4 testes que falham sob um
`--basetemp` longo (`assert '.mcp.json' in '╭─ error …'`) pareciam recusa que não nomeia o arquivo.
Reproduzido na porta da frente com caminho de projeto profundo, o produto **nomeia o arquivo**
corretamente. É o teste assertando substring contra painel Rich reembrulhado, não defeito de produto.

E **três fantasmas de ambiente** que quase viraram achado em subagentes diferentes, registrados
para quem repetir esta auditoria nesta máquina:

- `/tmp/.git` faz `/tmp` ser detectado como repositório e derruba 4 testes de escopo.
- `FORCE_COLOR=3` está no ambiente e faz o Rich emitir ANSI **sob pipe** — qualquer medição de
  "zero ANSI" precisa limpar `FORCE_COLOR`/`CLICOLOR_FORCE` do env do subprocesso antes.
- `uv run --directory <audit>` muda o cwd, e o `install` passa a escrever **dentro** do checkout
  auditado. Use `--project` quando o comando escreve.

---

## 7. Dúvidas abertas

O que não deu para executar, e o que faltou para executar.

| # | dúvida | o que faltou |
| --- | --- | --- |
| 1 | **`${env:VAR}` expande em `command`/`args` no Devin?** É a terceira dúvida da #87, que ficou aberta. O renderizador assume que sim, e `rendering.py:597-606` **declara** que não foi medido — a redação está correta, não é achado | uma conta real de Devin: o portão para o *uso* do servidor (spawn do processo) fica atrás de login obrigatório |
| 2 | **A metade de sucesso da história 24.** Provei que o caminho `git` e o fallback puro-Python obtêm a mesma árvore e concordam na **recusa** (mensagem byte a byte igual), não que escrevem o **mesmo enxerto** | um repositório público com `.overpower/mcp/<slug>.toml` para apontar, ou permissão para publicar um de fixture |
| 3 | **`${...}` dentro de um literal de `[server.env]` deveria ser recusado pelo leitor?** Medido: é aceito e chega literal aos três alvos — o que **reintroduz** a armadilha `${VAR:-default}` se alguém editar a receita. Não virou achado por falta de texto normativo: a #75 linha 190 diz que `[server.env]` é "o que ele escreve porque pode", e a linha 196 diz que o overpower não policia receita federada | uma decisão do dono. O conserto barato é o teste **P-2**, que pinaria as 4 receitas embutidas |
| 4 | **`url = "not a url at all"` sob `transport = "http"`** é aceito e renderizado literal | uma linha da #75 que exija validar a forma da URL — não existe |
| 5 | **Slot com espaço no nome** (`name = "SRV TOKEN"`) é aceito e renderiza `"SRV TOKEN": "${SRV TOKEN}"`. Suspeita: o Claude Code não expande nome com espaço, o que seria a mesma classe do S10-1 | medir o binário do Claude Code |
| 6 | ~~**`0 artifacts · 0 places` num repo que só tem MCP.**~~ **Fechada em 2026-08-19.** `Diagnosis` ganhou o campo `grafted`, gêmeo de `landed` para a classe de enxerto, e a contagem virou soma das duas classes — contadas **à parte e somadas**, nunca unidas num conjunto, porque o pool namespaceia por tipo e uma skill e um servidor podem dividir o nome | a decisão saiu por **consistência**, não por gosto: `_landed_in` também não tem procedência — conta toda árvore num caminho de runtime, inclusive uma que o usuário fez à mão —, então excluir o enxerto aplicava a uma classe uma regra que a outra nunca teve |
| 7 | ~~**A #75 continua dizendo o oposto do que o #100 decidiu** (história 48).~~ **Fechada em 2026-08-19**: a história 48 no corpo da #75 recebeu a emenda, com ponteiro para o [#100](https://github.com/ThiagoPanini/overpower/issues/100) e para a ADR 0017 | — |
| 8 | **Concorrência: dois `overpower install` no mesmo documento ao mesmo tempo.** É o único eixo que a auditoria nomeou e não abriu — nenhum dos cinco críticos o executou. A pergunta: um perde o enxerto do outro em silêncio? | tempo. O eixo é montável (dois processos, um `.mcp.json`), só não coube |
| 9 | ~~**`.mcp.json` de 0 bytes recusa em exit 3**~~ (*"Expecting value…"*), enquanto o arquivo **ausente** é criado em exit 0. **Fechada em 2026-08-19**: a assimetria fica — tudo que existe é do usuário —, e a mensagem parou de emprestar as palavras do parser. `_refuse_unless_strict` nomeia o documento vazio e o de só espaço em branco **antes** de chamar o leitor | a redação escolhida separa *vazio* de *só espaço em branco* porque `json` responde a mesma frase para os dois, e para o arquivo de só comentário também — a linha única que o usuário recebia não distinguia três casos |

**A dúvida 2 destravou sem ninguém ir atrás dela.** O que faltava era *"um repositório público com
`.overpower/mcp/<slug>.toml` para apontar, ou permissão para publicar um de fixture"* — e o
[#134](https://github.com/ThiagoPanini/overpower/issues/134) construiu exatamente esse fixture ao
entregar a vitrine remota (`git_remote.mcp_recipe_files`, em `tests/test_remote.py`). A dúvida
deixou de ser uma decisão do dono e virou um teste: passar o mesmo conteúdo pelos dois caminhos de
obtenção e comparar o **enxerto escrito**, não só a recusa. Segue aberta porque ninguém a escreveu.

### Sobre o critério de parada

As 68 histórias estão classificadas, os sete portões rodaram, e **todo** achado **B**/**D** passou
por verificação adversarial — 12 refutadores, dos quais 6 mataram o achado que examinavam.

Foram **cinco** passadas de crítico de cobertura: a 1ª nomeou 3 lacunas mais o portão P1/P2/P3 que
ninguém tinha rodado; a 2ª nomeou 1 (`C2-1`); a 3ª nomeou 1 (`C3-01`); a **4ª e a 5ª voltaram
limpas**, que é o par de passadas vazias que o critério exige. A 5ª escolheu o próprio território
e fechou dois eixos que ninguém tinha aberto:

- **Determinismo** — sob 4 valores de `PYTHONHASHSEED` (`0`, `1`, `12345`, `random`), `.mcp.json` e
  `.vscode/mcp.json` produzem **um único digest cada**. A ordem de inserção é a ordem digitada
  (regra 7), e reinstalar com os seletores invertidos preserva os bytes. `github,github` dedupa;
  ` github `, `github,`, `,github` e `github,,cloudflare` normalizam para o mesmo digest;
  `GitHub` recusa em exit 2 nomeando o catálogo.
- **Destino que não é arquivo comum** — `.mcp.json` como **diretório** → exit 1 (`[Errno 21]`),
  conteúdo intacto; **somente-leitura** → exit 1, `wrote 0 of 1`; **symlink pendurado** → exit 1,
  nada criado fora do repo; **symlink válido** → o enxerto atravessa e preserva o link. E os seis
  quase-vazios concordam entre si: `0 bytes`, só whitespace, só comentário, `null`, `[]`, `"hi"` →
  todos exit 3 com o arquivo **byte-idêntico** depois; `{}` e BOM+`{}` → exit 0, BOM preservado.

---

## 8. Recomendação

Os 29 achados cortam em três fatias, cada uma com 2–3 tickets de conteúdo e um único arquivo de
gravidade — não em 29 tarefas soltas:

**Fatia A — a inserção fecha as bordas** · `S4-1` + `S1-4` + `S4-2`, todas em `grafting.py`.
Chave duplicada, comentário de fim de linha, vírgula sobrando. ~19 linhas de produto e 3 casos
novos nas parametrizações que já existem (`BROKEN`, `OCCUPIED`).

**Fatia B — *Descobrir* entrega o que prometeu** · `S1-1` + `S1-2` + `S0-1`.
As duas únicas histórias `AUSENTE` da spec, mais as receitas declarando o ferramental que exigem.
~18 linhas em `screens.py`, 6 de TOML, 1 fixture e 2 testes.

**Fatia C — os dois contadores reconciliam com o documento** · `S4-3` + `C2-1`.
Mesma raiz de forma: ambos calculados por seleção e nunca reconciliados contra o caminho.
7 linhas entre `planning.py` e `writing.py`.

> ### Recomendação: a **Fatia A** primeiro.
>
> É a única fatia em que o produto **escreve um desfecho errado com exit 0** — a classe que a
> própria spec nomeia como a pior (*"escrever metade seria a classe **sucesso com conteúdo
> errado**"*, história 48). Nas outras duas o usuário **vê** o problema: na B a informação
> simplesmente não está na tela, na C é um número errado num relatório. Na A o usuário lê `Done!`,
> lê o plano nomeando `.mcp.json › mcpServers.cloudflare`, e o runtime lê outra coisa — ou não lê
> nada. É exatamente o falso positivo que a #75 diz que este produto existe para não cometer.
>
> E ela é a mais barata de provar, porque **a rede já está desenhada**: a segunda metade da
> identidade de três vias (`tests/test_writing.py:538`, *"nenhuma chave que ele não nomeou
> apareceu"*) é literalmente a asserção que pega os três casos. Falta plantar os documentos de
> entrada — um com chave duplicada, um com comentário de fim de linha, um com vírgula sobrando —
> nas parametrizações que já rodam nas 9 células.

Depois de A, a ordem natural é **B** (entrega o que falta da spec, e é o que um usuário novo
encontra primeiro) e então **C** (cosmético, mas o contrato está escrito no próprio docstring).

As 11 provas ausentes (**P-1** … **P-11**) não pedem ticket próprio: cada uma é um teste, e elas
caem junto das fatias que tocam o mesmo módulo. As duas que valem sozinhas são **P-2** (as 4
receitas embutidas nunca são renderizadas por teste nenhum — e é a rede que pegaria a dúvida
aberta nº 3) e **P-1** (a primeira linha da tabela de exit 3 não tem teste: apagar o
`elif carries_mcp` de `planning.py:615-616` deixa a suíte inteira verde).
