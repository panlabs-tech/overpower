# Empacotamento com uv, publicação no PyPI e o caminho do Artifactory

> Research de [Empacotamento com uv, publicacao no PyPI e o caminho do Artifactory](https://github.com/panlabs-tech/overpower/issues/3).
> Data da pesquisa: **2026-07-30**. Todas as afirmações abaixo citam a fonte que as possui.
> Versões de referência: `uv 0.11.7` (binário local usado nos testes) e `uv 0.12.0` (release mais recente, publicado em 2026-07-28 — <https://github.com/astral-sh/uv/releases/tag/0.12.0>).

---

## Veredito

**O caminho corporativo funciona, e foi provado — não inferido.** `uvx` resolve, autentica, baixa e executa a partir de um índice PEP 503 privado protegido por HTTP Basic, com quatro mecanismos de credencial distintos. O conteúdo vendorizado viaja no wheel e é lido em runtime por `importlib.resources` sem tocar em caminho de arquivo.

Três coisas que **não** são óbvias e que decidem o roteiro:

1. **`uv` não lê `pip.conf`.** O índice corporativo que o TI configurou para o `pip` não vale nada para o `uv`/`uvx`. Afirmação literal da Astral: *"uv does not read configuration files or environment variables that are specific to `pip`, like `pip.conf` or `PIP_INDEX_URL`."* — <https://docs.astral.sh/uv/pip/compatibility/>, acesso 2026-07-30.
2. **`uvx` ignora configuração de projeto.** Só lê `~/.config/uv/uv.toml` e `/etc/uv/uv.toml`. Um `[[tool.uv.index]]` no `pyproject.toml` do repositório do usuário é invisível para o `uvx`. — <https://docs.astral.sh/uv/concepts/configuration-files/>, acesso 2026-07-30, **confirmado empiricamente** (ver §6.4).
3. **O maior risco do caminho corporativo não é técnico, é de política.** O `JFrog Curation` tem uma condição chamada *"Package version is immature"* que bloqueia toda versão recém-publicada por N dias. Nenhum comando resolve isso — é conversa com o time de segurança. — <https://docs.jfrog.com/security/docs/list-of-available-conditions>, acesso 2026-07-30.

O nome **`overpower` está livre no PyPI e no TestPyPI** em 2026-07-30 (`GET https://pypi.org/simple/overpower/` → HTTP 404; idem `test.pypi.org`). Isso não o reserva — ver §5.2.

---

## 1. Método e o que foi provado empiricamente

O grosso desta pesquisa é doc oficial. Mas as afirmações de maior risco foram **executadas**, não lidas. O que rodou de fato:

- Um pacote de teste com layout `src/`, backend `hatchling`, um `[project.scripts]` cujo nome **difere** do nome do pacote, conteúdo em Markdown dentro da árvore do pacote, e conteúdo de **fora** da árvore trazido por `force-include`. Total: ~1,2 MB.
- `uv build` sobre ele, inspeção do `.whl` (nomes, tamanhos, método de compressão) e do `.tar.gz`.
- Um **índice PEP 503 mínimo servido em `127.0.0.1` atrás de HTTP Basic**, servindo aquele wheel, com log de qual requisição chegou com qual header `Authorization`.
- `uvx --from opdemo overpower-demo` contra esse índice, em seis configurações de credencial diferentes.

Os resultados aparecem inline, marcados como **[verificado]**.

---

## 2. Conteúdo vendorizado dentro do wheel

### 2.1 Onde o conteúdo tem de morar

**Dentro do diretório do pacote Python.** Não em `shared-data`, não em `.data/`. A spec do wheel diz que o `.data/` é para *"Any file that is not normally installed inside site-packages"* e que na instalação *"the contents of these subdirectories are moved onto their destination paths"* (<https://packaging.python.org/en/latest/specifications/binary-distribution-format/>, acesso 2026-07-30) — o que quebra `importlib.resources`, que só enxerga o que está dentro do pacote.

Layout recomendado:

```
src/overpower/
├── __init__.py
├── cli.py
└── frameworks/
    ├── mattpocock/…
    └── spec-kit/…
```

### 2.2 Escolha de build backend

| Backend | Traz conteúdo de dentro da árvore do pacote | Traz conteúdo de **fora** da árvore | Veredito |
| --- | --- | --- | --- |
| **hatchling** | sim, por default (respeita `.gitignore`) | sim — `force-include` e `artifacts` | **escolha recomendada** |
| `uv_build` | sim, se estiver em `src/<modulo>/` | **não existe mecanismo** | só se o conteúdo já mora lá dentro |
| `setuptools` | sim, via `package-data` / `include-package-data` | não diretamente | herança; sem razão para escolher hoje |

**hatchling.** A seleção default do target `wheel` é por travessia de diretório, não por extensão — Markdown e JSON dentro do pacote entram sozinhos. A doc lista a heurística literal (`<NAME>/__init__.py`, `src/<NAME>/__init__.py`, …) em <https://hatch.pypa.io/latest/plugins/builder/wheel/>. E: *"By default, Hatch will respect the first `.gitignore` or `.hgignore` file found in your project's root directory or parent directories."* — <https://hatch.pypa.io/latest/config/build/>, acesso 2026-07-30.

As duas escotilhas de escape, com a diferença exata entre elas:

- **`artifacts`** — opera dentro da árvore do projeto, sintaxe de glob, e **fura o filtro do `.gitignore`**. Literal: *"If you want to include files that are ignored by your VCS, such as those that might be created by build hooks, you can use the `artifacts` option. This option is semantically equivalent to `include`."* Além disso: *"Note that artifacts are not affected by the `exclude` option."*
- **`force-include`** — é um **mapa origem→destino**, não um glob, e é o **único** mecanismo que traz conteúdo de fora da raiz do projeto. Literal: *"The `force-include` option allows you to select specific files or directories from anywhere on the file system that should be included and map them to the desired relative distribution path."* e *"The contents of directory sources are recursively included."*

Ambos em <https://hatch.pypa.io/latest/config/build/>, acesso 2026-07-30.

**[verificado]** `force-include` mapeando um diretório irmão para dentro do pacote:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/opdemo"]

[tool.hatch.build.targets.wheel.force-include]
"vendor/spec-kit" = "opdemo/frameworks/spec-kit"
```

Resultado no `.whl`:

```
opdemo/frameworks/mattpocock/skills/foo/SKILL.md   raw=20       zip=22      method=8
opdemo/frameworks/spec-kit/COMMAND.md              raw=34       zip=34      method=8
opdemo/frameworks/spec-kit/big.bin                 raw=1621053  zip=1233110 method=8
```

`method=8` é `ZIP_DEFLATED` — o wheel comprime. O hatchling escreve com `zipfile.ZIP_DEFLATED` explicitamente (`backend/src/hatchling/builders/wheel.py`, classe `WheelArchive`). Markdown e JSON comprimem bem; 15 MB de texto tendem a virar 2–4 MB de download. O custo real fica no disco descompactado do venv, não na rede.

**`uv_build` não serve para o caso geral.** A lista completa de chaves de `[tool.uv.build-backend]` é `module-root`, `module-name`, `namespace`, `source-include`, `source-exclude`, `wheel-exclude`, `default-excludes`, `data` — e nada mais (<https://docs.astral.sh/uv/concepts/build-backend/> e `crates/uv-build-backend/src/settings.rs`, acesso 2026-07-30). Não há `force-include`, `artifacts`, `include`, `packages` nem `sources`. A própria Astral aponta a saída: *"While the backend supports a number of options for configuring your project structure, when build scripts or a more flexible project layout are required, consider using the hatchling build backend instead."*

> Nota de contexto: a partir do `uv 0.12.0`, `uv init` gera `[build-system]` com `uv_build` por default. Se o conteúdo dos frameworks for ficar fisicamente em `src/overpower/frameworks/`, o default serve. Se qualquer parte vier de fora (submodule, diretório irmão, geração no build), troque para `hatchling` **antes** de escrever o primeiro `pyproject.toml`, não depois.

### 2.3 A armadilha do `uv build`: o wheel sai do sdist

Literal da referência de CLI: *"By default, if passed a directory, `uv build` will build a source distribution ("sdist") from the source directory, and a binary distribution ("wheel") **from the source distribution**."* — <https://docs.astral.sh/uv/reference/cli/#uv-build>, acesso 2026-07-30.

**[verificado]** A saída do build confirma:

```
Building source distribution...
Building wheel from source distribution...
```

Consequência prática: **se um arquivo não entra no sdist, ele não entra no wheel.** Com `force-include` apontando para `vendor/`, o `vendor/` precisa estar no sdist. No teste, o sdist saiu com a árvore original preservada:

```
opdemo-0.0.1/src/opdemo/frameworks/mattpocock/skills/foo/SKILL.md
opdemo-0.0.1/vendor/spec-kit/COMMAND.md
opdemo-0.0.1/vendor/spec-kit/big.bin
```

`uv build --sdist --wheel` constrói **os dois direto da fonte**, o que mascara essa classe de erro. Prefira o default: ele é uma verificação implícita de que o sdist está completo.

Outras duas coisas do `uv build` que importam:

- `uv build --no-sources` — recomendado antes de publicar: *"When publishing a package, we recommend running `uv build --no-sources` to ensure that the package builds correctly when `tool.uv.sources` is disabled, as is the case when using other build tools, like `pypa/build`."* (<https://docs.astral.sh/uv/guides/package/>)
- O `uv build` cria um `.gitignore` no diretório de saída por default (`--no-create-gitignore` desliga). **[verificado]** — `dist/.gitignore` apareceu com 1 byte.

### 2.4 Limites do PyPI: 1 MB e 15 MB passam com folga

*"By default, PyPI limits the size of individual files to 100.0 MB."* e *"By default, PyPI limits the total size of all files in a project to 10.0 GB."* — <https://docs.pypi.org/project-management/storage-limits/>, acesso 2026-07-30. Confirmado em `warehouse/constants.py`: `MAX_FILESIZE = 100 * ONE_MIB`, `MAX_PROJECT_SIZE = 10 * ONE_GIB`.

Aumento de limite por arquivo exige ter **já publicado ao menos um release abaixo do limite** e abrir issue em `github.com/pypi/support` com o template `limit-request-file.yml`. Existe um teto não documentado para aumentos: `UPLOAD_LIMIT_CAP = ONE_GIB` (1 GiB) em `warehouse/constants.py`.

Único limite de metadata que existe: `Summary` = 512 caracteres (`warehouse/forklift/metadata.py`, `_LENGTH_LIMITS = {"summary": 512}`). O `Description`/README **não tem limite de caracteres**.

**Nada a pedir.** 15 MB é 15% do limite default.

### 2.5 Leitura em runtime: `importlib.resources`, nunca caminho de arquivo

**Por que `Path(__file__).parent` não serve.** Literal da doc do CPython: *"Resources and packages **do not** have to exist as physical files and directories on the file system: for example, a package and its resources can be imported from a zip file using `zipimport`."* — <https://docs.python.org/3/library/importlib.resources.html>, acesso 2026-07-30. E a sessão de exemplo da doc do `zipimport` mostra o `__file__` que não é caminho real:

```
>>> example.__file__
'example_archive.zip/example.py'
```

— <https://docs.python.org/3/library/zipimport.html>, acesso 2026-07-30. `open()` nesse caminho falha.

A API a usar:

```python
from importlib.resources import files

root = files("overpower") / "frameworks"          # Traversable
skill = root / "mattpocock" / "skills" / "foo" / "SKILL.md"
texto = skill.read_text(encoding="utf-8")
```

Métodos do `Traversable` (`importlib.resources.abc.Traversable`, adicionado em 3.11): `name`, `iterdir()`, `is_dir()`, `is_file()`, `joinpath(*segments)`, `__truediv__` (o operador `/`), `open(mode)`, `read_bytes()`, `read_text(encoding)`. **Não existe** `glob()`, `rglob()`, `exists()`, `stat()`, `walk()` nem escrita. Para varrer, é `iterdir()` + `is_dir()` recursivo.

`files()` e `as_file()` entraram em **3.9**. `as_file()` só passou a suportar **diretórios** em **3.12** (*"Added support for `traversable` representing a directory."*). As APIs legadas (`read_text`, `open_text`, `path`, `is_resource`, …) foram deprecadas em 3.11 e **des-deprecadas em 3.13**: *"These functions are no longer deprecated and are not scheduled for removal."* — <https://docs.python.org/3/whatsnew/3.13.html>. Só `contents()` segue deprecada, sem plano de remoção.

**Copiar uma árvore inteira para o disco alvo** — que é exatamente o que o `overpower` faz. Dois padrões, com o custo real de cada um lido do código do CPython (`Lib/importlib/resources/_common.py`):

```python
# Padrão A — as_file (Python >= 3.12). No caso comum é grátis.
from importlib.resources import files, as_file
import shutil

with as_file(files("overpower") / "frameworks" / "mattpocock") as src:
    shutil.copytree(src, dest, dirs_exist_ok=True)   # DENTRO do with
```

`as_file` é um `singledispatch`: para `pathlib.Path` ele faz `yield path` sem copiar nada; para qualquer outro `Traversable` (zip, namespace package) ele replica a árvore inteira num `TemporaryDirectory` que é **destruído ao sair do `with`** — daí o `copytree` ter de acontecer dentro do bloco.

```python
# Padrão B — walk manual. Evita a cópia dupla; funciona desde 3.9/3.11.
def copy_tree(src, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        target = dest / item.name
        if item.is_dir():
            copy_tree(item, target)
        else:
            target.write_bytes(item.read_bytes())
```

Duas armadilhas de performance que valem registro:

- **Não use namespace package (PEP 420) na raiz do conteúdo.** `NamespaceReader.files()` devolve um `MultiplexedPath`, que não é `pathlib.Path` — então `as_file` copia a árvore inteira para o tmp **mesmo instalado em disco solto**. Com 15 MB, isso é uma cópia completa por invocação.
- Para leitura pontual (um `.md`, um `.json`), **nunca** materialize: `read_text()` direto.

**[verificado]** Sob `uvx`, `files("opdemo") / "frameworks"` devolveu `PosixPath` — o wheel é descompactado num venv comum. Confirmado pela doc: *"When running a tool with `uvx`, a virtual environment is stored in the uv cache directory and is treated as disposable"* (<https://docs.astral.sh/uv/concepts/tools/>). Ou seja: **sob `uv`/`uvx` o cenário zip é teórico**. Ainda assim `importlib.resources` é a escolha certa — custa o mesmo em linhas de código, e cobre zipapp/shiv/pex e namespace packages, onde o cenário deixa de ser teórico. O setuptools recomenda explicitamente: *"It is strongly recommended that, if you are using data files, you should use `importlib.resources` to access them."* (<https://setuptools.pypa.io/en/latest/userguide/datafiles.html>).

---

## 3. O executável e a invocação canônica `uvx overpower`

### 3.1 `uvx <name>`: `<name>` é o **comando**, não o pacote

Literal: *"Run a command provided by a Python package. By default, the package to install is assumed to match the command name."* — <https://docs.astral.sh/uv/reference/cli/#uv-tool-run>, acesso 2026-07-30. E do guia: *"When `uvx ruff` is invoked, uv installs the `ruff` package which provides the `ruff` command. However, sometimes the package and command names differ."* — <https://docs.astral.sh/uv/guides/tools/>.

`uvx` é alias exato de `uv tool run`: *"a `uvx` alias is provided for `uv tool run` — the two commands are exactly equivalent."* (<https://docs.astral.sh/uv/concepts/tools/>).

**O que acontece se o console script tiver nome diferente do pacote — [verificado]:**

```
$ uvx --from opdemo opdemo
An executable named `opdemo` is not provided by package `opdemo`.
The following executables are available:
- overpower-demo

Use `uvx --from opdemo overpower-demo` instead.
```

O comando **falha** (exit non-zero). Comentário literal no código-fonte do uv (`crates/uv/src/commands/tool/run.rs`): *"If the user didn't use `--from` and the command isn't in the environment, we're now just invoking an arbitrary executable on the PATH and should exit instead."*

**Consequência travada para o overpower: pacote == comando == `overpower`, um único console script.** Qualquer divergência transforma a invocação canônica em `uvx --from overpower-cli overpower`, que é feia e ninguém vai lembrar.

Achado colateral do código: **o uv não lê `entry_points.txt` para decidir o que executar.** Há um TODO literal (`// TODO(zanieb): Determine the executable command via the package entry points`). Ele prepende o `bin/` do venv efêmero ao `PATH` e faz `Command::new(executable)` com a string que você digitou. O `entry_points.txt` importa porque o **build backend** o materializa como script no `bin/`; o uv só vê o resultado (e, para mensagens de erro, lê o `RECORD` do `.dist-info`, não o `entry_points.txt`).

### 3.2 `[project.scripts]`

```toml
[project.scripts]
overpower = "overpower.cli:main"
```

Semântica literal da PyPA: *"Executing this command will do the equivalent of `import sys; from spam import main_cli; sys.exit(main_cli())`"* (<https://packaging.python.org/en/latest/guides/writing-pyproject-toml/>) e *"The object reference points to a function which will be called with no arguments when this command is run. The function may return an integer to be used as a process exit code, and returning `None` is equivalent to returning `0`."* (<https://packaging.python.org/en/latest/specifications/entry-points/>), acesso 2026-07-30.

Portanto: `main()` sem argumentos; retorno `int` vira exit code; `None` vira `0`; `SystemExit` levantado lá dentro propaga (é o mecanismo do Click/Typer).

`[project.gui-scripts]` só difere no Windows (executável sem console, sem `sys.stdout`/`stderr` utilizáveis). Para CLI é sempre `[project.scripts]`.

### 3.3 A armadilha do cache do `uvx`

Literal: *"`uvx` will use the latest available version of the requested tool **on the first invocation**. After that, `uvx` will use the cached version of the tool unless a different version is requested, the cache is pruned, or the cache is refreshed."* — <https://docs.astral.sh/uv/concepts/tools/>, acesso 2026-07-30.

Um usuário que rodar `uvx overpower` hoje fica **preso naquela versão indefinidamente**. Não há TTL documentado. A invalidação é explícita: `@latest`, `--refresh`, `uv cache clean`, `--no-cache`.

Sintaxe de versão — **[verificado]** `uvx cowsay@6.1 -t ok` executou a versão pedida. Da doc: `command@<version>` e `command@latest`, com a ressalva *"the `@` syntax cannot be used for anything other than an exact version"*. O sufixo `@latest` também refresca o cache.

**Implicação para o README do overpower:** documentar `uvx overpower@latest` como a forma de atualizar, senão a base instalada congela na primeira versão que cada usuário tocou.

---

## 4. Publicação no PyPI

### 4.1 `uv publish` — o que faz, e o que não faz

Flags confirmadas no binário local (`uv publish --help`, uv 0.11.7) e na referência (<https://docs.astral.sh/uv/reference/cli/#uv-publish>):

| Flag | Env var | Nota |
| --- | --- | --- |
| `--publish-url` | `UV_PUBLISH_URL` | default `https://upload.pypi.org/legacy/` |
| `--token` / `-t` | `UV_PUBLISH_TOKEN` | equivale a `__token__` + token como senha |
| `--username` / `--password` | `UV_PUBLISH_USERNAME` / `UV_PUBLISH_PASSWORD` | |
| `--index <nome>` | `UV_PUBLISH_INDEX` | o índice precisa ter `publish-url` na config |
| `--check-url` | `UV_PUBLISH_CHECK_URL` | pula uploads duplicados; **é a URL do índice, não a de publicação** |
| `--trusted-publishing` | *(sem env var)* | `automatic` (default) / `always` / `never` |
| `--no-attestations` | `UV_PUBLISH_NO_ATTESTATIONS` | por default o uv sobe attestations PEP 740 que já existam |
| `--dry-run` | — | não sobe arquivo |

Os arquivos default são `dist/*`, *"Selects only wheels and source distributions and their attestations, while ignoring other files."*

Equivalência documentada na própria referência:

```bash
uv publish --index pypi
# ≡
uv publish --publish-url https://upload.pypi.org/legacy/ --check-url https://pypi.org/simple
```

**Onde ainda cabe `twine`.** A Astral posiciona o uv como substituto (*"A single tool to replace `pip`, `pip-tools`, `pipx`, `poetry`, `pyenv`, `twine`, `virtualenv`, and more."* — <https://docs.astral.sh/uv/>), e não recomenda twine em lugar nenhum da doc. As duas diferenças materiais, confirmadas em código-fonte e no README da PyPA:

1. **`uv publish` não faz o equivalente a `twine check`.** A função `validate` em `crates/uv-publish/src/lib.rs` é guardada por `if store.is_known_url(registry)` — para PyPI, nenhuma validação de metadata acontece antes do upload. Já a action `pypa/gh-action-pypi-publish` roda `twine check` por default (`verify-metadata`, `default: 'true'`).
2. **`uv publish` não gera attestations**, só sobe as que já existem. Literal: *"uv publish does not currently generate attestations; attestations must be created separately before publishing."* — <https://docs.astral.sh/uv/guides/package/>. A action da PyPA gera (`attestations`, `default: 'true'`).

Não há `--skip-existing` no `uv publish`; o mecanismo é `--check-url`.

**[verificado]** `uv publish --dry-run` sem credenciais em máquina local:

```
Checking 2 files against https://test.pypi.org/legacy/
Note: Neither credentials nor keyring are configured, and there was an error fetching the trusted publishing token.
error: Trusted publishing failed
  Caused by: No OIDC token discovered: are you in a supported trusted publishing environment?
```

Ou seja, `--trusted-publishing automatic` tenta OIDC primeiro e degrada. O default `Automatic` está no código (`crates/uv-configuration/src/trusted_publishing.rs`): *"Attempt trusted publishing when we're in a supported environment, continue if that fails. Supported environments include GitHub Actions and GitLab CI/CD."*

### 4.2 Trusted publishing e o caso "o projeto ainda não existe"

Trusted publishing troca um token OIDC efêmero do GitHub Actions por um token de API do PyPI de curta duração. *"using the OpenID Connect (OIDC) standard to exchange short-lived identity tokens between a trusted third-party service and PyPI"* — <https://docs.pypi.org/trusted-publishers/>, acesso 2026-07-30.

O token mintado dura **15 minutos** e é *"scoped to every project with a matching Trusted Publisher"* (<https://docs.pypi.org/trusted-publishers/internals/>). **Não é single-use** — é reutilizável dentro da janela.

**O ponto do ticket: projeto que ainda não existe.** A solução é o **pending publisher**:

> *"rather than having to manually upload a first release to 'prime' the project on PyPI, you can configure a 'pending' publisher that will create the project when used for the first time. 'Pending' publishers are converted into 'normal' publishers on first use, meaning that no further configuration is required."*
> — <https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/>, acesso 2026-07-30

O formulário fica **na barra lateral da conta**, não na do projeto (que não existe): **`https://pypi.org/manage/account/publishing/`** — rota confirmada em `warehouse/routes.py`: `"manage.account.publishing", "/manage/account/publishing/"`.

Campos (aba GitHub), de `warehouse/templates/manage/account/publishing.html`:

| Campo | Valor para o overpower | Obrigatório |
| --- | --- | --- |
| PyPI Project Name | `overpower` | sim |
| Owner | `panlabs-tech` | sim |
| Repository name | `overpower` | sim |
| Workflow name | `release.yml` — **o nome do arquivo**, não o `name:` do workflow | sim |
| Environment name | `pypi` | opcional, *"strongly encouraged"* |

Quatro restrições que a doc pública não deixa óbvias:

- **Um pending publisher NÃO reserva o nome.** Literal: *"A 'pending' publisher does not create a project or reserve a project's name until it is actually used to publish. If you create a 'pending' publisher but another user registers the project name before you actually publish to it, your 'pending' publisher will be invalidated."*
- **Expira em 30 dias.** Não está em `docs.pypi.org`; está no código: `PENDING_PUBLISHER_EXPIRY_DAYS = 30` e `PENDING_PUBLISHER_REMINDER_DAYS = 5` em `warehouse/oidc/tasks.py`, com tasks diárias registradas em `warehouse/oidc/__init__.py`. Feature mergeada em 2026-05-04 (`pypi/warehouse#19996`).
- **Máximo 3 por conta**, e exige e-mail primário verificado (`warehouse/accounts/views.py`: *"You can't register more than 3 pending trusted publishers at once."*).
- **Nome do publisher ≠ nome no metadata quebra feio.** Erro documentado: *"Non-user identities cannot create new projects. This was probably caused by successfully using a pending publisher but specifying the project name incorrectly."* O projeto é criado com o nome errado e é preciso deletá-lo — o que também deleta o publisher.

**2FA é obrigatório** na conta PyPI: *"Two-factor authentication is required on your PyPI account."* — <https://pypi.org/help/#twofa>.

### 4.3 O workflow

Workflow oficial da Astral, literal de <https://docs.astral.sh/uv/guides/integration/github/>, acesso 2026-07-30 — nenhuma credencial:

```yaml
name: "Publish release to PyPI"
on:
  push:
    tags:
      - v*
jobs:
  run:
    runs-on: ubuntu-latest
    environment:
      name: pypi
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v7
      - uses: astral-sh/setup-uv@08807647e7069bb48b6ef5acd8ec9567f424441b # v8.1.0
      - run: uv python install 3.13
      - run: uv build
      - run: uv run --isolated --no-project --with dist/*.whl tests/smoke_test.py
      - run: uv run --isolated --no-project --with dist/*.tar.gz tests/smoke_test.py
      - run: uv publish
```

Notas que valem:

- `id-token: write` é obrigatório, e *"you must provide this permission at either the job level (strongly recommended) or workflow level (discouraged)"* (<https://docs.pypi.org/trusted-publishers/using-a-publisher/>). Se faltar, o uv erra com a mensagem literal *"Failed to obtain OIDC token: is the `id-token: write` permission missing?"*.
- **Trusted publishing não funciona dentro de reusable workflow** (README da `pypa/gh-action-pypi-publish` e `docs.pypi.org/trusted-publishers/troubleshooting/`; rastreado em `warehouse#11096`).
- Rate limit de registro de publisher: **100 por dia** por usuário e por IP (<https://docs.pypi.org/trusted-publishers/troubleshooting/>).
- Se for usar `uv publish --index <nome>`, o `pyproject.toml` precisa estar presente no runner — *"you need to have a checkout step in a publish CI job"*.

### 4.4 sdist é obrigatório? Não. Mas publique.

O PyPI não exige sdist. A única regra sobre sdist no endpoint de upload é um **teto**, não um piso: `"Only one sdist may be uploaded per release."` (`warehouse/forklift/legacy.py`). E a API diz *"`filetype` must be set to the type of the artifact: `bdist_wheel` or `sdist`"* (<https://docs.pypi.org/api/upload/>).

A PyPA recomenda em linguagem forte: *"even for a pure Python project, you should always upload both an sdist and a wheel"* — <https://packaging.python.org/en/latest/discussions/package-formats/>, acesso 2026-07-30.

Para o overpower: publique os dois. O default do `uv build` já faz isso, e o wheel-a-partir-do-sdist é a verificação de que o conteúdo vendorizado está completo (§2.3).

---

## 5. Reserva do nome

### 5.1 Normalização

Dois nomes são o mesmo projeto se normalizam igual: `re.sub(r"[-_.]+", "-", name).lower()`. `Overpower`, `over-power`, `over_power` e `over.power` colidem todos com `overpower`. — <https://packaging.python.org/en/latest/specifications/name-normalization/>, acesso 2026-07-30.

### 5.2 O nome está livre — e o que isso significa

**[verificado]** 2026-07-30: `https://pypi.org/simple/overpower/` → HTTP 404; `https://test.pypi.org/simple/overpower/` → HTTP 404.

Um pending publisher **não reserva nada** (§4.2). A única coisa que reserva o nome é **um upload bem-sucedido**. É exatamente o que o ticket [Reservar o nome no PyPI e provar o pipeline ponta a ponta](https://github.com/panlabs-tech/overpower/issues/13) existe para fazer, e é a razão de ele rodar cedo.

---

## 6. O caminho do Artifactory

### 6.1 Como o Artifactory espelha o PyPI

Três tipos de repositório (<https://docs.jfrog.com/artifactory/docs/pypi-repositories>, acesso 2026-07-30):

- **local** — pacotes da própria organização.
- **remote** — proxy com cache de um registry externo. **É este que espelha o pypi.org**, e é um cache *preguiçoso*: só busca o que alguém pede.
- **virtual** — agrega os outros sob uma única URL. É o que o dev normalmente recebe do TI.

O remote tem dois campos distintos: **URL** (`https://files.pythonhosted.org/`, onde estão os arquivos) e **Registry URL** (`https://pypi.org/`, onde está o índice).

URL de índice que o cliente usa, literal: *"when using pip to resolve PyPI packages it must point to `<Artifactory URL>/api/pypi/<repository key>/simple`"*. Isto é:

```
https://<host>/artifactory/api/pypi/<repo-key>/simple
```

Para **upload** em um repo local, a URL é a mesma **sem** o `/simple`: `https://<host>/artifactory/api/pypi/<repo-key>` (confirmado pelo `.pypirc` de exemplo na doc).

O JFrog documenta suporte a **`uv` 0.8.15+** (instala e publica), além de pip 20.2+, Poetry 1.2.0+ e Twine 3.3.0+.

### 6.2 Autenticação: identity token, não API key

**API key está morta.** Literal: *"API key has reached End of Life at the end of Q4, 2024."* e *"As of Artifactory version 7.98, you will not be able to create new API keys through UI or API."* — <https://docs.jfrog.com/user-management/docs/api-key>, acesso 2026-07-30.

O substituto é **identity token** (JWT longo) ou **reference token** (string de 64 caracteres, pensada para clientes que engasgam com senhas longas). Obtenção: Web UI → **Edit Profile** → **Generate an Identity Token** → *"You now have a one-time chance to copy the token text"*. Alternativa: **Set Me Up** no menu do usuário, que gera o token e já entrega o snippet pronto.

A doc do JFrog embute a credencial na URL:

```ini
[global]
index-url = https://<USER>:<TOKEN>@<host>/artifactory/api/pypi/<REPO>/simple
```

`.netrc` é suportado para pip. **Twine não lê `.netrc`** — literal: *"The Twine client is not compatible with `.netrc` credentials."*

### 6.3 Como apontar o `uv`/`uvx` para o índice corporativo — **[verificado ponta a ponta]**

Este é o coração do ticket. Foi executado contra um índice PEP 503 real com HTTP Basic, servindo o wheel de teste.

| # | Mecanismo | Resultado |
| --- | --- | --- |
| 1 | sem credencial | **falha**, com hint preciso do uv |
| 2 | credencial embutida na URL do índice | **instalou e executou** |
| 3 | `UV_DEFAULT_INDEX="corp-pypi=<url>"` + `UV_INDEX_CORP_PYPI_USERNAME` / `_PASSWORD` | **instalou e executou** |
| 4 | `~/.config/uv/uv.toml` com `[[index]]` nomeado + credenciais por env | **instalou e executou** |
| 5 | mesma config, sem credenciais, com `authenticate = "always"` | **falha rápida**, antes de qualquer requisição |
| 6 | `.netrc` via `NETRC` | **instalou e executou** |

Saída do caso 1:

```
× No solution found when resolving tool dependencies:
╰─▶ Because opdemo was not found in the package registry and you require
    opdemo, we can conclude that your requirements are unsatisfiable.

    hint: An index URL (http://127.0.0.1:8731/simple/) could not be queried
    due to a lack of valid authentication credentials (401 Unauthorized).
```

Saída do caso 5:

```
error: Failed to fetch: `http://127.0.0.1:8731/simple/opdemo/`
  Caused by: Missing credentials for http://127.0.0.1:8731/simple/opdemo/
```

O log do servidor confirmou header `Authorization` válido em **todas** as requisições dos casos 2, 3, 4 e 6 — tanto na página `/simple/opdemo/` quanto no download do `.whl`.

**A regra de normalização do nome do índice**, literal: *"`UV_INDEX_INTERNAL_PROXY_USERNAME` and `UV_INDEX_INTERNAL_PROXY_PASSWORD` environment variables, where `INTERNAL_PROXY` is the uppercase version of the index name, with non-alphanumeric characters replaced by underscores"* — <https://docs.astral.sh/uv/concepts/indexes/>, acesso 2026-07-30. Verificado: índice `corp-pypi` → `UV_INDEX_CORP_PYPI_USERNAME`.

**A sintaxe `<name>=<url>` funciona em env var e na linha de comando**, e é o que permite usar as credenciais por env sem arquivo de configuração:

```bash
UV_DEFAULT_INDEX="corp-pypi=https://host/artifactory/api/pypi/pypi-virtual/simple"
```

Literal: *"When providing an index on the command line (with `--index` or `--default-index`) or through an environment variable (`UV_INDEX` or `UV_DEFAULT_INDEX`), names are optional but can be included using the `<name>=<url>` syntax"* — <https://docs.astral.sh/uv/concepts/indexes/>. (A nota *"Index names are not supported as values"* na referência de `--index` fala de **referenciar** um nome já definido, não de defini-lo inline. O teste 3 desfaz a ambiguidade.)

O uv também tem um store de credenciais próprio: `uv auth login` / `logout` / `token` / `dir` — **[verificado]** presente em 0.11.7. Documentado em <https://docs.astral.sh/uv/concepts/authentication/cli/>: *"At this time, only HTTPS Basic authentication is supported."*

### 6.4 Os dois achados que mudam o roteiro

**(a) `uv` não lê `pip.conf`.** Literal: *"uv does not read configuration files or environment variables that are specific to `pip`, like `pip.conf` or `PIP_INDEX_URL`."* — <https://docs.astral.sh/uv/pip/compatibility/>, acesso 2026-07-30. A doc lista os motivos (compatibilidade bug-a-bug, travamento no formato do pip, etc.).

Isso significa: numa máquina corporativa onde o `pip install` já funciona contra o Artifactory, **`uvx overpower` vai tentar o PyPI público e falhar** se a saída para a internet estiver bloqueada. Não é bug; é o desenho. Tem que configurar o uv separadamente.

**(b) `uvx` ignora configuração de projeto.** Literal: *"For `tool` commands, which operate at the user level, local configuration files will be ignored. Instead, uv will exclusively read from user-level configuration (e.g., `~/.config/uv/uv.toml`) and system-level configuration (e.g., `/etc/uv/uv.toml`)."* — <https://docs.astral.sh/uv/concepts/configuration-files/>, acesso 2026-07-30. Confirmado no código (`crates/uv/src/lib.rs`):

```rust
} else if matches!(&*cli.command, Commands::Tool(_) | Commands::Self_(_)) {
    // For commands that operate at the user-level, ignore local configuration.
    FilesystemOptions::user()...combine(FilesystemOptions::system()...)
}
```

**[verificado]** Um `uv.toml` no diretório corrente com um índice default bogus foi **ignorado** — o `uv tool run` foi ao PyPI real. Já um `~/.config/uv/uv.toml` (via `XDG_CONFIG_HOME`) foi respeitado.

Duas consequências:

- Config de usuário para `uvx` **tem que ser `uv.toml`**, nunca `pyproject.toml`: *"User- and system-level configuration files cannot use the `pyproject.toml` format."* E o cabeçalho de tabela é `[[index]]`, **sem** o prefixo `tool.uv`.
- Não dá para pinar `overpower` a um índice nomeado via `tool.uv.sources` no contexto de `uvx`: *"Named indexes referenced via `tool.uv.sources` must be defined within the project's `pyproject.toml` file; indexes provided via the command-line, environment variables, or user-level configuration will not be recognized."* — <https://docs.astral.sh/uv/concepts/indexes/>.

### 6.5 Precedência e comportamento entre índices

Precedência para `uvx`: **CLI > env vars > `~/.config/uv/uv.toml` > `/etc/uv/uv.toml`**. O nível "project" não existe.

`default = true` num índice **remove o PyPI da resolução**: *"The default index is always treated as lowest priority"* e *"To exclude PyPI from the list of indexes, set `default = true` on another index entry"*. Um índice sem `default` é **adicional** e tem prioridade sobre o default.

Estratégia default `first-index`: *"uv will stop at the first index on which a given package is available, and limit resolutions to those present on that first index. This prevents 'dependency confusion' attacks."* As alternativas (`unsafe-first-match`, `unsafe-best-match`) têm "unsafe" no nome de propósito.

Detalhe operacional que morde no diagnóstico: *"When using the first-index strategy, uv will stop searching across indexes if an HTTP 401 Unauthorized or HTTP 403 Forbidden status code is encountered."* e *"uv will always continue searching across indexes when it encounters a `404 Not Found`. This cannot be overridden."* — <https://docs.astral.sh/uv/concepts/indexes/>.

Credenciais **não são cacheadas entre invocações**: *"Authentication is not cached across invocations of uv."* — <https://docs.astral.sh/uv/concepts/authentication/http/>.

### 6.6 Os quatro atrasos possíveis entre publicar e instalar

Este é o material de diagnóstico mais valioso da pesquisa. Fontes JFrog, acesso 2026-07-30.

| Barreira | Espera | Sintoma | Contorno |
| --- | --- | --- | --- |
| Nome nunca pedido naquele Artifactory | ~imediato | — | — |
| **404 em cache** (negative caching) | **1800 s = 30 min** | 404 / "não encontrado" | Zap Cache, ou esperar |
| **Índice `/simple` em cache** (versão nova de projeto já conhecido) | **até 7200 s = 2 h** | a versão não aparece na lista | Zap Cache |
| **Curation "immature package"** | **dias** (configurável) | **403** — ou **404**, se via virtual repo | waiver com o time de segurança |

**Negative caching — `missedRetrievalCachePeriodSecs`, default 1800 s.** Literal: *"If a remote repository is missing a requested artifact, Artifactory will return a '404 Not found' error. This response is cached for the period of time specified by this parameter."* (<https://docs.jfrog.com/artifactory/docs/remote-repositories>). Consequência prática, e é o conselho mais acionável da pesquisa: **não rode `pip install overpower` antes de publicar.** Um pedido prematuro envenena o cache negativo por 30 minutos, à toa.

**Metadata cache — `retrievalCachePeriodSecs`.** Aqui **duas docs oficiais divergem**: <https://docs.jfrog.com/artifactory/docs/remote-repositories> diz *"The default Metadata Retrieval Cache Period is 2 hours (7,200 seconds) for most remote repository types"*, enquanto <https://docs.jfrog.com/installation/docs/repositories-configurations-in-artifactory-yaml> lista `Default: 600`. **Assuma 2 h e confirme no repositório concreto da empresa.** O Artifactory cacheia sim a página `/simple` do projeto — as release notes registram que *"Response times for api/pypi/simple were reduced on PyPI remote repositories by caching the translated package and repository indexes."*

**Zap Cache** — <https://docs.jfrog.com/artifactory/reference/zapCache>, disponível desde Artifactory 7.49.3, exige permissão *Manage* ou *Delete* no remote:

```bash
curl -X POST https://<host>/artifactory/api/zap/<repo>-cache/<path> \
  -H "Authorization: Bearer <TOKEN>"
```

Note o sufixo `-cache` no path: zapeia-se o **cache do remote**, não o remote. Semântica: *"Zapping the cache invalidates all cached metadata artifacts … so they are re-fetched from the upstream on the next request."* e *"Immutable binaries are not invalidated."* Isto é: **Zap Cache resolve cache, e só cache.**

### 6.7 Bloqueios de política corporativa

**JFrog Curation** é bloqueio no momento do download, por policy — *"preventing risky dependencies from entering repositories before they are even used"* (<https://docs.jfrog.com/security/docs/curation-intro>). Aplica-se a **remotes com cache habilitado**; repositórios virtuais não são alvo direto.

A condição que mais provavelmente vai morder o overpower: **`"Package version is immature — Blocks 3rd party packages whose version release date is less than the defined number of dates old"`** (sic, no original) — <https://docs.jfrog.com/security/docs/list-of-available-conditions>. É uma política deliberada de *time-delay*: segura toda versão recém-publicada por N dias para dar tempo de um pacote envenenado ser sinalizado. O número de dias é configurável pelo admin; a doc de referência **não fixa um default**. Materiais JFrog citam **14 dias** como valor típico, mas isso não está em página de referência — trate como ordem de grandeza.

**Nenhum comando resolve.** Não é cache. É espera ou waiver.

**Bloqueio por licença: existe.** As condições legais são *"Block list by License"* e *"Allow list by License"*. O modo *allow list* é o perigoso para o overpower: se a empresa mantém uma lista de licenças permitidas e o pacote tem licença ausente ou não reconhecida, ele cai fora da lista e é bloqueado. Não há condição nomeada especificamente para `NOASSERTION` — o efeito vem do allow list. Isto conversa diretamente com o **risco de redistribuição aceito** registrado no mapa: declarar a licença do overpower corretamente e carregar os `LICENSE`/`NOTICE` upstream não é só higiene jurídica, é requisito de instalabilidade no ambiente alvo.

**403 vira 404 dentro de virtual repos** — a armadilha de diagnóstico. Literal: *"If the artifact is blocked by the curation policy, Artifactory returns 403 (Blocked)."* mas também *"If the artifact does not exist (404), Artifactory moves to the next remote"* e *"If no remotes resolve the artifact, a 404 Not Found response is returned."* (<https://docs.jfrog.com/security/docs/how-to-manage-virtual-repository-behavior-and-curation-in-jfrog-xray>). Ou seja: **"pacote não existe" pode significar "bloqueado por política"**. Rode `jf ca` (curation-audit do JFrog CLI) antes de concluir que é cache.

**Compliant Version Selection** — outra fonte de confusão: com essa opção ativa, *"Curation automatically serves the highest compliant version instead of failing the request"*. O cliente pode receber silenciosamente uma versão **mais antiga** em vez de um erro (<https://docs.jfrog.com/security/docs/fallback-behavior-for-blocked-packages>).

**Include/Exclude Patterns** filtram por padrão Ant-like: *"Filtering works by subtracting the excluded patterns (default is none) from the included patterns (default is all)."* Em repositórios PyPI os patterns operam sobre o caminho de **metadata**, não sobre o nome do arquivo, e são **case-sensitive**.

**Limite de tamanho de artefato: não encontrado.** Busca em fonte primária JFrog não achou nenhuma configuração de limite máximo de tamanho de artefato em remote repositories de PyPI. O que existe: SaaS com default de 25 GB de upload, UI limitada a 100 MB, e limites de proxy/WAF na frente do Artifactory — que não são config do Artifactory. **Para 1–15 MB isso é irrelevante.**

**Bloqueio de sdist e permissão só de wheel: não existe.** Revisada a lista completa de condições do Curation, **nenhuma opera sobre formato de distribuição ou tipo de arquivo**. Exclude patterns em tese casariam com `*.tar.gz`, mas em PyPI eles atuam sobre metadata, não sobre nomes de artefato. Se esse requisito aparecer, o lugar dele é no cliente (`pip install --only-binary=:all:`), não no Artifactory.

---

## 7. Roteiro executável

O roteiro assume `uv` instalado (`curl -LsSf https://astral.sh/uv/install.sh | sh`) e conta PyPI com 2FA.

### Fase 0 — `pyproject.toml` mínimo

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "overpower"
version = "0.0.1"
description = "Instala AI Frameworks curados num repositório ou na máquina"
readme = "README.md"
requires-python = ">=3.10"
license = "MIT"                     # declare — o allow-list de licença do Curation depende disso (§6.7)
license-files = ["LICENSE", "NOTICE"]

[project.scripts]
overpower = "overpower.cli:main"    # nome do comando == nome do pacote (§3.1)

[tool.hatch.build.targets.wheel]
packages = ["src/overpower"]

# só se algum conteúdo vier de fora da árvore do pacote (§2.2)
# [tool.hatch.build.targets.wheel.force-include]
# "vendor/spec-kit" = "overpower/frameworks/spec-kit"
```

```python
# src/overpower/cli.py
def main() -> int:      # sem argumentos; int vira exit code, None vira 0 (§3.2)
    ...
    return 0
```

### Fase 1 — Registrar o pending publisher (antes de existir projeto no PyPI)

1. Ir a **<https://pypi.org/manage/account/publishing/>** (barra lateral da **conta**, não de projeto).
2. Aba **GitHub**, preencher:
   - PyPI Project Name: `overpower`
   - Owner: `panlabs-tech`
   - Repository name: `overpower`
   - Workflow name: `release.yml` *(o nome do arquivo)*
   - Environment name: `pypi`
3. **Add**.
4. Criar o environment `pypi` em Settings → Environments do repo GitHub.

Prazo: **publicar em até 30 dias**, ou o pending publisher é deletado (aviso por e-mail 5 dias antes). O pending publisher **não reserva o nome** — quem reserva é o primeiro upload.

Opcional e recomendado: repetir tudo no **TestPyPI** (`https://test.pypi.org/manage/account/publishing/`) para um ensaio sem consumir o nome real.

### Fase 2 — O workflow de release

`.github/workflows/release.yml` — o nome do arquivo **tem** que bater com o registrado na Fase 1:

```yaml
name: Publish release to PyPI
on:
  push:
    tags: ["v*"]

jobs:
  publish:
    runs-on: ubuntu-latest
    environment:
      name: pypi
      url: https://pypi.org/p/overpower
    permissions:
      id-token: write      # obrigatório para OIDC; mantenha no job, não no workflow
      contents: read
    steps:
      - uses: actions/checkout@v7
      - uses: astral-sh/setup-uv@v8
        with:
          version: "0.12.0"
      - run: uv build --no-sources
      # smoke test do artefato real, antes de publicar
      - run: uv run --isolated --no-project --with dist/*.whl -- overpower --version
      - run: uv publish
```

`uv publish` sem credencial nenhuma: `--trusted-publishing automatic` (default) detecta o ambiente e troca o token OIDC.

### Fase 3 — Publicar a `0.0.1` e reservar o nome

```bash
git tag v0.0.1 && git push origin v0.0.1
```

Verificações imediatas:

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://pypi.org/simple/overpower/   # espera 200
```

O pending publisher agora virou publisher normal, e o nome está reservado.

**Publicação manual, se precisar** (não é o caminho recomendado, mas é o fallback):

```bash
uv build --no-sources
uv publish --token pypi-XXXX                      # ou UV_PUBLISH_TOKEN
uv publish --check-url https://pypi.org/simple    # para retomar upload interrompido
```

### Fase 4 — Validar o lado público

```bash
# a invocação canônica, sem cache, do PyPI público
uvx --no-cache overpower --version

# smoke test de import isolado
uv run --isolated --no-project --with overpower -- python -c "import overpower; print(overpower.__file__)"

# se o cache atrapalhar
uvx overpower@latest --version
uv cache clean overpower
```

Checar que o conteúdo vendorizado chegou:

```bash
uv run --isolated --no-project --with overpower -- python -c \
  "from importlib.resources import files; print(sorted(p.name for p in (files('overpower')/'frameworks').iterdir()))"
```

### Fase 5 — Validar o lado Artifactory

**5a. Obter as credenciais.** Web UI do Artifactory → **Edit Profile** → **Generate an Identity Token** (cópia única). Ou **Set Me Up**, que já entrega o snippet.

**5b. Descobrir a URL do índice.** Formato: `https://<host>/artifactory/api/pypi/<repo-key>/simple`. O `<repo-key>` costuma ser o **virtual** repo (ex.: `pypi-virtual`, `pypi-remote`).

**5c. Configurar o `uv` — e lembrar que `pip.conf` não vale (§6.4).** Escolha uma das três formas:

*Forma A — arquivo de usuário, a mais durável. `~/.config/uv/uv.toml` (Windows: `%APPDATA%\uv\uv.toml`):*

```toml
[[index]]
name = "corp-pypi"
url = "https://<host>/artifactory/api/pypi/<repo-key>/simple"
default = true              # remove o PyPI público da resolução
authenticate = "always"     # falha rápido em vez de vazar requisição sem credencial
```

com as credenciais fora do arquivo:

```bash
export UV_INDEX_CORP_PYPI_USERNAME='<usuario>'
export UV_INDEX_CORP_PYPI_PASSWORD='<identity-token>'
```

> O nome do índice vira `UV_INDEX_<NOME>_...` em maiúsculas, com não-alfanuméricos virando `_`: `corp-pypi` → `CORP_PYPI`.
> O arquivo de usuário usa `[[index]]`, **sem** o prefixo `tool.uv` — e **tem** que ser `uv.toml`, não `pyproject.toml`.

*Forma B — só variáveis de ambiente, sem arquivo:*

```bash
export UV_DEFAULT_INDEX="corp-pypi=https://<host>/artifactory/api/pypi/<repo-key>/simple"
export UV_INDEX_CORP_PYPI_USERNAME='<usuario>'
export UV_INDEX_CORP_PYPI_PASSWORD='<identity-token>'
```

*Forma C — `.netrc`, se a política proibir credencial em variável de ambiente:*

```
machine <host>
login <usuario>
password <identity-token>
```

Todas as três **[verificadas]** contra um índice autenticado real (§6.3).

**5d. Se houver TLS inspection no proxy corporativo:**

```bash
export UV_SYSTEM_CERTS=true          # usa o certificate store nativo do SO
# ou
export SSL_CERT_FILE=/caminho/ca-bundle.pem
export HTTPS_PROXY=http://proxy.corp:3128
```

**5e. Instalar e executar:**

```bash
uvx --no-cache overpower --version           # a invocação canônica
uv tool install overpower                    # instalação persistente; retém as settings do install
```

> `uv tool upgrade` **retém as settings do install**: *"tool upgrades will retain the settings provided when installing the tool."* Ou seja, o índice configurado no `uv tool install` continua valendo no upgrade.

### Fase 6 — Diagnóstico quando o lado corporativo falha

Rode nesta ordem. Cada passo elimina uma hipótese.

```bash
# 1. o uv está mesmo indo ao índice certo? (-v mostra as URLs consultadas)
uvx -v --no-cache overpower --version 2>&1 | grep -i 'http\|index'
```

| Sintoma | Hipótese | Ação |
| --- | --- | --- |
| Foi ao `pypi.org` em vez do Artifactory | config não aplicada — provavelmente está num `pyproject.toml`, que o `uvx` **ignora** | mover para `~/.config/uv/uv.toml` (§6.4b) |
| `Missing credentials for …` | `authenticate = "always"` e nenhuma credencial encontrada | conferir a normalização `UV_INDEX_<NOME>_...` |
| `401 Unauthorized` | credencial inválida ou expirada | regenerar identity token |
| `403 Forbidden` | **Curation bloqueou** | `jf ca`; falar com segurança |
| `404` / "not found in the package registry", pacote existe no PyPI | (a) cache negativo de 30 min, (b) 403 do Curation mascarado por virtual repo | esperar 30 min → Zap Cache → `jf ca` |
| Versão nova não aparece, versões antigas sim | metadata cache do `/simple` (até 2 h) | Zap Cache |
| Instalou, mas veio versão antiga | Compliant Version Selection do Curation | `jf ca`; falar com segurança |

```bash
# 2. o índice enxerga o projeto?
curl -s -u '<usuario>:<token>' https://<host>/artifactory/api/pypi/<repo>/simple/overpower/

# 3. invalidar cache do remote (precisa de Manage/Delete no repo)
curl -X POST -H "Authorization: Bearer <TOKEN>" \
  https://<host>/artifactory/api/zap/<repo>-cache/overpower
```

**Regra de ouro: não teste `pip install overpower` antes de publicar.** O 404 fica em cache por 30 minutos.

---

## 8. O que fica em aberto

Coisas que a pesquisa não conseguiu fechar em fonte primária, e que só o ambiente real responde:

1. **Default efetivo do `retrievalCachePeriodSecs`** — duas docs oficiais da JFrog divergem (600 vs 7200). Ver no repositório concreto da empresa.
2. **Se o Artifactory da empresa roda Curation, e com qual janela de "immature package"** — a doc de referência não fixa default. Este é o único risco capaz de tornar o caminho corporativo inviável por dias, e não há contorno técnico.
3. **Se o proxy/WAF na frente do Artifactory impõe limite de tamanho** — não é config do Artifactory, então não aparece na doc dele. Um wheel de 15 MB é o caso a testar.
4. **Se o Artifactory aceita attestations PEP 740** — se rejeitar, `uv publish --no-attestations` resolve, mas isso só importa se um dia se publicar *no* Artifactory (o cenário do mapa é publicar no PyPI e consumir do Artifactory).

## 9. Impacto nos axiomas do mapa

Nenhum axioma foi contrariado. Dois ficam **reforçados** por evidência:

- **Axioma 5 (conteúdo vendorizado).** Confirmado viável e barato: 15 MB é 15% do limite do PyPI, o wheel comprime, e `importlib.resources` lê tudo sem materializar. O `force-include` do hatchling resolve o caso de conteúdo fora da árvore do pacote.
- **Axioma 1 (autocontido).** O `uvx` não precisa de nada além do próprio `uv` para funcionar contra índice privado — nenhum instalador de terceiro entra na jogada.

Uma consequência nova, que não estava enunciada: **declarar licença corretamente deixou de ser só higiene jurídica.** O `Allow list by License` do JFrog Curation pode bloquear um pacote cuja licença não esteja na lista da empresa (§6.7). Isso conecta o "risco de redistribuição aceito" do mapa ao ticket de layout dos assets — o `NOTICE` com estado de licença por framework tem valor operacional, não só de compliance.

---

## Fontes

Todas acessadas em **2026-07-30**.

**Astral / uv**
`docs.astral.sh/uv/`, `/concepts/indexes/`, `/concepts/authentication/http/`, `/concepts/authentication/cli/`, `/concepts/configuration-files/`, `/concepts/tools/`, `/concepts/build-backend/`, `/concepts/cache/`, `/guides/package/`, `/guides/tools/`, `/guides/integration/github/`, `/reference/cli/`, `/reference/environment/`, `/pip/compatibility/`.
Código: `astral-sh/uv` — `crates/uv/src/lib.rs`, `crates/uv-cli/src/lib.rs`, `crates/uv/src/commands/tool/run.rs`, `crates/uv-tool/src/lib.rs`, `crates/uv-publish/src/lib.rs`, `crates/uv-configuration/src/trusted_publishing.rs`, `crates/uv-build-backend/src/settings.rs`.
Binário: `uv 0.11.7` local (`uv tool run --help`, `uv publish --help`, `uv build --help`, `uv auth --help`).

**PyPI / PyPA**
`docs.pypi.org/trusted-publishers/` (+ `creating-a-project-through-oidc/`, `using-a-publisher/`, `internals/`, `security-model/`, `troubleshooting/`), `/project-management/storage-limits/`, `/api/upload/`, `pypi.org/help/#twofa`.
Código: `pypi/warehouse` — `routes.py`, `constants.py`, `accounts/views.py`, `oidc/tasks.py`, `oidc/__init__.py`, `forklift/legacy.py`, `forklift/metadata.py`, `templates/manage/account/publishing.html`.
`packaging.python.org` — `/specifications/entry-points/`, `/specifications/pyproject-toml/`, `/specifications/name-normalization/`, `/specifications/binary-distribution-format/`, `/guides/writing-pyproject-toml/`, `/discussions/package-formats/`.
`pypa/gh-action-pypi-publish` — `README.md`, `action.yml`.

**Python**
`docs.python.org/3/library/importlib.resources.html`, `/importlib.resources.abc.html`, `/zipimport.html`, `/whatsnew/3.13.html`. Código: `cpython` — `Lib/importlib/resources/_common.py`, `Lib/importlib/resources/readers.py`, `Lib/zipimport.py`.

**Build backends**
`hatch.pypa.io/latest/config/build/`, `/plugins/builder/wheel/`; `pypa/hatch` — `backend/src/hatchling/builders/wheel.py`. `setuptools.pypa.io/en/latest/userguide/datafiles.html`.

**JFrog**
`docs.jfrog.com/artifactory/docs/pypi-repositories`, `/remote-repositories`, `/repository-management-overview`, `/reference/zapCache`; `docs.jfrog.com/security/docs/curation-intro`, `/list-of-available-conditions`, `/how-to-manage-virtual-repository-behavior-and-curation-in-jfrog-xray`, `/connect-remote-repositories-to-curation`, `/fallback-behavior-for-blocked-packages`, `/block-downloads-from-cached-remote-repositories`, `/supported-technologies`; `docs.jfrog.com/user-management/docs/api-key`, `/administration/docs/security-configuration`, `/installation/docs/repositories-configurations-in-artifactory-yaml`; `jfrog.com/help/r/platform-api-key-deprecation-and-the-new-reference-tokens/…`.
