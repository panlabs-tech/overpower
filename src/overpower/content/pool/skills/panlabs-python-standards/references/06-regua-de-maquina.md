# A régua de máquina — a config é a norma executando

A pergunta deste eixo é uma só: **quais regras deste padrão a máquina consegue forçar, e com qual config exata?** É o único eixo em que a regra e o mecanismo que a força são o mesmo objeto — por isso o artefato aqui não é posição argumentada com um exemplo colado no fim, é **baseline literal copiável** com prosa justificando linha a linha. Um config passa o portão anti-cerimônia por construção: cumprir *é* o CI verde.

> Régua: toda posição abaixo passou pelo portão anti-cerimônia — cenário nomeado nos dois sentidos, garantia verificável, autoridade não preenche.

Dois espécimes sustentam as medições deste arquivo. **O espécime gateado** — o backend Python de um organizador doméstico full-stack, nascido já sob os seis gates bloqueantes descritos aqui, ~102 arquivos em `src/`, quatro contextos delimitados. **O espécime sem trava** (`b3stocks`) — serviço de dados de bolsa em Lambdas, forma de código 10/10 na prosa (ports ABC, camadas nomeadas, docstrings) e garantia ~0 na máquina: `.pylintrc` com regras de classe-de-bug desligadas, `mypy` removido do projeto, `fail-under=10` no gate de lint e `--cov` medindo execução de seis features sem teste. O segundo é o cenário permanente deste eixo: **a prosa existia e a trava não**.

---

## O baseline

Nome de pacote genérico `myapp`; `finance` e `identity` são **exemplos de contexto delimitado** — troque pelos seus, o formato não muda. Versões contra as quais todo comportamento abaixo foi verificado por experimento: CPython 3.14, ruff 0.15.x, pyright 1.1.4xx, import-linter 2.13.

```toml
# --- ruff: format + lint ---------------------------------------------------
[tool.ruff]
line-length = 100          # knob condicional: empate arbitrário, corte livre
target-version = "py314"
src = ["src", "tests"]

[tool.ruff.lint]
preview = true                  # exigido por DOC501/DOC502 (pydoclint)
explicit-preview-rules = true   # liga SÓ as preview listadas, nada mais
select = [
    "E", "W",      # pycodestyle
    "F",           # pyflakes
    "I",           # isort
    "B",           # flake8-bugbear
    "C4",          # flake8-comprehensions  (knob condicional)
    "UP",          # pyupgrade
    "SIM",         # flake8-simplify
    "N",           # pep8-naming
    "D",           # pydocstyle
    "PTH",         # flake8-use-pathlib     (knob condicional)
    "ASYNC",       # flake8-async
    "PL",          # pylint
    "TID",         # flake8-tidy-imports
    "RUF",         # ruff-specific
    "BLE",         # blind-except
    "DOC501",      # raise não documentado no docstring   (preview)
    "DOC502",      # docstring documenta raise inexistente (preview)
]
ignore = [
    "E501",        # comprimento de linha é do formatter
]

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.lint.flake8-tidy-imports]
ban-relative-imports = "all"

[tool.ruff.lint.flake8-tidy-imports.banned-api]
"datetime.datetime.now".msg = "Time enters through the Clock port; only SystemClock reads the real clock."
"datetime.date.today".msg   = "Time enters through the Clock port; only SystemClock reads the real clock."
"os.environ".msg            = "Environment is read once at boot, in the settings module."
"os.getenv".msg             = "Environment is read once at boot, in the settings module."

[tool.ruff.lint.per-file-ignores]
# Testes: sem docstring obrigatório, magic value liberado, relógio real liberado.
"tests/**" = ["D", "PLR2004", "TID251"]
# Os DOIS únicos arquivos autorizados a atravessar a banned-api, por arquivo.
"src/myapp/shared/adapters/system_clock.py" = ["TID251"]
"src/myapp/composition/settings.py"         = ["TID251"]
# Adapter herda o contrato do port: docstring de método/`__init__` é cópia derivável.
"src/myapp/*/adapters/**" = ["D102", "D107", "DOC501", "DOC502"]
# `Raises:` verificado vale no CONTRATO PUBLICADO (application/: ports + use-cases).
"src/myapp/*/domain/**"   = ["DOC501", "DOC502"]
"src/myapp/composition/**" = ["DOC501", "DOC502"]
"src/myapp/http/**"        = ["DOC501", "DOC502"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

# --- pyright ---------------------------------------------------------------
[tool.pyright]
pythonVersion = "3.14"
typeCheckingMode = "strict"
include = ["src", "tests"]      # tests SOB strict — não é engano
venvPath = "."
venv = ".venv"

# --- pytest ----------------------------------------------------------------
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
markers = [
    "infra: needs real infrastructure; skipping it is a failure when CI=true",
]
# `-W error` deliberadamente AUSENTE — ver eixo 4.
```

```toml
# --- import-linter: as fronteiras, executáveis -----------------------------
[tool.importlinter]
root_package = "myapp"

[[tool.importlinter.contracts]]
name = "contexts follow hexagonal layers (domain < application < adapters)"
type = "layers"
layers = ["(adapters)", "application", "domain"]
containers = ["myapp.shared", "myapp.finance", "myapp.identity"]

[[tool.importlinter.contracts]]
name = "shared kernel imports no bounded context"
type = "forbidden"
source_modules = ["myapp.shared"]
forbidden_modules = ["myapp.finance", "myapp.identity"]

# Um bloco POR CONTEXTO: cada um proíbe o domain/adapters de todos os outros.
# N contextos ⇒ N blocos. Conversa entre contextos só pela camada `application`.
[[tool.importlinter.contracts]]
name = "finance reaches other contexts only through their application layer"
type = "forbidden"
source_modules = ["myapp.finance"]
forbidden_modules = ["myapp.identity.domain", "myapp.identity.adapters"]
allow_indirect_imports = true

[[tool.importlinter.contracts]]
name = "server edge reaches contexts only through their application layer"
type = "forbidden"
source_modules = ["myapp.http", "myapp.health"]
forbidden_modules = [
    "myapp.finance.domain", "myapp.finance.adapters",
    "myapp.identity.domain", "myapp.identity.adapters",
]
allow_indirect_imports = true
# `myapp.composition` fica FORA por construção: instanciar adapter concreto é o
# trabalho dele. Exceção pontual é sempre `ignore_imports = ["a -> b"]` nomeado,
# nunca afrouxar o contrato.
```

```yaml
# --- CI: seis passos bloqueantes, nenhum continue-on-error -----------------
on:
  pull_request:          # NÃO glob de branch — ver eixo 4
  push:
    branches: [main]

jobs:
  api:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env: { POSTGRES_USER: app, POSTGRES_PASSWORD: app, POSTGRES_DB: app }
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U app" --health-interval 5s
          --health-timeout 5s --health-retries 10
    steps:
      - uses: actions/checkout@v7
      - uses: astral-sh/setup-uv@v6
        with: { enable-cache: true }
      - run: uv sync --frozen
      - run: uv run --frozen ruff format --check .
      - run: uv run --frozen ruff check .
      - run: uv run --frozen pyright
      - run: uv run --frozen lint-imports
      - run: uv run --frozen pytest
        env:
          CI: "true"       # o conftest lê isto: sem infra ⇒ FALHA, não skip
          DATABASE_URL: postgres://app:app@localhost:5432/app
```

---

## A régua, eixo a eixo

### 1. Checador de tipos

**REGRA.** `pyright` em `typeCheckingMode = "strict"`, com `include` cobrindo `src` **e** `tests`. Relaxamento existe só como escape local (`# pyright: ignore[reportX]` com justificativa inline); `reportX = false` global é proibido.

**CONDIÇÃO.** Qualquer projeto Python que possa ter Node no ambiente de dev/CI — pyright arrasta Node (via `nodeenv`). Projeto que não pode ter Node **não é knob, é gatilho de reabertura**: a troca invalida claims, não afrouxa uma preferência.

**GARANTIA.** O escape local é auditável e contável (`grep -c "pyright: ignore"` é o orçamento de cerimônia executável); o global é invisível e permanente. `tests` sob strict é o que trava a decisão irmã de que o fake de um port **herda** o port: sem tipo no teste, o fake diverge do contrato em silêncio.

**CENÁRIO.** *Incluir:* no espécime sem trava, `mypy` foi removido do projeto e o wiring manual dos ports passou a ser verificado só pelo trap de runtime do ABC na instanciação — o seam existe e ninguém o checa; `os.getenv("X").strip("/")` sobrevive ao lint e explode em produção porque `str | None` não é pego por ninguém. *Excluir `tests`:* é onde a régua mais dói — no espécime gateado, os ~50 `type: ignore` do repo concentram-se numa **única** fábrica de teste (`replace(_BASE, **over)`), padrão único e nomeável, exatamente o formato que a régua aceita.

**DISSENSO.** Vice = "um checador strict qualquer" (aceitar `mypy --strict` como equivalente). *Steelman:* mypy é a implementação de referência da tipagem de Python, não precisa de Node e tem ecossistema de plugins maior. *Perdeu porque:* as posições deste padrão foram verificadas por experimento **sob pyright** — o não-narrowing de `result.ok: bool`, os mecanismos de conformidade de `Protocol`. Sancionar mypy como intercambiável transformaria claims verificados em claims presumidos, e a régua exige experimento para alegação de comportamento.

**GATILHO DE REABERTURA.** (i) Ambiente que proíba Node; (ii) contagem de escapes crescer **sem** cair num padrão único e nomeável — aí o strict virou ritual e o eixo reabre inteiro.

---

### 2. Lint — as 15 famílias em 3 camadas

**REGRA.** `select` fixo de 15 famílias, `ignore = ["E501"]`, zero adições sem cenário. As famílias se organizam em três camadas com garantias diferentes: **(1) classe-de-bug** (`F`, `B`, `ASYNC`, `E7xx`) — inegociável, zero escape; **(2) consistência-em-escala** (`I`, `N`, `UP`, `TID`, `RUF`, `D`) — o custo aparece passando de algumas dezenas de módulos; **(3) heurística com escape** (`PL`, `SIM`, `C4`, `PTH`) — a garantia **não é a regra**, é o `# noqa` com justificativa.

**CONDIÇÃO.** Camada 1 vale em qualquer projeto Python. Camada 2 vale a partir do momento em que mais de uma pessoa (ou mais de um agente) escreve no mesmo pacote. Camada 3 é a única negociável por projeto.

**GARANTIA.** Camada 1 pega classe-de-bug, não estilo: o espécime sem trava desligou `W0102` (default mutável) no `.pylintrc` e comeu o "default de região avaliado no import" — `B006` é literalmente a mesma regra pelo outro lado, e ligada. Camada 3 não promete código bom: `PLR0913` não impede função ruim, o que ela compra é **forçar decisão nomeada** exatamente onde a complexidade se concentra.

**CENÁRIO.** `TID` com `ban-relative-imports = "all"` é **mais estrito que a PEP 8**, que permite relativo explícito — divergência assumida, com falha nomeada: cadeia de re-export + mover módulo sem reescrever import, que o relativo esconde e o absoluto quebra na hora. No sentido de excluir, duas famílias saem **por redundância medida**: `E501` porque o formatter é dono do comprimento de linha (duas autoridades sobre a mesma coluna produzem conflito, não garantia), e `ANN` porque rodá-la em `src/` sob pyright strict rendeu **1 achado** — redundância provada por número, não por opinião.

**Empates rotulados como arbitrários** (sem fingir princípio): `C4` e `PTH` **nunca dispararam** no espécime gateado. "É de graça" não é garantia — ficam marcados **empate arbitrário, corte livre**. Idem `line-length = 100`: a PEP 8 sanciona 99; 100 é escolha de um caractere.

**Candidatos rejeitados, cada um medido em `src/` e cada um com gatilho:**

| família | medição | por que fora | gatilho |
|---|---|---|---|
| `T20` | **0 achados** | e a hipótese que a justificava era **falsa** — ver abaixo | `print` de produção aparecer em forma que o `T20` veja |
| `S` | 2 achados | ambos triviais; nada demonstrado | primeiro incidente de segurança rastreável a padrão que `S` pega |
| `ARG` | 1 achado | ruído sob assinatura de port | argumento morto virar fonte de bug real |
| `ERA` | 6 achados | código comentado é problema de review | comentário-código sobreviver a review repetidamente |
| `TC` | **147 achados** | churn puro: mover import para bloco `TYPE_CHECKING` em massa, sem defeito atrás | custo de import no boot virar medido |

O `T20` é a peça didática. A hipótese era que ele pegaria o `(log or print)(message)` de produção. **Não pega** — o `print` ali não é nó de chamada de `print`, é um valor default passado como argumento; `T20` é sintático e o padrão é invisível a ele. A regra que "obviamente" resolveria o defeito não o toca; quem o mata é a regra-mãe da observabilidade (eixo 8), por design e não por lint.

**DISSENSO.** Vice = `select = ["ALL"]` com `ignore` grande. *Steelman:* pega regra nova ao atualizar o ruff sem ninguém precisar reavaliar o `select`, e a lista de `ignore` documenta explicitamente o que se recusou. *Perdeu porque:* inverte o default da régua (excluir-por-default vira incluir-por-default), e o custo cai no momento errado — bump de versão passa a poder quebrar o CI com regra que ninguém decidiu adotar, transformando cada upgrade numa sessão de adjudicação não planejada.

**GATILHO DE REABERTURA.** `noqa` de camada 3 crescer sem padrão nomeável ⇒ corta-se a família inteira, não se acrescenta escape.

---

### 3. Fronteiras de import — 4 contratos

**REGRA.** Quatro contratos de import-linter, todos bloqueantes: (1) `layers` por contexto (`domain < application < adapters`); (2) `shared` ↛ qualquer contexto; (3) contexto ↛ `domain`/`adapters` de outro contexto; (4) borda HTTP ↛ `domain`/`adapters` de contexto. Exceção é sempre `ignore_imports` nomeado, **nunca** afrouxar o contrato.

**CONDIÇÃO.** A partir de dois contextos delimitados no mesmo pacote raiz. Com um contexto só, o contrato (1) já paga sozinho.

**GARANTIA.** Os contratos (2), (3) e (4) mecanizam **três regras que a documentação escreve em prosa e máquina nenhuma força**: hoje, sem eles, `shared.domain` importar `finance` passa; a borda alcançar `finance.adapters` direto passa; um contexto tocar o `domain` do outro passa. Os três foram escritos e **rodados** contra o espécime gateado: `3 kept, 0 broken` — mecanizáveis hoje, com **zero** migração. E o mecanismo se limpa sozinho: verificado por experimento, uma exceção obsoleta de `ignore_imports` **derruba o run sozinha** (`No matches for ignored import ...`), então ela se auto-deleta quando o código muda. Exceção que não expira é a cerimônia que a régua corta; esta expira por construção.

**CENÁRIO.** *Incluir (4) agora:* colocar a trava enquanto a borda ainda está quase vazia é o momento mais barato possível — depois cada rota nova é uma negociação. *Não incluir `composition` em (4):* instanciar adapter concreto é literalmente o trabalho do composition root; bani-lo ali seria proibir o padrão que o resto do padrão prescreve.

**DISSENSO.** Vice = contrato `independence` estrito (acoplamento zero entre contextos). *Steelman:* independência real é o que dá autonomia de evolução ao contexto delimitado, e uma dívida nomeada continua sendo dívida — legitimar `finance.application → identity.application` é escolher conviver com acoplamento. *Perdeu porque:* (a) a regra correta de contexto delimitado é **interface publicada**, não acoplamento zero; (b) medido: o `independence` exigiria **3 exceções permanentes no dia 1**, uma por aresta existente, e exceção que nunca expira é exatamente o que a régua corta; (c) "só via `application`" é verde hoje, sem migração. O que uma auditoria anterior tinha chamado de *dívida não-guardada* revela-se **regra não-nomeada** — nomeada, deixa de ser dívida.

**GATILHO DE REABERTURA.** Um contexto precisar evoluir sem coordenar com o outro (deploy separado, time separado, cadência separada) ⇒ `independence` volta à mesa.

---

### 4. Gates de CI

**REGRA.** Conjunto bloqueante de **seis passos**, nesta ordem: `uv sync --frozen`, `ruff format --check`, `ruff check`, `pyright`, `lint-imports`, `pytest`. `continue-on-error` em gate de qualidade é **proibido**. Trigger em `pull_request`, não em glob de branch. **Sem pre-commit/husky** — o CI é a única autoridade; local é comando documentado *idêntico* ao do CI. Sem gate de cobertura. **Em CI, skip de infra vira falha.**

**CONDIÇÃO.** Qualquer projeto com CI hospedado. A ordem importa por custo: os passos baratos falham antes dos caros.

**GARANTIA.** `continue-on-error` é o `fail-under=10` do espécime sem trava em outra roupa — reporta e não para; um gate que não para não é gate, é relatório. **Gate que pode pular em silêncio também não é gate:** medido no espécime gateado, sem `DATABASE_URL` a suíte dá **535 passed, 60 skipped, 3 errors** — um verde que não exercitou **um único** adapter de Postgres, e com as duas guardas incoerentes entre si (Postgres pula, o object store quebra). O `conftest` já raciocinava certo ao gatear em `CI` (porque `DATABASE_URL` vaza para o shell local), mas **nada afirmava que os testes gateados rodaram no CI**: derrube o env do passo e o job fica verde com 60 skips. Daí a regra `if CI and not DATABASE_URL: fail`, com as guardas uniformizadas entre todas as infraestruturas.

**CENÁRIO.** *Trigger em `pull_request`:* modo-de-falha **acontecido** — branch fora do glob configurado ⇒ CI nunca dispara ⇒ o job que abre o PR nunca roda, e o silêncio parece sucesso. *Sem segundo caminho local:* a documentação do mesmo repo já carregava um aviso "NÃO use `<runner> exec <linter>` (falso-verde)" — um segundo caminho local **já produziu** falso-verde antes; pre-commit é a mesma classe de defeito institucionalizada. *Sem cobertura:* cobertura mede execução, não verificação — o espécime sem trava roda `--cov=./` com seis de sete features sem um único teste, e o número sobe do mesmo jeito.

**`-W error` excluído, contra o instinto.** Foi medido: **zero** falhas novas (535 iguais). É grátis. Sai mesmo assim porque "deprecation quebra bump" é conhecimento de indústria e **autoridade não preenche** — não há cenário demonstrado em nenhum dos dois espécimes. Incluí-lo seria aplicar a régua assimetricamente logo depois de matar `T20`, `ANN` e `S` com exatamente esse argumento. **Gatilho específico:** a primeira vez que um deprecation de dependência quebrar um bump, ele entra com cenário.

**DISSENSO.** Vice = pre-commit hooks espelhando os seis passos. *Steelman:* feedback em segundos em vez de minutos, e o autor nunca abre PR vermelho por vírgula — o custo de contexto de um round-trip de CI é real. *Perdeu porque:* cria uma segunda autoridade cujo estado (versão do hook instalada, hook pulado com `--no-verify`) diverge da primeira sem avisar, e o falso-verde local já é modo-de-falha registrado neste portfólio. O mesmo benefício se obtém sem a divergência: um comando local **idêntico** ao do CI, documentado.

**GATILHO DE REABERTURA.** Tempo de CI passar do ponto em que o round-trip domina o ciclo de trabalho ⇒ reavaliar hook local *gerado a partir* da mesma fonte do CI, nunca mantido em paralelo.

---

### 5. Docstrings

**REGRA.** `D` (Google convention) fica em tudo, com **isenção cirúrgica onde o contrato é herdado**: `per-file-ignores` de `["D102", "D107"]` em `**/adapters/**`. `D101` **fica** nos adapters. `D100`/`D103`/`D104` ficam em tudo. `DOC501`/`DOC502` obrigatórios no contrato publicado (`application/`: ports e use-cases), dispensados no interior.

**CONDIÇÃO.** A isenção de `D102` pressupõe que o adapter **herda** o port (o `Protocol` híbrido, em que a classe concreta declara a herança). Sem essa herança, a isenção não se aplica.

**GARANTIA.** Verificado por experimento: sob o `Protocol` híbrido, `inspect.getdoc()` — o que `help()`, IDE, `pydoc` e Sphinx usam — **herda o docstring do port**. Omitir no adapter perde **zero** informação em qualquer superfície que alguém realmente leia. Do lado do `DOC501`/`DOC502`: a espinha do modelo de erro é exceção semântica, que sob pyright strict tem **zero** garantia estática — o contrato vive só no docstring, e sem check "documente suas exceções" é exatamente a prosa-sem-trava do espécime sem trava. `DOC502` cobre o modo-de-falha real: o docstring apodrecendo, documentando exceção que não se levanta mais. Cobertura é **parcial e conhecida**: dispara no `raise` direto, **não** na função que apenas propaga o que a chamada levanta — a trava pina o contrato direto, não o transitivo.

**CENÁRIO.** *Isentar:* medidos **566 docstrings** em `src/`, com **41 textos duplicados em 93 ocorrências (16,4%)**, concentrados no seam port↔adapter — o `create_bill` do repositório SQL repete *palavra por palavra* o docstring do port. Isso reprova no portão anti-cerimônia: dá para cumprir `D102` a 100% e a garantia falhar — mude o contrato no port, esqueça a cópia, e o lint fica verde com um docstring que **mente**. A regra não só não compra garantia: **fabrica** um modo-de-falha novo. *Manter `D101`:* o docstring de classe do adapter diz qual port implementa e o que é específico daquela implementação ("é a camada anticorrupção", "cada método é sua própria transação") — informação que o port não carrega e que ninguém herda.

**DISSENSO.** Vice = manter `D` uniforme, sem isenção. *Steelman:* ler o adapter isolado no editor fica pior — você precisa pular para o port para saber o que o método promete. *Perdeu porque:* o pulo é um `F12`, enquanto a cópia derivada é erro silencioso que sobrevive ao review. A isenção remove a **obrigação**, não a permissão: onde a implementação tem o que dizer, diga.

**GATILHO DE REABERTURA.** (i) Abandonar o `Protocol` híbrido ⇒ a herança de `getdoc` some e `D102` volta aos adapters. (ii) `DOC501` estabilizar (ou mudar de comportamento) ao sair do preview ⇒ revisita das duas linhas de `preview` no baseline.

---

### 6. Façade

**REGRA.** **Import é sempre pelo módulo dono.** A façade de camada morre: `<ctx>/<layer>/__init__.py` reexportando a camada inteira vira **docstring-mapa + `__all__: list[str] = []`**. Sobrevive só a façade de `application/ports/`, onde a descoberta de ports é "marcador `Protocol` + façade" — conjunto pequeno e descobrível, não camada inteira. `__all__` obrigatório **só onde há re-export real**.

**CONDIÇÃO.** Qualquer projeto que use a convenção "estrutura por conceito de domínio" (módulo nomeado pelo conceito, não pelo tipo DDD). É justamente essa convenção — boa, e que fica — que torna a façade invisível à máquina.

**GARANTIA.** Medido:

| | via façade | via módulo dono |
|---|---|---|
| mesmo contexto | 8 | **399** |
| cruzando fronteira | 32 | 58 |
| **total** | **40 (8%)** | **457 (92%)** |

1010 linhas de `__init__.py` mantidas à mão (só o de `finance/application` tem 413) para servir 8% dos imports. E o golpe: **o import-linter não distingue os dois**. Verificado — `from myapp.finance.application import (...)`, a façade canônica com dez símbolos, é resolvida pelo grafo como import de `finance.application.record_payment`, porque o módulo tem o nome do seu símbolo principal. A regra "use a façade" é **inobservável pela máquina** e desobedecida por 92% do código. Uma regra em vez de duas meio-seguidas — e é a que 92% do código já pratica. O que sobra do valor original (navegação, `D104`) cabe num parágrafo de docstring.

**CENÁRIO.** *Matar:* mudar a assinatura de um símbolo exige tocar a façade **e** o módulo; esquecer a façade produz re-export defasado que pyright às vezes pega e às vezes não, dependendo de `__all__`. *Não matar tudo:* a façade de `ports/` é o mecanismo de descoberta já decidido em outro eixo — decisão-irmã fechada não se re-decide aqui. Sobre `__all__`: verificado que **sem ele**, pyright strict acusa `reportUnusedImport` no módulo que reexporta; onde o módulo define o que exporta, `__all__` não compra nada mecânico e é cerimônia.

**DISSENSO.** Vice = manter a façade como interface publicada do contexto. *Steelman:* é exatamente o conceito que o contrato de fronteira do eixo 3 invoca — "conversa só pela camada `application`" soa como "só pela façade da `application`". *Perdeu porque:* dois fatos medidos — a fronteira **já é** mecanizada sem ela (o contrato opera no pacote, não na façade), e o único mecanismo que a forçaria é cego a ela. Regra não-forçável com 8% de adesão não é regra, é folclore.

**GATILHO DE REABERTURA.** import-linter (ou equivalente) ganhar resolução em nível de símbolo ⇒ a façade volta a ser mecanizável e o cálculo muda.

---

### 7. Idioma do código

**REGRA.** **Um idioma por codebase, escolhido uma vez, registrado.** Inglês é o **default**, não dogma. Costura com o domínio explícita e de mão única: termo de domínio na língua do domínio vive no glossário; o código usa o identificador traduzido. Copy de usuário na língua do usuário. **Sem mecanismo** — convenção verificada em review.

**CONDIÇÃO.** A regra "um só idioma" é incondicional. *Qual* idioma é escolha do projeto; a forma que porta é a condicional, não a escolha.

**GARANTIA.** Nomeável e específica: **identificador híbrido**. A superfície de API do ecossistema Python é inglês, então idioma misto produz `parse_lancamento` em cada seam de chamada — a fronteira entre os dois idiomas não fica numa camada, fica em cada assinatura. O inglês como default vem de empírico do próprio portfólio: custo de migração **zero** nos dois espécimes. "Copy na língua do usuário" não é exceção à regra, é a regra aplicada: *artefato de código* no idioma do código, *copy de produto* no idioma de quem lê.

**CENÁRIO.** *Não mecanizar:* medido no espécime gateado, a regra de idioma **não tem trava nenhuma** e segurou em **99,9%** — apenas 7 ocorrências de identificador em pt-BR espalhadas por 102 arquivos (`remetente` ×4, `competencia` ×2, `descricao` ×1); as outras 73 ocorrências em pt-BR são copy de produto em string, que a regra permite. O espécime sem trava já é 100% inglês. Uma trava aqui compraria ~7 achados de uma vez e depois ficaria verde para sempre, ao custo de manter um dicionário de palavras proibidas — cerimônia com garantia marginal. *Mecanizar se:* auditoria achar vazamento passando de ~1% dos identificadores.

**DISSENSO.** Sem rival vivo quanto à regra (um idioma só é consenso). O rival é sobre a **camada**: trava-máquina (lista de termos proibidos em `flake8-tidy-imports`/regex customizado) versus convenção. *Steelman da trava:* é a mesma estrutura de argumento que fez o eixo 6 matar a façade — "regra não-forçável decai". *Perdeu porque:* a premissa é empírica e foi **medida no sentido oposto**. Ver a assimetria abaixo.

**GATILHO DE REABERTURA.** Vazamento acima de ~1% dos identificadores numa auditoria, ou entrada de contribuidores que não compartilham a língua do domínio.

---

### 8. Observabilidade — a regra-mãe

**REGRA.**

> **Porta-se o que a decisão consome; não se porta o que apenas a registra.**

**CONDIÇÃO.** Vale em qualquer projeto que use ports e a `logging` da stdlib. Não vale onde o log É o produto (pipeline de auditoria) — aí ele cai na cláusula de evento, abaixo.

**GARANTIA.** O `Clock` é port porque o tempo é **entrada da decisão**: a saída depende dele e o teste precisa controlá-lo. O log é **saída da qual nenhuma decisão depende** — injetá-lo põe um parâmetro transversal em toda assinatura para permitir asserção que testa implementação, não comportamento. E a hierarquia de loggers da stdlib **já é** o seam: config no root, `getLogger(__name__)` na folha. O port reimplementaria pior algo que a stdlib entrega.

**O corte que evita o abuso da regra.** Se uma linha de log é **requisito** — trilha que alguém precisa poder provar — então não é log: é **evento**, vira port com teste. A pergunta que separa as duas: *"se isso sumisse, alguém teria direito de reclamar?"* Se sim, é evento e ganha port, contrato e asserção. Se não, é `getLogger(__name__)`.

**CENÁRIO.** A contradição estava dentro do mesmo contexto do espécime gateado: um use-case registra **por escrito** a escolha pelo `getLogger` direto; outro injeta um parâmetro `log` com **default `print`**. Adjudicado a favor do `getLogger`. **Corolário: `(log or print)` morre.** Em produção isso escreve stdout cru, fora da hierarquia, sem nível, sem formato, sem filtro — parece log e não é. E note o encadeamento com o eixo 2: é precisamente este `print` que o `T20` **não** pega, porque não é nó de chamada de `print`. A regra de design mata o que o lint não alcança.

**DISSENSO.** Vice = log como port. *Steelman:* o levantamento do campo registra convergência forte em "port para toda dependência", e log é I/O — a mesma categoria de `Clock` e repositório. *Perdeu porque:* a convergência foi argumentada sobre dependências que a decisão **consome**, e a stdlib já entrega o seam que o port reimplementaria pior. O steelman prova demais: por ele, `time.monotonic` num contador de métrica também viraria port.

**GATILHO DE REABERTURA.** Requisito de asserção sobre log em teste que **não** seja melhor modelado como evento de domínio.

---

### 9. Configuração de logging, formato e correlação

**REGRA.** Configurar logging é **obrigatório** e mora no composition root, ponto único. Formato JSON estruturado **não é prescrito** — é condicional. Correlação de request **é** prescrita. Dado pessoal não entra em log sem máscara.

**CONDIÇÃO.** *JSON:* "quando os logs forem para um agregador que consulta **por campo**, o formatter vira JSON e os identificadores migram de `%`-format para `extra=`." Enquanto a leitura for `docker logs`, JSON é custo sem consumidor. *Correlação:* adiável com gatilho enquanto a borda não servir requisição de produto.

**GARANTIA.** *Config no root:* sem config explícita, nível e formato são o default do root logger sob o servidor ASGI — ninguém decidiu, foi herdado; um `logger.debug` com dado sensível pode virar visível por **mudança de default do servidor**, exposição que ninguém autorizou. *Correlação:* passa o portão anti-cerimônia por ser **verificável por teste** — a resposta de erro carrega um id que aparece na linha de log daquela request; um teste afirma a igualdade. Custo ~30 linhas: middleware + `contextvar` + campo.

**CENÁRIO.** O argumento usual para correlação (logs concorrentes se entrelaçando) é **fraco** num app de duas pessoas, e foi descartado. O cenário que sustenta é o **loop de suporte**: dá erro, a pessoa diz "deu erro agora", e é preciso achar *aquela* request. Como a borda `application/problem+json` já é madura e já carrega extensões, o id entra como extensão do corpo do erro e o `grep` acha. *Máscara:* a prática já existe no espécime gateado (`_mask_phone` preserva o `+` e dois dígitos) — falta ser regra. Não é mecanizável, então cai na mesma camada da regra de idioma (convenção verificada em review), com o mesmo lastro empírico.

**DISSENSO.** Vice = JSON estruturado desde o dia 1. *Steelman:* migrar depois exige tocar todas as chamadas que hoje interpolam com `%`, e formato é exatamente o tipo de coisa que ninguém volta para arrumar. *Perdeu porque:* o custo de migrar foi estimado e é **limitado** — troca de formatter no ponto único + mover campos para `extra=` —, e prescrever formato sem consumidor é a definição de cerimônia. A regra condicional carrega o gatilho junto, então não se perde.

**GATILHO DE REABERTURA.** Entrada de um agregador que consulte por campo ⇒ JSON vira obrigatório na mesma linha do composition root.

---

## A assimetria — a medição decide a camada

Duas regras deste arquivo são estruturalmente idênticas: ambas são prosa, ambas não têm trava-máquina, ambas se aplicam a todo o `src/`. O veredito foi **oposto**, e o que decidiu foi um número.

- **Façade** — 8% de adesão a uma regra não-forçável ⇒ **mata-se a regra**. Ninguém a segue, a máquina não a vê, e o custo de manutenção (1010 linhas escritas à mão) é real.
- **Idioma** — 99,9% de adesão a uma regra igualmente não-forçável ⇒ **a regra funciona e mecanizá-la compraria ~nada**. Fica como convenção, verificada em review.

*A medição decide a camada, não a doutrina.* Não existe princípio geral "regra sem trava decai" nem "convenção basta" — existe uma pergunta empírica, respondida por contagem, projeto a projeto. Quem levar qualquer um dos dois vereditos como doutrina portátil está aplicando a conclusão sem o método.

---

## Nota de método

Quatro hipóteses do autor morreram por medição durante a sessão que produziu este arquivo, e ficam registradas porque a régua manda **experimento** decidir alegação de comportamento:

1. **`T20` pegaria o `print` de produção** — **não pega**. O `(log or print)(message)` não é nó de chamada de `print`; a regra é sintática e o padrão é invisível a ela.
2. **Não haveria skip silencioso na suíte** — **há 60**, e um verde local que não exercita um único adapter de Postgres.
3. **A regra de idioma teria decaído sem trava** — **99,9% intacta**, 7 identificadores vazados em 102 arquivos.
4. **A façade estaria viva nas fronteiras** — **36% ali, 8% no total**, e invisível à máquina que supostamente a forçaria.

**Três das quatro inverteram a recomendação que o autor levava pronta.** Nas quatro, o instinto era plausível, articulável e errado. É exatamente por isso que a régua exige experimento contra as versões pinadas antes de promover qualquer alegação de comportamento a regra — e por isso o baseline acima traz medição junto de cada linha não óbvia, em vez de autoridade. Autoridade não preenche.
