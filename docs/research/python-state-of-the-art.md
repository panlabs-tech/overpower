# Estado da arte de biblioteca Python em 2026 — findings e recomendação por eixo

Resolve a [issue #2](https://github.com/panlabs-tech/overpower/issues/2).
Data da pesquisa: **2026-07-30**. Todas as versões, URLs e medições são desta data.

**Regra de evidência deste documento.** Cada afirmação é ou (a) **fonte primária** — doc
oficial do projeto, código-fonte no repo oficial, typeshed, devguide do CPython, PEP — com
URL e data, ou (b) **[medido aqui]** — experimento reproduzível que eu rodei nesta máquina,
com o comando e a saída registrados. Onde não achei fonte primária, está escrito
**não confirmado em fonte primária** em vez de preenchido por inferência. Nenhuma
afirmação vem de blog, tutorial ou resumo de terceiro.

Ambiente das medições: `uv 0.11.7` (x86_64-unknown-linux-gnu), CPython 3.14 gerenciado
pelo uv, `pyright 1.1.411`, `mypy 2.3.0 (compiled: yes)`, `ty 0.0.65`, Linux
6.6.87.2-microsoft-standard-WSL2 (WSL2).

**Escopo estreitado pelo comentário da issue.** Dois eixos do enunciado original saíram
deste ticket porque outras pesquisas já os fixaram, e **não são reabertos aqui**:

- **Backend de build** → `hatchling`, decidido em
  [#3](https://github.com/panlabs-tech/overpower/issues/3), porque o `uv_build` não tem
  `force-include` nem `artifacts` e o overpower precisa de conteúdo vendorizado no wheel.
- **Stack de CLI** → `typer` + `rich` + `questionary`, decidida em
  [#4](https://github.com/panlabs-tech/overpower/issues/4), com pin direto em
  `prompt-toolkit>=3.0.53`.

Eles aparecem aqui só como **restrição** — coisas que outras escolhas precisam respeitar.

---

## 1. Resumo executivo

> Preenchido ao final, quando todos os eixos estiverem escritos.

---

## 2. Mapa: onde está cada resposta

| eixo da issue #2 | recomendação em uma linha | seção |
| --- | --- | --- |
| Layout `src/` × flat | **`src/`**, e não por estilo: é o único que faz o bug de empacotamento falhar no teste do dev | §3 |
| Gerência de projeto com `uv` | **`uv` sozinho fecha env, lock, sync, build e publish**; falta task runner e release | §4 |
| `ruff`: regras que valem × ruído | **`extend-select`, nunca `select`** — em 2026 um `select` explícito *desliga* 160 regras | §5 |
| Tipagem `pyright` × `mypy` × `ty` | §6 |
| `pytest`, plugins, cobertura | §7 |
| Versionamento e trusted publishing | §8 |
| CHANGELOG | §9 |
| Piso de versão do Python | §10 |

---

## 3. Layout: `src/` × flat

### 3.1 Recomendação

**`src/overpower/`. Sem hesitação, e a razão é o axioma 5 do domínio, não estética.**

O overpower **vendoriza conteúdo dentro do wheel** (`docs/agents/domain.md`, axioma 5). A
falha que mais dói nesse desenho é silenciosa: um arquivo de framework que **não entra no
wheel**, com a suíte de testes verde. O layout `src/` é o que transforma essa falha
silenciosa em erro imediato na máquina do dev.

### 3.2 O que a fonte primária diz

O guia da PyPA, [src-layout vs
flat-layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/)
(consultado 2026-07-30), nomeia o mecanismo:

> "the Python interpreter includes the current working directory as the first item on the
> import path. This means that if an import package exists in the current working directory
> with the same name as an installed import package, the variant from the current working
> directory will be used."

E nomeia a consequência exata que interessa ao overpower:

> "subtle misconfiguration of the project's packaging tooling, which could result in files
> not being included in a distribution."

O segundo argumento da página é sobre instalação editável:

> "helps enforce that an editable installation is only able to import files that were meant
> to be importable"

sem o qual o flat layout põe no import path "the other project files (eg: `README.md`,
`tox.ini`) and packaging/tooling configuration files (eg: `setup.py`, `noxfile.py`)",
fazendo "certain imports work in editable installations but not regular installations".

A vantagem declarada do flat, na mesma página, é uma só: **não exige instalar o projeto
para rodar o código**. Essa é a economia real que o `src/` cobra.

**Nota de honestidade:** a página **não declara** qual layout a PyPA recomenda. Ela expõe
os trade-offs e para. Quem diz "a PyPA recomenda `src/`" está inferindo. A recomendação
abaixo é minha, com o experimento como argumento.

### 3.3 O experimento — [medido aqui]

Dois projetos idênticos, mesmo backend (`hatchling`), mesmo pacote com um asset
vendorizado em `assets/catalog.json` lido via `Path(__file__).parent`. Um flat, um `src/`.
Ambos instalados no próprio venv com `uv pip install .`.

**Passo 1 — sem bug nenhum.** Já aqui o sombreamento aparece:

```
### FLAT: rodando a partir da raiz do projeto
  __file__ = .../layout/flat/opdemo/__init__.py            <- a árvore de trabalho
### SRC: rodando a partir da raiz do projeto
  __file__ = .../srclay/.venv/lib/python3.14/site-packages/opdemo2/__init__.py   <- o instalado
```

No flat, **o teste nunca tocou no pacote instalado**. Testou a árvore de trabalho e chamou
isso de verde. No `src/`, o mesmo comando testou o que o usuário vai receber.

**Passo 2 — com um bug de empacotamento real.** Injetei em ambos o erro mais banal do
mundo, o mesmo que a PyPA chama de *"subtle misconfiguration"*:

```toml
[tool.hatch.build.targets.wheel]
exclude = ["**/*.json"]   # o asset vendorizado deixa de entrar no wheel
```

Reinstalei os dois e rodei o mesmo teste, da raiz do projeto:

```
### FLAT + bug de empacotamento, teste rodado da raiz do projeto:
  PASSOU -> {"frameworks": []}

### SRC + bug de empacotamento, teste rodado da raiz do projeto:
  FileNotFoundError: [Errno 2] No such file or directory:
    '.../site-packages/opdemo2/assets/catalog.json'
```

**O flat passou com o wheel quebrado.** O `src/` estourou na hora, na primeira execução,
antes de qualquer CI, antes de qualquer publicação.

Reprodução: `scripts` em `layout/run.sh` e `layout/run2.sh` do scratchpad da pesquisa;
o essencial são as quatro linhas de `pyproject.toml` acima e um `Path(__file__).parent`.

### 3.4 Por que isso é decisivo *para o overpower* e não genericamente

Numa lib de código puro, o bug do passo 2 não existe — não há asset para esquecer, e o
flat layout erra pouco. O overpower é o caso oposto: o **wheel inteiro é conteúdo**. Os
frameworks vendorizados são centenas de arquivos `.md`, `.json` e diretórios de skill,
incluídos por `force-include`/`artifacts` do hatchling — precisamente a maquinaria em que
um glob errado não levanta exceção nenhuma, só produz um wheel menor.

O axioma 5 (`conteúdo vendorizado`) e o layout `src/` são, portanto, a mesma decisão vista
de dois ângulos. Escolher flat aqui é escolher que o modo de falha principal do produto
seja invisível para a suíte de testes.

Há um reforço no achado da pesquisa de empacotamento (#3): o `uvx overpower` **congela a
versão sem TTL** no primeiro uso. Um wheel publicado sem os assets não é só um bug — é um
bug que fica cacheado na máquina de quem instalou.

### 3.5 O custo, dito com todas as letras

1. **O pacote precisa estar instalado para importar.** Não dá para `python -c "import
   overpower"` da raiz do repo sem instalar. Com `uv` isso custa **zero** na prática:
   `uv run pytest` sincroniza e instala o projeto antes de rodar, sem passo manual.
2. **Ferramenta que assume flat precisa de uma linha de config.** `ruff` (via
   `lint.isort.known-first-party` ou `src = ["src"]`), `pytest` (via `pythonpath` ou, melhor,
   confiando no pacote instalado) e o `pyright` (`include = ["src"]`). Uma linha cada.
3. **Um nível a mais de diretório.** Custo cosmético.

### 3.6 Custo de reverter

**Baixíssimo, e assimétrico no tempo.** Hoje é `git mv src/overpower overpower` mais três
linhas de config. Depois de o catálogo de frameworks existir, reverter para flat não custa
mecânica — custa **perder o detector**: a partir daí, todo bug de inclusão de asset volta
a passar verde. A reversão é barata de fazer e cara de ter feito.

### 3.7 Reforço de terceira fonte primária

A doc do **pytest** ([Good Integration
Practices](https://docs.pytest.org/en/stable/explanation/goodpractices.html), consultada
2026-07-30) é mais direta que a da PyPA:

> "Generally, but especially if you use the default import mode `prepend`, it is
> **strongly** suggested to use a `src` layout."

e diz por quê, na mesma linguagem do experimento acima:

> "you want to test the *installed* version of your package, not the local code from the
> repository."

E o **próprio `uv`** concorda por ação: `uv init --lib` gera `src/<pacote>/` — e ainda põe
um `py.typed` no pacote. **[medido aqui]**, `uv 0.11.7`:

```
$ uv init --lib --build-backend hatch libinit
libinit/pyproject.toml
libinit/src/libinit/__init__.py
libinit/src/libinit/py.typed
libinit/.python-version
```

Três fontes primárias independentes (PyPA descreve o mecanismo, pytest recomenda
explicitamente, uv implementa como padrão para `--lib`) e um experimento local. O eixo está
fechado.

---

## 4. Gerência de projeto com `uv`

### 4.1 Recomendação

**`uv` como ferramenta única de ambiente, resolução, sincronização, build e publicação.
Sem `poetry`, sem `pip-tools`, sem `tox`, sem `pyenv`, sem `pipx`.** Backend de build
`hatchling` (fixado em #3). **Sem task runner** — ver §4.4, a decisão é deliberada.

Config mínima recomendada no `pyproject.toml`:

```toml
[tool.uv]
required-version = ">=0.11"      # trava a versão do uv do time e do CI

[dependency-groups]
dev = ["pytest", "pytest-cov", "ruff", "pyright", ...]
```

E `uv.lock` + `.python-version` **commitados**.

### 4.2 O que o `uv` já resolve — e a fonte de cada um

| capacidade | comando | fonte primária |
| --- | --- | --- |
| Layout de lib e marcador de tipos | `uv init --lib` | **[medido aqui]**, `uv 0.11.7` (§3.7) |
| Interpretador do projeto | `uv python pin`, `.python-version` | gerado por `uv init` **[medido aqui]** |
| Lockfile universal | `uv lock` | [Resolution](https://docs.astral.sh/uv/concepts/resolution/) |
| Sincronização exata | `uv sync` | [Locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/) |
| Deps de dev fora do wheel | `[dependency-groups]` (PEP 735) | [Dependencies](https://docs.astral.sh/uv/concepts/projects/dependencies/) |
| Bump de versão | `uv version --bump <x>` | `uv version --help` **[medido aqui]** |
| Build e publicação | `uv build`, `uv publish` | [Packaging](https://docs.astral.sh/uv/guides/package/) |
| Piso de dependência testado | `--resolution lowest-direct` | [Resolution](https://docs.astral.sh/uv/concepts/resolution/) |
| Trava do próprio uv | `[tool.uv] required-version` | [Settings](https://docs.astral.sh/uv/reference/settings/) |

**O lockfile é universal, não da máquina.** A doc diz, literalmente:

> "uv.lock is a *universal* or *cross-platform* lockfile that captures the packages that
> would be installed across all possible Python markers such as operating system,
> architecture, and Python version."

Isso importa muito para o overpower, que precisa ser reproduzível em Linux, macOS e
Windows (o modo de aterrissagem por symlink no Windows tem três degraus — ver #5) sem
manter três lockfiles.

**E deve ser commitado.** A doc, literalmente:

> "This file should be checked into version control, allowing for consistent and
> reproducible installations across machines."

**Mas o lockfile de uma lib não é contrato com o consumidor.** Ele governa o ambiente de
*desenvolvimento e CI*, não o que o `uvx overpower` vai resolver na máquina do usuário —
isso é decidido pelos ranges do `[project.dependencies]`. Corolário prático: **os limites
inferiores das dependências precisam ser testados de propósito**, porque o `uv.lock`
sempre esconde o piso resolvendo para o topo. A doc do uv dá o comando e a
recomendação:

> "it is recommended to separately run tests with `--resolution lowest` or
> `--resolution lowest-direct` in continuous integration to ensure compatibility with the
> declared lower bounds."

**Isso não é teórico aqui.** O #4 fixou `prompt-toolkit>=3.0.53` como pin obrigatório, num
pacote que o `questionary` só pede como `>=2.0,<4.0`. Um job de CI com
`--resolution lowest-direct` é exatamente o que prova que o piso declarado é o piso que
funciona. **Recomendo esse job.**

### 4.3 `[dependency-groups]` × `[project.optional-dependencies]` — a regra é limpa

A doc do uv separa os dois papéis sem ambiguidade:

- `[dependency-groups]` (PEP 735) — dev, teste, lint, docs. São
  "local-only and will *not* be included in the project requirements when published to
  PyPI or other indexes".
- `[project.optional-dependencies]` — extras de verdade, que o consumidor instala com
  `overpower[algo]`. A doc os enquadra como recurso de biblioteca publicada:
  "It is common for projects that are published as libraries to make some features optional
  to reduce the default dependency tree."

**Para o overpower: nenhum extra.** O axioma 1 (**autocontido**) e o axioma 5 (**conteúdo
vendorizado**) dizem que a instalação padrão já é a instalação completa. Um extra seria
uma forma de dizer "esta parte do overpower pode não estar aí", e não há nenhuma parte
assim. Todas as ferramentas vão para `[dependency-groups]`.

Grupos recomendados, e por que mais de um: `dev` (o guarda-chuva do dia a dia, incluído
por padrão — `[tool.uv] default-groups` já é `["dev"]`) e um `typecheck` separado, porque
o `pyright` arrasta Node e é a única dependência de dev que não é puro Python; separá-lo
deixa o job de teste do CI mais magro. `--no-default-groups` e `--group typecheck` dão o
controle fino por job.

### 4.4 Onde ainda falta — e o que fazer sobre isso

**1. Não existe task runner.** A doc de [Running
commands](https://docs.astral.sh/uv/concepts/projects/run/) descreve `uv run <comando>`,
`--with` e scripts com metadata inline. **Não há tarefa nomeada em `pyproject.toml`**, nada
equivalente a `npm scripts`. A doc não nega o recurso — ela simplesmente não o tem
(*não confirmado em fonte primária* que seja uma não-decisão deliberada da Astral).

**Recomendação: não adicionar `just`, `make`, `poe` nem `nox`.** O overpower tem quatro
comandos de verdade — `uv run pytest`, `uv run ruff check`, `uv run ruff format`,
`uv run pyright` — e eles já são a linha do CI. Um task runner aqui adiciona uma
dependência, um arquivo e uma camada de indireção para economizar digitação que o histórico
do shell já economiza. Se um dia forem doze comandos, `just` é a adição de menor custo
(binário único, sem runtime). **O gatilho de reabertura é numérico**: mais de ~8 alvos, ou
o primeiro alvo que precise de mais de uma linha.

**2. `uv` não faz release.** `uv version --bump patch` **escreve o `pyproject.toml` e para
aí** — não faz tag, não faz commit, não gera changelog, não empurra. O ciclo de release
continua sendo do CI. Ver §8 e §9.

**3. `uv version` é incompatível com versão dinâmica — e isso é uma escolha de eixo, não
um detalhe.** **[medido aqui]**, `uv 0.11.7`, projeto com `dynamic = ["version"]` e
`hatch-vcs`:

```
$ uv version
error: We cannot get or set dynamic project versions in: pyproject.toml
$ uv version --bump patch
error: We cannot get or set dynamic project versions in: pyproject.toml
```

Ou seja: **`uv version --bump` e `hatch-vcs` são mutuamente exclusivos.** Escolher um é
abrir mão do outro. Isso é decidido em §8.

**4. `uv` não substitui `tox`/`nox` para matriz de versões de Python — mas quase.**
`uv run --python 3.12 pytest` roda em outra versão sem ambiente pré-declarado, e o
`.python-version` fixa o padrão. Para uma matriz de verdade, quem itera é o
`strategy.matrix` do GitHub Actions, não um arquivo de tox. **Recomendação: matriz no CI,
sem `tox` nem `nox`.**

**5. Workspaces: não usar.** A doc os posiciona para "multiple interconnected packages in
one repository" e avisa que "uv's workspaces enforce a single `requires-python` for the
entire workspace". O overpower é **um** pacote — `pacote == comando == overpower`, achado
de #3. Workspace aqui é complexidade sem contraparte.

**O gatilho de reabertura é concreto**: se o conteúdo vendorizado dos frameworks um dia
sair para um pacote próprio (por exemplo `overpower-catalog`, para o wheel principal parar
de crescer), aí são dois pacotes no mesmo repo e o workspace passa a ser a ferramenta certa
— é literalmente o caso "libraries with plugin systems where each plugin is a separate
workspace package" da doc.

### 4.5 CI: as linhas que a doc do uv manda escrever

A [integração com GitHub Actions](https://docs.astral.sh/uv/guides/integration/github/)
(consultada 2026-07-30) é explícita em dois pontos que costumam ser feitos errado:

> "It is considered best practice to pin to a specific uv version"

com a action fixada por SHA (`astral-sh/setup-uv@<sha> # v8.1.0`) e `version: "0.12.0"`. E:

```yaml
- name: Install the project
  run: uv sync --locked --all-extras --dev
```

O `--locked` é o que importa: "If the lockfile is not up-to-date, uv will raise an error
instead of updating the lockfile". **`uv sync --locked` no CI é o gate que impede um PR de
mudar dependência sem mexer no `uv.lock`.** Sem ele, o CI atualiza o lock em silêncio e o
lockfile deixa de significar alguma coisa. `--frozen`, o parente próximo, "use[s] the
lockfile without checking if it is up-to-date" — é o que se quer num passo de build puro,
não no de instalação.

### 4.6 Custo, e custo de reverter

**Custo de adotar `uv`:** uma dependência de ferramenta que não é do PyPA e cuja
governança é de uma empresa. Mitigado por ela ser **um binário** e por tudo que ela produz
ser padrão: o `pyproject.toml` é PEP 621, os grupos são PEP 735, o wheel é do `hatchling`.
O `uv.lock` é o único artefato proprietário, e é de desenvolvimento.

**Custo de reverter: baixo, e o motivo é esse mesmo.** Sair do `uv` custa apagar
`uv.lock`, trocar quatro linhas de CI e escolher outro instalador. Nenhum arquivo
publicado muda. O que **não** é reversível barato é o caminho oposto — o achado de #3 de
que `uv` **não** lê `pip.conf` nem `PIP_INDEX_URL`, e de que `uvx` só lê
`~/.config/uv/uv.toml` e `/etc/uv/uv.toml`, é uma dívida de documentação corporativa que já
foi paga naquele ticket e que voltaria a ser cobrada.

---

## 5. `ruff`: o que ligar, e o que é ruído

### 5.1 Recomendação

**`extend-select`, nunca `select`.** Esta é a recomendação principal do eixo, e ela
**diverge do prior art** por uma razão que não existia quando o prior art foi escrito.

```toml
[tool.ruff]
line-length = 88          # default do ruff; ver §5.5
src = ["src"]             # ensina o isort onde mora o primeiro-partido

[tool.ruff.lint]
extend-select = [
  "E", "W", "F", "I", "N", "UP", "B", "SIM", "RUF",   # a base
  "PTH",                        # pathlib — a de maior rendimento aqui, ver §5.4
  "ANN",                        # anotação obrigatória; casa com o §6
  "TC",                         # imports só-de-tipo fora do runtime
  "S",                          # bandit
  "PT",                         # estilo de pytest
  "D",                          # docstrings
  "EM", "TRY", "RSE", "RET",    # forma de erro
  "T20",                        # print() — ver §5.4
  "ARG", "SLF", "TID", "INP",
  "C4", "C90", "PERF", "FURB", "PIE", "PL",
  "DTZ", "LOG", "G", "A", "ERA", "FBT",
]
ignore = [
  "D203", "D213",   # incompatíveis com D211/D212; o ruff já avisa
  "FBT002",         # falso positivo medido em opção `Annotated` do typer, ver §5.6
  "TRY003",         # exige classe de exceção por mensagem; a CLI fala com humano
]

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101", "D", "ANN", "SLF001", "PLR2004"]

[tool.ruff.format]
docstring-code-format = true
```

E o formatter do ruff no lugar do `black`. Um binário faz as duas coisas.

### 5.2 Por que `select` virou uma armadilha — [medido aqui]

O conselho antigo era: `ruff` liga pouca coisa por padrão (`E4`, `E7`, `E9`, `F`), então
escreva um `select` generoso. **Isso deixou de ser verdade.** A doc de hoje
([Rules](https://docs.astral.sh/ruff/rules/), consultada 2026-07-30) diz:

> "By default, Ruff enables rules from the `F`, `E`, `B`, `UP`, and `RUF` categories, as
> well as many more, omitting any stylistic rules that overlap with the use of a formatter"

E `select` **substitui** o padrão; quem soma é `extend-select`. A conta, com `ruff 0.16.1`,
contando as regras que o próprio ruff reporta em `--show-settings`:

| configuração | regras habilitadas |
| --- | --- |
| **nenhuma config** (default do ruff 0.16.1) | **413** |
| `select = ["E","F","I","N","UP","B","SIM","RUF","ANN"]` (**o prior art**) | **253** |
| `extend-select = [...]` (**a proposta do §5.1**) | **641** |

Comando: `uvx ruff check --isolated --show-settings <arquivo>` e a mesma coisa com
`--config`, contando as linhas de `linter.rules.enabled`.

**O `select` do prior art hoje habilita 160 regras a menos do que instalar o ruff e não
escrever configuração nenhuma.** Não é um detalhe de contagem: as famílias inteiras que ele
apaga, medidas por diferença de conjuntos, são

```
ASYNC BLE C D DTZ EXE FA FLY FURB G INT ISC LOG PERF PGH PIE
PLC PLE PLR PLW PT PTH PYI RET S T TC TRY W YTT
```

Isso inclui **`PTH`** (pathlib), **`S`** (bandit), **`PLE`** (erros do Pylint), **`TRY`**,
**`PT`** (estilo de pytest), **`LOG`**, **`PERF`** e **`FURB`**. Um `select` escrito em
2023 envelheceu para uma lista de exclusão.

**Esta é a divergência do prior art que eu defendo com mais convicção**, e ela é barata:
trocar `select` por `extend-select` é uma palavra.

### 5.3 Por que não `select = ["ALL"]`

O ruff suporta: "The special `ALL` code enables all rules, with automatic conflict
resolution" ([Linter](https://docs.astral.sh/ruff/linter/)). A resolução automática é real
— medi o ruff avisando e escolhendo sozinho entre `D203`/`D211` e `D212`/`D213`.

**Não achei na doc do ruff nenhuma recomendação contra o `ALL`** — *não confirmado em
fonte primária* que a Astral o desaconselhe. A razão de não usá-lo aqui é minha e é
operacional: com `ALL`, **toda atualização do ruff pode quebrar o CI sem que uma linha de
código tenha mudado**, porque regras novas entram habilitadas. Num repo que quer ser
exemplar, o pior sinal possível é o CI vermelho por bump de ferramenta. `extend-select`
explícito troca "surpresa a cada upgrade" por "uma linha a cada regra nova que eu quiser".

Nota de precisão que mudou minha própria lista: **o default do ruff habilita
*subconjuntos*, não famílias inteiras.** O default traz 29 regras de `B` — e **`B904` não
está entre elas** (*"raise ... from err"*, dentro de `except`). **[medido aqui]**: com
`extend-select = ["B"]`, o `B904` aparece; sem, não. Por isso a lista do §5.1 renomeia
famílias que "já vêm por padrão": ela as promove de subconjunto para família inteira.

### 5.4 As regras que pagam *neste* projeto — [medido aqui]

Rodei `--select ALL` sobre um módulo escrito no formato que o overpower vai ter (typer +
rich + I/O de arquivo + JSON). O que apareceu, e o veredito:

| regra | o que pegou | vale? |
| --- | --- | --- |
| `PTH118`, `PTH123`, `PTH103`, `PTH120`, `PTH201` | `os.path.join`, `open()`, `os.makedirs`, `os.path.dirname`, `Path(".")` | **Sim — a de maior rendimento.** 5 achados num arquivo. O overpower é I/O de arquivo; `PTH` é a família feita para ele, e é a que o `select` do prior art desliga. |
| `TRY004` | `isinstance(...)` falso levantando `ValueError` em vez de `TypeError` | **Sim.** Erro de contrato numa fronteira de JSON, que é exatamente o assunto do §6. |
| `B904` | `raise typer.Exit(2)` dentro de `except` sem `from` | **Sim.** Traceback limpo importa numa CLI. |
| `T201` | `print()` num módulo que já tem `Console` | **Sim.** A stack de #4 é `rich`; `print()` cru fura o `NO_COLOR` e a largura. |
| `INP001` | falta `__init__.py` | Artefato do laboratório, não do repo real. Fica ligada. |
| `ANN401` | `def f(payload: Any)` | **Sim, e ligada de propósito** — ver §6.6. É o alarme que impede `Any` de vazar de uma fronteira JSON para dentro do domínio. |
| `CPY001` | falta aviso de copyright | **Não.** Ruído puro. Fica de fora (não está no `extend-select`). |
| `FBT002` | `force: Annotated[bool, typer.Option(...)] = False` | **Não.** Falso positivo estrutural sobre o estilo idiomático do typer. Ver §5.6. |

### 5.5 O formatter, e as regras que brigam com ele

Usar o formatter do ruff e não `black`. A doc do ruff
([Formatter](https://docs.astral.sh/ruff/formatter/), consultada 2026-07-30) publica a
lista de regras que conflitam com ele, e nenhuma delas está no `extend-select` do §5.1:

`W191`, `E111`, `E114`, `E117`, `D203`, `D206`, `D300`, `Q000`, `Q001`, `Q002`, `Q003`,
`Q004`, `COM812`, `COM819`, `ISC002`.

Duas notas de precisão. **`D203` está nessa lista e no `ignore` do §5.1** — ele é
conflito com o formatter *e* incompatível com `D211`; um `ignore` resolve os dois. E
`E501` (linha longa) a doc trata à parte: pode ser usado, mas "may produce warnings since
formatted code sometimes exceeds configured line length limits". Mantenho `E501` ligado com
`line-length = 88` (o default medido do ruff) porque o formatter resolve 99% dos casos
sozinho, e o 1% restante — URL longa, string de erro — merece a atenção que o aviso pede.

`COM812` e `ISC001` aparecem em listas de `ignore` alheias por causa desse conflito.
**Aqui não são necessários**: `COM` não está no `extend-select`, e o default do ruff traz
apenas `ISC004`, não `ISC001`. Listá-los seria cargo cult.

### 5.6 O conflito com o `typer`, medido — e a boa notícia

A dor conhecida é `B008` (*function-call-in-default-argument*) contra
`x: T = typer.Option(...)`. A doc do ruff oferece
`lint.flake8-bugbear.extend-immutable-calls` com exemplo
`["fastapi.Depends", "fastapi.Query"]`.

**[medido aqui]**, `ruff 0.16.1`, e o resultado é melhor do que a fama:

| estilo | `B008` dispara? |
| --- | --- |
| `name: str = typer.Option("x")` | **não** — a doc: "Parameters with immutable type annotations will be ignored by this rule" |
| `target: Path = typer.Option(...)` | **sim** |
| `tags: list[str] = typer.Option([])` | **sim** |
| `target: Annotated[Path, typer.Option(...)] = Path(".")` | **não** |

Ou seja: **o conflito desaparece inteiro ao usar o estilo `Annotated`** — que é o estilo
que o próprio typer recomenda hoje, e o que o protótipo de #4 já usa. **Recomendação:
`Annotated` em todo comando, e nenhum `extend-immutable-calls` no `pyproject.toml`.** A
configuração que todo mundo copia é o remédio de uma doença que o estilo moderno não tem.

O que sobra de verdade é `FBT002` (*boolean-default-positional-argument*), que dispara
mesmo no estilo `Annotated`, sobre `force: Annotated[bool, typer.Option(...)] = False`.
Toda flag booleana de CLI é isso. **`FBT002` no `ignore`**, e `FBT001`/`FBT003` ficam
ligados — eles pegam booleano posicional em função interna, que é o abuso real que a
família existe para caçar (e que o laboratório também mediu, no `_install(..., force: bool
= False)`).

### 5.7 Custo, e custo de reverter

**Custo:** um `extend-select` de 641 regras num repo verde é indolor; num repo com código
legado seria um mutirão. O overpower não tem código ainda — **este é o momento de menor
custo possível**, e o custo cresce monotonicamente com cada linha escrita.

**Custo de reverter: quase zero, e assimétrico.** Afrouxar (`ignore` a mais, família a
menos) é uma linha e vale imediatamente. Apertar depois é o mutirão. **Portanto: apertar
agora, afrouxar sob evidência** — cada `ignore` futuro entra com um comentário dizendo qual
falso positivo o justificou, e é essa disciplina que faz o arquivo servir de template.

---
