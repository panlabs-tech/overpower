# CLI Python de alto impacto visual — findings e recomendação de stack

Resolve a [issue #4](https://github.com/panlabs-tech/overpower/issues/4).
Data da pesquisa: **2026-07-30**. Todas as versões e URLs foram consultadas nesta data.

**Regra de evidência deste documento.** Cada afirmação é ou (a) **fonte primária** — doc
oficial do projeto, código-fonte no repo oficial, metadata do PyPI, docs.python.org — com
URL e versão, ou (b) **[medido aqui]** — experimento reproduzível que eu rodei nesta
máquina, com o comando registrado. Onde não achei fonte primária, está escrito
**não confirmado em fonte primária** em vez de preenchido por inferência.

Ambiente das medições: `uv 0.11.7`, CPython 3.14.4 (interpretador gerenciado pelo uv),
Linux 6.6.87.2-microsoft-standard-WSL2 (WSL2), conexão doméstica rápida.

---

## 1. Resumo executivo

**A stack recomendada é `typer` + `rich` + `questionary`, com `questionary` em import
tardio, banner ASCII hardcodado (sem `pyfiglet`), e teste em três camadas com `syrupy`.**

| papel | escolha | versão hoje | por quê, em uma linha |
| --- | --- | --- | --- |
| Parsing e subcomandos | **typer** | 0.27.0 | Único com `CliRunner` oficial de stdout/stderr separados; vendoriza click, então zero risco de conflito de versão. |
| Renderização | **rich** | 15.0.0 | Já vem com o typer. Cidadania de terminal completa e documentada. |
| Wizard interativo | **questionary** | 2.1.1 | Seleção com setas, que é o que dá a sensação de `npx vercel`. Importado só no ramo interativo. |
| Arte ASCII | **string no código** | — | `pyfiglet` custa 1,72 MiB de wheel para uma decisão que se toma uma vez. |
| Snapshot de teste | **syrupy** | 5.5.3 | Uma dependência, 55 KB, e serializa saída multilinha em bloco legível. |
| Full-screen TUI | **não usar `textual`** | — | +147 ms de import por invocação num comando que roda e sai. |

**Os cinco achados que decidem o desenho.**

1. **`typer` deixou de depender de `click` — ele o vendoriza.** Desde a 0.26.0
   (2026-05-26). Isso mata a classe inteira de dor "typer preso a uma faixa de versões do
   click", e dá ao typer um `CliRunner` próprio com `stdout`, `stderr` e `output`
   independentes. É a razão principal de escolher typer sobre cyclopts. Ver §4.
2. **Nenhuma biblioteca de prompt degrada sozinha sem TTY.** Todas levantam exceção —
   `questionary` e `rich.prompt` com traceback cru, inclusive quando há `default=`
   declarado. **O gate de `isatty()` é responsabilidade do overpower**, não da biblioteca,
   e o mantenedor do `prompt_toolkit` diz isso com todas as letras. E `textual` é pior que
   todos: sem TTY ele **não falha, ele pendura o processo**. Ver §6.
3. **`rich.Progress` degrada perfeitamente sozinho.** Sem TTY ele imprime uma única linha
   final em vez de animar; com `transient=True` não imprime **nada**. Log de CI limpo de
   graça. Ver §7.
4. **A saída rica é testável sem fragilidade.** `typer.testing.CliRunner` captura o
   `Console` de módulo, separa stdout de stderr, e `COLUMNS` no `env=` fixa a largura do
   rich. Provei que trocar a cor da marca não quebra nenhum teste. Ver §8.
5. **O peso da stack completa é aceitável: +0,55 s de cold start** sobre um CLI de zero
   dependências, e +0,04 s com cache quente. O que pesa não é o typer — é o `pygments`
   (1,20 MB, arrastado pelo rich) e o `prompt_toolkit` (+63 ms de import), e este último
   se evita com import tardio. Ver §9.

**Uma decisão de pin que não é opcional.** `prompt_toolkit 3.0.53`, publicada em
**2026-07-26 — quatro dias antes desta pesquisa** — é a primeira versão em que o caso
"sem TTY" no macOS vira `EOFError` em vez de `OSError [Errno 22]` cru. CHANGELOG oficial:
*"Treat OSError on add_reader as EOFError (macOS kqueue)."* Sem esse pin, um `except
EOFError` defensivo simplesmente não pega no macOS. Ver §6.5.

---

## 2. O que o ticket pedia, e onde está a resposta

| pergunta da issue #4 | seção |
| --- | --- |
| `typer` × `click` × `cyclopts` × `argparse` | §4 |
| `rich` × `textual` | §5 |
| Wizard `questionary`/`InquirerPy`/`rich.prompt`, degradando sem TTY | §6.1–6.2 |
| A convenção `--yes` em fontes de primeira parte | §6.3 |
| O pin de `prompt_toolkit` e a convivência com o rich | §6.6–6.7 |
| `NO_COLOR`, `FORCE_COLOR`, TTY, pipe, largura, CI, Windows | §7.1–7.3, §7.5–7.6 |
| Progresso, spinners, árvore de arquivos | §7.4, §12.3 |
| Testabilidade sem fragilidade estética | §8 |
| Como testar o ramo interativo do wizard | §8.7 |
| Peso de dependência e cold start | §9 |
| Arte ASCII e identidade | §10 |
| Referências vivas (`npx vercel`, `uv`, `gh`) | §11 |
| Exemplos concretos de código para o protótipo (#12) | §12 |
| Riscos e o que não foi confirmado | §13, §16 |

---

## 3. Como reproduzir as medições

Todos os experimentos citados como **[medido aqui]** são scripts curtos e independentes.
Os padrões usados:

```bash
# custo de instalação com cache do uv realmente vazio
rm -rf ./cache ./venv && uv venv -q ./venv
time uv pip install -q --cache-dir ./cache --python ./venv/bin/python typer questionary

# custo de import por invocação: wall time do processo, melhor de N
python -c "import subprocess,time; ..."   # ver §9

# uvx ponta a ponta com cache frio
rm -rf ./xcache && time uvx --cache-dir ./xcache --from ./pkgs/full opfull

# matriz de cidadania de terminal
env NO_COLOR=1 python -c "from rich.console import Console; c=Console(); print(c.is_terminal, c.color_system, c.no_color, c.width)"

# PTY real, para ver o que só existe com terminal de verdade
script -qec "python app.py install matt-pocock" /dev/null | od -c
```

---

## 4. Parsing e estrutura: typer × click × cyclopts × argparse

### 4.1 O fato que reordena a comparação: typer vendorizou o click

Release notes oficiais do typer, seção `## 0.26.0 (2026-05-26)`, PR #1774
([docs/release-notes.md](https://raw.githubusercontent.com/fastapi/typer/0.27.0/docs/release-notes.md)):

> **Typer no longer depends on Click as a third party dependency, it vendors (includes
> the source code of) Click.** […] This also means that Click-specific functionality is
> no longer supported, like extracting the Click app and adding Click-specific plug-ins,
> or customizing the field types with Click-specific types.

Confirmado na metadata do PyPI — `requires_dist` literal de `typer 0.27.0`:

```
['shellingham>=1.3.0', 'rich>=13.8.0', 'annotated-doc>=0.0.2',
 'colorama; platform_system == "Windows"']
```

`click` não está lá. **[medido aqui]** Num venv com `typer` instalado, `import click`
falha com `ModuleNotFoundError`, e existe `typer/_click/` com `LICENSE.txt` da Pallets
(BSD-3, "Copyright 2014 Pallets"). O cabeçalho de
[`typer/_click/__init__.py`](https://github.com/fastapi/typer/blob/master/typer/_click/__init__.py)
declara a versão embutida:

```python
"""
Code taken and adapted from Click: https://github.com/pallets/click/releases/tag/8.3.1
"""
```

**Consequência para o overpower.** Qualquer material que descreva typer como "um wrapper
fino do click" está desatualizado desde 2026-05-26. E o plano de fuga "uso typer e caio
pro click quando precisar de algo específico" **não existe mais**. Em compensação, some
o histórico de pins tipo `"📌 Pin max version of Click to >= 8.2.1, < 8.4 temporarily to
prevent incompatibilities. PR #1753"` (release notes 0.26.0) — exatamente a dor que o
vendoring elimina.

### 4.2 Metadata e peso

| | typer 0.27.0 | click 8.4.2 | cyclopts 4.22.3 | argparse |
| --- | --- | --- | --- | --- |
| `requires_python` | `>=3.10` | `>=3.10` | `>=3.10` | — |
| deps transitivas | 6 | 0 | 7 | 0 |
| soma dos wheels | **1,70 MiB** | 116 KiB | **2,14 MiB** | 0 |
| depende de `rich` | sim, dura | não | sim, dura | — |
| depende de `click` | **não** (vendoriza) | — | não | — |
| runner de teste oficial | `typer.testing.CliRunner` | `click.testing.CliRunner` | **nenhum** | nenhum |
| última release | 2026-07-15 | 2026-06-24 | 2026-07-30 | — |
| releases totais | 88 | 64 | 150 | — |

Fontes: `https://pypi.org/pypi/{typer,click,cyclopts}/json` consultados em 2026-07-30;
tamanhos de `urls[].size` do wheel `py3-none-any`.

`requires_dist` literal do `cyclopts 4.22.3` (runtime, sem os markers `extra ==`):

```
['attrs>=23.1.0', 'docstring-parser<4.0,>=0.15', 'rich-rst<3.0.0,>=1.3.1',
 'rich>=13.6.0', 'tomli>=2.0.0; python_version < "3.11"',
 'typing-extensions>=4.8.0; python_version < "3.11"']
```

`rich` é dependência **dura** nos dois, não extra. E `rich 15.0.0` arrasta
`markdown-it-py>=2.2.0` e `pygments>=2.13.0,<3.0.0` — o pygments sozinho são **1,20 MB de
wheel**, 69% do peso de download da opção typer.

### 4.3 O `rich` não é carregado no `import` — só quando renderiza

**[medido aqui]**, e é o achado que desarma o medo de peso:

```python
import typer, sys
'rich' in sys.modules          # False
'pygments' in sys.modules      # False
'typer.rich_utils' in sys.modules  # False
'typer._click' in sys.modules  # True
```

O mesmo vale para cyclopts. O import de `rich_utils` no typer é tardio, dentro de
`format_help` ([typer/core.py](https://raw.githubusercontent.com/fastapi/typer/0.27.0/typer/core.py)):

```python
if not HAS_RICH or self.rich_markup_mode is None:
    ...
    return super().format_help(ctx, formatter)
from . import rich_utils
return rich_utils.rich_format_help(obj=self, ctx=ctx, markup_mode=self.rich_markup_mode)
```

E existe um kill-switch documentado, no mesmo arquivo:

```python
HAS_RICH = parse_boolean_env_var(os.getenv("TYPER_USE_RICH"), default=True)
```

Doc oficial ([docs/tutorial/commands/help.md](https://raw.githubusercontent.com/fastapi/typer/0.27.0/docs/tutorial/commands/help.md)):

> You can disable rich text formatting by setting `rich_markup_mode` to `None` for your
> specific app. Alternatively, you can disable it globally using an environmental
> variable `TYPER_USE_RICH` set to `False` or `0`.

Para o cyclopts **não achei equivalente em fonte primária**. O `help_formatter="plain"`
documentado em
[help_customization.rst](https://raw.githubusercontent.com/BrianPugh/cyclopts/v4.22.3/docs/source/help_customization.rst)
muda a aparência, não o custo de import.

### 4.4 Testabilidade oficial — o critério que decide

Esta é a diferença material entre as três.

**typer** — runner próprio desde 0.26.3, em
[`typer/testing.py`](https://raw.githubusercontent.com/fastapi/typer/0.27.0/typer/testing.py).
O `Result` carrega os três fluxos separados:

```python
class Result:
    @property
    def output(self) -> str:   # stdout + stderr intercalados, como o usuário vê
    @property
    def stdout(self) -> str:
    @property
    def stderr(self) -> str:
```

E o `isolation()` fixa a largura do help durante a invocação:

```python
old_forced_width = formatting.FORCED_WIDTH
formatting.FORCED_WIDTH = 80
```

**click** — `click.testing.CliRunner`, mais rico (tem `isolated_filesystem()` e, desde
8.4.0, `capture="fd"`), mas com uma quebra que ainda machuca quem tem teste antigo.
[CHANGES.md](https://github.com/pallets/click/blob/main/CHANGES.md), `## Version 8.2.0`
(2025-05-10):

> Keep stdout and stderr streams independent in `CliRunner`. Always collect stderr output
> and never raise an exception. Add a new output stream to simulate what the user sees in
> its terminal. **Removes the `mix_stderr` parameter in `CliRunner`.**

Três armadilhas concretas daí: `CliRunner(mix_stderr=False)` vira `TypeError`;
`result.output` **deixou de ser proxy de `stdout`** e virou stdout+stderr intercalados,
o que muda o significado de testes existentes **em silêncio**; e `result.stderr` vazio
não levanta mais `ValueError`.

**cyclopts** — **não oferece runner de teste.** A doc oficial
([unit_testing.rst](https://raw.githubusercontent.com/BrianPugh/cyclopts/v4.22.3/docs/source/cookbook/unit_testing.rst))
manda usar `pytest.raises(SystemExit)` + `capsys`, e injetar um `rich.console.Console`
fixo à mão para testar o help. Ela também documenta uma armadilha própria:

> A common mistake is accidentally calling `app()` or `app.parse_args()` with the intent
> of providing no arguments. Calling these methods with no arguments will read from
> `sys.argv` […] and Cyclopts **will produce a warning**.

### 4.5 O que o cyclopts tem de melhor, e por que ainda não ganha

Dois recursos genuinamente superiores, ambos documentados:

**Lazy loading por string de import**
([lazy_loading.rst](https://raw.githubusercontent.com/BrianPugh/cyclopts/v4.22.3/docs/source/lazy_loading.rst)):

```python
user_app.command("myapp.commands.users:create")   # módulo só carrega ao executar
```

> This defers importing command modules until they are actually executed, which could
> significantly improve CLI startup time […] Parent `--help` displays lazy commands using
> metadata provided at registration time **without** resolving them.

**Não confirmado em fonte primária** um equivalente oficial em typer ou click.

**Flattening de sub-app** com `app.command(tools_app, name="*")`
([commands.rst](https://raw.githubusercontent.com/BrianPugh/cyclopts/v4.22.3/docs/source/commands.rst)).

**Mas os contras pesam mais para este projeto:**

- Sem runner de teste oficial — e testabilidade é o critério declarado do ticket.
- **Bus factor 1** (autor único) com **150 releases** e um ramo `5.0.0a7` em alpha desde
  2026-06-23, sinalizando breaking changes. Nove releases nos últimos 38 dias.
- Known issue oficial que morde um projeto Python moderno
  ([known_issues.rst](https://raw.githubusercontent.com/BrianPugh/cyclopts/v4.22.3/docs/source/known_issues.rst)):
  > Cyclopts can only support some scenarios surrounding PEP-0563, the stringization of
  > type hints via `from __future__ import annotations`. Notably, this can also sometimes
  > break `dataclass` definitions when inheritance from multiple python modules is involved.
- 2,14 MiB de wheels contra 1,70 MiB, por causa do `rich-rst` extra.

### 4.6 E o argparse, que é de graça?

O argparse ficou melhor: desde Python 3.14 ele colore o help por padrão
([docs.python.org/3/library/argparse.html](https://docs.python.org/3/library/argparse.html)):

> `color` - Allow color output (default: True). **Changed in version 3.14:**
> `suggest_on_error` and `color` parameters were added.

Mas a mesma doc registra uma armadilha séria para um CLI que grava log:

> Error messages will include color codes when redirecting stderr to a file. To avoid
> this, set the `NO_COLOR` or `PYTHON_COLORS` environment variable (for example,
> `NO_COLOR=1 python script.py 2> errors.txt`).

Ou seja: **argparse em 3.14 emite ANSI mesmo com stderr redirecionado**, o oposto do que
o rich faz. Somado à ausência de qualquer utilitário de teste e ao trabalho manual de
subcomandos aninhados, o argparse não serve a um CLI cujo requisito declarado é impacto
visual. Fica registrado como o piso: `>=3.10` no overpower significa que nem essa
melhoria de 3.14 estaria garantida.

### 4.7 Veredito

**typer**, por três razões nesta ordem: (1) `CliRunner` oficial com stdout/stderr
separados, que é o que torna a suíte de testes sustentável; (2) vendoring do click, que
elimina a superfície de conflito de versão numa lib publicada no PyPI; (3) menor peso
entre as opções que dão help rico.

**Risco aceito e registrado:** typer está em refatoração estrutural agora. A 0.27.0
(2026-07-15) tem, nas Breaking Changes, `💥 Update metavar printing. PR #1863` — o que
**quebra qualquer snapshot de `--help`** ao subir de 0.26.x. Isso é gerenciável porque o
snapshot é a camada 2 da estratégia de teste (§8), atualizável com uma flag.

---

## 5. Renderização: `rich`, e onde `textual` seria exagero

`rich 15.0.0` já entra na árvore como dependência dura do typer, então o custo marginal
de adotá-lo é **zero**.

`textual` é a ferramenta errada aqui, por quatro razões, em ordem de gravidade.

**1. Sem TTY, `App.run()` pendura o processo.** Este é o argumento que encerra a
discussão, porque viola direto o requisito do ticket. Um `App` mínimo rodado com
`printf '' | python app.py` e com `< /dev/null` foi **morto por timeout em ambos os
casos**, depois de despejar ~2 KB de escape sequences cruas dentro do pipe — alt screen
(`\x1b[?1049h`), mouse tracking, posicionamento absoluto de cursor. Não levanta
`EOFError`, não devolve default, **não termina**. A causa está em
[`drivers/linux_driver.py`](https://github.com/Textualize/textual/blob/main/src/textual/drivers/linux_driver.py):
ele **calcula** `self.input_tty = sys.__stdin__.isatty()`, mas nenhum caminho de `run()`
aborta com base nisso.

**2. Custo de import.** **[medido aqui]**, wall time do processo, melhor de 7:

| | ms | delta sobre interpretador vazio |
| --- | --- | --- |
| interpretador vazio | 11,0 | — |
| `import rich.console` | 37,8 | +26,8 |
| `import textual.app` | **158,4** | **+147,3** |

Pagar +147 ms de event loop em toda invocação de um comando que roda e sai, para depois
não usar tela cheia, é custo sem contrapartida.

**3. Superset estrito do rich, sem ganho de snapshot.** `textual 8.2.8` tem
`rich>=14.2.0` como dep dura. E o `App.export_screenshot()` — a base de toda a infra de
snapshot do textual — é **literalmente a receita do rich**
([app.py](https://github.com/Textualize/textual/blob/main/src/textual/app.py)):

```python
console = Console(
    width=width, height=height, file=io.StringIO(),
    force_terminal=True, color_system="truecolor",
    record=True, legacy_windows=False, safe_box=False,
)
...
return console.export_svg(title=title or self.title)
```

Um app rich puro já tem 100% dessa capacidade sem instalar textual.

**4. O plugin de snapshot é armadilha.** `pytest-textual-snapshot` — que a doc do textual
chama de *"The official Textual pytest plugin"* — **pina `syrupy==4.8.0`** no
`requires_dist`, contra a 5.5.3 atual, e sua fixture só aceita `textual.app.App`. Última
release `v1.1.0` em 2025-01-23. Detalhes em §8.4.

**Não confirmado em fonte primária:** qualquer página oficial do Textual comparando
"quando usar Textual vs quando usar Rich". O FAQ, a homepage e o guide não têm essa
entrada.

`textual` se justificaria se o overpower fosse um navegador de catálogo persistente. Não é
o desenho.

---

## 6. O wizard, e a degradação sem TTY

Este é o requisito concreto do ticket: um wizard que pergunta **projeto ou global** e que
degrada quando não há TTY.

### 6.1 Nenhuma biblioteca degrada sozinha

**[medido aqui]** — cada chamada rodada num subprocesso com `stdin=DEVNULL`:

| chamada | exit | resultado |
| --- | --- | --- |
| `questionary.select(...).ask()` | 1 | `EOFError` (traceback cru) |
| `questionary.select(...).unsafe_ask()` | 1 | `EOFError` |
| `questionary.confirm(...).ask()` | 1 | `EOFError` |
| `rich.prompt.Prompt.ask(...)` | 1 | `EOFError: EOF when reading a line` |
| `rich.prompt.Prompt.ask(..., default="projeto")` | 1 | **`EOFError` mesmo com default** |
| `rich.prompt.Confirm.ask(..., default=True)` | 1 | **`EOFError` mesmo com default** |
| `typer.confirm(...)` (click vendorizado) | 1 | `Abort` |
| `typer.prompt(...)` | 1 | `Abort` |
| `InquirerPy inquirer.select().execute()` | 1 | `EOFError` |
| `textual App.run()` | **124** | **TRAVA PARA SEMPRE** + despeja ANSI no pipe |

Nem `questionary` nem `InquirerPy` contêm **uma única** chamada a `isatty` no código de
decisão — `grep -rn isatty` nos dois pacotes instalados retorna zero ocorrências.

E há um quarto estado, distinto de "pipe": **fd 0 fechado** (`app 0<&-`), onde
`sys.stdin is None`. Aí `sys.stdin.isatty()` levanta `AttributeError`, `rich` e `click`
levantam `RuntimeError: lost sys.stdin`, e `questionary` levanta
`AttributeError: 'NoneType' object has no attribute 'fileno'`. **Nenhum dos quatro trata.**

Dois resultados contrariam a intuição comum e precisam ficar registrados:

1. **`questionary.ask()` não devolve `None` sem TTY.** O código é explícito
   ([question.py](https://github.com/tmbo/questionary/blob/master/questionary/question.py)):

   ```python
   def ask(self, patch_stdout=False, kbi_msg=DEFAULT_KBI_MESSAGE):
       try:
           return self.unsafe_ask(patch_stdout)
       except KeyboardInterrupt:
           print("{}".format(kbi_msg))
           return None
   ```

   Só `KeyboardInterrupt` é capturado. `EOFError` **propaga** nos dois métodos. A
   diferença `ask()` × `unsafe_ask()` é *só* sobre Ctrl-C, não sobre TTY. A doc oficial
   não menciona TTY, pipe ou EOF em lugar nenhum — `grep -i "tty\|EOF\|pipe"` no README e
   no CHANGELOG retorna zero.

2. **`rich.prompt` ignora o `default=` no EOF.** Ele imprime o prompt no stdout —
   sujando o log — e depois estoura. A causa está no fonte
   ([prompt.py](https://github.com/Textualize/rich/blob/master/rich/prompt.py)):

   ```python
   value = self.get_input(self.console, prompt, self.password, stream=stream)
   if value == "" and default != ...:
       return default
   ```

   O `default` só entra quando o valor é string vazia — e `Console.input` usa `input()`
   builtin puro, que em EOF **levanta** em vez de devolver `""`. Nem `isatty`, nem
   try/except.

   ⚠️ **E o "conserto" tem armadilha pior.** Passar `stream=io.StringIO("")` faz
   `readline()` devolver `""`, o que aciona o default — mas com `choices=` **sem**
   `default`, o `""` falha na validação, cai no `continue`, e o `while True` **nunca
   termina**. Reproduzido: processo morto por timeout.

O único com caminho desenhado é o `typer.confirm`/`typer.prompt`, que levanta `Abort`, e
o `main()` do click vendorizado o converte em saída limpa. **[medido aqui]**, dentro de
um app typer real:

```
$ python app.py < /dev/null
Instalar? [y/N]: Aborted.
exit=1
```

Sem traceback. Mas note o outro lado: **[medido aqui]** `echo "y" | python app.py`
responde `resposta=True` e sai 0 — o prompt do click **aceita input de pipe**. Isso é
scriptabilidade, mas para um wizard de instalação é um footgun: um `yes | overpower
install` responderia tudo sozinho.

### 6.2 A conclusão de desenho

**O gate de TTY é responsabilidade do overpower, não da biblioteca.** Isso não é
inferência — é declaração do mantenedor do `prompt_toolkit`, Jonathan Slenders, em
[issue #502](https://github.com/prompt-toolkit/python-prompt-toolkit/issues/502#issuecomment-294218873)
(2017-04-16):

> The reason is that prompt_toolkit is meant for user interaction, not for
> machine-interaction like a pipe. **If you want to support pipe input on the other hand,
> it's best to test for `sys.stdin.isatty()` yourself** […] A pipe does not respond to a
> CPR (cursor position request). There is actually no cursor. […] prompt_toolkit won't
> support pipes as stdin.

**Qual descritor importa: `stdin`.** **[medido aqui]**, com **stdin=PTY e stdout=pipe**,
`questionary.select(...).ask()` funcionou e devolveu o valor, exit 0. O `prompt_toolkit`
degrada o *output* sozinho — `output/defaults.py` tem `if not stdout.isatty(): return
PlainTextOutput(stdout)`. **O que quebra é o stdin.**

Ainda assim o overpower deve exigir **os dois**: `sys.stdout.isatty()` responde "o usuário
vai ver o que eu desenhar?", e sob `overpower install | tee log.txt` a seleção com setas
iria para o arquivo. Melhor não perguntar do que perguntar no vazio.

**A checagem precisa ser `None`-safe.** `sys.stdin` pode ser `None` (fd fechado,
`pythonw.exe`), e a doc do stdlib avisa:

> Under some conditions `stdin`, `stdout` and `stderr` as well as the original values
> `__stdin__`, `__stdout__` and `__stderr__` can be `None`.
> — [docs.python.org/3/library/sys.html](https://docs.python.org/3/library/sys.html#sys.stdin)

O modelo recomendado:

```python
def _tty(stream) -> bool:
    return stream is not None and stream.isatty()

interactive = _tty(sys.stdin) and _tty(sys.stdout) and not non_interactive_requested
if interactive:
    import questionary          # import tardio: só este ramo paga o prompt_toolkit
    ...
elif not yes:
    # sem TTY e sem --yes: falha ensinando o comando não interativo
    raise typer.Exit(code=2)
```

Três estados, não dois:

| ambiente | flag | comportamento | exit |
| --- | --- | --- | --- |
| TTY | — | wizard com setas | 0 |
| TTY | `--yes` | usa o default declarado, sem perguntar | 0 |
| sem TTY | `--yes` | executa não interativo | 0 |
| sem TTY | — | **painel de erro ensinando o comando com `--yes`**, em stderr | **2** |

**Nunca** cair num default silencioso quando não há TTY e o usuário não pediu. Escrever no
repo *ou* na máquina do usuário são consequências diferentes demais para serem adivinhadas.
O erro precisa ser acionável — mostrar as duas linhas de comando que resolvem.

### 6.3 A convenção `--yes`, em fontes de primeira parte

O `--yes` não é invenção do overpower. O que as fontes primárias estabelecem:

**click** define a convenção e o texto de ajuda, em
[`decorators.py`](https://github.com/pallets/click/blob/main/src/click/decorators.py):

```python
def confirmation_option(*param_decls, **kwargs):
    """Add a ``--yes`` option which shows a prompt before continuing if
    not passed. If the prompt is declined, the program will exit."""
    ...
    kwargs.setdefault("help", _("Confirm the action without prompting."))
```

**pip** usa o par flag + env var — `--no-input` / `PIP_NO_INPUT`, "Disable prompting for
input" ([pip.pypa.io/en/stable/cli/pip/](https://pip.pypa.io/en/stable/cli/pip/)). É o
desenho a copiar se o overpower quiser um interruptor de ambiente.

**apt-get** documenta a semântica que interessa a um instalador
([manpages.debian.org/trixie/apt/apt-get.8.en.html](https://manpages.debian.org/trixie/apt/apt-get.8.en.html)):

> **-y, --yes, --assume-yes** — Automatic yes to prompts […] **If an undesirable
> situation, such as changing a held package, trying to install an unauthenticated
> package or removing an essential package occurs then apt-get will abort.**

Ou seja: `-y` assume sim, **mas ainda aborta em situação destrutiva**. É o precedente
para "default explícito, nunca default perigoso".

**`CI=true`** é convenção confirmada em primeira parte — a tabela de *Default environment
variables* do GitHub Actions
([docs.github.com](https://docs.github.com/en/actions/reference/workflows-and-actions/variables))
diz de `CI`: *"Always set to `true`."* Convenções de outros provedores (`GITLAB_CI`,
`TF_BUILD`) **não foram verificadas** nesta pesquisa.

⚠️ **`uv` NÃO tem `--no-input`.** Verificado em `uv --help` (0.11.7) e nas docs oficiais:
as *Global options* são `-q`, `-v`, `--color`, `--system-certs`, `--offline`,
`--allow-insecure-host`, `--no-progress`, `--directory`, `--project`, `--config-file`,
`--no-config`. Nenhum `--no-input`, `--yes` ou `--non-interactive`; o `uv publish` resolve
por `--token` / `UV_PUBLISH_TOKEN`. **Não copie um "`--no-input` do uv" — ele não existe.**

**Precedência recomendada** (síntese das fontes acima, não citação): flag explícita
(`--yes`) > env var dedicada (`OVERPOWER_NO_INPUT`, no espírito do `PIP_NO_INPUT`) >
`CI=true` > `isatty()`. A flag existe para o humano *querer* pular; o `isatty` existe para
não travar quando ninguém pediu nada.

### 6.4 Por que `questionary` e não `rich.prompt`

`rich.prompt` seria "de graça" (já está na árvore), mas ele é digitação, não seleção. A
sensação de `npx vercel` vem da lista navegável com setas, e isso exige `prompt_toolkit`.
`questionary 2.1.1` é a camada fina sobre ele: **36 KB de wheel**, arrastando
`prompt_toolkit` (383 KB) e `wcwidth` (316 KB).

**[medido aqui]**, `questionary` funcionando em PTY real (via `script`), com setas
enviadas por `pty.fork()` — o fluxo completo roda:

```
  ___  _  _ ____ ____ ___  ____ _ _ _ ____ ____
  |  | |  | |___ |__/ |__] |  | | | | |___ |__/
  |__|  \/  |___ |  \ |    |__| |_|_| |___ |  \

? Onde instalar? (Use arrow keys)
 » projeto (./.agents/)
   global (~/.claude/)
                                   ← seta para baixo
   projeto (./.agents/)
 » global (~/.claude/)
                                   ← enter
? Onde instalar? global (~/.claude/)
⠙ instalando matt-pocock (global) ━━━━━━━━━━╺━━━━━━━━━ 1/3
matt-pocock instalado em global
├── .agents/skills
│   ├── skills/grilling/SKILL.md
│   ├── skills/wayfinder/SKILL.md
│   └── commands/tdd.md
└── symlink .claude/skills -> .agents/skills

OK 3 arquivos escritos, 1 symlink criado.
proximo: git status
```

**O import tardio paga o aluguel.** **[medido aqui]**:

| | wall ms | delta |
| --- | --- | --- |
| interpretador vazio | 9,8 | — |
| `import typer` | 47,6 | +37,8 |
| typer + rich efetivamente usado | 67,3 | +57,5 |
| ... + `import questionary` | **130,2** | **+120,4** |

Importar `questionary` custa **~63 ms adicionais**. Como `overpower list`,
`overpower --help` e qualquer execução em CI nunca entram no ramo interativo, o import
tardio devolve esses 63 ms em toda invocação não interativa — que serão a maioria.

**`InquirerPy` descartado por manutenção, não por API.** É a mesma base
(`prompt_toolkit`), mas a última release é a **0.3.4 de 2022-06-27** e o último commit é
de **2022-11-19** — ~4 anos parado, 43 issues abertas. Consequência prática: o pin dele é
`prompt-toolkit >=3.0.1,<4.0.0`, e não há release upstream que ateste compatibilidade com
a 3.0.53 que traz o fix de macOS (§6.6). Fica-se dependendo do resolver, não de um teste.

### 6.5 `questionary.skip_if` — a única alavanca de degradação embutida

Achado que melhora o desenho: o `questionary` tem, sozinho entre todas as bibliotecas
comparadas, um mecanismo declarativo de pular a pergunta
([question.py](https://github.com/tmbo/questionary/blob/master/questionary/question.py)):

```python
def skip_if(self, condition: bool, default: Any = None) -> "Question":
    """Skip the question if flag is set and return the default instead."""
    self.should_skip_question = condition
    self.default = default
    return self
```

Quando `should_skip_question` é verdadeiro, o `unsafe_ask()` retorna o default sem rodar a
`Application` — nada de EOF. **[medido aqui]**, `skip_if(True, default="projeto")` devolve
`'projeto'` com exit 0 e sem exceção.

⚠️ **Mas ele não é gate suficiente, e a razão só aparece medindo.** Construir a `Question`
já instancia a `Application` do `prompt_toolkit` e, com ela, o `Vt100Input` — que **emite
`Warning: Input is not a terminal (fd=0).` no stderr** antes de qualquer `skip_if` ser
consultado. **[medido aqui]**, com `stdin=/dev/null`:

| forma | stderr |
| --- | --- |
| `import questionary` | vazio |
| `questionary.select(...)` — só construir, sem perguntar | **`Warning: Input is not a terminal (fd=0).`** |
| `questionary.select(...).skip_if(True, default="a").unsafe_ask()` | **`Warning: Input is not a terminal (fd=0).`** |
| gate manual de `isatty()`, que nem constrói a `Question` | **vazio** |

Um `assert r.stderr == ""` na camada 1 dos testes pegaria isso. Em CI, é lixo no log.

**Conclusão:** o gate de `isatty()` **antes** de construir a pergunta continua sendo o
mecanismo primário — é a única forma que não escreve nada. O `skip_if` fica como
conveniência para pular perguntas **dentro** de uma sessão já interativa (por exemplo,
quando uma flag já respondeu a segunda pergunta), não como caminho de degradação.

### 6.6 O pin obrigatório: `prompt_toolkit >= 3.0.53`

O caminho "sem TTY → `EOFError`" foi construído aos poucos, e a última peça é **de quatro
dias atrás**. CHANGELOG oficial
([prompt-toolkit/CHANGELOG](https://github.com/prompt-toolkit/python-prompt-toolkit/blob/master/CHANGELOG)):

| versão | data | mudança |
| --- | --- | --- |
| 3.0.8 | 2020-10-12 | "Handle situation when /dev/null is piped into stdin, or when stdin is closed somehow." |
| 3.0.24 | 2021-12-09 | "Handle `PermissionError` when trying to attach /dev/null in vt100 input." (caso **Linux/epoll**) |
| 3.0.29 | 2022-04-04 | *Breaking*: `create_pipe_input` virou context manager (importa para teste, §8) |
| **3.0.53** | **2026-07-26** | **"Treat OSError on add_reader as EOFError (macOS kqueue)."** |

O código que faz isso, em
[`input/vt100.py`](https://github.com/prompt-toolkit/python-prompt-toolkit/blob/master/src/prompt_toolkit/input/vt100.py):

```python
try:
    loop.add_reader(fd, callback_wrapper)
except (PermissionError, OSError):
    # ... Both mean "nothing more to read here", so we surface them as `EOFError`
    raise EOFError
```

**Antes da 3.0.53, no macOS, o caso não-TTY vazava `OSError: [Errno 22] Invalid argument`
cru** — a [issue #1943](https://github.com/prompt-toolkit/python-prompt-toolkit/issues/1943)
(aberta 2024-12-13) segue aberta. Um `except EOFError` defensivo **não pega** em
`prompt_toolkit` antigo no macOS.

Nota adicional: `prompt_toolkit` **não** faz assert de TTY — ele imprime
`Warning: Input is not a terminal (fd=0).` em stderr e segue
([vt100.py](https://github.com/prompt-toolkit/python-prompt-toolkit/blob/master/src/prompt_toolkit/input/vt100.py),
comentário literal: *"For convenience, we print an error message and go on."*). Essa linha
aparece em toda execução sem TTY, e é mais um motivo para nunca deixar o wizard chegar lá.

### 6.7 Convivência `questionary` + `rich`: dois donos do terminal

**Confirmado.** Há um conflito documentado, e ele tem conserto. Na
[issue #1431 do rich](https://github.com/Textualize/rich/issues/1431) (2021-08-25,
fechada), o relator descreve `PromptSession` + `Console()` imprimindo em paralelo, e
resolve:

> Sorry, my mistake. It seems that prompt_toolkit's `patch_stdout()` removed escaped
> characters completely. **I can turn that off with specifying `raw=True`.** All fixed!

O mecanismo está no `prompt_toolkit`
([output/defaults.py](https://github.com/prompt-toolkit/python-prompt-toolkit/blob/master/src/prompt_toolkit/output/defaults.py)):
ele desembrulha o `StdoutProxy` antes de renderizar.

**Não confirmado em fonte primária:** qualquer conflito documentado especificamente entre
`prompt_toolkit` e `rich.Live`/`rich.Progress`. Busca por issues nos dois repos oficiais
não retornou nada. O que dá para afirmar é estrutural, não um incidente documentado: o
`Live` do rich mantém pilha de contexto e desenha por cima do cursor, enquanto o
`prompt_toolkit` assume raw mode e responde a CPRs — dois loops de render no mesmo fd.

**Regra prática, derivada do que está confirmado:** serializar os donos. `rich` imprime →
`rich` para → `questionary` pergunta → `questionary` retorna → `rich` volta. É exatamente
o que o desenho de §12.2/§12.3 faz: o wizard termina antes de o `Progress` começar. Se um
dia houver output concorrente durante o prompt, aí sim `ask(patch_stdout=True)`, com o
`raw=True` da issue #1431 em mente.

**Nota de arquitetura:** também existe a opção de usar `typer.confirm` (click vendorizado)
para as perguntas de sim/não, aproveitando o `Abort` → `Aborted!` + exit 1 de graça, e
reservar o `questionary` só para a seleção com setas. Isso reduz a superfície do
`prompt_toolkit` ao mínimo. Fica como opção de implementação, não como decisão travada
aqui.

---

## 7. Boa cidadania de terminal

### 7.1 A matriz medida

**[medido aqui]** com `rich 15.0.0`, `Console()` sem argumentos, **stdout sob pipe**:

| ambiente | `is_terminal` | `color_system` | `no_color` | `width` | ANSI emitido? |
| --- | --- | --- | --- | --- | --- |
| pipe, sem env | False | None | False | 80 | **não** |
| pipe + `FORCE_COLOR=1` | True | truecolor | False | 80 | sim, com cor |
| pipe + `FORCE_COLOR=1` + `NO_COLOR=1` | True | truecolor | **True** | 80 | **sim, sem cor** |
| pipe + `NO_COLOR=1` | False | None | True | 80 | não |
| pipe + `COLUMNS=60` | False | None | False | **60** | não |
| pipe + `TERM=dumb` | False | None | False | 80 | não |
| pipe + `TERM=dumb` + `FORCE_COLOR=1` | True | **None** | False | 80 | não (`is_dumb=True`) |
| pipe + `TTY_COMPATIBLE=1` | **True** | truecolor | False | 80 | sim |
| pipe + `TTY_COMPATIBLE=0` + `FORCE_COLOR=1` | **False** | None | False | 80 | não |
| pipe + `CI=true` | False | None | False | 80 | não |
| pipe + `GITHUB_ACTIONS=true` | False | None | False | 80 | não |

Leituras:

- **Sob pipe, o rich desliga cor sozinho e assume 80 colunas.** Nada a fazer.
- **`TTY_COMPATIBLE=0` vence `FORCE_COLOR=1`.** É o knob mais autoritativo.
- **`TERM=dumb` mata a cor mesmo com `FORCE_COLOR`.**
- **O rich não detecta CI.** `CI` e `GITHUB_ACTIONS` não são lidos — `grep -rniE "\bCI\b|github_actions|jenkins|travis"`
  sobre o pacote `rich/` inteiro retorna **zero**. Quem quiser cor em CI precisa declarar.

A ordem de decisão está literal em
[`rich/console.py`](https://raw.githubusercontent.com/Textualize/rich/master/rich/console.py),
método `is_terminal` — e explica a matriz inteira:

```python
def is_terminal(self) -> bool:
    if self._force_terminal is not None:      # 1. kwarg force_terminal=
        return self._force_terminal
    if ... idlelib ...: return False          # 2. IDLE
    if self.is_jupyter: return False          # 3. Jupyter
    tty_compatible = environ.get("TTY_COMPATIBLE", "")
    if tty_compatible == "0": return False    # 4. TTY_COMPATIBLE
    if tty_compatible == "1": return True
    force_color = environ.get("FORCE_COLOR")
    if force_color is not None:               # 5. FORCE_COLOR
        return force_color != ""
    isatty = getattr(self.file, "isatty", None)   # 6. isatty do arquivo
    return False if isatty is None else isatty()
```

Precedência: **`force_terminal=` > IDLE > Jupyter > `TTY_COMPATIBLE` > `FORCE_COLOR` >
`file.isatty()`**.

**Semântica de string vazia**, conforme a spec [no-color.org](https://no-color.org/) e o
CHANGELOG do rich `## [14.0.0] - 2025-03-30`: *"An empty `NO_COLOR` env var is now
considered disabled"* / *"An empty `FORCE_COLOR` env var is now considered disabled"*. Ou
seja: `NO_COLOR=""` **não** desliga cor; `FORCE_COLOR=""` **não** força terminal.

Datação dos knobs: `FORCE_COLOR` entrou na 12.6.0 (2022-10-02), `TTY_COMPATIBLE` na 14.0.0
(2025-03-30), `TTY_INTERACTIVE` na 14.1.0 (2025-06-25).

⚠️ **Duas armadilhas de produção**, ambas verificadas no código:

**(a) `Console.size` consulta os streams padrão, não `self.file`.** O código itera sobre
`_STD_STREAMS = (stdin, stdout, stderr)` chamando `os.get_terminal_size`. Logo, um CLI com
**stdout em pipe mas stderr ainda em terminal** herda a largura do terminal, não 80.

**(b) `color_system=` explícito ignora o pipe.** O `__init__` só chama
`_detect_color_system()` quando `color_system == "auto"` (o default). Um
`Console(file=f, color_system="truecolor")` **vaza ANSI para dentro do arquivo**.
Regra: nunca fixe `color_system` fora do caminho de teste.

### 7.2 `NO_COLOR` remove cor, não ANSI

Achado que contraria a leitura ingênua da spec. Doc oficial do rich
([console.rst, "Environment variables"](https://raw.githubusercontent.com/Textualize/rich/master/docs/source/console.rst)):

> **If the environment variable `NO_COLOR` is set, Rich will disable all color in the
> output. `NO_COLOR` takes precedence over `FORCE_COLOR`.** […]
> **The `NO_COLOR` environment variable removes *color* only. Styles such as dim, bold,
> italic, underline etc. are preserved.**

**[medido aqui]**, bytes literais em PTY real com `Console().print("[bold red]ALERTA[/] normal")`:

```
sem env:        \033 [ 1 ; 3 1 m   A L E R T A   \033 [ 0 m ...
NO_COLOR=1:     \033 [ 1 m         A L E R T A   \033 [ 0 m ...
```

O `;31` (vermelho) sai, o `1` (bold) fica. **Um consumidor que faça `grep` por ESC ainda
verá escapes sob `NO_COLOR`.** Para saída realmente limpa é preciso pipe (o rich desliga
tudo) ou `Console(no_color=True, color_system=None)`.

A razão de a doc dizer "precedência" e o código não ter branch nenhum: **são dois eixos
ortogonais que se compõem.** `FORCE_COLOR` atua em `is_terminal`; `NO_COLOR` atua em
`self.no_color`, aplicado no fim do pipeline em `_render_buffer`:

```python
if self.no_color and color_system:
    buffer = Segment.remove_color(buffer)
```

`remove_color` tira a cor dos segmentos, não os escapes de atributo. O resultado líquido é
o que a doc promete — sem cor — mas por composição, não por precedência.

Também documentado na mesma página, e vale registrar a precedência:

> Note that environment variables set defaults in the Console object. **If you explicitly
> set any variables in the constructor then these will take precedence.**

### 7.3 A receita oficial de CI, validada

A doc do rich recomenda, literalmente:

> If you want Rich output in CI or Github Actions, then you should set
> `TTY_COMPATIBLE=1` and `TTY_INTERACTIVE=0`.

**[medido aqui]**, sob pipe:

| env | `is_terminal` | `is_interactive` | efeito no `Progress` |
| --- | --- | --- | --- |
| (nada) | False | False | uma linha final, sem cor |
| `TTY_COMPATIBLE=1` | True | **True** | **anima e redesenha** — polui log de CI |
| `TTY_COMPATIBLE=1` + `TTY_INTERACTIVE=0` | True | False | **uma linha final, colorida** |

A receita funciona exatamente como anunciada: cor sim, animação não.

### 7.4 `Progress` degrada sozinho — e `transient` silencia

**[medido aqui]**, `rich.Progress` com stdout **não-tty**:

```
$ python prog.py | cat -A
baixando ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00$
--- fim ---$
```

Uma linha só, no estado final. Sem frames intermediários, sem `\r`, sem código de cursor.

E com `transient=True`:

```
$ python prog_transient.py | cat -A
$
--- fim ---$
```

**Nada.** Log de CI limpo de graça.

O mecanismo está em [`rich/live.py`](https://github.com/Textualize/rich/blob/master/rich/live.py),
e a guarda dupla é o que produz o "imprime uma vez só":

```python
elif (
    not self._started and not self.transient
):  # if it is finished allow files or dumb-terminals to see final result
    with self.console:
        self.console.print(Control())
```

Como `transient=True` faz a segunda condição falhar, nada é impresso. Efeito colateral
estrutural: `rich.status.Status` constrói internamente um `Live(..., transient=True)`, e
portanto **spinner de status sempre some fora de terminal** — que é o comportamento
desejado.

Resumo do comportamento fora de terminal, **[medido aqui]**:

| construção | saída sob pipe |
| --- | --- |
| `Progress(console=...)` | 1 linha, estado final |
| `track(range(n))` | 1 linha, estado final |
| `Progress(..., transient=True)` | **nada** |
| `Progress(..., disable=True)` | nada |
| `console.status(...)` | **nada** (sempre) |

Doc oficial que cobre a política (`console.rst`, *Interactive mode*):

> Rich will remove animations such as progress bars and status indicators when not writing
> to a terminal as you probably don't want to write these out to a text file (for
> example). You can override this behavior by setting the `force_interactive` argument.

**Recomendação:** usar `transient=True` no progresso de instalação. Em terminal o usuário
vê o spinner e a barra; sob pipe e em CI a saída é só o resumo final. `Progress(disable=True)`
existe como desligamento explícito e também foi verificado.

### 7.5 Largura estreita

**[medido aqui]**, `overpower list` com `COLUMNS=60`. A tabela de 4 colunas **não vaza** —
o rich quebra e trunca com reticências. Mas fica ruim:

```
                 AI Frameworks disponiveis
┏━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ nome        ┃ desc… ┃ origem                    ┃   tam. ┃
┡━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━┩
│ matt-pocock │ Skil… │ mattpocock/skills         │ 412 KB │
│             │ de    │                           │        │
│             │ enge… │                           │        │
```

A coluna de descrição vira lixo. **Isso é decisão de design, não de biblioteca:** abaixo
de ~72 colunas o `list` deve **derrubar colunas** (esconder origem e tamanho) em vez de
espremer. `console.width` dá o número; a regra é do overpower.

O banner tem o mesmo problema, e pior. **[medido aqui]**, banner de 47 colunas num console
de 30: o rich **quebra a arte no meio**, destruindo o desenho. Com
`soft_wrap=True, crop=False` ele preserva os 47 e deixa o terminal decidir. A regra
recomendada é mais simples: **só imprimir o banner se `console.width >= len(banner)`**.

### 7.6 Windows: `legacy_windows` não faz o que o nome sugere

**[medido aqui]**, `Console(legacy_windows=True)` com uma `Table` padrão:

```
'┌───┐\n│ a │\n├───┤\n│ 1 │\n└───┘\n'    ← ainda Unicode
```

Não vira ASCII. O código de
[`rich/box.py`](https://raw.githubusercontent.com/Textualize/rich/master/rich/box.py)
explica — são **dois mecanismos distintos**:

```python
def substitute(self, options, safe=True) -> "Box":
    box = self
    if options.legacy_windows and safe:
        box = LEGACY_WINDOWS_SUBSTITUTIONS.get(box, box)   # HEAVY_HEAD -> SQUARE (Unicode!)
    if options.ascii_only and not box.ascii:
        box = ASCII                                        # aqui sim vira ASCII
    return box
```

e em `rich/console.py`:

```python
@property
def ascii_only(self) -> bool:
    return not self.encoding.startswith("utf")
```

Ou seja: `legacy_windows` troca caixa pesada por caixa quadrada, **ainda Unicode**; o
fallback para ASCII depende do **encoding do stream** não ser UTF. E — crítico — nada
disso protege caracteres Unicode que o overpower escreva **à mão** num banner: o
`substitute()` só age sobre objetos `Box`.

**[medido aqui]**, quais boxes são ASCII puro: `box.ASCII` (`+---+`) e `box.ASCII2`.
`SQUARE`, `ROUNDED`, `HEAVY_HEAD`, `MINIMAL`, `SIMPLE` são todos Unicode.

A doc oficial ([appendix/box.rst](https://raw.githubusercontent.com/Textualize/rich/master/docs/source/appendix/box.rst)):

> Some of the box drawing characters will not display correctly on Windows legacy
> terminal (cmd.exe) with *raster* fonts, and are disabled by default. If you want the
> full range of box options on Windows legacy terminal, use a *truetype* font and set the
> `safe_box` parameter on the Table class to `False`.

Mais um detalhe que quebra snapshot cross-platform, do `rich/console.py`:

```python
width = int(columns) - self.legacy_windows   # em legacy Windows a largura efetiva é 1 menor
```

**Achado negativo importante: o rich NÃO lê `WT_SESSION`.** `grep -rn "WT_SESSION"` sobre
o repo inteiro (código, docs, testes) retorna **zero ocorrências**. A distinção Windows
Terminal × cmd.exe legado é feita 100% via Win32 API, em
[`rich/_windows.py`](https://raw.githubusercontent.com/Textualize/rich/master/rich/_windows.py):

```python
console_mode = GetConsoleMode(handle)
vt = bool(success and console_mode & ENABLE_VIRTUAL_TERMINAL_PROCESSING)
truecolor = False
if vt:
    win_version = sys.getwindowsversion()
    truecolor = win_version.major > 10 or (
        win_version.major == 10 and win_version.build >= 15063
    )
```

O rich **lê** o flag `ENABLE_VIRTUAL_TERMINAL_PROCESSING`; ele **não ativa** VT (não chama
`SetConsoleMode`). E `truecolor` exige VT **e** build ≥ 15063 (Win10 1703). **Não
confirmado em fonte primária** qualquer doc do rich sobre ativação de VT no console
legado.

**Recomendação para o overpower:** desenhar o banner **em ASCII de 7 bits** (é o caso do
banner proposto em §12), o que remove a questão inteira; e manter as tabelas/painéis em
Unicode, aceitando o fallback automático do rich. `colorama` já entra na árvore como dep
condicional do typer (`platform_system == "Windows"`).

---

## 8. Testabilidade — a pergunta que decide a sustentabilidade

### 8.1 A estratégia: três camadas

O erro a evitar é uma suíte onde trocar a cor da marca quebra vinte testes. A saída é
**separar o que é contrato do que é aparência**, e testar cada um com a ferramenta certa.

| camada | o que asserta | ferramenta | quebra quando |
| --- | --- | --- | --- |
| **1. Contrato** | exit code, qual stream, substring acionável | `typer.testing.CliRunner` | o comportamento muda — **corretamente** |
| **2. Aparência** | layout completo, largura fixa, sem cor | `syrupy` (snapshot) | o visual muda — **de propósito**, atualizável com uma flag |
| **3. Renderização** | componente isolado | `Console` determinístico + `capture()` | a regra de layout muda |

### 8.2 Por que o `CliRunner` do typer basta

**[medido aqui]**, quatro propriedades verificadas:

1. **Ele captura o `Console` de módulo**, criado no import. A razão está no código do
   rich ([`rich/console.py:757`](https://raw.githubusercontent.com/Textualize/rich/master/rich/console.py)):

   ```python
   @property
   def file(self) -> IO[str]:
       """Get the file object to write to."""
       file = self._file or (sys.stderr if self.stderr else sys.stdout)
   ```

   `sys.stdout` é resolvido **a cada escrita**, não na construção. Logo, o
   `CliRunner`, que troca `sys.stdout`, captura tudo. **Não é preciso injetar console.**

2. **stdout e stderr saem separados.** Um `Console(stderr=True)` cai em `result.stderr`,
   e `result.stdout` fica vazio. Verificado com um comando que só escreve erro.

3. **A saída capturada não tem ANSI**, porque o rich vê um stream não-tty. Snapshot em
   texto puro, sem sujeira.

4. **`COLUMNS` no `env=` controla a largura do rich.** `runner.invoke(app, ["list"],
   env={"COLUMNS": "60"})` produz saída de exatamente 60 colunas. **Este é o lever de
   determinismo** — sem ele, o snapshot varia com o terminal do dev.

Uma nuance registrada: **[medido aqui]** `FORCE_COLOR=1` no `env=` **não** afeta um
`Console` de módulo (o rich lê `FORCE_COLOR` no `__init__`), mas **afeta** o help do
typer, que constrói o console na hora. Para testar cor, use um `Console` explícito com
`force_terminal=True` (camada 3), não a env var.

### 8.3 Provado: mudança estética não quebra teste

Suíte de 9 testes nas três camadas (código em §12.5). **[medido aqui]**:

```
$ pytest test_layers.py -q
.........
3 snapshots passed. 9 passed in 0.29s

# troca a cor da marca: "bold magenta" -> "bold cyan"
$ pytest test_layers.py -q
.........
3 snapshots passed. 9 passed in 0.26s      ← ZERO testes quebrados
```

O snapshot sobrevive porque é tirado com `NO_COLOR=1` e `COLUMNS` fixo: ele congela
**layout**, não **cor**. Uma mudança de layout (texto de help, coluna nova) quebra só a
camada 2, e `pytest --snapshot-update` reconcilia com revisão de diff.

### 8.4 As ferramentas de snapshot, comparadas

| | versão | deps | peso | veredito |
| --- | --- | --- | --- | --- |
| **syrupy** | 5.5.3 (2026-07-11) | `pytest>=8.0.0` — **uma** | 55 KB | **recomendado** |
| inline-snapshot | 0.35.3 (2026-07-27) | 6 (`asttokens`, `executing`, `rich`, …) | 95 KB | descartado, ver abaixo |
| pytest-regressions | 2.11.0 (2026-05-25) | `pytest-datadir`, `pyyaml` | — | alternativa viável |
| pytest-textual-snapshot | 1.1.0 (2025-01-23) | **`syrupy==4.8.0`** pinado | 11 KB | **armadilha** |
| pytest-snapshot | 0.9.0 (2022-04-23) | — | — | abandonado |

**syrupy** — README oficial: *"Syrupy is a zero-dependency pytest snapshot plugin."*
Serializa string multilinha em bloco `'''…'''` legível no `.ambr`, o que torna o diff
revisável — decisivo para saída de terminal. **[medido aqui]**, o snapshot gerado:

```
# name: test_help_snapshot[60]
  '''
   Usage: root [OPTIONS] COMMAND [ARGS]...
  ╭─ Options ────────────────────────────────────────────────╮
  │ --help          Show this message and exit.              │
  ╰──────────────────────────────────────────────────────────╯
  '''
```

**inline-snapshot descartado** por duas limitações oficiais
([docs/limitations.md](https://github.com/15r10nk/inline-snapshot)):

> **pytest-xdist is not supported** — if you have pytest-xdist installed and active,
> inline-snapshot will act as if `--inline-snapshot=disable` is set.

e o default `disable` em CI. Uma ferramenta de snapshot que se desliga sozinha no CI
não serve como portão.

**pytest-textual-snapshot é armadilha**: `requires_dist` inclui `syrupy==4.8.0` — **pin
exato** contra a 5.5.3 atual. Sua fixture só aceita `textual.app.App`; não há entrada
para saída rich pura. Parado desde 2025-04.

O que **vale copiar dele** é a técnica, sem instalá-lo: `Console(record=True).export_svg()`
+ `SingleFileSnapshotExtension` do syrupy + normalização do id aleatório, que o próprio
plugin faz:

```python
def normalize_svg(svg: str) -> str:
    """Strip the unique id generated by rich.Console.export_svg()."""
    return re.sub(r"\bterminal-\d+-([\w-]+)", r"terminal-\1", svg)
```

Isso dá snapshot **visual** (SVG revisável no browser) para as telas que valem — banner e
resumo final. Fica como opção, não como base.

### 8.5 O que a doc oficial do rich recomenda para testes

[console.rst](https://raw.githubusercontent.com/Textualize/rich/master/docs/source/console.rst),
seção "Capturing output", literal:

> An alternative way of capturing output is to set the Console file to a `io.StringIO`.
> **This is the recommended method if you are testing console output in unit tests.**

```python
from io import StringIO
from rich.console import Console
console = Console(file=StringIO())
console.print("[bold red]Hello[/] World")
str_output = console.file.getvalue()
```

E é o que o próprio rich faz consigo mesmo
([tests/test_console.py](https://raw.githubusercontent.com/Textualize/rich/master/tests/test_console.py)):

```python
def test_soft_wrap() -> None:
    console = Console(file=io.StringIO(), width=20, soft_wrap=True)
    console.print("foo " * 10)
    assert console.file.getvalue() == "foo " * 20
```

Igualdade exata **com `width` fixado explicitamente**. O padrão de fato dos projetos de
primeira parte não é afrouxar a asserção — é **congelar as variáveis de renderização** e
comparar exato.

**Armadilha do `export_text`**, **[medido aqui]** e confirmada na docstring: o parâmetro
`clear` é `True` por padrão, então **a primeira chamada consome o buffer**.

```python
c = Console(record=True, file=io.StringIO(), width=40, force_terminal=True)
c.print("[bold green]OK[/] pronto")
c.export_text(clear=False)                 # 'OK pronto\n'
c.export_text(clear=False, styles=True)    # '\x1b[1;32mOK\x1b[0m pronto\n'
c.export_text()                            # 'OK pronto\n'  (e limpa)
c.export_text()                            # ''             ← buffer vazio
```

**Não há posição oficial de nenhum projeto sobre "substring versus snapshot completo".**
É decisão de projeto. A doc do click usa as duas granularidades no mesmo documento. A
posição adotada aqui — contrato em substring, aparência em snapshot — é escolha do
overpower, e está registrada como tal.

Correção de premissa que vale registrar: **não existe seção "Testing" na página
`console.html` do rich.** O conteúdo equivalente está sob "Exporting" e "Capturing
output". Não há página de doc de primeira parte do rich dedicada a testes.

### 8.6 Isolar o ambiente do CI dentro do teste

O `Console` lê `NO_COLOR`, `FORCE_COLOR`, `COLUMNS`, `TTY_COMPATIBLE` do ambiente. Num CI
que declara alguma delas, isso vaza para dentro do teste. Dois caminhos:

**Público** — passar tudo explicitamente no construtor, que sempre vence a env
(`console.rst`: *"If you explicitly set any variables in the constructor then these will
take precedence."*). É o que a fixture de §12.5 faz.

**Privado, mas mais completo** — o `Console` aceita `_environ`, com o comentário literal
no fonte `# Copy of os.environ allows us to replace it for testing`:

```python
Console(file=io.StringIO(), width=60, force_terminal=True,
        color_system="truecolor", record=True, _environ={})
```

É API privada; usar com consciência disso.

### 8.7 Testar o caminho interativo do wizard

A camada 1 cobre o ramo **não** interativo (que é o que o CliRunner enxerga). Para testar
o ramo com setas, o `prompt_toolkit` tem receita **oficial**
([unit_testing.html](https://python-prompt-toolkit.readthedocs.io/en/master/pages/advanced_topics/unit_testing.html)):

```python
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput

def test_prompt_session():
    with create_pipe_input() as inp:
        inp.send_text("hello\n")
        session = PromptSession(input=inp, output=DummyOutput())
        result = session.prompt()
    assert result == "hello"
```

Aviso da própria doc: **sempre inclua o `\n`**, senão "the Application will wait forever
for some more input to receive".

E funciona com `questionary`, porque todo construtor de pergunta repassa `**kwargs` para a
`Application`. É o padrão da própria suíte de testes do questionary
([tests/utils.py](https://github.com/tmbo/questionary/blob/master/tests/utils.py), que
define `KeyInputs.DOWN = "\x1b[B"`, `ENTER = "\r"` etc.). Verificado:

```python
from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput


def test_wizard_escolhe_global() -> None:
    with create_pipe_input() as inp:
        with create_app_session(input=inp, output=DummyOutput()):
            inp.send_text("\x1b[B\r")          # DOWN + ENTER
            escolha = questionary.select(
                "Onde instalar?", choices=["projeto", "global"]
            ).unsafe_ask()
    assert escolha == "global"
```

O `create_app_session` evita poluir a assinatura de produção com `input=`/`output=`. Use
`unsafe_ask()` nos testes — `ask()` engoliria um `KeyboardInterrupt` e devolveria `None`,
mascarando falha.

**Pin mínimo: `prompt_toolkit >= 3.0.29`**, quando `create_pipe_input` virou context
manager (CHANGELOG 3.0.29, *Breaking changes*). O pin de §6.6 (`>= 3.0.53`) já cobre.

---

## 9. Peso de dependência e cold start

O overpower é invocado com `uvx` num ambiente que pode não ter cache. Cada dependência
custa tempo. Os números:

### 9.1 Bytes de download

**[medido aqui]**, somando `urls[].size` do wheel `py3-none-any` de cada pacote da árvore:

| conjunto | wheels | KB de download |
| --- | --- | --- |
| argparse (stdlib) | 0 | 0 |
| **typer + rich** | 7 | **1.739** |
| cyclopts | 8 | 2.188 |
| **typer + rich + questionary** | 10 | **2.474** |
| ... + `pyfiglet` | 11 | **4.238** |
| ... + `art` (em vez de pyfiglet) | 11 | 3.070 |
| typer + rich + textual | 13 | 2.612 |

Os maiores individualmente:

| pacote | versão | KB |
| --- | --- | --- |
| **pyfiglet** | 1.0.4 | **1.764** |
| **pygments** | 2.20.0 | **1.202** |
| textual | 8.2.8 | 714 |
| art | 6.5 | 596 |
| prompt-toolkit | 3.0.53 | 383 |
| wcwidth | 0.8.2 | 316 |
| rich | 15.0.0 | 303 |
| typer | 0.27.0 | 120 |
| questionary | 2.1.1 | 36 |

**`pygments` é 69% do peso da opção typer+rich** e é inescapável — é dependência dura do
rich, para syntax highlighting que o overpower não vai usar. **`pyfiglet` sozinho é maior
que toda a stack typer+rich.** Ver §10.

### 9.2 `uvx` ponta a ponta

**[medido aqui]** com três pacotes locais reais, `uvx --cache-dir` apontando para
diretório recém-apagado a cada rodada (melhor de 3):

| pacote | deps | **cold** | **warm** |
| --- | --- | --- | --- |
| `opbare` (argparse, 0 deps) | 0 | **0,59 s** | 0,06 s |
| `opmin` (typer + rich) | 6 | **0,89 s** | 0,10 s |
| `opfull` (+ questionary + pyfiglet) | 10 | **1,14 s** | 0,10 s |

**A stack visual completa custa +0,55 s no cold start e +0,04 s no warm** contra um CLI
de zero dependências. O piso de 0,59 s é do próprio `uvx` — resolução e criação de venv —
e não some com escolha de biblioteca.

⚠️ **Ressalva honesta:** medido em conexão doméstica rápida. Num link corporativo lento os
2,4 MB de download passam a dominar. A tabela de bytes de §9.1 é o número portável; o
tempo não é.

O comportamento de cache do `uvx` está documentado
([docs/concepts/tools.md](https://raw.githubusercontent.com/astral-sh/uv/main/docs/concepts/tools.md)):

> When running a tool with `uvx`, a virtual environment is stored in the uv cache
> directory and is treated as disposable […] The environment is only cached to reduce the
> overhead of repeated invocations.

E — relevante para uma lib publicada:

> `uvx` will use the latest available version of the requested tool *on the first
> invocation*. After that, `uvx` will use the cached version of the tool unless a
> different version is requested, the cache is pruned, or the cache is refreshed.

### 9.3 Custo por invocação (import)

**[medido aqui]**, wall time do processo, melhor de 7:

| caso | ms | delta |
| --- | --- | --- |
| interpretador vazio | 11,0 | — |
| `import argparse` | 16,2 | +5,1 |
| `import typer` (rich **não** carregado) | 47,5 | +36,5 |
| `import rich.console` | 37,8 | +26,8 |
| `import cyclopts` | 63,4 | +52,4 |
| `import questionary` | 102,6 | **+91,6** |
| `import pyfiglet` | 35,3 | +24,3 |
| `import textual.app` | 158,4 | **+147,3** |
| **stack typer+rich, sem questionary** | 64,5 | **+53,5** |
| stack typer+rich+questionary | 138,3 | +127,3 |

**Regra que sai daqui:** importar `questionary` só dentro do ramo interativo. Isso mantém
todo comando não interativo — `list`, `--help`, tudo que roda em CI — em ~65 ms em vez de
~138 ms.

---

## 10. Arte ASCII e identidade

### 10.1 Recomendação: hardcodar o banner

**Nem `pyfiglet` nem `art` entram na árvore.** Gera-se o banner **uma vez**, em
desenvolvimento, e a string vai para o código.

O argumento é de peso, e é grande:

| | wheel | descomprimido | deps | licença do código |
| --- | --- | --- | --- | --- |
| pyfiglet 1.0.4 | 1,72 MiB | **6,46 MiB** (575 arquivos de fonte) | 0 | MIT |
| art 6.5 | 610 KB | **3,34 MiB** (fontes como módulos `.py`) | 0 runtime | MIT |
| string no código | **~300 bytes** | ~300 bytes | 0 | — |

`pyfiglet` seria **a maior dependência do projeto**, maior que typer+rich somados, para
produzir uma string que nunca muda. As fontes são ~94% do wheel.

### 10.2 A questão de licença, com o que é e o que não é confirmado

**Confirmado.** O `LICENSE` do pyfiglet é MIT, mas **cobre o código, não as fontes**. O
cabeçalho de
[`pyfiglet/fonts-standard/standard.flf`](https://raw.githubusercontent.com/pwaller/pyfiglet/master/pyfiglet/fonts-standard/standard.flf)
traz uma **BSD-3-Clause** própria:

```
Copyright (C) 1991, 1993, 1994 Glenn Chappell and Ian Chai
Copyright (C) 1996, ... 2001 John Cowan
...
2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.
```

**Confirmado.** O próprio README do pyfiglet admite que parte das fontes não tem direito
de distribuição claro:

> **Q**: Why are some fonts missing in \<my favourite\> distribution?
> **A**: […] we have divided the fonts into ones that **have a clear redistribution
> license** and those that **don't**.

> **A**: While there isn't a watertight case for the license, we believe that any legal
> constraint for these fonts has long expired and so they are public domain […]

E o wheel do PyPI inclui **as duas** categorias — o Makefile oficial tem um alvo
`minimal` justamente com o comentário `Run "make minimal" to build a package compliant
with Fedora licensing`.

**Não confirmado em fonte primária.** Procurei em `figlet.org`, `figlet.org/faq.html`, no
`LICENSE` e README do pyfiglet e no cabeçalho do `standard.flf`: **nenhuma fonte de
primeira parte declara posição sobre redistribuir a *saída renderizada* de uma fonte
FIGlet.** A BSD-3 do `.flf` fala de "source and binary forms" do arquivo de fonte, não de
obras produzidas com ele. Não vou fabricar autoridade jurídica aqui.

**O que isso muda na recomendação:** hardcodar já era a escolha por peso. A ambiguidade de
licença reforça, e sugere um caminho que dispensa a pergunta: **desenhar o banner à mão**,
em ASCII de 7 bits, sem passar por fonte FIGlet nenhuma. É o que a proposta de §12.1 faz.

Bônus operacional: banner hardcodado é determinístico — não há risco de a fonte mudar
entre versões da lib e quebrar um snapshot.

### 10.3 Cor no banner: o rich não tem gradiente nativo

**Não confirmado em fonte primária** qualquer API de gradiente no rich — `grep -i gradient`
em `rich/__init__.py`, `rich/style.py`, `rich/text.py` e nas docs de `style`, `text`,
`console` e `markup` retorna **zero ocorrências**. O que existe é um helper de baixo nível
não documentado, em `rich/color.py`:

```python
def blend_rgb(color1, color2, cross_fade: float = 0.5) -> ColorTriplet:
    """Blend one RGB color in to another."""
```

Gradiente se constrói com `Text.stylize(style, start, end)` posição a posição. A doc de
[text.rst](https://raw.githubusercontent.com/Textualize/rich/master/docs/source/text.rst)
cobre `stylize`, `append`, `assemble`, `highlight_words`, `highlight_regex`.

⚠️ Um gradiente truecolor caractere a caractere gera **um span de estilo por caractere** —
mais um motivo para snapshotar com `styles=False`. Para o overpower, **uma cor sólida de
marca no banner é a escolha certa**: sobrevive a `NO_COLOR` (vira monocromático legível),
não explode snapshot, e não custa nada.

---

## 11. Referências vivas

O ticket cita `npx vercel`, `uv`, `gh` e `bun`. Aqui há um limite honesto de método: o
comportamento visual dessas ferramentas em execução **não é documentação de primeira
parte**, e eu não consegui rodar as três num terminal desta sessão. Então registro
separadamente o que é citável e o que é leitura de desenho.

**Citável.** A doc do `uv` sobre cache de ferramenta (§9.2) e a política de versão do
`uvx` — que informam o modelo de invocação do overpower, não sua estética.

**Leitura de desenho, não fonte primária.** Os padrões que o ticket descreve como "o que
vale copiar" e que a stack recomendada suporta:

| padrão | como se faz na stack recomendada |
| --- | --- |
| Wizard de poucas perguntas, com setas e defaults sensatos | `questionary.select` / `.confirm`, §12.2 |
| Flag de escape para automação (`--yes`) | `typer.Option(False, "--yes", "-y")`, §12.2 |
| Progresso que some ao terminar | `Progress(transient=True)`, §7.4 |
| Resumo final acionável, com "próximo passo" | `rich.tree.Tree` + linha final, §12.3 |
| Erro em painel, com o comando que resolve | `rich.panel.Panel` no stderr, §12.4 |
| Sob pipe, virar log limpo | comportamento automático do rich, §7.1 |

**Não confirmado em fonte primária:** qualquer afirmação sobre o que `npx vercel`, `gh` ou
`bun` fazem exatamente na tela. O desenho proposto em §12 é derivado do requisito do dev e
do que a stack sustenta, não de engenharia reversa dessas ferramentas.

O ticket [#5](https://github.com/panlabs-tech/overpower/issues/5) pesquisa o `npx skills`
em detalhe e é o lugar certo para o estudo de comportamento dessa família.

---

## 12. Exemplos concretos de código

Todo o código desta seção **foi executado** durante a pesquisa. Alimenta o ticket
[#12](https://github.com/panlabs-tech/overpower/issues/12).

### 12.1 Console, tema e banner

```python
from rich.console import Console
from rich.theme import Theme

THEME = Theme(
    {
        "op.brand": "bold magenta",
        "op.ok": "bold green",
        "op.warn": "bold yellow",
        "op.err": "bold red",
        "op.dim": "dim",
    }
)

out = Console(theme=THEME)
err = Console(theme=THEME, stderr=True)

# ASCII de 7 bits: sobrevive a cmd.exe legado e a qualquer codepage.
BANNER = r"""
  ___  _  _ ____ ____ ___  ____ _ _ _ ____ ____
  |  | |  | |___ |__/ |__] |  | | | | |___ |__/
  |__|  \/  |___ |  \ |    |__| |_|_| |___ |  \
"""


def banner() -> None:
    # Sem terminal, o banner é ruído. Estreito demais, ele quebra.
    if not out.is_terminal or out.width < 50:
        return
    out.print(BANNER, style="op.brand", highlight=False)
```

Dois `Console` — um para stdout, um para stderr — é o que torna `result.stdout` e
`result.stderr` assertáveis em separado (§8.2). O tema nomeado é o que faz a troca de
paleta ser um diff de cinco linhas.

### 12.2 O wizard com degradação

```python
import os
import sys
from typing import IO

import typer
from rich.panel import Panel

app = typer.Typer(add_completion=False, rich_markup_mode="rich")


def _tty(stream: IO[str] | None) -> bool:
    # sys.stdin pode ser None (fd fechado, pythonw.exe). A doc do stdlib avisa.
    return stream is not None and stream.isatty()


def _pode_perguntar(yes: bool) -> bool:
    """Precedencia: flag > env dedicada > CI > isatty. Ver secao 6.3."""
    if yes or os.environ.get("OVERPOWER_NO_INPUT"):
        return False
    if os.environ.get("CI") == "true":       # docs.github.com: "Always set to true."
        return False
    return _tty(sys.stdin) and _tty(sys.stdout)


@app.command("install")
def install(
    framework: str = typer.Argument(..., help="AI Framework a instalar"),
    global_: bool = typer.Option(False, "--global", help="Instala em ~/ em vez do repo."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Confirma sem perguntar."),
) -> None:
    """Instala um AI Framework, com wizard quando ha TTY."""
    banner()
    scope = "global" if global_ else "projeto"

    if _pode_perguntar(yes):
        import questionary  # import tardio: so este ramo paga o prompt_toolkit (+63 ms)

        answer = questionary.select(
            "Onde instalar?",
            choices=["projeto (./.agents/)", "global (~/.claude/)"],
        ).ask()
        if answer is None:            # Ctrl-C: questionary devolve None
            err.print("[op.warn]cancelado pelo usuario[/]")
            raise typer.Exit(code=130)
        scope = "global" if answer.startswith("global") else "projeto"

    elif not yes:
        # Sem TTY e sem --yes: falhar ensinando, nunca adivinhar o alvo.
        err.print(
            Panel(
                "Sem TTY e sem [bold]--yes[/]: nao da para perguntar.\n\n"
                "Rode de novo declarando o alvo:\n"
                "  [op.ok]overpower install matt-pocock --yes[/]            (projeto)\n"
                "  [op.ok]overpower install matt-pocock --global --yes[/]   (maquina)",
                title="[op.err]entrada nao interativa[/]",
                border_style="op.err",
            )
        )
        raise typer.Exit(code=2)

    _executa(framework, scope)
```

⚠️ **Não troque esse gate por `skip_if`.** Construir a `Question` já emite
`Warning: Input is not a terminal (fd=0).` no stderr, antes de o `skip_if` ser consultado
— ver a medição em §6.5. O `import questionary` precisa ficar **dentro** do ramo
interativo, e é isso que mantém o stderr limpo em CI.

### 12.3 Progresso e resumo

```python
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.tree import Tree


def _executa(framework: str, scope: str) -> None:
    files = ["skills/grilling/SKILL.md", "skills/wayfinder/SKILL.md", "commands/tdd.md"]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=out,
        transient=True,   # em terminal: some ao acabar. Sob pipe: nao imprime nada.
    ) as progress:
        task = progress.add_task(f"instalando {framework} ({scope})", total=len(files))
        for f in files:
            _escreve(f)
            progress.advance(task)

    tree = Tree(f"[op.ok]{framework}[/] instalado em [bold]{scope}[/]")
    node = tree.add(".agents/skills")
    for f in files:
        node.add(f"[op.dim]{f}[/]")
    tree.add("[op.dim]symlink[/] .claude/skills -> .agents/skills")

    out.print(tree)
    out.print()
    out.print(f"[op.ok]OK[/] {len(files)} arquivos escritos, 1 symlink criado.")
    out.print("[op.dim]proximo:[/] git status")
```

Saída real em terminal:

```
matt-pocock instalado em global
├── .agents/skills
│   ├── skills/grilling/SKILL.md
│   ├── skills/wayfinder/SKILL.md
│   └── commands/tdd.md
└── symlink .claude/skills -> .agents/skills

OK 3 arquivos escritos, 1 symlink criado.
proximo: git status
```

A árvore casa com o axioma **"sem estado no alvo"**: ela mostra exatamente o que o
`git status` vai mostrar, e o próximo passo sugerido é justamente conferir isso.

### 12.4 Erro apresentado

```python
@app.command("boom")
def boom() -> None:
    err.print(
        Panel(
            "Nao foi possivel criar o symlink [bold].claude/skills[/].\n"
            "[op.dim]OSError: [WinError 1314] required privilege is not held[/]\n\n"
            "O overpower caiu para [bold]copia real[/]. Nada foi perdido.",
            title="[op.warn]symlink indisponivel[/]",
            border_style="op.warn",
        )
    )
    raise typer.Exit(code=1)
```

Renderizado (capturado do `result.stderr`, 80 colunas, sem cor):

```
╭──────────────────────────── symlink indisponivel ────────────────────────────╮
│ Nao foi possivel criar o symlink .claude/skills.                             │
│ OSError: [WinError 1314] required privilege is not held                      │
│                                                                              │
│ O overpower caiu para copia real. Nada foi perdido.                          │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### 12.5 A suíte de testes nas três camadas

```python
import io

import pytest
from rich.console import Console
from typer.testing import CliRunner

from overpower.cli import app

runner = CliRunner()


# ---------------------------------------------------------------- camada 1
# Contrato: sobrevive a qualquer mudanca estetica.
def test_list_sai_zero_e_cita_os_frameworks() -> None:
    r = runner.invoke(app, ["list"])
    assert r.exit_code == 0
    for nome in ("matt-pocock", "spec-kit", "bmad"):
        assert nome in r.stdout


def test_sem_tty_e_sem_yes_falha_com_codigo_2_no_stderr() -> None:
    r = runner.invoke(app, ["install", "matt-pocock"])
    assert r.exit_code == 2
    assert r.stdout == ""         # nada de ruido no stdout
    assert "--yes" in r.stderr    # a saida ensina o caminho


def test_sem_tty_com_yes_instala() -> None:
    r = runner.invoke(app, ["install", "matt-pocock", "--yes"])
    assert r.exit_code == 0
    assert "3 arquivos escritos" in r.stdout


def test_erro_vai_para_stderr_nao_stdout() -> None:
    r = runner.invoke(app, ["boom"])
    assert r.exit_code == 1
    assert r.stdout == ""
    assert "symlink" in r.stderr


# ---------------------------------------------------------------- camada 2
# Snapshot: quebra de proposito quando o visual muda.
# Atualiza com: pytest --snapshot-update
@pytest.mark.parametrize("largura", ["80", "60"])
def test_help_snapshot(largura: str, snapshot) -> None:
    r = runner.invoke(app, ["--help"], env={"COLUMNS": largura, "NO_COLOR": "1"})
    assert r.exit_code == 0
    assert r.stdout == snapshot


def test_list_snapshot_60_colunas(snapshot) -> None:
    r = runner.invoke(app, ["list"], env={"COLUMNS": "60", "NO_COLOR": "1"})
    assert r.stdout == snapshot


# ---------------------------------------------------------------- camada 3
# Renderizacao pura: Console deterministico, sem CLI no meio.
@pytest.fixture
def console() -> Console:
    return Console(
        file=io.StringIO(),
        width=60,
        force_terminal=False,
        no_color=True,
        legacy_windows=False,
        highlight=False,
    )


def test_painel_de_erro_cabe_em_60_colunas(console: Console) -> None:
    from rich.panel import Panel

    with console.capture() as cap:
        console.print(Panel("linha curta", title="titulo"))
    assert all(len(x) <= 60 for x in cap.get().splitlines())


def test_cores_exigem_force_terminal() -> None:
    c = Console(file=io.StringIO(), width=40, force_terminal=True, record=True)
    c.print("[bold green]OK[/] pronto")
    # clear=False e obrigatorio: export_text() consome o buffer por padrao.
    assert "\x1b[1;32m" in c.export_text(styles=True, clear=False)
    assert c.export_text(clear=False) == "OK pronto\n"
```

`env={"COLUMNS": ..., "NO_COLOR": "1"}` nos testes de snapshot é o que os torna
determinísticos: congela largura e desliga cor, deixando o snapshot sensível só a
**layout**.

### 12.6 Comando de diagnóstico

Vale existir — `overpower doctor` ou similar — porque responde por si um bug de
"as cores não aparecem no meu CI":

```python
@app.command("diag")
def diag() -> None:
    """Reporta o que o rich detectou do ambiente."""
    t = Table(title="diagnostico de terminal")
    t.add_column("propriedade", style="op.dim")
    t.add_column("valor")
    for k, v in [
        ("is_terminal", out.is_terminal),
        ("is_interactive", out.is_interactive),
        ("is_dumb_terminal", out.is_dumb_terminal),
        ("no_color", out.no_color),
        ("color_system", out.color_system),
        ("width", out.width),
        ("legacy_windows", out.legacy_windows),
        ("stdin.isatty()", sys.stdin.isatty()),
        ("stdout.isatty()", sys.stdout.isatty()),
        ("env NO_COLOR", os.environ.get("NO_COLOR")),
        ("env FORCE_COLOR", os.environ.get("FORCE_COLOR")),
        ("env TTY_COMPATIBLE", os.environ.get("TTY_COMPATIBLE")),
        ("env TERM", os.environ.get("TERM")),
        ("env COLUMNS", os.environ.get("COLUMNS")),
    ]:
        t.add_row(str(k), str(v))
    out.print(t)
```

### 12.7 Dependências do `pyproject.toml`

```toml
[project]
requires-python = ">=3.10"
dependencies = [
    "typer>=0.27",              # traz rich, shellingham, annotated-doc; vendoriza click
    "questionary>=2.1",         # importado so no ramo interativo
    "prompt-toolkit>=3.0.53",   # pin DURO: antes disso, sem TTY no macOS vaza OSError
]

[dependency-groups]
dev = [
    "pytest>=8",
    "syrupy>=5.5",
]
```

Duas notas sobre esta lista:

- **O pin de `prompt-toolkit` não é opcional.** Ele é dependência transitiva do
  `questionary`, cujo requisito é só `prompt_toolkit<4.0,>=2.0` — largo demais. Sem o pin
  direto, o resolver pode escolher uma versão em que o caminho não-TTY no macOS levanta
  `OSError` em vez de `EOFError` (§6.6). Declarar transitiva no `[project]` é o preço de
  travar uma garantia de comportamento.
- **`rich` não precisa ser listado** — vem do typer. Listá-lo explicitamente também é
  defensável, se o overpower quiser travar um piso próprio de versão do rich.

---

## 13. Riscos registrados

| risco | evidência | mitigação |
| --- | --- | --- |
| typer em refatoração estrutural; 0.27.0 mudou impressão de metavar e **quebra snapshot de `--help`** | release notes 0.27.0, Breaking Changes | pin de faixa no `pyproject.toml`; snapshot é camada atualizável por flag |
| `pygments` (1,20 MB) é 69% do download e o overpower não usa syntax highlighting | `requires_dist` de `rich 15.0.0` | nenhuma — é dep dura do rich. Aceito. |
| Sem cache, `uvx` custa ~1,1 s; em link lento os 2,4 MB dominam | medição §9.2 | manter a árvore enxuta; não adicionar pyfiglet/textual |
| `NO_COLOR` não remove ANSI de `bold`/`dim` | doc do rich + bytes medidos §7.2 | documentar; oferecer o `diag` de §12.6 |
| `legacy_windows` **não** dá fallback ASCII | `rich/box.py` + medição §7.6 | banner em ASCII de 7 bits |
| Licença da saída renderizada de fonte FIGlet **não resolvida por fonte primária** | §10.2 | banner desenhado à mão, sem passar por FIGlet |
| Tabela de 4 colunas fica ilegível abaixo de ~72 colunas | medição §7.5 | derrubar colunas por `console.width`; não é problema de biblioteca |
| **macOS: sem `prompt_toolkit>=3.0.53`, o caso não-TTY vaza `OSError` cru** e um `except EOFError` não pega | CHANGELOG 3.0.53 (2026-07-26) + issue #1943 aberta, §6.6 | pin duro no `[project].dependencies` |
| `sys.stdin` pode ser `None`; `sys.stdin.isatty()` levanta `AttributeError` | §6.1 | guarda `_tty()` de §12.2 |
| `Console.size` lê `stdin/stdout/stderr`, não `self.file`: stdout em pipe + stderr em tty herda a largura do terminal | `rich/console.py`, §7.1 | fixar `width` nos testes; aceitar em produção |
| `Console(color_system="truecolor")` explícito **vaza ANSI para arquivo** | `rich/console.py`, §7.1 | nunca fixar `color_system` fora de teste |
| `rich.prompt` com `stream=` e `choices=` sem `default` entra em **loop infinito** | §6.2 | não usar `rich.prompt` no wizard |
| `pytest-textual-snapshot` pina `syrupy==4.8.0` e trava a versão do syrupy do projeto | §8.4 | não instalar |

---

## 14. Perguntas que este ticket deixa em aberto

Não são falhas de pesquisa — são decisões que pertencem a outros tickets do mapa.

- **Modelo de erro do CLI** — a tabela de códigos de saída (`0`, `2` para não interativo,
  `130` para Ctrl-C) é proposta aqui, mas o conjunto completo é do ticket de superfície de
  comandos ([#8](https://github.com/panlabs-tech/overpower/issues/8)). O mapa registra
  isso em *Not yet specified*.
- **Estratégia de teste como portão de CI** — a estratégia de três camadas está definida;
  se ela vira gate de PR sai do ticket de portões do repo.
- **A identidade visual em si** — o banner de §12.1 é um placeholder funcional, não uma
  proposta de marca. O ticket [#12](https://github.com/panlabs-tech/overpower/issues/12)
  é onde a direção visual trava.

---

## 15. Fontes primárias consultadas

Todas em **2026-07-30**.

**Metadata do PyPI** (`https://pypi.org/pypi/<pkg>/json`): typer 0.27.0, click 8.4.2,
cyclopts 4.22.3, rich 15.0.0, questionary 2.1.1, prompt-toolkit 3.0.53, textual 8.2.8,
pyfiglet 1.0.4, art 6.5, syrupy 5.5.3, inline-snapshot 0.35.3, pytest-regressions 2.11.0,
pytest-textual-snapshot 1.1.0, pytest-snapshot 0.9.0, pygments 2.20.0, wcwidth 0.8.2.

**typer** — [release-notes.md](https://raw.githubusercontent.com/fastapi/typer/0.27.0/docs/release-notes.md) ·
[pyproject.toml](https://raw.githubusercontent.com/fastapi/typer/0.27.0/pyproject.toml) ·
[typer/core.py](https://raw.githubusercontent.com/fastapi/typer/0.27.0/typer/core.py) ·
[typer/testing.py](https://raw.githubusercontent.com/fastapi/typer/0.27.0/typer/testing.py) ·
[typer/_click/__init__.py](https://github.com/fastapi/typer/blob/master/typer/_click/__init__.py) ·
[docs/tutorial/testing.md](https://raw.githubusercontent.com/fastapi/typer/0.27.0/docs/tutorial/testing.md) ·
[docs/tutorial/commands/help.md](https://raw.githubusercontent.com/fastapi/typer/0.27.0/docs/tutorial/commands/help.md) ·
[docs/tutorial/click.md](https://raw.githubusercontent.com/fastapi/typer/0.27.0/docs/tutorial/click.md)

**click** — [CHANGES.md](https://github.com/pallets/click/blob/main/CHANGES.md) ·
[docs/testing.md](https://github.com/pallets/click/blob/main/docs/testing.md) ·
[src/click/testing.py](https://github.com/pallets/click/blob/main/src/click/testing.py) ·
[docs/commands-and-groups.md](https://raw.githubusercontent.com/pallets/click/8.4.2/docs/commands-and-groups.md)

**cyclopts** — [pyproject.toml](https://raw.githubusercontent.com/BrianPugh/cyclopts/v4.22.3/pyproject.toml) ·
[cookbook/unit_testing.rst](https://raw.githubusercontent.com/BrianPugh/cyclopts/v4.22.3/docs/source/cookbook/unit_testing.rst) ·
[lazy_loading.rst](https://raw.githubusercontent.com/BrianPugh/cyclopts/v4.22.3/docs/source/lazy_loading.rst) ·
[known_issues.rst](https://raw.githubusercontent.com/BrianPugh/cyclopts/v4.22.3/docs/source/known_issues.rst) ·
[commands.rst](https://raw.githubusercontent.com/BrianPugh/cyclopts/v4.22.3/docs/source/commands.rst)

**rich** — [rich/console.py](https://raw.githubusercontent.com/Textualize/rich/master/rich/console.py) ·
[rich/box.py](https://raw.githubusercontent.com/Textualize/rich/master/rich/box.py) ·
[rich/prompt.py](https://raw.githubusercontent.com/Textualize/rich/master/rich/prompt.py) ·
[docs/source/console.rst](https://raw.githubusercontent.com/Textualize/rich/master/docs/source/console.rst) ·
[docs/source/text.rst](https://raw.githubusercontent.com/Textualize/rich/master/docs/source/text.rst) ·
[docs/source/appendix/box.rst](https://raw.githubusercontent.com/Textualize/rich/master/docs/source/appendix/box.rst) ·
[tests/test_console.py](https://raw.githubusercontent.com/Textualize/rich/master/tests/test_console.py)

**snapshot** — [syrupy README](https://raw.githubusercontent.com/syrupy-project/syrupy/main/README.md) ·
[syrupy amber/serializer.py](https://github.com/syrupy-project/syrupy/blob/main/src/syrupy/extensions/amber/serializer.py) ·
[pytest-textual-snapshot README](https://raw.githubusercontent.com/Textualize/pytest-textual-snapshot/main/README.md) ·
[inline-snapshot docs](https://15r10nk.github.io/inline-snapshot/latest) ·
[pytest-regressions](https://github.com/ESSS/pytest-regressions)

**arte ASCII** — [pyfiglet LICENSE](https://raw.githubusercontent.com/pwaller/pyfiglet/master/LICENSE) ·
[pyfiglet README](https://raw.githubusercontent.com/pwaller/pyfiglet/master/README.md) ·
[pyfiglet Makefile](https://raw.githubusercontent.com/pwaller/pyfiglet/master/Makefile) ·
[standard.flf](https://raw.githubusercontent.com/pwaller/pyfiglet/master/pyfiglet/fonts-standard/standard.flf) ·
[pyfiglet issue #59](https://github.com/pwaller/pyfiglet/issues/59) ·
[art README](https://raw.githubusercontent.com/sepandhaghighi/art/master/README.md)

**prompt / wizard** — [questionary question.py](https://github.com/tmbo/questionary/blob/master/questionary/question.py) ·
[questionary tests/utils.py](https://github.com/tmbo/questionary/blob/master/tests/utils.py) ·
[questionary issue #263](https://github.com/tmbo/questionary/issues/263) ·
[prompt_toolkit CHANGELOG](https://github.com/prompt-toolkit/python-prompt-toolkit/blob/master/CHANGELOG) ·
[prompt_toolkit input/vt100.py](https://github.com/prompt-toolkit/python-prompt-toolkit/blob/master/src/prompt_toolkit/input/vt100.py) ·
[prompt_toolkit input/defaults.py](https://github.com/prompt-toolkit/python-prompt-toolkit/blob/master/src/prompt_toolkit/input/defaults.py) ·
[prompt_toolkit output/defaults.py](https://github.com/prompt-toolkit/python-prompt-toolkit/blob/master/src/prompt_toolkit/output/defaults.py) ·
[prompt_toolkit unit_testing](https://python-prompt-toolkit.readthedocs.io/en/master/pages/advanced_topics/unit_testing.html) ·
[prompt_toolkit issue #502](https://github.com/prompt-toolkit/python-prompt-toolkit/issues/502) ·
[prompt_toolkit issue #1943](https://github.com/prompt-toolkit/python-prompt-toolkit/issues/1943) ·
[click termui.py](https://github.com/pallets/click/blob/main/src/click/termui.py) ·
[click decorators.py](https://github.com/pallets/click/blob/main/src/click/decorators.py) ·
[click prompts](https://click.palletsprojects.com/en/stable/prompts/) ·
[rich issue #1431](https://github.com/Textualize/rich/issues/1431)

**textual** — [textual README](https://raw.githubusercontent.com/Textualize/textual/main/README.md) ·
[drivers/linux_driver.py](https://github.com/Textualize/textual/blob/main/src/textual/drivers/linux_driver.py) ·
[drivers/headless_driver.py](https://github.com/Textualize/textual/blob/main/src/textual/drivers/headless_driver.py) ·
[src/textual/app.py](https://github.com/Textualize/textual/blob/main/src/textual/app.py) ·
[guide/testing](https://textual.textualize.io/guide/testing/)

**convenções** — [docs.python.org/3/library/argparse.html](https://docs.python.org/3/library/argparse.html) ·
[docs.python.org/3/library/sys.html](https://docs.python.org/3/library/sys.html#sys.stdin) ·
[docs.python.org/3/library/os.html#os.isatty](https://docs.python.org/3/library/os.html#os.isatty) ·
[uv docs/concepts/tools.md](https://raw.githubusercontent.com/astral-sh/uv/main/docs/concepts/tools.md) ·
[pip CLI reference](https://pip.pypa.io/en/stable/cli/pip/) ·
[apt-get(8)](https://manpages.debian.org/trixie/apt/apt-get.8.en.html) ·
[GitHub Actions variables](https://docs.github.com/en/actions/reference/workflows-and-actions/variables) ·
[no-color.org](https://no-color.org/)

---

## 16. O que ficou explicitamente NÃO confirmado

Registrado para que ninguém precise refazer a busca.

1. **Licença da saída renderizada de fonte FIGlet** — nem `figlet.org`, nem o FAQ, nem o
   `LICENSE`/README do pyfiglet, nem o cabeçalho do `standard.flf` dizem qualquer coisa
   sobre obras produzidas *usando* a fonte.
2. **`WT_SESSION` no rich** — zero ocorrências no repo. Não há doc de primeira parte sobre
   ativação de VT no console legado do Windows.
3. **Detecção de CI no rich** — não existe no código; a doc delega ao usuário via
   `TTY_COMPATIBLE`/`TTY_INTERACTIVE`.
4. **Página oficial do Textual comparando "quando usar Textual vs Rich"** — não existe no
   FAQ, homepage, guide nem README.
5. **Seção "Testing" na doc do rich** — não existe; o conteúdo está em "Exporting" e
   "Capturing output".
6. **Conflito documentado entre `prompt_toolkit` e `rich.Live`/`Progress`** — nenhuma
   issue de primeira parte nos dois repos. O risco é estrutural, não um incidente
   registrado.
7. **Forma oficial de rodar cyclopts sem carregar rich** — não há env var equivalente a
   `TYPER_USE_RICH`; `help_formatter="plain"` muda só a aparência.
8. **Equivalente de lazy loading por string de import em typer ou click** — não existe.
9. **Utilitário oficial de teste de CLI para argparse na stdlib** — não existe.
10. **Posição oficial de qualquer projeto sobre substring vs snapshot completo** — não
    existe; é decisão de projeto.
11. **Convenções de CI de provedores além do GitHub Actions** (`GITLAB_CI`, `TF_BUILD`) —
    não verificadas nesta pesquisa.
12. **Comportamento visual exato de `npx vercel`, `gh` e `bun`** — não é documentação de
    primeira parte e não foi executado aqui. Ver §11.
