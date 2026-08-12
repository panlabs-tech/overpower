# Doutrina de teste

Que forma tem um teste neste repo — o que é substituído por dublê, o que roda de verdade, e como a saída visual é asseverada sem que todo ajuste estético quebre teste.

Decidido em [Doutrina de teste](https://github.com/panlabs-tech/overpower/issues/30). O que **não** se decide aqui, porque já estava travado: **onde** o teste roda — `static` (ubuntu, um Python) + `test` (**3 SOs × 3 versões**) + `gate` —, `pytest` bloqueante, e o corte local × CI, todos do [#24](https://github.com/panlabs-tech/overpower/issues/24); e `pytest 9` com `strict = true`, do [#2](https://github.com/panlabs-tech/overpower/issues/2).

## Resumo executável

| pergunta | resposta |
| --- | --- |
| dublê de filesystem | **não existe** — `tmp_path`, sempre ([ADR 0010](../adr/0010-nao-existe-duble-de-sistema-de-arquivos.md)) |
| `git` do `--from` | **subprocesso real, remoto local** em `tmp_path` |
| GitHub de verdade | **fora de todo portão**; ato de curadoria, `OVERPOWER_NETWORK_TESTS=1` |
| plano × tela × disco | uma asserção só, a **identidade de três vias**, nas 9 células |
| saída visual | **estrutura no portão**; snapshot **por tela**, sem cor, a 80 e 60 |
| seleção interativa | seam é **stub**; um teste de PTY prova a fiação, só em POSIX |
| cobertura | diagnóstico efêmero, **nada** no `pyproject.toml` |
| divergências da régua | **nenhuma** — ver a seção seguinte |

## A régua, posição por posição

A régua é o `panlabs-python-standards`, `references/05-doutrina-de-testes.md`. Pela nota do mapa, onde ela e uma decisão do mapa divergirem **vence o mapa e a divergência vira ADR**. Procurei divergência nas oito posições e **não achei nenhuma** — em todos os casos onde a resposta daqui parece contrariar a régua, é a **condição declarada da própria régua** que a redireciona. A afirmação é falsificável e está aberta: quem achar uma divergência real escreve a ADR.

| § | posição da régua | aqui |
| --- | --- | --- |
| 1 | pirâmide, fake de port no use-case | **inverte-se pela condição (i)**: não há port de filesystem, e a própria régua manda testar contra o real quando falta. [ADR 0010](../adr/0010-nao-existe-duble-de-sistema-de-arquivos.md) |
| 2 | gate de infra + trava anti-skip | **redireciona**: a condição é *serviço que o dev sobe à mão*. O disco não é serviço; a rede é, e a rede não entra em portão |
| 3 | forma do contract test | **vazia por falta de sujeito** — não há fake de port |
| 4 | escopo do contract test | **aplicada, e o resultado é zero**: a obrigação atrela-se a *fake com adapter real executável no gate*, e não existe nenhum. O seam do wizard é **stub**, que a régua exclui por nome |
| 5 | espelho de `src/` + três casas por papel | **aplicada**; das três casas só `tests/support/` se ocupa |
| 6 | `test_<cenario>_<esperado>`, AAA, `parametrize` com `ids` | **aplicada como escrita** |
| 7 | cobertura sem threshold, efêmera | **aplicada como escrita** |
| 8 | async e relógio | **inerte** — não há async e não há leitura de relógio no produto |

Duas dessas linhas são as que um leitor apressado leria como omissão, e por isso ficam declaradas em voz alta: **não há `tests/fakes.py` e não há `tests/contracts/`**, e a razão é a condição literal da §4 — contract test é obrigatório para *"fake de port com adapter real executável sob o gate"*, e este repo não tem nenhum.

## 1. O disco é real

`tmp_path`, sempre. Sem `FakeFileSystem`, sem port, sem `mock_open`, sem gate de ambiente em teste de escrita. O argumento inteiro está na [ADR 0010](../adr/0010-nao-existe-duble-de-sistema-de-arquivos.md); em uma linha: as **três armadilhas obrigatórias** do mapa são comportamento de filesystem real, e um dublê que não implemente symlink e junction de verdade fica verde exatamente onde o produto quebra.

As três, que todo caminho de escrita tem de exercitar:

```python
def test_removing_a_symlinked_destination_does_not_write_through_it(tmp_path: Path) -> None:
    """#9: rmtree(ignore_errors=True) over a symlink removes nothing, silently,
    and the copytree that follows corrupts whatever the link pointed at."""

def test_removing_a_junction_uses_the_predicate_that_recognises_it(tmp_path: Path) -> None:
    """#19: os.path.islink() is False for a junction and shutil.rmtree() refuses
    it anyway. Windows only — sys.platform is the key, never an env var."""

def test_installing_over_a_previous_version_leaves_no_stale_file(tmp_path: Path) -> None:
    """#9: dirs_exist_ok=True overlays without syncing, so yesterday's file
    survives and reads as installed."""
```

O terceiro caso é o que **prende a semântica de escrita à identidade de três vias** (§5 abaixo): se o disco tem de ser igual ao plano, o destino de uma escrita planejada tem de ficar **igual à origem**, não sobreposto a ela. Como satisfazer isso é implementação — o [#9](https://github.com/panlabs-tech/overpower/issues/9) já tinha nomeado a armadilha sem escolher o conserto —, mas a asserção não admite sobreposição.

## 2. Uma suíte só, e ela roda inteira nas 9 células

Não existe categoria *"roda numa célula só"*, e não existe marcador `slow`. O [#24](https://github.com/panlabs-tech/overpower/issues/24) mediu **7–13 s de overhead fixo por job** contra uma bateria de **~2 s**: dividir a suíte não compra tempo, e o que se testa — disco — é justamente o que diverge entre as 9 células.

Teste que não pode rodar numa plataforma **chaveia por `sys.platform`**, nunca por variável de ambiente. A preocupação da régua (§2) é que a exigência suma do workflow e o CI fique verde skipando tudo; `sys.platform` não pode ser esquecido no YAML.

Três ausências ficam registradas como **conhecidas**, não como cobertura:

- o caso **sem privilégio de symlink** no Windows não é reproduzível na CI hospedada — o `actions/runner-images` liga **Developer Mode** e põe o usuário em `Administrators` ([#19](https://github.com/panlabs-tech/overpower/issues/19)). A máquina do dev é o único lugar onde ele aparece;
- **PyPy não tem `CreateJunction`**, e não está na matriz;
- **construir uma pergunta do `questionary` não roda nas células Windows.** Medido em [#57](https://github.com/panlabs-tech/overpower/issues/57): a construção monta um `Application` do `prompt_toolkit`, e a saída Win32 dele levanta `NoConsoleScreenBufferError` num processo sem console screen buffer — que é o que um filho do `pytest` no runner hospedado é. Um terminal Windows de verdade tem o buffer, então o caminho do produto não é afetado; o que fica sem cobertura ali é a asserção de que a biblioteca aceita os argumentos que o wizard passa.

## 3. `git` roda de verdade, e o remoto é local

O [#25](https://github.com/panlabs-tech/overpower/issues/25) fixou o primário como `init` + `remote add` + `fetch --depth 1 origin <ref>` + `checkout FETCH_HEAD`, e o fallback como tarball anônimo do `codeload`. Isso é **subprocesso e rede**. O corte separa os dois: **o subprocesso roda; a rede não.**

Medido para esta decisão, com um repositório local fazendo de remoto:

| ref pedido | rc | resultado |
| --- | --- | --- |
| branch (`main`) | 0 | 1 `SKILL.md` encontrado |
| tag (`v1.0.0`) | 0 | 1 `SKILL.md` encontrado |
| **SHA completo** | 0 | 1 `SKILL.md` encontrado |
| ref inexistente | **128** | `fatal: couldn't find remote ref nope` |
| remoto inexistente | **128** | `fatal: … does not appear to be a git repository` |

Três coisas saem daí. O caminho **branch/tag/SHA** — o discriminador que fez o `init`+`fetch` vencer o `clone --branch`, que falha em SHA — é exercitável **sem rede**. A string `couldn't find remote ref`, que o #25 mediu contra o GitHub, sai **idêntica** contra um remoto local. E o argv, o `checkout`, o `exit=128` e a guarda **`LC_ALL=C`** são todos reais.

**O limite honesto**, porque um remoto local não o cobre: buscar um SHA arbitrário depende de o **servidor** permitir (`uploadpack.allowAnySHA1InWant`), e isso o #25 mediu contra o GitHub, não este teste.

**A falha de credencial não precisa da rede, porque não é lógica.** `could not read Username` exige HTTPS autenticado de verdade — mas o #25 fixou que o fallback dispara em **falha de obtenção**, uma classe só; o overpower não ramifica por string, só a **reporta**. Logo o texto é conteúdo de mensagem, e a asserção que importa é de **passagem** — que o stderr do subprocesso chega ao usuário —, com stub.

O que é dublê e o que é real no caminho de `--from`:

| camada | dublê | onde |
| --- | --- | --- |
| decidir cair no fallback | **stub** do obtentor, devolvendo o desfecho | portão |
| `git` primário | **nenhum** — subprocesso real, remoto local em `tmp_path` | portão, 9 células |
| descompressão do fallback | **nenhum** — `tarfile` real sobre `.tar.gz` montado em `tmp_path` | portão |
| HTTP do fallback | **stub** de `urlopen` (200, 404, timeout) | portão |
| busca do `SKILL.md` | **nenhum** — `os.walk` sobre `tmp_path` | portão, 9 células |
| GitHub | **nenhum**, e **fora do portão** | curadoria |

A asserção que o #25 comprou com uma medição, e que é a mais importante deste bloco:

```python
def test_a_search_that_finds_nothing_does_not_fall_back() -> None:
    """#25 measured this as a live bug: the fallback ran for "the skill is not
    there", re-fetched the whole repository and returned the same answer.

    Obtention failure -> fallback, then exit 1 if it also fails.
    Obtained, searched, not found -> exit 3, and the fallback is never called.
    """
```

## 4. Rede nunca entra em portão

Esta é a **quarta ocorrência da mesma classe**, e a regra já estava escrita: o [#11](https://github.com/panlabs-tech/overpower/issues/11) recusou o P3 por pôr rede num CI que o [#3](https://github.com/panlabs-tech/overpower/issues/3) mediu instável; o [#19](https://github.com/panlabs-tech/overpower/issues/19) rebaixou o job `windows-latest` a verificação de release; o [#24](https://github.com/panlabs-tech/overpower/issues/24) recusou o portão de frescura da tabela e generalizou — **portão bloqueia o que este repo controla; o que depende de terceiro é ato de curadoria, não automação.** O GitHub é terceiro.

Então o teste ponta a ponta contra o `mattpocock/skills` real **existe**, é comando documentado, e **não roda em job nenhum** — nem no PR, nem no release. Ele é passo de curadoria, ao lado do refresh do conteúdo.

E aqui a §2 da régua entra inteira, com o sujeito trocado: quando o dev **liga** a exigência, skip vira falha.

```python
# tests/support/gates.py
_REQUIRE = os.getenv("OVERPOWER_NETWORK_TESTS") == "1"

needs_network = pytest.mark.skipif(
    not _REQUIRE,
    reason="talks to GitHub: set OVERPOWER_NETWORK_TESTS=1 (curation step, never a gate)",
)
```

Com a variável ligada a condição de skip não pode mais ser satisfeita — um teste de rede renomeado ou perdido vira vermelho em vez de sumir em silêncio. A chave é **própria e nomeada por cenário**, jamais a `CI` genérica, que todo runner seta.

## 5. A identidade de três vias

O [#18](https://github.com/panlabs-tech/overpower/issues/18) mediu **três** comandos do `npx skills` anunciando um conjunto de caminhos e escrevendo outro, sempre com `exit 0`. Isso sobe a exigência do [#8](https://github.com/panlabs-tech/overpower/issues/8) — que era o `--dry-run` espelhar o **exit code** — para espelhar o **conteúdo**. A asserção que prova as três de uma vez é uma só:

> **`caminhos(stdout do --dry-run)` == `caminhos(stdout da execução real)` == `walk(disco)`**

```python
def test_the_plan_the_screen_and_the_disk_name_the_same_paths(tmp_path: Path) -> None:
    dry = run(request, root=tmp_path / "dry", dry_run=True)
    real = run(request, root=tmp_path / "real", dry_run=False)

    assert paths_in(dry.stdout) == paths_in(real.stdout)
    assert paths_in(real.stdout) == walk(tmp_path / "real")
    assert not any((tmp_path / "dry").iterdir())          # dry-run wrote nothing
    assert dry.exit_code == real.exit_code                # #8, still
```

**Roda nas 9 células.** É a propriedade com maior chance de quebrar por plataforma — separador de caminho (a tabela guarda `/` e o disco não), `Path` × `PurePosixPath`, sistema de arquivos que não distingue maiúscula —, e é justamente o tipo de bug que passa verde numa célula só.

A identidade também **manda no desenho**, não só no teste: o escritor consome **o plano e nada além dele**. Um escritor que recalcula caminho pode divergir da tela por construção, e nenhum teste fecha isso depois.

## 6. Saída visual: estrutura no portão, snapshot por tela

O [#12](https://github.com/panlabs-tech/overpower/issues/12) mediu que **cor não quebra teste e layout quebra** — numa suíte de 9, trocar a cor da marca quebrou **zero**, porque o snapshot congelava layout e não cor. A variante F, porém, tem moldura, identação e **reembrulho por largura**, e largura é entrada. Três medições contra as capturas reais do protótipo decidiram a forma.

**Medição 1 — o tamanho do estrago.** Quantas linhas de um snapshot gravado mudariam num ajuste estético real:

| mudança | 80 col | 60 col |
| --- | --- | --- |
| os **quatro** ajustes da rodada 2 do #12 (borda fina, respiro, cor do nome, identação) — variante D → F | **49%** | **52%** |
| **uma** tela redesenhada — variante E → F, que diferem só no `list` | **17%** | — |

Meio snapshot mudado é um diff que ninguém lê, e pior: uma regressão não intencional viajando dentro dos 49% é **invisível**. Mas o número cai para 17% quando a mudança é localizada — e é aí que está o conserto. **O problema é de granularidade, não de snapshot.** Com **um arquivo por tela**, a reforma da rodada 2 teria tocado 4 arquivos e deixado os outros em **0%**, e o revisor veria exatamente que telas o ajuste tinha licença para mexer. Snapshot de sessão inteira é borrão; snapshot por tela é verificação de escopo.

**Medição 2 — o que é ANSI nas capturas.** Nas capturas de 80 e 60 colunas, as **únicas** sequências ANSI presentes são **2 linhas** de controle de cursor do `Progress` transiente — `ESC[?25l`, `ESC[2K`, `ESC[1A`, `ESC[?25h`. Nenhuma de cor. Duas consequências: layout está inteiro sem cor nenhuma (é o que reproduz a propriedade que o #12 mediu), e um snapshot do **fluxo de bytes** grava a **animação**, não a tela — `ESC[1A` mais `ESC[2K` significam que o resultado final tem uma linha onde a captura tem duas. Snapshot é da **tela renderizada** (`Console(record=True).export_text()`), nunca do stdout bruto.

**Medição 3 — sob pipe não há ANSI nenhum.** As três capturas `piped` (117, 114 e 134 linhas) têm **zero** bytes `ESC`. A cidadania de terminal já é observável; ela vira asserção estrutural, não snapshot.

Daí a divisão de trabalho:

**No portão, estrutura.** São as propriedades que carregam significado e não podem regredir, e nenhuma delas quebra num ajuste de borda:

```python
def test_piped_output_carries_no_ansi() -> None: ...
def test_the_banner_is_suppressed_without_a_tty() -> None: ...
def test_no_description_is_truncated_at_eighty_or_sixty_columns() -> None: ...
def test_no_rendered_line_exceeds_the_terminal_width() -> None: ...
def test_every_planned_path_appears_in_the_rendered_plan() -> None: ...
def test_the_section_title_is_not_dim(): ...  # #12: rich composes border_style into the title
```

A de truncagem é a que o #12 usou para separar F de E — **0 truncagens a 60 colunas contra 2** —, e ela é computável: nenhuma linha renderizada termina em `…`, e cada descrição do catálogo aparece **inteira** depois de juntar o reembrulho.

**Fora do portão como bytes, snapshot.** Um arquivo por tela, a **80 e 60 colunas**, **sem cor**, da tela renderizada. Cor é asseverada por estrutura, nunca gravada — gravá-la desfaz a propriedade que o #12 mediu. O comparador é caseiro, ~15 linhas em `tests/support/snapshots.py`, com atualização por opção explícita:

```
uv run pytest --snapshot-update tests/test_screens.py
```

Nada de plugin: uma dev-dep a menos, e o caminho de atualização fica explícito em vez de reflexo.

~~**A tela do `questionary` não é nossa para gravar.** O #12 mediu que as telas de seleção saem **idênticas em todas as variantes**, porque o `questionary` é dono daquela tela inteira. Snapshot dela grava o desenho de terceiro.~~

> **Revisto pelo [#65](https://github.com/panlabs-tech/overpower/issues/65).** A premissa era a posse, e ela mudou: o wizard substitui `questionary.prompts.common.create_inquirer_layout`, então o bloco travado, o viewport, o contador e o rodapé são desenho **nosso**. O que continua não sendo nosso são as linhas de escolha, que o `InquirerControl` desenha — e elas continuam sem snapshot.
>
> O que entrou não foi snapshot, e a razão é uma medida: **o fluxo de bytes não distingue *escrito* de *visível*.** O layout antigo escrevia as 57 linhas da lista e deixava o terminal rolar 56 delas, então uma gravação de bytes teria passado verde sobre o defeito que o #65 existe para consertar — 1 linha selecionável numa tela de 24. A guarda é portanto **aritmética**: pergunta + bloco estático + viewport + contador + rodapé tem de caber em 24 linhas, e o viewport não pode cair abaixo das 8 do `npx skills`. Roda nas 9 células, porque não precisa de terminal.
>
> Ao lado dela, **um** teste de PTY assevera que trilho, bloco, contador e rodapé chegam a um terminal real — provando que a substituição do layout pegou, e declarando que não assevera visibilidade. É a mesma divisão da §7: o PTY prova a fiação, nunca os pixels.

## 7. O seam do wizard é stub, e por isso não deve contract test

O que o wizard entrega ao resto do programa é um **pedido** — artefatos, escopo, runtimes. Os testes de fluxo injetam esse pedido por um seam fino; a lógica de seleção é testada sobre valores, não sobre teclas.

Alguém vai perguntar se o seam deve contract test, porque a §4 da régua o exige para *fake de port com adapter real executável sob o gate* — e o real (`questionary` sob PTY) **é** executável. A resposta é não, e sai da taxonomia da própria régua: o seam **não emula o comportamento do `questionary`**, ele **fornece entrada indireta**. É **Stub**, e a §4 exclui Stub por nome — *"um 'contrato do relógio' seria asserção vazia"*.

O que prova a fiação é **um** teste de PTY com teclas enviadas, asseverando o **pedido que sai**, não os pixels — a forma que o #12 já usou. Ele é **POSIX only** (o módulo `pty` não existe no Windows), e essa é uma ausência declarada: no Windows o seam é exercitado, a fiação até o `questionary` não.

## 8. Descoberta: onde mora a asserção do `README.md` solto

A [ADR 0006](../adr/0006-a-arvore-e-o-catalogo.md) trocou catálogo declarado por convenção descoberta, e o [#10](https://github.com/panlabs-tech/overpower/issues/10) mediu o único ponto cego: **`README.md` solto na pasta de tipo vira artefato**.

A asserção mora **no espelho do módulo de descoberta**, sobre uma árvore montada em `tmp_path` — `tests/test_catalog.py`, ao lado dos outros casos de descoberta. Uma só, e ela nomeia o defeito:

```python
def test_a_loose_file_in_the_type_folder_is_not_an_artifact(tmp_path: Path) -> None:
    """#10: the one blind spot of discovery-by-convention. One line of code."""
```

**Não** nasce um segundo teste varrendo o `content/` real atrás de arquivo solto: com o primeiro verde, um `README.md` no repo é inofensivo, e asseverar o repo em vez do código é testar o conteúdo de hoje.

**E a descoberta não duplica P1 e P2.** Que o conteúdo chegue **dentro do wheel** é garantia dos dois portões de git e build do [#11](https://github.com/panlabs-tech/overpower/issues/11) — e não é observável de dentro do `pytest`, que sob layout `src/` importa a árvore de fonte e veria conteúdo que o wheel não tem. `pytest` prova que a descoberta está **certa dada uma árvore**; P1 e P2 provam que a **árvore chega**. Somar um teste que finge cobrir o segundo é falso conforto.

## 9. Forma, nomes e casas

Espelho de `src/`, com `__init__.py` por nível. O repo é **single-context**, então não há nível de contexto:

```
tests/
  __init__.py
  test_runtimes.py          # espelho de src/overpower/runtimes.py
  test_catalog.py
  test_cli.py
  test_screens.py
  support/                  # maquinário: sem sujeito próprio
    __init__.py
    gates.py                # needs_network
    snapshots.py            # comparador + --snapshot-update
    git_remote.py           # monta um remoto local em tmp_path
    screens.py              # renderiza uma tela por Console(record=True)
  snapshots/
    list-framework-80.txt
    list-framework-60.txt
    plan-confirm-80.txt
```

Sem `fakes.py` e sem `contracts/`, pela §4 — e a vacuidade é declarada, não esquecida.

Forma do caso, §6 da régua, integral: nome `test_<cenario>_<esperado>`; corpo AAA separado por linha em branco, com `# given` / `# when` / `# then` **só onde há montagem real**; `parametrize` liberado para variação de dado sobre a **mesma** asserção, **sob a condição de `ids` nomeados** — sem eles o relatório vira `[0]` e a garantia do nome morre. As larguras de tela são o caso canônico:

```python
@pytest.mark.parametrize("width", [pytest.param(80, id="80cols"), pytest.param(60, id="60cols")])
```

O `--strict-markers` é obrigatório e o inventário de marcadores é **fechado** — hoje `network`, e mais nada. Marcador não declarado é erro, não aviso.

## 10. Cobertura

§7 da régua, sem emenda. **Threshold no portão: proibido.** Nada nas dev deps, nada no `pyproject.toml`, nada em workflow, nada de badge. Só um comando documentado, para responder *"o que não tem teste nenhum"* quando alguém perguntar:

```bash
uv run --with pytest-cov pytest --cov=src/overpower --cov-report=term-missing
```

Mutation testing é **gatilho, não adoção**: entra se um bug escapar com a suíte verde, apontado ao código determinístico, nunca no portão.

## O que isto encomenda ao [#14](https://github.com/panlabs-tech/overpower/issues/14)

Lista fechada, e é o insumo de teste da estruturação:

- `tests/__init__.py` e `tests/support/__init__.py`, mais as quatro peças de `support/`;
- `[tool.pytest.ini_options]` com `testpaths`, `--strict-markers`, `--strict-config` e o inventário de marcadores com **um** membro (`network`);
- o `conftest.py` que declara `--snapshot-update`;
- o comando de curadoria com `OVERPOWER_NETWORK_TESTS=1` documentado onde o resto dos comandos morar;
- nada de `pytest-cov`, nada de plugin de snapshot, nada de `freezegun`.

E uma dependência de ordem que o [#24](https://github.com/panlabs-tech/overpower/issues/24) já tinha nomeado, aqui só reafirmada: `pytest` sem nenhum teste sai **5**, e sob ruleset isso é deadlock de merge. Os primeiros testes já estão no `main`.
