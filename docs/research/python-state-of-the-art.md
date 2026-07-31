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

**A recomendação por eixo, em uma tabela.** O `pyproject.toml` inteiro que sai dela está no
§11.

| eixo | recomendação | custo de reverter |
| --- | --- | --- |
| Layout | **`src/overpower/`** | Baixo hoje; caro é ter revertido — perde-se o detector de asset faltando no wheel |
| Gerência | **`uv` sozinho**, sem task runner, sem workspaces | Baixo — nenhum arquivo publicado muda |
| Lint | **`ruff` com `extend-select`**, nunca `select` | Quase zero para afrouxar; caro para apertar depois |
| Tipagem | **`pyright` strict** + confinar `json.load` a um módulo | Uma palavra (`strict` → `standard`) |
| Testes | **`pytest 9` com `strict = true`** + `importlib`; cov/syrupy/randomly | Uma linha; só `importlib` tem custo escondido |
| Versão | **manual com `uv version --bump`** + asserção tag == versão | Minutos, nos dois sentidos |
| CHANGELOG | **`towncrier`** emitindo Keep a Changelog | Baixo — a saída sobrevive ao abandono da ferramenta |
| Piso Python | **`>=3.12`**, dev em **3.14** | Subir é um caractere; **descer é caro** — único eixo com a assimetria invertida |

**Os seis achados que mandam no desenho.**

1. **O layout `src/` não é estilo — é o único que faz o bug central do overpower falhar.**
   Com um erro de empacotamento real (asset vendorizado fora do wheel), o flat layout
   **passa verde** e o `src/` estoura `FileNotFoundError` na primeira execução. Como o
   axioma 5 põe todo o conteúdo dos frameworks dentro do wheel, esse é o modo de falha
   principal do produto. Medido em §3.3.

2. **O `select` do `ruff` virou uma armadilha, e o prior art caiu nela.** O default do
   `ruff 0.16.1` habilita **413 regras**; o `select = ["E","F","I","N","UP","B","SIM","RUF","ANN"]`
   do `panlabs-tech/.github` habilita **253** — **160 a menos do que não escrever
   configuração nenhuma**, apagando `PTH`, `S`, `TRY`, `PT`, `TC`, `LOG`, `PERF` e `FURB`.
   Trocar `select` por `extend-select` é uma palavra e devolve tudo. §5.2.

3. **O modo estrito paga, e o custo não está onde a issue supunha.** Num módulo com a
   forma do overpower e as três dependências reais, `pyright` strict produz **1 erro** — e
   ele não é sobre I/O de arquivo, é sobre JSON. A I/O custa **zero** (o `pathlib` é
   integralmente tipado) e as dependências custam **zero** (typer, rich e questionary
   publicam `py.typed`). §6.2.

4. **Mas o `pyright` strict tem um ponto cego bem no meio do assunto, e a saída não é
   trocar de checker.** `Any` explícito não é `Unknown`, então `return data["name"]` numa
   função declarada `-> str` **passa** — e, pior, o strict reclama justamente do código que
   *valida* com `isinstance`. Uma regra de arquitetura fecha o buraco: **`json.load` mora
   num módulo só e devolve `object`**. Com ela, os três checkers pegam o bug — e o `ruff`
   cobra a regra sozinho, via `TID251`. §6.4 e §6.5.

5. **Versionamento por VCS falha em silêncio exatamente onde não pode.** Em `git clone
   --depth 1` — que é o **default** do `actions/checkout` — o `hatch-vcs` não acha a tag,
   emite só um `UserWarning`, **o build tem sucesso** e produz uma versão inventada. Some-se
   que `uv version --bump` e `dynamic = ["version"]` são mutuamente exclusivos, com erro
   duro. §8.3 e §8.4.

6. **Duas peças novas de 2026 que superam o prior art sem discussão.** O `pytest 9.0.0`
   (2025-11-05) criou `strict = true`, que liga quatro checagens onde o
   `--strict-markers --strict-config` liga duas — medido pegando marcador não registrado,
   `xfail` que passa e `ids` duplicados, todos verdes sem ele (§7.2). E o `ty` da Astral,
   apesar de ~18× mais rápido que o pyright na partida, **está em beta e erra**: produz
   falso positivo em `isinstance(x, dict)` + chave `str`, que é o primeiro padrão que este
   projeto vai escrever (§6.7).

**Onde divirjo do prior art, e onde não.**

| item | prior art `panlabs-tech/.github` | aqui | por quê |
| --- | --- | --- | --- |
| `ruff` | `select = [...]` | **`extend-select = [...]`** | Diverge — 160 regras a mais, medido |
| `pytest` | `--strict-markers --strict-config` | **`strict = true`** | Diverge — recurso do pytest 9, mais checagens em menos linha |
| `pyright` | strict | **strict** | **Não diverge** — e §6.6 diz por que, mesmo tendo o mypy achado mais bug |
| Python | 3.12 | **3.12** | **Não diverge** — mas por razão própria: o baseline do Ubuntu LTS, não gosto |

As duas divergências têm a mesma forma: **não são discordância de critério, são fatos que
chegaram depois.** O prior art estava certo quando foi escrito.

---

## 2. Mapa: onde está cada resposta

| eixo da issue #2 | recomendação em uma linha | seção |
| --- | --- | --- |
| Layout `src/` × flat | **`src/`**, e não por estilo: é o único que faz o bug de empacotamento falhar no teste do dev | §3 |
| Gerência de projeto com `uv` | **`uv` sozinho fecha env, lock, sync, build e publish**; falta task runner e release | §4 |
| `ruff`: regras que valem × ruído | **`extend-select`, nunca `select`** — em 2026 um `select` explícito *desliga* 160 regras | §5 |
| Tipagem `pyright` × `mypy` × `ty` | **`pyright` strict** — o estrito paga, e o custo está todo no JSON, não na I/O | §6 |
| `pytest`, plugins, cobertura | **`strict = true`** (pytest 9) e **cobertura como catraca**, não como número escolhido | §7 |
| Versionamento e trusted publishing | **manual com `uv version --bump`** — o `hatch-vcs` publica versão errada em clone raso | §8 |
| CHANGELOG | **`towncrier` emitindo formato Keep a Changelog** — não é ou-um-ou-outro | §9 |
| Piso de versão do Python | **`>=3.12`**, desenvolvendo em **3.14** — piso e versão de dev são decisões distintas | §10 |
| — | O `pyproject.toml` inteiro que sai das oito, executado e verde | §11 |
| — | Riscos, lacunas e o que **não** foi confirmado | §12 |

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
"tests/**" = ["S101", "D", "ANN", "SLF001", "PLR2004", "INP001"]

[tool.ruff.format]
docstring-code-format = true
```

E o formatter do ruff no lugar do `black`. Um binário faz as duas coisas.

**Sobre o `INP001` no `per-file-ignores` — ele não é decoração, é um conflito real que
esta pesquisa levou uma rodada para achar.** `INP001` exige `__init__.py` em todo
diretório, e o `--import-mode=importlib` do §7.3 existe justamente para que a suíte **não**
precise dele. **[medido aqui]**: com a config acima sem esse `ignore`, `ruff check .` acusa
`INP001` em todo arquivo de `tests/`. Com ele, `All checks passed!`. Os dois eixos —
lint e teste — só fecham juntos.

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
| `extend-select = [...]` (**a proposta do §5.1**) | **720** |

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

## 6. Tipagem: `pyright` × `mypy` × `ty`, e se o estrito paga

Este é o eixo em que a issue faz uma pergunta específica — *"o modo estrito paga o custo
numa lib com muita I/O de arquivo e leitura de JSON sem esquema?"* — então ele é respondido
com experimento, não com opinião.

### 6.1 Recomendação

**`pyright` em `strict`, como gate único. `mypy` não entra. `ty` fica no editor, não no
CI.** E — a parte que importa mais que a escolha da ferramenta — **uma regra de arquitetura
de uma linha, que o `ruff` sabe cobrar sozinho**:

> **`json.load` é chamado em exatamente um módulo, e esse módulo devolve `object`,
> nunca `Any`.**

Sem essa regra, o `pyright` strict tem um ponto cego bem no meio do assunto do overpower.
Com ela, o ponto cego vira erro de compilação. §6.5 mostra os dois lados medidos.

### 6.2 A resposta curta: sim, e o custo não está onde se supõe

**[medido aqui]** — módulo escrito no formato do overpower (typer + rich + I/O de arquivo
com `pathlib` + JSON sem esquema), com as três dependências reais instaladas
(`typer`, `rich`, `questionary`), `pyright 1.1.411` em `typeCheckingMode = "strict"`:

```
1 error, 0 warnings, 0 informations
  cli.py:27:12 - error: Return type, "dict[Unknown, Unknown]", is partially unknown
                 (reportUnknownVariableType)
```

**Um erro. E ele não é sobre I/O de arquivo — é sobre o JSON.**

O custo da I/O de arquivo em modo estrito é **zero**, e a razão é estrutural: `pathlib`,
`shutil` e `os` são inteiramente tipados no typeshed. Escrever `Path.rglob`,
`Path.write_bytes`, `Path.relative_to` e `shutil.copy2` sob strict não custa uma anotação a
mais do que sob `standard`.

O custo das **dependências** também é zero, e isso foi verificado e não suposto: as três
publicam o marcador `py.typed` no pacote — confirmado via API do GitHub nos repositórios
oficiais `fastapi/typer`, `Textualize/rich` e `tmbo/questionary` (2026-07-30). Como
`reportMissingTypeStubs` é `"error"` em strict e `"none"` em standard
([configuration.md](https://raw.githubusercontent.com/microsoft/pyright/main/docs/configuration.md)),
essa é justamente a linha em que uma stack mal escolhida faria o strict doer. A stack de #4
não faz.

**Todo o custo do modo estrito neste projeto está concentrado numa única fronteira: o
`json.load`.** Que é uma fronteira que a gente quer estreita de qualquer jeito.

### 6.3 Por que o JSON dói, e por que dói *menos* do que a fama

O typeshed declara ([stdlib/json/__init__.pyi](https://raw.githubusercontent.com/python/typeshed/main/stdlib/json/__init__.pyi),
consultado 2026-07-30) que `json.load` e `json.loads` devolvem **`Any`**.

E aqui está o ponto que quase todo mundo erra: **`Any` explícito não é `Unknown`, e o
`pyright` strict só reclama de `Unknown`.** A doc do pyright
([type-inference.md](https://raw.githubusercontent.com/microsoft/pyright/main/docs/type-inference.md)):

> "If a symbol's type cannot be inferred, Pyright sets its type to "Unknown", which is a
> special form of "Any"."
>
> "The "Unknown" type allows Pyright to optionally warn when types are not declared and
> cannot be inferred, thus leaving potential "blind spots" in type checking."

Como `json.load` **declara** `Any` no stub, o valor que sai dele não é `Unknown`. **O
pyright strict não emite um único diagnóstico sobre ele.** A confirmação vem de uma fonte
adversarial: a doc do **basedpyright**, um fork que existe em parte por discordar disso,
descreve sua regra exclusiva `reportAny` como cobrindo

> "all scenarios not covered by the `reportUnknown*` rules (since "Unknown" isn't a real
> type, but a distinction pyright makes to disallow the `Any` type only in certain
> circumstances)"

com default `"none"` em standard **e em strict**, `"error"` só em `all`
([basedpyright, config-files](https://docs.basedpyright.com/latest/configuration/config-files/),
consultada 2026-07-30). `reportAny` e `reportExplicitAny` **não existem no pyright
upstream** — quem os cita como parte do "pyright strict" está descrevendo outra
ferramenta.

**Conclusão do sub-eixo:** ler JSON sem esquema sob `pyright` strict **não** gera enxurrada
de erro. Gera **silêncio** — que é um problema diferente, e o §6.5 trata dele.

### 6.4 O que cada checker faz com o mesmo arquivo — [medido aqui]

Mesmo módulo, cinco funções, três checkers. Versões: `pyright 1.1.411` (strict),
`mypy 2.3.0 (compiled: yes)` (`--strict`), `ty 0.0.65`.

| a função | `pyright` strict | `mypy --strict` | `ty 0.0.65` |
| --- | --- | --- | --- |
| `def f(p) -> object: return json.load(...)` | ok | ok | ok |
| `def f(p):` sem anotação de retorno | **ok** (o `Any` do stub não é `Unknown`) | **erro** `no-untyped-def` | ok |
| `def f(p) -> str: ... return data["name"]` — **retorno inseguro** | **ok — passa** | **erro** `Returning Any from function declared to return "str"` | ok |
| I/O de arquivo com `pathlib`, `rglob`, `write_bytes` | ok | ok | ok |
| `isinstance(raw, list)` + `isinstance(item, dict)` + `item["name"]` — **o código que valida** | **3 erros** `reportUnknown*` | ok | **2 erros, falsos** |

Três leituras saem daí, e elas invertem a intuição:

**1. O `mypy --strict` pega o bug de verdade e o `pyright` strict não.** O caso
`return data["name"]` numa função declarada `-> str` é *o* erro de fronteira de JSON, e
quem o pega é o `--warn-return-any`, que a doc do mypy descreve como "generate a warning
when returning a value with type Any from a function declared with a non-Any return type"
e que o `--strict` inclui ([mypy, command_line](https://mypy.readthedocs.io/en/stable/command_line.html),
consultada 2026-07-30 — a mesma página avisa que "the exact list of flags enabled by
running `--strict` may change over time").

**2. O `pyright` strict reclama exatamente do código que faz a coisa certa.** As três
reclamações caem sobre a função que *valida* com `isinstance`, porque estreitar `object`
para um `list`/`dict` pelado produz `list[Unknown]` e `dict[Unknown, Unknown]`. O código
que não valida nada passa em silêncio. **É um incentivo invertido**, e é a crítica mais
séria que se pode fazer ao strict do pyright nesse domínio.

**3. O `ty 0.0.65` erra.** Reprodução mínima de 4 linhas:

```python
def f(raw: object) -> str:
    if isinstance(raw, dict):
        return str(raw["name"])   # ty: erro. pyright: ok. mypy: ok.
    return ""
```

```
error[invalid-argument-type]: Method `__getitem__` of type
  `bound method Top[dict[Unknown, Unknown]].__getitem__(key: Never, /) -> object`
  cannot be called with key of type `Literal["name"]`
```

Indexar um `dict` gradualmente tipado com uma chave `str` é Python legal e tipagem legal; o
`ty` resolve o parâmetro de chave para `Never` e rejeita. `pyright` e `mypy` aceitam. É
**falso positivo**, e não é obscuro — é o primeiro padrão que qualquer leitor de JSON
escreve.

### 6.5 A regra de uma linha que resolve os três problemas — [medido aqui]

Se o `json.load` nunca escapa como `Any`, e sim como **`object`**, tudo se realinha:

```python
def load_json(path: Path) -> object:      # único ponto do codebase que chama json.load
    with path.open(encoding="utf-8") as fh:
        return cast("object", json.load(fh))
```

O mesmo bug de antes, agora com o valor tipado `object`:

```
pyright strict : error: "__getitem__" method not defined on type "object" (reportIndexIssue)
mypy --strict  : error: Value of type "object" is not indexable  [index]
ty 0.0.65      : error (gate.py:19)
```

**Os três pegam.** O ponto cego do `pyright` era uma consequência do `Any`, não do pyright —
tirado o `Any`, some. E some **sem** um segundo checker no CI.

E as reclamações do §6.4, item 2, também somem, desde que a validação produza tipo
concreto em vez de estreitar um `dict` pelado. O padrão completo — `load_json() -> object`,
mais validadores `_as_mapping(v: object) -> dict[str, object]` e
`_as_str(v: object) -> str` — foi medido **limpo nos três**:

```
pyright strict : 0 errors     mypy --strict : Success     ty : All checks passed!
```

**E o `ruff` sabe cobrar a regra.** `TID251` com `banned-api` transforma "só um módulo
chama `json.load`" em erro de lint, não em acordo de cavalheiros. **[medido aqui]**:

```toml
[tool.ruff.lint.flake8-tidy-imports.banned-api]
"json.load"  = { msg = "use overpower.jsonio.load_json, que devolve object" }
"json.loads" = { msg = "use overpower.jsonio.loads_json, que devolve object" }

[tool.ruff.lint.per-file-ignores]
"src/overpower/jsonio.py" = ["TID251"]
```

```
clean.py:19:31: TID251 `json.load` is banned: use overpower.jsonio.load_json, que devolve object
```

O módulo sancionado passa; qualquer outro é barrado. **Esta é a recomendação mais
transferível deste documento inteiro**: a fronteira de dados sem esquema não se defende
escolhendo um checker mais bravo, defende-se estreitando a fronteira até caber num arquivo
— e aí qualquer checker serve.

### 6.6 Por que `pyright` e não `mypy`, dado que o `mypy` pegou mais

Honestamente: **o `mypy --strict` teve o melhor resultado bruto** nos experimentos —
pegou o retorno inseguro, pegou a função sem anotação, e não produziu um único falso
positivo. Se o critério fosse só "quem acha mais bug e reclama menos à toa", seria mypy.

Escolho `pyright` assim mesmo, por quatro razões, e a primeira é a que decide:

1. **A regra do §6.5 apaga a vantagem do mypy.** Os dois erros que só o mypy pegou existem
   porque havia um `Any` solto. Com `json.load` confinado, o `pyright` pega os mesmos casos
   (medido). A vantagem do mypy é real **e** é contingente a uma prática que já vamos
   proibir por lint.
2. **É o checker que o editor já roda.** `pyright` é o motor do Pylance no VS Code e o que
   dá diagnóstico enquanto se digita. Um gate de CI que discorda do editor gera a pior das
   experiências — vermelho no CI que não aparece na tela. Alinhar gate e editor vale mais
   que uma regra a mais.
3. **É o prior art do `panlabs-tech/.github`.** Aqui **não** divirjo, e conscientemente:
   divergir custa consistência, e nas três razões acima não há ganho que pague.
4. **A anotação obrigatória vem do `ruff`, não do checker.** `ANN` no `extend-select`
   (§5.1) já cobra anotação em toda assinatura, que era o outro achado exclusivo do mypy.
   E `ANN401` proíbe `Any` em assinatura — o mesmo alvo do `reportExplicitAny` do
   basedpyright, sem trocar de checker.

**A configuração:**

```toml
[tool.pyright]
include = ["src", "tests"]
typeCheckingMode = "strict"
pythonVersion = "3.12"        # ver §10
venvPath = "."
venv = ".venv"
```

Note `include = ["src", "tests"]`: os testes também são código, e são onde o `Any` costuma
entrar de fininho.

### 6.7 `ty`: onde ele entra em 2026, e onde não

O README oficial ([astral-sh/ty](https://raw.githubusercontent.com/astral-sh/ty), consultado
2026-07-30) é explícito:

> ty is currently in **beta** — "ty does not yet have a stable API; breaking changes,
> including changes to diagnostics, may occur between any two versions."

Versão medida: **`ty 0.0.65`**, ainda no esquema `0.0.x`.

**Recomendação: não usar como gate de CI, usar no editor.** A velocidade é real e é
mensurável **[medido aqui]**, no mesmo projeto de 2 arquivos com as três dependências:

| checker | tempo (cache quente) | tempo (cache frio) |
| --- | --- | --- |
| `ty 0.0.65` | **0,095 s** | — |
| `mypy 2.3.0` (compiled) | 0,161 s | 1,541 s |
| `pyright 1.1.411` | 1,705 s | — |

**Aviso de honestidade sobre esses números:** o projeto tem 2 arquivos, então o que está
medido é essencialmente **custo de partida**, não escala. O 1,7 s do pyright é o Node
subindo. Não trate a tabela como prova da alegação de "10x - 100x" da doc do ty
([Introduction](https://docs.astral.sh/ty/)) — ela não mede isso, e eu **não** medi isso.

O que **desqualifica** o `ty` como gate hoje não é velocidade, é o falso positivo do §6.4
sobre o padrão central deste projeto. Um gate que reprova código correto é pior que gate
nenhum.

**O gatilho de reabertura é limpo e vai acontecer sozinho:** `ty` em 1.0, ou o falso
positivo de `isinstance(x, dict)` + chave `str` corrigido. Vale reexecutar a matriz do §6.4
a cada minor. Trocar `pyright` por `ty` depois é trocar uma linha de CI e uma seção de
`pyproject.toml` — **é a reversão mais barata deste documento**, o que é precisamente o
argumento para não apostar cedo.

### 6.8 Custo, e custo de reverter

**Custo do strict, medido e não estimado:** 1 erro num módulo representativo, e o erro
aponta para uma decisão de desenho que a gente ia querer tomar de qualquer forma. Em
`standard`, esse erro some junto com `reportUnknownParameterType`,
`reportUnknownArgumentType`, `reportUnknownVariableType`, `reportUnknownMemberType`,
`reportMissingParameterType`, `reportMissingTypeArgument`, `reportMissingTypeStubs` e
`reportUnnecessaryIsInstance` — todos `"none"` em standard e `"error"` em strict, pela
tabela oficial do pyright.

**O custo real não é o strict: é largar o strict depois.** Adotar strict num repo vazio é
grátis. Adotá-lo em 3.000 linhas é um projeto. O modo estrito é a decisão mais barata de
tomar cedo e mais cara de adiar deste documento inteiro.

**Custo de reverter:** trocar `"strict"` por `"standard"` é uma palavra, e é reversível a
qualquer momento sem tocar em código. **Assimetria total a favor de começar estrito.**

---

## 7. `pytest`, os plugins que pagam, e cobertura

### 7.1 Recomendação

```toml
[tool.pytest.ini_options]
minversion = "9.0"
testpaths = ["tests"]
addopts = "-ra --import-mode=importlib"
strict = true                       # ver §7.2 — supera o prior art
filterwarnings = ["error"]
markers = ["slow: teste que toca rede ou muitos arquivos"]
required_plugins = ["pytest-cov", "syrupy", "pytest-randomly"]
```

Plugins: **`pytest-cov`, `syrupy`, `pytest-randomly`**. Mais nada por padrão.
**`pytest-xdist` e `hypothesis`** entram sob gatilho declarado (§7.4).
Cobertura: **catraca, não número escolhido** (§7.5).

### 7.2 `strict = true` — a divergência do prior art, e ela é nova

O prior art do `panlabs-tech/.github` usa `--strict-markers --strict-config`. Isso está
certo e ficou **incompleto**: o pytest 9.0.0 (**lançado 2025-11-05**, changelog oficial)
introduziu um interruptor único.

> "Added a **'strict mode'** enabled by the `strict` configuration option. When set to
> `true`, the `strict` option currently enables `strict_config`, `strict_markers`,
> `strict_parametrization_ids`, `strict_xfail`"

e, no mesmo release,

> "The previously-deprecated `--strict` command-line flag now enables strict mode."

([changelog do pytest](https://docs.pytest.org/en/stable/changelog.html), consultado
2026-07-30. O `--strict` era, historicamente, um alias depreciado de `--strict-markers`;
ele foi **reaproveitado**, não ressuscitado. Quem lembra da depreciação e evita a flag está
usando informação que venceu.)

Versão medida aqui: **`pytest 9.1.1`**. O `--help` da ferramenta confirma:

```
strict (bool): Enables all strictness options, currently:
               strict_config, strict_markers, strict_xfail,
               strict_parametrization_ids
```

**O que os dois modos veem no mesmo arquivo — [medido aqui].** Uma suíte com três defeitos
plantados: marcador não registrado, um `xfail` que passa, e dois casos parametrizados com
`ids` idênticos.

| | sem `strict` | com `strict = true` |
| --- | --- | --- |
| marcador `slow` não registrado | `PytestUnknownMarkWarning` | **erro de coleta**: `'slow' not found in markers configuration option` |
| `xfail` que na verdade passa | `1 xpassed` — **verde** | **falha**: `[XPASS(strict)] ...` |
| `ids=["dup", "dup"]` | silêncio total | **erro de coleta**: `Duplicate parametrization IDs detected` |
| resultado final | `3 passed, 1 xpassed, 1 warning` | `1 error during collection` |

Os dois primeiros são clássicos: um marcador com typo simplesmente não filtra nada, e um
`xfail` que passou é um bug **consertado** cujo teste ninguém religou. O terceiro,
`strict_parametrization_ids`, é o que quase ninguém tem, porque não existia: dois casos com
o mesmo id são dois casos indistinguíveis num relatório de CI.

**Divergência recomendada: `strict = true` no lugar de `--strict-markers --strict-config`.**
Ganha duas checagens, e a linha fica menor.

### 7.3 `--import-mode=importlib`, que é consequência do §3

A doc do pytest ([Good Integration
Practices](https://docs.pytest.org/en/stable/explanation/goodpractices.html), consultada
2026-07-30) recomenda, para projeto novo:

> "For new projects, we recommend to use `importlib` [import mode]"

com a razão: "The `importlib` import mode does not have any of the drawbacks above, because
`sys.path` is not changed when importing test modules", enquanto no modo `prepend` (o
padrão) "your test files must have **unique names**".

Isso **completa** o eixo do §3. O layout `src/` faz o teste rodar contra o pacote instalado;
o `importlib` garante que nem o `sys.path` de teste reintroduza o sombreamento pela porta
dos fundos. Os dois juntos são o que dá o resultado do §3.3 — teste que falha quando o
wheel está quebrado.

Não há chave de `.ini` própria para isso; vai em `addopts`, como a própria doc instrui.

### 7.4 Os plugins, um a um, com veredito

| plugin | veredito | razão |
| --- | --- | --- |
| **`pytest-cov`** | **sim** | Integra a medição na mesma execução. `--cov-branch` e `--cov-fail-under` na mão. Ver §7.5. |
| **`syrupy`** | **sim** | Já decidido em #4: congela layout de saída rica sem congelar cor — 9 testes, zero quebras ao trocar a cor da marca. 55 KB. |
| **`pytest-randomly`** | **sim** | Ordem aleatória com semente reprodutível. Numa suíte que escreve em diretório temporário e instala arquivos, **dependência de ordem é o bug de teste mais provável do projeto**, e é o único que não aparece rodando a suíte de novo. |
| **`pytest-xdist`** | **não agora** | Paralelismo é remédio para suíte lenta, e ainda não há suíte. Complica cobertura e ordem. **Gatilho: suíte passando de ~30 s local.** |
| **`hypothesis`** | **não agora, mas com alvo nomeado** | O overpower normaliza e junta caminhos, e resolve destino por tabela framework × runtime (#5, #6). É exatamente o tipo de função onde property test acha o caso que ninguém escreveu. **Gatilho: a primeira função pura de manipulação de caminho.** |
| **`pyfakefs`** | **não** | `tmp_path` é **built-in** do pytest, "a temporary directory unique to each test function" e "a `pathlib.Path` object", com `tmp_path_factory` de escopo de sessão. Um FS falso adicionaria uma emulação entre o teste e o `pathlib` real — e o `pathlib` real, num projeto cujo produto é escrever arquivo, **é o que a gente quer testar**. Além disso, `symlink` no Windows tem três degraus (#5): FS falso mentiria justamente aí. |
| **`pytest-mock`** | **não** | `monkeypatch` é built-in e `unittest.mock` é stdlib. `mocker` é açúcar de escopo. Uma dependência a menos. |
| **`pytest-sugar`, `pytest-clarity`** | **não** | Cosmético. Num repo que quer ser template, cada linha de dependência precisa se justificar. |
| **`pytest-timeout`** | **não, com ressalva** | O achado de #4 é que **`textual` pendura o processo sem TTY** — e `textual` está fora. Se algum dia um caminho interativo entrar em teste, este plugin vira a rede de segurança. |
| **`typer.testing.CliRunner`** | **sim, e não é plugin** | Achado de #4: o typer vendoriza o click desde a 0.26.0 e traz runner próprio com `stdout` e `stderr` separados. Nada a instalar. |

### 7.5 Cobertura: gate ou sinal? — **catraca**

**As duas posições comuns estão erradas para este projeto**, e por motivos opostos.

*Cobertura como número escolhido* (`fail_under = 80`) mede a distância até um número que
alguém inventou. Assim que o CI fica vermelho num PR legítimo, o número desce — e um limiar
que desce quando incomoda não é gate, é decoração.

*Cobertura como puro sinal* (medir e relatar, sem gate) é honesto e não segura nada: a
cobertura cai de PR em PR, cada queda pequena demais para alguém comentar.

**A recomendação é a catraca:** `fail_under` **igual à cobertura atual**, e só sobe. Todo PR
que baixa fica vermelho; todo PR que sobe **muda o número no mesmo commit**, e essa linha do
diff é o registro. Não há número a defender — só uma direção.

```toml
[tool.coverage.run]
source_pkgs = ["overpower"]
branch = true              # "measure branch coverage in addition to statement coverage"
relative_files = true      # medir num ambiente, relatar em outro

[tool.coverage.report]
show_missing = true
fail_under = 0             # sobe para o valor real no primeiro PR com testes; nunca desce
exclude_also = ["if TYPE_CHECKING:", "raise NotImplementedError"]
```

`branch = true` não é opcional aqui. O overpower é feito de decisão binária sobre o mundo
de fora — o arquivo existe?, é symlink?, tem TTY?, o `core.symlinks` está falso? (#5) —
e cobertura de linha dá 100% num `if` cujo ramo falso nunca rodou. **Cobertura de ramo é a
única que mede o que este projeto faz.**

Três notas de precisão, todas de fonte primária:

- `fail_under` "If the total coverage measurement is under this value, then exit with a
  status code of 2"
  ([coverage.py, config](https://coverage.readthedocs.io/en/latest/config.html), consultada
  2026-07-30). Status **2**, não 1 — importa para quem escreve o passo de CI.
- O `pytest-cov` **sobrescreve** opções do coverage: a doc diz que ele controla `parallel`,
  `source` e `branch`, o que torna essas chaves no arquivo de config "pointless" a menos que
  o coverage rode sozinho ([pytest-cov,
  config](https://pytest-cov.readthedocs.io/en/latest/config.html), consultada 2026-07-30).
  Então **`--cov-branch` vai na linha de comando/`addopts`**, mesmo com `branch = true`
  declarado. É a pegadinha mais comum do par.
- A própria FAQ do coverage.py aponta para um texto chamado *"Flaws in Coverage
  Measurement"* e admite que a medição "isn't perfect". Não achei na doc oficial nenhuma
  declaração de que 100% signifique bem testado — **quem diz isso não tem fonte primária, e
  eu também não tenho a de sinal contrário.** A posição do §7.5 é minha, com o argumento
  acima.

**E há uma parte do overpower que a cobertura não mede, por construção:** o conteúdo
vendorizado dos frameworks. São centenas de arquivos que não são código executável do
pacote. Um número de cobertura que os incluísse seria ficção — daí o `source_pkgs` apontando
para o pacote, e não para o diretório.

### 7.6 Custo, e custo de reverter

**Custo:** três dependências de dev, todas puras. `strict = true` cobra o registro de
marcador — que é justamente a documentação que a gente quer.

**Custo de reverter:** desligar `strict` é uma linha, e o efeito é imediato. Baixar a
catraca é uma linha, e **é visível no diff** — que é o ponto inteiro do desenho. Trocar
`importlib` por `prepend` depois é o único item com custo escondido: exigiria nomes de
arquivo de teste únicos em toda a suíte. **Adotar `importlib` agora é grátis; adotar depois
é renomear.**

---

## 8. Versionamento: manual × `hatch-vcs` × `setuptools-scm`

### 8.1 Recomendação

**Versão literal no `pyproject.toml`, movida por `uv version --bump`, com a tag derivada
dela — e uma asserção de CI que reprova se tag e versão discordarem.** Nada de
`dynamic = ["version"]`.

Esta é a recomendação em que mais custei a me decidir, porque o versionamento por VCS é o
que "parece" moderno. Os três experimentos abaixo me moveram na direção contrária.

### 8.2 Achado 1: `uv version` e versão dinâmica são mutuamente exclusivos — [medido aqui]

Já registrado em §4.4, e é o custo que ninguém menciona:

```
$ uv version                    # projeto com dynamic = ["version"] + hatch-vcs
error: We cannot get or set dynamic project versions in: pyproject.toml
$ uv version --bump patch
error: We cannot get or set dynamic project versions in: pyproject.toml
```

Adotar `hatch-vcs` **desliga o comando de versão da ferramenta que gerencia o projeto**.
Não é fatal — `git tag` passa a ser o bump — mas é um trade que precisa ser dito, e a doc
do `hatch-vcs` não o diz porque não é problema dela.

Com versão literal, o ferramental existe e é bom **[medido aqui]**:

```
$ uv version --short
0.1.0
$ uv version --bump minor --dry-run
libinit 0.1.0 => 0.2.0
```

`--bump` aceita `major, minor, patch, stable, alpha, beta, rc, post, dev`, e tem
`--dry-run`, `--locked` e `--frozen` (`uv version --help`, `uv 0.11.7`).

### 8.3 Achado 2: fora da tag, o `hatch-vcs` produz versão que o PyPI proíbe — [medido aqui]

Projeto com `hatch-vcs`, tag `v0.1.0`, `uv build --wheel`:

| estado do repo | wheel produzido |
| --- | --- |
| exatamente na tag `v0.1.0` | `vdemo-0.1.0-py3-none-any.whl` |
| **um commit além da tag** | `vdemo-0.1.1.dev1+g277ae8e26-...whl` |
| **árvore suja** (arquivo não commitado) | `vdemo-0.1.1.dev1+g277ae8e26.d20260731-...whl` |

O `+g277ae8e26` é um **local version identifier**, e a especificação de versões da PyPA
([Version specifiers](https://packaging.python.org/en/latest/specifications/version-specifiers/),
consultada 2026-07-30) é categórica:

> "As the Python Package Index is intended solely for indexing and hosting upstream
> projects, it MUST NOT allow the use of local version identifiers."

**Leitura justa: isso é metade proteção, metade armadilha.** Proteção, porque torna
impossível publicar um build fora da tag por acidente. Armadilha, porque também impossibilita
o ensaio — subir um build de desenvolvimento no TestPyPI para exercitar o caminho de
publicação inteiro. E "provar o pipeline ponta a ponta antes de construir" é exatamente a
mitigação que o mapa combinou em [#13](https://github.com/panlabs-tech/overpower/issues/13).

### 8.4 Achado 3: o que quebra de verdade — clone raso publica versão errada em silêncio — [medido aqui]

Este é o achado que decide o eixo.

```
$ git clone --depth 1 file://.../proj shallow
$ cd shallow && uv build --wheel
UserWarning: ".../shallow" is shallow and may cause errors
Successfully built dist/vdemo-0.1.dev1+g277ae8e26-py3-none-any.whl
```

Três coisas, na ordem em que doem:

1. A tag `v0.1.0` não veio no clone raso, então a versão derivada é **`0.1.dev1`** — que
   não é `0.1.0` nem `0.1.1.dev1`. É **outra versão**, inventada a partir de história
   ausente.
2. **O build não falha.** Emite um `UserWarning` e sai com sucesso. Num log de CI de 400
   linhas, um `UserWarning` é invisível.
3. **É a configuração padrão do CI.** O `actions/checkout` documenta `fetch-depth` com
   default **`1`** e `fetch-tags` com default **`false`**
   ([README oficial](https://raw.githubusercontent.com/actions/checkout/main/README.md),
   consultado 2026-07-30). O caminho feliz — copiar o exemplo do checkout e usar `hatch-vcs` —
   **é exatamente o caminho quebrado**.

Existe conserto (`fetch-depth: 0`), existe rede (`fallback-version` do hatch-vcs) — mas
ambos são conhecimento que precisa estar na cabeça de quem escreve o workflow. **O modo de
falha do versionamento manual é esquecer de bumpar, e ele é ruidoso: o PyPI recusa versão
repetida. O modo de falha do `hatch-vcs` é silencioso e publica.** Entre errar alto e errar
baixinho, numa lib que quer ser referência, escolho errar alto.

### 8.5 `hatch-vcs` × `setuptools-scm`, para registro

Não é uma escolha de dois: o README do `hatch-vcs` diz que ele é
"a plugin for Hatch that uses your preferred version control system (like Git) to determine
project versions" e que é **construído sobre o `setuptools-scm`** — o `raw-options` é
literalmente um repasse de parâmetros para ele. Com `hatchling` fixado por #3, `hatch-vcs`
é a única porta; `setuptools-scm` direto exigiria trocar o backend, o que #3 fechou.

Uma nota do README que morde na prática: *"The version file is only updated upon install or
build"* — em instalação editável, `overpower.__version__` fica velho até o próximo build.
Num CLI que vai ter `--version`, isso é confusão garantida em desenvolvimento.

**Contra-argumento honesto, e o gatilho de reabertura:** a favor do `hatch-vcs` está uma
fonte de verdade só, e a impossibilidade estrutural de publicar `0.2.0` com a tag `v0.1.9`.
São argumentos reais. **O gatilho é a frequência**: se o overpower passar a publicar mais
de uma vez por semana, o custo de esquecer o bump ultrapassa o custo do `fetch-depth: 0`, e
a decisão inverte.

### 8.6 A interação com trusted publishing

A doc do PyPI ([Trusted publishers](https://docs.pypi.org/trusted-publishers/), consultada
2026-07-30) descreve o mecanismo:

> "'Trusted Publishing' is our term for using the OpenID Connect (OIDC) standard to exchange
> short-lived identity tokens between a trusted third-party service and PyPI."

com o PyPI cunhando um token temporário de **15 minutos** quando o token OIDC bate com uma
configuração confiada, o que elimina token de longa duração no CI.

**A interação com o versionamento é indireta, e é aqui que quase todo mundo erra o
diagnóstico:** o OIDC não sabe nem se importa com o número da versão. Ele autentica
*quem publica*. O que a doc de
[adicionar um publisher](https://docs.pypi.org/trusted-publishers/adding-a-publisher/) diz
é que a confiança é amarrada a "the repository owner's name, the repository's name, and the
filename of the GitHub Actions workflow", mais um Environment opcional que ela recomenda com
ênfase:

> "Configuring an environment is optional, but **strongly** recommended: with a GitHub
> Environment, you can apply additional restrictions to your trusted workflow, such as
> requiring manual approval on each run by a trusted subset of repository maintainers."

Três consequências de desenho:

1. **O nome do arquivo de workflow faz parte do contrato.** Renomear
   `.github/workflows/release.yml` quebra a publicação — e quebra num lugar onde a mensagem
   de erro não vai dizer "você renomeou um arquivo".
2. **O Environment com aprovação manual é a proteção que o versionamento manual quer.** Ele
   põe um humano entre "tag empurrada" e "artefato no PyPI" — que é exatamente o ponto em
   que um bump esquecido seria pego. Os dois se completam: manual + aprovação = duas
   chances de ver o número.
3. **Publicar exige `permissions: id-token: write` no job.** *Não confirmado nas duas
   páginas da doc do PyPI que consultei* — elas descrevem o fluxo OIDC sem mostrar o YAML.
   A afirmação está aqui como lembrete de verificação, não como fato citado.

Do lado do uv, nada a configurar: "For publishing to PyPI from GitHub Actions or another
Trusted Publisher, you don't need to set any credentials"
([uv, Packaging](https://docs.astral.sh/uv/guides/package/), consultada 2026-07-30). E o
`uv publish` "can automatically discover and upload attestations alongside distributions",
o que dá proveniência (PEP 740) de graça.

**Contexto que já é do repo, de #3, e que este eixo não pode ignorar:** *pending publisher*
**não reserva o nome** e expira em 30 dias; e o Curation do JFrog segura versão
recém-publicada por dias, devolvendo **403 como 404**. Ou seja: no caminho corporativo,
"a versão nova não aparece" **não é** sintoma de versionamento errado. Quem for depurar
publicação precisa dessa distinção antes de mexer no esquema de versão.

### 8.7 A asserção que fecha o buraco do versionamento manual

O único modo de falha real da recomendação é tag e `pyproject.toml` discordarem. Ele custa
uma linha de CI:

```yaml
- name: A tag tem que bater com a versão do projeto
  run: |
    test "v$(uv version --short)" = "${GITHUB_REF_NAME}" \
      || { echo "tag ${GITHUB_REF_NAME} != versão v$(uv version --short)"; exit 1; }
```

`uv version --short` imprime só o número — **[medido aqui]**, `0.1.0`. Com essa asserção, o
versionamento manual passa a ter a mesma garantia estrutural que o `hatch-vcs` dá de graça,
**sem** herdar o modo de falha silencioso do §8.4.

### 8.8 Custo, e custo de reverter

**Custo:** lembrar de bumpar. Mitigado pela asserção do §8.7 (falha ruidosa), pelo
Environment com aprovação (§8.6) e pelo `towncrier` (§9), que já obriga a mexer no release
no mesmo PR.

**Custo de reverter — e este é o argumento decisivo, porque a reversão é barata nos dois
sentidos.** Ir de manual para `hatch-vcs` é trocar `version = "..."` por
`dynamic = ["version"]`, somar duas tabelas e pôr `fetch-depth: 0` no checkout: **minutos**.
Voltar é o mesmo caminho ao contrário. Nenhuma das duas escolhas prende. Sendo assim, a
regra de decisão certa é **escolher a que falha mais alto agora** e trocar quando a
frequência de release justificar — que é exatamente o gatilho do §8.5.

---

## 9. CHANGELOG: `towncrier` × changesets × Keep a Changelog manual

### 9.1 Recomendação

**`towncrier`, configurado para emitir formato Keep a Changelog.** A pergunta do ticket
opõe três coisas que não estão no mesmo eixo: **Keep a Changelog é um formato de saída,
`towncrier` é o mecanismo de entrada, e changesets é do npm.** A resposta certa combina os
dois primeiros e descarta o terceiro.

### 9.2 As duas fontes primárias concordam contra a mesma coisa

Antes de escolher, vale registrar o que as duas docs oficiais **proíbem** — porque é a
opção que estaria mais à mão neste repo, que já usa Conventional Commits.

Keep a Changelog ([1.1.0](https://keepachangelog.com/en/1.1.0/), consultado 2026-07-30):

> "Using commit log diffs as changelogs is a bad idea: they're full of noise."

towncrier ([doc oficial](https://towncrier.readthedocs.io/en/stable/), consultada
2026-07-30), dizendo o mesmo por outro ângulo:

> "Rather than reading the Git history, or having one single file which developers all write
> to and produce merge conflicts, towncrier reads 'news fragments' which contain information
> useful to end users."
>
> "Towncrier delivers the news which is convenient to those that hear it, not those that
> write it."

**Consequência direta e um pouco contraintuitiva:** o repo usa Conventional Commits — este
documento mesmo é commitado assim — e isso **continua certo**, mas *não* é a fonte do
CHANGELOG. Conventional Commits organiza o histórico para quem desenvolve; changelog é para
quem instala. `git-cliff` e afins derivam o segundo do primeiro, e é exatamente essa
derivação que as duas fontes chamam de ruído. **Recomendo não usar changelog derivado de
commit**, e a razão não é minha, é das duas docs.

### 9.3 changesets: fora, e por duas razões

O README oficial ([changesets/changesets](https://raw.githubusercontent.com/changesets/changesets/main/README.md),
consultado 2026-07-30) se define como "A tool to manage versioning and changelogs with a
focus on monorepos", e o alvo é npm/JavaScript. Não há menção a Python.

1. **Ecossistema errado.** É um monorepo de `package.json`. O overpower é um pacote Python.
2. **Traz Node para o loop de desenvolvimento.** O motivo declarado do axioma 1
   (`docs/agents/domain.md`) é ambiental: *"o alvo de replicação é um ambiente corporativo
   sem esse ferramental"*. O axioma governa o **runtime**, não o dev loop, então isso **não
   é** violação de axioma — mas seria estranho um projeto cuja razão de existir é não
   depender de `npx` escolher uma ferramenta de `npx` para escrever o próprio changelog.

### 9.4 Keep a Changelog manual: o formato fica, o arquivo único não

O formato é bom e eu o adoto: as seis seções (`Added`, `Changed`, `Deprecated`, `Removed`,
`Fixed`, `Security`), a seção `Unreleased` no topo, versão mais nova primeiro, data
visível, seções linkáveis, e o princípio-raiz — "Changelogs are *for humans*, not machines."

O que não adoto é o **arquivo único editado à mão**, e a razão é específica deste repo,
não genérica.

O argumento normal contra o arquivo único é conflito de merge, e o contra-argumento normal é
"mas aqui é um mantenedor só, não há conflito". **Esse contra-argumento não vale aqui**, e
dá para ver isso olhando o repo: no momento desta pesquisa, o overpower tem **seis
worktrees simultâneas**, uma por agente, cada uma numa branch de pesquisa
(`git worktree list`, 2026-07-30). O modelo de trabalho deste projeto é *muitos escritores
paralelos em branches de vida curta* — que é literalmente a situação que o arquivo único
pune, com um mantenedor humano só. **O padrão de trabalho, não o tamanho do time, é o que
decide.**

### 9.5 `towncrier` medido, e a configuração recomendada

**[medido aqui]**, `towncrier 25.8.0`. Dois fragmentos e um `build --draft`:

```
$ cat changelog.d/2.added.md
Instala AI Frameworks curados com `uvx overpower install`.
$ cat changelog.d/5.fixed.md
Corrige symlink em Windows sob `core.symlinks=false`.

$ uvx towncrier build --draft --version 0.1.0
## [0.1.0] - 2026-07-30

### Added

- Instala AI Frameworks curados com `uvx overpower install`. ([#2](https://github.com/panlabs-tech/overpower/issues/2))

### Fixed

- Corrige symlink em Windows sob `core.symlinks=false`. ([#5](https://github.com/panlabs-tech/overpower/issues/5))
```

**Saída em Markdown, no formato Keep a Changelog, com link automático para a issue.** É a
prova de que os dois não competem: o `title_format` e os `[[tool.towncrier.type]]` fazem o
towncrier emitir exatamente o que o Keep a Changelog descreve.

E o link para a issue sai de graça do nome do arquivo, o que casa com o modelo de wayfinding
deste repo, onde **a decisão mora no ticket**. O CHANGELOG vira índice navegável do mapa.

```toml
[tool.towncrier]
name = "overpower"
directory = "changelog.d"
filename = "CHANGELOG.md"
title_format = "## [{version}] - {project_date}"
issue_format = "[#{issue}](https://github.com/panlabs-tech/overpower/issues/{issue})"

[[tool.towncrier.type]]
directory = "added"
name = "Added"
showcontent = true
# idem para changed, deprecated, removed, fixed, security — as seis do Keep a Changelog
```

Os tipos padrão do towncrier são `feature`, `bugfix`, `doc`, `removal`, `misc`; **substituo
pelos seis do Keep a Changelog**, porque o formato de saída é a decisão do §9.4 e o vocabulário
do leitor deve ser o dele.

**`towncrier check` como gate de PR**, com uma ressalva medida: ele compara contra uma base
git, então precisa de `--compare-with origin/main` e de um checkout que tenha essa
referência. **[medido aqui]**: rodado sem base válida, ele estoura um
`subprocess.CalledProcessError` do `git diff` — falha feia, mas falha, então não passa
despercebido. A doc descreve o outro lado: `towncrier check` "will fail if there are any
news fragment files that have invalid filenames".

### 9.6 Custo, e custo de reverter

**Custo:** um arquivo a mais por PR que muda comportamento, e o `towncrier check` reprovando
quem esquece. Para PR de refatoração pura, a saída é o `ignore` da config ou um fragmento
`misc`. **É cerimônia real, e é a recomendação mais "cara em fricção" deste documento.**

O contra-argumento honesto: enquanto a v0.1.0 não sair, **não há usuário para quem escrever
o changelog**, e todo fragmento é escrito para um leitor hipotético. Quem quiser adiar tem
um argumento defensável — e o custo de adiar é baixo, ver abaixo.

**Custo de reverter: assimétrico, e a favor de adotar.** Sair do `towncrier` para o arquivo
manual é rodar `towncrier build` uma última vez e apagar `changelog.d/` — **o CHANGELOG.md
já está escrito e continua válido**, porque a saída é Keep a Changelog puro. Entrar depois é
mais caro: o histórico anterior não vira fragmento retroativamente. E adotar changesets em
qualquer momento significa Node no dev loop. **O `towncrier` é a única das três opções cuja
saída sobrevive ao abandono da ferramenta.**

---

## 10. Piso de versão do Python em 2026

### 10.1 Recomendação

**`requires-python = ">=3.12"`, com `.python-version` em `3.14` e matriz de CI nas duas
pontas.**

A recomendação de fundo deste eixo não é o número — é a distinção que quase todo projeto
colapsa:

> **O piso é uma promessa de compatibilidade com quem instala. A versão de
> desenvolvimento é uma escolha de conforto de quem escreve. São decisões diferentes, com
> donos diferentes e gatilhos diferentes.** Um projeto exemplar declara as duas, e prova as
> duas no CI.

### 10.2 O calendário, que é fato e não opinião

[Status of Python versions](https://devguide.python.org/versions/), devguide oficial do
CPython, consultado **2026-07-30**:

| versão | status | lançamento | fim de vida |
| --- | --- | --- | --- |
| 3.15 | prerelease | *2026-10-01* | *2031-10* |
| **3.14** | **bugfix** | 2025-10-07 | *2030-10* |
| **3.13** | **bugfix** | 2024-10-07 | *2029-10* |
| 3.12 | security | 2023-10-02 | *2028-10* |
| 3.11 | security | 2022-10-24 | *2027-10* |
| 3.10 | security | 2021-10-04 | ***2026-10*** |
| 3.9 | **end-of-life** | 2020-10-05 | 2025-10-31 |

Duas leituras imediatas, e uma armadilha:

- **3.9 já morreu** (2025-10-31) e **3.10 morre em ~2 meses**. Qualquer piso em 3.10 ou
  abaixo nasce vencido. Isso elimina metade das opções sem discussão.
- **3.11 e 3.12 estão em fase de segurança**, não de correção. Só 3.13 e 3.14 recebem
  bugfix.
- **A armadilha:** o segundo ponto tenta a conclusão "então o piso deve ser 3.13". Ele não
  deve, e o §10.4 explica por quê — **a fase de suporte governa em que versão se
  desenvolve, não abaixo de qual não se instala.**

### 10.3 Por que o piso quase não importa aqui — e onde ele volta a importar

O `overpower` é invocado como `uvx overpower` (`docs/agents/domain.md`), e o `uv`
**provisiona o próprio interpretador**. A doc de [Python
versions](https://docs.astral.sh/uv/concepts/python-versions/) (consultada 2026-07-30):

> "uv instead uses pre-built distributions from the Astral `python-build-standalone`
> project."
>
> "By default, uv will automatically download Python versions when needed."

Ou seja, no caminho feliz o Python do sistema do usuário é **irrelevante**: o `uv` baixa um
compatível com o `requires-python`. Declarar `>=3.14` não deixaria ninguém de fora — só
faria o `uv` baixar 3.14.

**Onde volta a importar é o caminho corporativo, que é metade do destino do mapa.** Os
downloads vêm de releases do GitHub, e a doc oferece justamente os interruptores que um
ambiente fechado precisa:

- `python-downloads`: "By default, it is set to `automatic`; set to `manual` to only allow
  Python downloads during `uv python install`", mais a flag `--no-python-downloads`.
- `python-install-mirror`: "The provided URL will replace
  `https://github.com/astral-sh/python-build-standalone/releases/download` in download
  paths. Distributions can be read from a local directory by using the `file://` URL
  scheme."

A existência desses interruptores é a prova de que **o cenário "a máquina não baixa Python"
é real e previsto pela Astral**. Nele, o `uv` cai para o interpretador do sistema — e aí o
piso declarado decide entre funcionar e não funcionar.

**E o interpretador do sistema, no baseline corporativo mais comum, é 3.12.** O Ubuntu
24.04 LTS (noble) entrega `python3` na versão **3.12.3** ([packages.ubuntu.com/noble/python3](https://packages.ubuntu.com/noble/python3),
consultado 2026-07-30) — o mesmo número que esta máquina de pesquisa reporta em
`/usr/bin/python3` **[medido aqui]**.

**Este é o argumento inteiro do piso**, e ele é assimétrico: um piso em 3.13 quebra o
overpower numa máquina Ubuntu LTS sem download de Python, e **compra em troca apenas
açúcar de sintaxe**.

**Lacuna honesta:** a pesquisa de #3 provou o índice corporativo (PEP 503 atrás de HTTP
Basic, quatro formas de credencial), mas **não** testou provisionamento de interpretador
nesse ambiente. *Não confirmado*: se o Artifactory-alvo permite ou bloqueia o download do
`python-build-standalone`. **É a verificação que mais barato retira risco deste eixo**, e
cabe num ticket de uma linha.

### 10.4 O que se ganha subindo, e por que não paga

| subir para | o que entra | vale o piso? |
| --- | --- | --- |
| **3.12** | PEP 695 (`type` e parâmetros de tipo com sintaxe própria), PEP 698 `@override`, PEP 701 (f-string sem restrição), `itertools.batched`, `pathlib.Path.walk` | **Sim, é o piso.** `Path.walk` e `@override` são usados por código que copia árvore de arquivo e por hierarquia de comando. |
| 3.13 | PEP 696 (defaults em parâmetro de tipo), `warnings.deprecated`, REPL novo | Não como **piso**. Nada aqui é estrutural para um CLI que copia arquivo. |
| 3.14 | PEP 649/749 (anotações preguiçosas), PEP 750 (t-strings), PEP 758 (`except A, B` sem parênteses), PEP 779 (free-threading oficialmente suportado) | Não como **piso** — mas **sim como versão de desenvolvimento**, §10.5. |

Fonte das novidades de 3.14: [What's New In Python
3.14](https://docs.python.org/3/whatsnew/3.14.html), consultado 2026-07-30; lançamento em
**7 de outubro de 2025**.

Vale um comentário sobre a mais tentadora. PEP 649/749 faz as anotações deixarem de ser
avaliadas com pressa — "The annotations on functions, classes, and modules are no longer
evaluated eagerly" — o que torna o `from __future__ import annotations` desnecessário. É
uma melhoria real de ergonomia. **Mas ela é benefício de quem escreve, e o piso é promessa
para quem instala.** Com o piso em 3.12, o `from __future__ import annotations` continua no
topo dos arquivos, custa uma linha, e funciona nas duas pontas. Trocar compatibilidade
corporativa por uma linha a menos é um mau negócio.

### 10.5 Desenvolver em 3.14, declarar 3.12, provar as duas

```toml
# pyproject.toml
[project]
requires-python = ">=3.12"     # a promessa
```

```
# .python-version
3.14                            # o conforto — o uv respeita, e o uv init já gera este arquivo
```

E a matriz de CI **nas duas pontas, não no meio**: `3.12` (o piso, onde a promessa quebra
se quebrar) e `3.14` (a versão de dev, e a que vai virar piso um dia). Testar 3.13 no meio
custa um job e não descobre nada que os extremos não descubram.

Combinado com o `--resolution lowest-direct` do §4.2, o CI passa a provar **as duas
declarações de piso do projeto** — a de Python e a de dependência. São as duas promessas
que um `pyproject.toml` faz e que ninguém verifica.

**E o `requires-python` é fonte de verdade de mais gente do que parece.** A doc do ruff
sobre `target-version` recomenda explicitamente não duplicar o número:

> "If you're already using a `pyproject.toml` file, we recommend `project.requires-python`
> instead, as it's based on Python packaging standards, and will be respected by other
> tools."

**[medido aqui]**: num projeto com `requires-python = ">=3.12"` e **nenhum**
`target-version` declarado, o `ruff 0.16.1` reporta em `--show-settings`

```
linter.unresolved_target_version = 3.12
formatter.unresolved_target_version = 3.12
analyze.target_version = 3.12
```

Então **não escreva `target-version` no `[tool.ruff]`** — ele já lê o piso, e duplicar é
criar duas verdades que vão divergir no dia do bump.

O `pyright`, ao contrário, **não** infere: o `pythonVersion` do §6.6 precisa ser escrito à
mão, e precisa ser **3.12, o piso — não 3.14**. Um type checker rodando na versão de
desenvolvimento aceitaria alegremente `except A, B` sem parênteses e reprovaria o usuário,
não o autor.

### 10.6 Custo, e custo de reverter

**Custo do piso em 3.12:** perde-se t-strings, `except` sem parênteses e anotação
preguiçosa **no código publicado**. Custo real: um `from __future__ import annotations` por
arquivo, que o `ruff` (família `FA`, já no default) cobra sozinho.

**Custo de reverter — e aqui a assimetria inverte em relação aos outros eixos.** **Subir** o
piso é trivial e sempre permitido: `>=3.12` → `>=3.13` é um caractere, e o pior efeito é um
usuário antigo travar numa versão antiga do overpower, que é o comportamento correto do
resolvedor. **Descer** é que é caro: exige revisar todo o código escrito com sintaxe nova.

**Portanto, aqui e só aqui, a escolha conservadora é a certa** — o oposto de todos os
outros eixos deste documento, e vale dizer por quê: nos outros, o rigor é barato agora e
caro depois; **no piso de versão, a promessa é barata de apertar e cara de afrouxar.** É a
mesma lógica de assimetria, com o sinal trocado.

**Gatilho de reabertura, e ele tem data:** quando o 3.12 sair de suporte (**outubro de
2028**), ou quando o Ubuntu LTS seguinte virar o baseline corporativo, o piso sobe para o
que aquele LTS entregar. Até lá, `>=3.12`.

---

## 11. O `pyproject.toml` que sai deste documento

Consolidação das oito recomendações num arquivo só. Cada bloco aponta a seção que o
justifica. Isto **não é** o `pyproject.toml` final do overpower — as dependências de
runtime vêm de #3 e #4, e o ticket de estruturação é que escreve o arquivo de verdade.

```toml
[project]
name = "overpower"
version = "0.1.0"                       # §8 — literal, movida por `uv version --bump`
requires-python = ">=3.12"              # §10 — o piso; o ruff lê daqui sozinho
dependencies = [
  "typer>=0.27",                        # §escopo — fixado em #4
  "rich>=15",
  "questionary>=2.1",
  "prompt-toolkit>=3.0.53",             # #4 — pin direto, o questionary é frouxo demais
]

[project.scripts]
overpower = "overpower.cli:app"         # #3 — pacote == comando == overpower

[build-system]
requires = ["hatchling"]                # §escopo — fixado em #3 (force-include/artifacts)
build-backend = "hatchling.build"

# ---------------------------------------------------------------- §4
[tool.uv]
required-version = ">=0.11"

[dependency-groups]
dev = ["pytest>=9", "pytest-cov", "syrupy", "pytest-randomly", "ruff", "towncrier"]
typecheck = ["pyright"]                 # separado: arrasta Node

# ---------------------------------------------------------------- §5
[tool.ruff]
line-length = 88
src = ["src"]
# NÃO declarar target-version: o ruff infere de requires-python (§10.5, medido)

[tool.ruff.lint]
extend-select = [
  "E", "W", "F", "I", "N", "UP", "B", "SIM", "RUF",
  "PTH", "ANN", "TC", "S", "PT", "D",
  "EM", "TRY", "RSE", "RET",
  "T20", "ARG", "SLF", "TID", "INP",
  "C4", "C90", "PERF", "FURB", "PIE", "PL",
  "DTZ", "LOG", "G", "A", "ERA", "FBT",
]
ignore = ["D203", "D213", "FBT002", "TRY003"]

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.lint.flake8-tidy-imports.banned-api]                     # §6.5
"json.load"  = { msg = "use overpower.jsonio.load_json, que devolve object" }
"json.loads" = { msg = "use overpower.jsonio.loads_json, que devolve object" }

[tool.ruff.lint.per-file-ignores]
"src/overpower/jsonio.py" = ["TID251"]
"tests/**"                = ["S101", "D", "ANN", "SLF001", "PLR2004", "INP001"]

[tool.ruff.format]
docstring-code-format = true

# ---------------------------------------------------------------- §6
[tool.pyright]
include = ["src", "tests"]
typeCheckingMode = "strict"
pythonVersion = "3.12"                  # o PISO, não a versão de dev (§10.5)
venvPath = "."
venv = ".venv"

# ---------------------------------------------------------------- §7
[tool.pytest.ini_options]
minversion = "9.0"
testpaths = ["tests"]
addopts = "-ra --import-mode=importlib --cov-branch"
strict = true
filterwarnings = ["error"]
markers = ["slow: teste que toca rede ou muitos arquivos"]
required_plugins = ["pytest-cov", "syrupy", "pytest-randomly"]

[tool.coverage.run]
source_pkgs = ["overpower"]
branch = true
relative_files = true

[tool.coverage.report]
show_missing = true
fail_under = 0                          # catraca: sobe e nunca desce (§7.5)
exclude_also = ["if TYPE_CHECKING:", "raise NotImplementedError"]

# ---------------------------------------------------------------- §9
[tool.towncrier]
name = "overpower"
directory = "changelog.d"
filename = "CHANGELOG.md"
title_format = "## [{version}] - {project_date}"
issue_format = "[#{issue}](https://github.com/panlabs-tech/overpower/issues/{issue})"
# + um [[tool.towncrier.type]] para cada seção do Keep a Changelog
```

Arquivos irmãos: `.python-version` com `3.14` (§10.5), e `uv.lock` commitado (§4.2).

**Este bloco foi executado, não só escrito — [medido aqui].** Montei o `pyproject.toml`
acima num diretório com `src/overpower/jsonio.py`, `src/overpower/__init__.py` e
`tests/test_x.py`, e rodei:

```
$ uvx ruff check .
All checks passed!
$ uvx ruff format --check .
3 files already formatted
```

Com **720 regras habilitadas**, o `TID251` corretamente silencioso no módulo sancionado, e
o `INP001` corretamente silencioso em `tests/`. Foi essa execução que revelou o conflito
`INP001` × `importlib` do §5.1 — a config anterior deste documento estava errada.

**Os quatro comandos**, que são o CI inteiro e o dia a dia (§4.4 — por isso não há task
runner):

```
uv run ruff format --check .
uv run ruff check .
uv run --group typecheck pyright
uv run pytest
```

Mais os três jobs que provam o que ninguém prova:

```
uv sync --locked                             # §4.5 — lock não muda em silêncio
uv run --resolution lowest-direct pytest     # §4.2 — o piso de dependência é real
test "v$(uv version --short)" = "$GITHUB_REF_NAME"   # §8.7 — tag == versão
```

---

## 12. Riscos, lacunas e o que eu não confirmei

Registrado de propósito, para que ninguém trate inferência como achado.

1. **Provisionamento de interpretador no ambiente corporativo — a lacuna mais importante.**
   #3 provou o índice de pacotes; **ninguém testou se o Artifactory-alvo deixa o `uv` baixar
   o `python-build-standalone` do GitHub**. Se não deixar, o `uv` cai para o Python do
   sistema e o piso do §10 passa de teórico a decisivo. **Retirar esse risco custa um
   comando** nesse ambiente: `uv python list --all-versions`.

2. **`permissions: id-token: write`.** As duas páginas de trusted publishing que consultei
   descrevem o fluxo OIDC sem mostrar o YAML do job. Está no §8.6 como lembrete de
   verificação, **não** como fato citado.

3. **Cobertura como gate: a posição do §7.5 é minha.** A FAQ do coverage.py admite que a
   medição "isn't perfect" e aponta para *"Flaws in Coverage Measurement"*, mas **não achei
   declaração oficial** nem a favor nem contra usar um limiar como gate. O desenho de
   catraca é argumento, não citação.

4. **`select = ["ALL"]`: não achei recomendação contrária na doc da Astral.** O §5.3 o
   recusa por argumento operacional meu (upgrade de ferramenta quebrando CI), não por fonte.

5. **Os tempos do §6.7 medem partida, não escala.** Projeto de 2 arquivos. Eles **não**
   verificam a alegação de "10x - 100x" da doc do `ty`, e não devem ser citados como se
   verificassem.

6. **`hatch-vcs` e clone raso: medi com `git clone --depth 1` local, não com
   `actions/checkout` real.** O mecanismo é o mesmo (tag ausente), e os defaults do
   `actions/checkout` estão citados da fonte, mas a composição exata dos dois **não foi
   executada num runner**.

7. **O que muda se o conteúdo vendorizado sair para um pacote próprio.** Dois eixos
   reabrem juntos: workspaces do `uv` (§4.4) deixa de ser complexidade sem contraparte, e o
   `source_pkgs` da cobertura (§7.5) precisa de revisão. É a mudança estrutural mais
   provável do projeto, e vale reler estas duas seções quando ela vier.

8. **Nada aqui foi verificado contra o Windows.** Todas as medições são WSL2/Linux. O
   achado de #5 — três degraus de symlink no Windows, `core.symlinks=false` materializando
   arquivo-texto — sugere que a suíte vai precisar de um job Windows. **Este documento não
   tem dado sobre isso.**
