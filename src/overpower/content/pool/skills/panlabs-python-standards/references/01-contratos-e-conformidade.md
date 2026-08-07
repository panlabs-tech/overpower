# Contratos e conformidade — ports, dublês e a prova de que o adapter cumpre o contrato

Este eixo responde uma pergunta só, em seis pedaços: **como você garante — por máquina, não por disciplina — que o adapter concreto e o dublê de teste realmente cumprem o contrato do port?** Cobre o mecanismo do contrato (`Protocol` × `ABC`), onde a checagem dispara, o teste que amarra o comportamento que tipo nenhum enxerga, a doutrina de fakes, a granularidade do port e onde os ports moram.

> Régua: toda posição abaixo passou pelo portão anti-cerimônia — cenário nomeado nos dois sentidos, garantia verificável, autoridade não preenche.

## Espécimes de evidência

As posições citam três corpos de evidência, sempre como **evidência-caso**, nunca como justificativa por autoridade:

- **o espécime gateado** — backend Python 3.14 / FastAPI / uv, ~102 arquivos, 4 contextos, com `pyright` strict + `ruff` + `import-linter` gateando o merge e ~600 testes. É o caso "tem trava de máquina".
- **o espécime sem trava** — backend Python de Lambdas com vertical slices e ports em `ABC`, Clean/Hexagonal nominal, **sem** type-checker (o `mypy` foi removido do repositório) e sem `import-linter`. É o caso "tem a forma, não tem a garantia".
- **o radar de produção** — seis backends Python públicos lidos por eixo (Netflix Dispatch, Polar, Prefect, Warehouse/PyPI, Sentry, mais o template full-stack de FastAPI, este último rotulado template e não produção).

As posições §1 e §2 leem-se **em par**: §1 fixa o mecanismo, §2 fixa em que condição aquele mecanismo é o certo. Ler §1 sozinha produz aplicação errada fora do Ramo A.

---

### 1. Mecanismo de contrato — `Protocol` híbrido

**REGRA.** O port é `Protocol`, não `ABC`. O adapter concreto **e o seu dublê de teste** declaram herança do port — `class SqlBillRepo(BillRepo)` — para que a conformidade seja checada no lugar onde não dá para esquecer: a **definição**.

```python
# finance/application/ports/bill_repo.py
class BillRepo(Protocol):
    async def get(self, bill_id: UUID, household_id: UUID) -> Bill | None: ...
    async def close(self, bill_id: UUID, expected_version: int) -> bool: ...

# finance/adapters/sql_bill_repo.py — herda: deriva de assinatura falha AQUI
class SqlBillRepo(BillRepo): ...

# tests/finance/fakes.py — o fake herda o mesmo port, pela mesma razão
class FakeBillRepo(BillRepo): ...
```

**CONDIÇÃO.** Vale quando (a) um type-checker strict gateia o merge **e** (b) o conjunto de implementadores é fechado e in-repo — todo adapter e todo fake são escritos no seu próprio repositório. Implementador que só aparece em runtime, ou tipo de terceiro que você não pode fazer herdar, cai no Ramo B da §2.

**GARANTIA.** A checagem é colhida na definição do adapter, o arquivo que você sempre edita ao mexer no contrato. Verificável por máquina: em modo strict, `pyright` reporta assinatura incompatível na própria definição via `reportIncompatibleMethodOverride` — que é `none` em basic e vira `error` **só** em strict — e membro faltante na instanciação. A mesma checagem cai de graça sobre o fake, porque o fake também herda. Custo: +1 token por adapter.

**CENÁRIO.**
- *Omitir (estrutural puro):* sem herança, o type-checker não acusa nada na definição — o erro só nasce no **ponto de uso/injeção** (`reportArgumentType` / `reportReturnType`, no retorno de uma factory anotada ou no argumento do use-case). Se esse pino tipado não existir, não acusa em lugar nenhum. Medição no espécime gateado: a garantia estrutural estava sendo colhida em **3/10** pontos — o composition root anotava apenas `provide_clock`, `provide_settings` e o fake de um matcher; os **7 repos SQL** não tinham anotação com seu `Protocol` em ponto algum, de modo que uma deriva de assinatura repo↔port **não seria pega pelo type-checker**, só talvez pelos testes de comportamento. O buraco fica exatamente onde a deriva é mais provável.
- *Aplicar onde não cabe:* forçar herança num adapter que não pode herdar (tipo de terceiro, objeto de plugin, classe gerada por codegen) troca a checagem por um erro de hierarquia ou de import; nesses casos o port deve ser satisfeito estruturalmente e a conformidade volta ao ponto de injeção.
- *Armadilha do híbrido:* um membro do `Protocol` com corpo `...` que o adapter **não** sobrescreve vira, em runtime, um no-op que devolve `None` — o type-checker recusa instanciar, mas nada trava em runtime. Só `@abstractmethod` no membro dá trava de runtime (§2).

**DISSENSO.** Vice = `Protocol` estrutural puro, sem ninguém herdar. *Steelman:* desacoplamento máximo — o adapter não precisa conhecer o port, e um tipo pode satisfazer um port que não foi escrito pensando nele; é também o estado default de quem já adotou `Protocol`, então "não mudar nada" é gratuito. *Perdeu porque:* o único poder exclusivo do estrutural puro (satisfazer um port não-escrito) não tem cenário vivo num conjunto fechado, e a medição 3/10 mostra que a garantia anunciada não estava sendo colhida na prática.

**GATILHO DE REABERTURA.** Surgir adapter que não pode herdar (terceiro, plugin, codegen); ou o type-checker deixar de tratar `reportIncompatibleMethodOverride` como erro em strict no arranjo híbrido.

### 2. Verificação — onde a checagem dispara (regra de dois ramos)

**REGRA.** Escolha o mecanismo por "onde o implementador se torna conhecido".
- **Ramo A** (conjunto fechado + gate estático no merge): conformidade **estática** pelo híbrido da §1, **sem** trava de runtime.
- **Ramo B** (implementador aberto): trava de **runtime** — `@abstractmethod` **dentro do próprio `Protocol`**. Escale a `abc.ABC` só quando precisar de `register()` para um tipo não-herdável, ou de semântica nominal-only. `zope.interface` fica fora: peso alto e ecossistema efetivamente restrito a Pyramid.

```python
# Ramo B: o mesmo Protocol, com trava de runtime — implementação incompleta
# levanta TypeError na instanciação, sem migrar para ABC nem perder o match estrutural.
class StorageBackend(Protocol):
    @abstractmethod
    def put(self, key: str, blob: bytes) -> None: ...
```

**CONDIÇÃO.** O predicado é uma pergunta só: o implementador fica conhecido em **type-check time** (A) ou só em **runtime** (B)? Cai no Ramo B se houver qualquer um de — plugins / entry-points, adapter selecionado por string de config, multi-backend, tipo de terceiro, ou CI heterogêneo em que o gate estático não roda sobre todo implementador.

**GARANTIA.** Ramo A: o type-checker strict barra a instanciação incompleta no CI, antes do merge — verificável e antecipada. Ramo B: `TypeError` na instanciação, no processo que carrega o implementador desconhecido — verificável só quando o caminho executa, que é precisamente por que essa trava existe ali e não no Ramo A.

**CENÁRIO.**
- *Omitir a trava no Ramo B:* uma implementação incompleta carregada por entry-point instancia limpa e estoura `AttributeError` no primeiro método faltante, já em produção — não há gate anterior que a tenha visto.
- *Aplicar a trava no Ramo A:* a trava de runtime **nunca dispara**, porque o type-checker strict já barrou a instanciação incompleta no CI. É cerimônia pelo teste da garantia verificável: você paga herança obrigatória e ruído por um evento que não pode ocorrer.
- *Evidência do lado oposto:* no radar de produção, ports aparecem quase só em seams de **segunda implementação real** (multi-backend, integração plugável, RPC cross-silo), via `abc.ABC` ou `zope.interface` — quase nunca `typing.Protocol` como fronteira. O motivo é consistente com a regra: naquelas apps o implementador chega em runtime **e** não existe type-checker strict gateando universalmente o merge; o `ABC` delas *substitui* um gate estático que elas não rodam.
- *Base de medição:* o comportamento de cada mecanismo (onde o erro nasce, o que trava, o que `isinstance` checa) foi medido por experimento contra CPython 3.14.4 e pyright 1.1.411, não inferido de documentação.

**DISSENSO.** Vice = `ABC` uniforme em todo port, sem ramos. *Steelman:* um mecanismo só é mais simples de ensinar e imune ao erro de classificar mal o ramo; é o que a produção efetivamente faz; e reaproveita corpo default e docstring por herança, coisa que o estrutural não dá. *Perdeu porque:* impõe trava de runtime a um conjunto fechado e gateado onde ela nunca dispara, e força acoplamento de herança onde a checagem já vem de graça.

**GATILHO DE REABERTURA.** A→B quando o projeto ganhar plugins/entry-points, seleção de adapter por config, multi-backend, tipo não-herdável, ou o gate estático deixar de ser universal no CI.

### 3. Contract test — o contrato semântico que tipo nenhum enxerga

**REGRA.** Todo port que tem **fake e adapter real** é amarrado por **um** contract test: uma única suíte de asserções rodada contra os **dois** sujeitos, com o sujeito real gateado por variável de ambiente de infra (`DATABASE_URL` e equivalentes). Deriva entre fake e real faz a suíte falhar.

**CONDIÇÃO.** *Se* você usa fake de port em teste de use-case, *então* o contract test é obrigatório — sem ele o fake é um dublê não-verificado. Não se aplica a port cujo contrato é puramente de **forma** (o tipo já cobre), nem a projeto que testa use-case contra a infra real (não há fake a amarrar).

**GARANTIA.** Amarra por máquina a afirmação "o fake se comporta como produção", que é a premissa silenciosa de toda suíte de use-case com fake. Cobre o que o type-checker é cego para ver: que uma operação é de fato **compare-and-swap**, que o escopo por tenant/agregado não vaza entre linhas, que a coluna se chama mesmo `household_id`, que o presign não assina checksum. Tipo prova forma; só teste contra o real prova comportamento. E não adiciona trabalho: **dedupe** — consolida duas suítes escritas à mão em uma suíte rodada duas vezes.

**CENÁRIO.**
- *Omitir:* o contrato passa a ser mantido por duplicação disciplinada — duas suítes paralelas que só coincidem enquanto alguém lembrar. No espécime gateado, `FakeBillRepo` e `SqlBillRepo` eram testados por suítes separadas escritas à mão; existia **um** contract test genuíno (fidelidade do `MetaData` contra o schema migrado), e nenhum de comportamento. Esta regra generaliza aquele um, de schema para comportamento. O extremo está no espécime sem trava: nenhum fake, `Mock(spec=AdapterConcreto)` (o adapter concreto, não o port) e `@patch` da biblioteca — e, com `ABC` herdada em **10/10** adapters, bugs vivos passando (um `UnboundLocalError` no caminho de timeout de um cliente HTTP; e-mail saindo em produção com `{{placeholders}}` crus).
- *Aplicar onde não cabe:* exigir contract test de port sem adapter real, ou de port puramente-forma, produz suíte que não pode falhar por deriva — ritual.

A **forma** executiva (fixture parametrizada pelo sujeito, casa em `tests/<contexto>/contracts/`) e o **escopo** por papel do dublê pertencem à doutrina de testes: ver `05-doutrina-de-testes.md`.

**DISSENSO.** Vice = duplicação disciplinada (manter as duas suítes à mão). *Steelman:* sem banco no CI, metade real skipa de qualquer jeito, então "a disciplina cobre o resto"; e suítes separadas por sujeito são mais legíveis, cada uma falando a língua do seu adapter. *Perdeu porque:* a metade que skipa é limite do **gate de infra**, não do mecanismo — quando o banco está lá, o oráculo compartilhado vale por inteiro; e "disciplina" é exatamente a garantia não-verificável que o portão anti-cerimônia corta.

**GATILHO DE REABERTURA.** A estratégia de teste de use-case trocar fake por infra real (some o fake a amarrar); ou um port cujo contrato seja inteiramente capturado pelo tipo.

### 4. Fakes e dublês

**REGRA.**
- **(a) Localização.** Dublê de teste genuíno — Fake de um port que tem adapter real — mora em `tests/<contexto>/fakes.py`, compartilhado e importado uma vez. Null-object que **embarca como implementação de produção** (port sem adapter real) **não é fake**: vira adapter real `NullNotifier` / `NoOpNotifier` em `adapters/`, sujeito ao contract test da §3.
- **(b) Nome.** `Fake<Port>` como default, seguindo o papel na taxonomia de Meszaros. Dublê que não é Fake leva nome fiel ao seu papel (`FixedClock` é um Stub e continua `FixedClock`).
- **(c) Forma.** In-memory (`dict`/`list`), comportamento-completo, Fake+Spy onde a asserção precisa inspecionar saída indireta, e herdando o port conforme §1.
- **(d) Mock × Fake.** Fake para todo port que **você possui**, nunca mock. `unittest.mock` banido. `monkeypatch` só para estado global de processo ou variável de ambiente.

**CONDIÇÃO.** Vale para port definido no seu próprio repositório. Dependência de terceiro que você não possui e não envolveu num port seu está fora deste eixo — envolva primeiro, depois fake.

**GARANTIA.** Fake fora de `src/` tira código de teste do wheel de produção — verificável por inspeção do artefato construído. `unittest.mock` banido é grep-ável no CI. A sincronia fake↔port é comprada pelo **contract test** (§3), não pela proximidade física — é isso que libera a mudança de (a). Já a fidelidade do **nome** ao papel Meszaros **não é verificável por máquina**: é convenção sustentada por revisão, e vale dizer isso com todas as letras.

**CENÁRIO.**
- *Omitir:* mock acopla o teste à implementação — verbatim de Fowler, "changing the nature of calls… usually cause a mockist test to break". O espécime sem trava é o anti-exemplo completo: zero fakes, `Mock(spec=AdapterConcreto)` e `@patch` da lib, isto é, teste caixa-branca que afirma chamada de biblioteca; a `ABC` herdada não compra absolutamente nada no teste. No espécime gateado a doutrina classicista está viva (zero `unittest.mock`, `FakeBillRepo` como Fake+Spy in-memory, `FixedClock` como Stub), mas com dívida de localização e nome: **13 fakes** morando em `src/`, `FakeBillRepo` duplicado 2× e três convenções concorrentes (`Fake*` × `InMemory*` × `Fixed*`).
- *Aplicar onde não cabe:* renomear tudo para `Fake*` mente sobre o papel — `FixedClock` é *control point* das entradas indiretas (Stub) e é impl de produção; e mover para `tests/` um null-object que produção importa quebra o build.

**DISSENSO.** Vice = manter os fakes em `src/`, co-locados com o port. *Steelman:* proximidade — quem edita o port vê o fake na mesma pasta e atualiza junto; e um fake em `src/` é publicável com o pacote, de modo que consumidores externos possam testar contra o seu port. *Perdeu porque:* a sincronia passa a ser subsumida pelo contract test da §3, e não existe consumidor externo — é aplicação, não biblioteca.

**GATILHO DE REABERTURA.** Um contexto virar biblioteca publicada cujos consumidores testam contra o port — aí o fake volta para o pacote, num submódulo `testing` explícito.

### 5. Granularidade do port

**REGRA.** Port **coeso por agregado/repositório** é o default — gordo tudo bem se coeso. A disciplina obrigatória é **liveness**: todo método do port tem ≥1 consumidor vivo; método sem consumidor **se deleta**. Role interface (ISP) só entra por cenário nomeado: (a) implementações divergentes — read model com adapter próprio (CQRS) → split reader/writer; (b) least-privilege de tipo → `Protocol` **estrutural declarado pelo consumidor**, que o adapter gordo satisfaz de graça por causa do híbrido da §1. Adapter herdando N role interfaces é dominado pela forma (b) — não fazer.

**CONDIÇÃO.** A granularidade espelha a **coesão da coisa** (eixo estável: o agregado, o recurso), não a do consumidor (eixo volátil: quem chama hoje).

**GARANTIA.** Liveness é verificável: para cada método do port, uma busca de referências responde se há consumidor. Zero consumidores é achado objetivo, não opinião — e é o check que faz "port coeso" parar de degenerar. Já "coeso" em si **não é verificável por máquina**: é julgamento de quem escreve, e a liveness é a única trava que se pode automatizar em cima dele.

**CENÁRIO.**
- *Omitir a liveness:* o espécime sem trava tem `IDataCatalogAdapter` com **5 métodos e 1 usado**. A leitura fácil é "port gordo demais, segregue"; o diagnóstico correto é **método morto**. Segregar apenas embrulha código morto numa interface nova; deletar resolve. O mesmo bug existe no espécime gateado em escala menor: `BillRepo.set_logo` tem **0 consumidores**.
- *Aplicar ISP onde não cabe:* interface mínima por consumidor, num conjunto com um adapter e um fake, produz N interfaces sem nenhuma segunda implementação — proliferação sem ganho, e o custo recai sobre cada implementador. O radar de produção não prolifera role interfaces, e a referência de repositório-por-agregado (Cosmic Python) argumenta o mesmo default.

**DISSENSO.** Vice = ISP por consumidor (cada use-case declara a interface mínima que consome, e o adapter as implementa). *Steelman:* superfície de dependência honesta — o tipo do parâmetro conta exatamente o que aquele use-case pode fazer, e barra por construção chamar um método-irmão por acidente. *Perdeu porque:* no conjunto fechado, um-adapter/um-fake torna a segregação sem ganho estrutural, e o `Protocol` estrutural declarado-pelo-consumidor entrega o mesmo least-privilege sem tocar no adapter — dominando a forma por herança.

**GATILHO DE REABERTURA.** O read model ganhar adapter próprio (CQRS) → split reader/writer; ou least-privilege virar garantia desejada → nasce um `BillReader` estrutural declarado pelo consumidor.

### 6. Onde os contratos moram e como são descobertos

**REGRA.** Fatia vertical por conceito. Ports **segregados em pasta própria**, `<contexto>/application/ports/`, separados de `use_cases/`; `ports/{inbound,outbound}` só quando **ambos** os papéis estiverem povoados. Port vive na camada de **aplicação**, nunca em `domain/`. Nome por papel/capacidade (`BillRepo`, `AttachmentStore`, `Clock`), sem prefixo `I` nem sufixo `_interface`.

```
src/<pkg>/finance/
├── domain/                     # entidades e regras puras — não conhece port nenhum
├── application/
│   ├── ports/                  # a casa do contrato; ports/{inbound,outbound} só se ambos povoados
│   │   ├── bill_repo.py        # class BillRepo(Protocol)
│   │   └── attachment_store.py
│   └── use_cases/
└── adapters/                   # SqlBillRepo, R2AttachmentStore, NullNotifier
tests/finance/
├── fakes.py                    # FakeBillRepo — dublê genuíno, fora do wheel
└── contracts/                  # a suíte única rodada contra fake e real (§3)
```

**CONDIÇÃO.** Vale sob topologia de fatia-vertical-por-conceito — a convergência tanto do radar de produção quanto das referências hexagonais. Projeto layer-first global muda o eixo e esta posição não porta como está.

**GARANTIA.** A **descoberta** ganha três camadas, uma delas verdade-máquina: a pasta `ports/` (convenção), o marcador `Protocol` (`grep 'class .*(Protocol)'` ou introspecção — funciona mesmo se a pasta estiver errada) e a façade no `__init__` (conveniência). A **fronteira**, por outro lado, não é comprada pela pasta: é comprada por `import-linter` + type-checker. Pasta compra legibilidade; máquina compra arquitetura. As duas são ortogonais, e tê-las juntas custa zero. Agrupar por **papel** é legítimo — o que se proíbe é bucket por tipo de DDD (`entities/`, `value_objects/`), que corta o código pelo eixo errado.

**CENÁRIO.**
- *Pasta sem máquina:* o espécime sem trava tem topologia impecável — `domain/interfaces/`, adapters herdando `ABC` em 10/10 — e nenhuma cerca: `import awswrangler` dentro de um use-case, `os.getenv` / URL / `datetime.now` no núcleo de **4** use-cases, `mypy` removido e sem `import-linter`. Pasta bonita não é fronteira; adote pasta **e** máquina.
- *Máquina sem pasta:* os ports se misturam aos use-cases no mesmo nível e a descoberta cai só no grep — legibilidade perdida sem economia real.
- *Aplicar onde não cabe:* `inbound/` criado vazio é cerimônia — a maioria dos contextos só tem outbound, e um handler público já serve de driver port. E segregar **arquivos** não é licença para proliferar **interfaces**: a §5 fica intacta.
- *Port em `domain/`:* inverte a dependência — o domínio passa a conhecer a fronteira de I/O, que é exatamente o que a camada de aplicação existe para absorver.

**DISSENSO.** Vice = plano dentro de `application/` (módulos por papel, sem pasta dedicada). *Steelman:* menos aninhamento para uma escala pequena, e é o que se vê em produção — módulos-de-papel como arquivos, não pastas, quando há dois ou três ports. *Perdeu porque:* consistência ("ports têm casa", independente da escala, em vez de julgamento caso a caso), legibilidade, a referência hexagonal que fixa `application/ports/{inbound,outbound}` como estrutura de primeira classe, e preferência autoral nomeável — que decide no mérito. O custo, uma pasta com dois arquivos, é nulo.

**GATILHO DE REABERTURA.** O projeto adotar topologia layer-first global.

---

## Aplicação rápida

| Pergunta | Resposta | Posição |
| --- | --- | --- |
| Implementadores todos in-repo e type-checker strict gateia o merge? | Sim → `Protocol` + adapter e fake herdam. Não → `@abstractmethod` no `Protocol` (ou `ABC` se precisar de `register()`). | §1, §2 |
| Existe fake deste port usado em teste de use-case? | Sim → contract test único rodado contra fake e real. | §3 |
| Este dublê embarca em produção? | Sim → não é fake: é adapter `Null*`/`NoOp*` em `adapters/`. Não → `tests/<contexto>/fakes.py`. | §4 |
| Este método do port tem consumidor? | Não → delete. Nunca segregue para esconder método morto. | §5 |
| Onde declaro o port? | `<contexto>/application/ports/`, nome por capacidade, fronteira travada por `import-linter`. | §6 |
