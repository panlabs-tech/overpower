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
| Gerência de projeto com `uv` | §4 |
| `ruff`: regras que valem × ruído | §5 |
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

---
