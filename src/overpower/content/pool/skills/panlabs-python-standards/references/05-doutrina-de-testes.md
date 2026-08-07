# Doutrina de testes — onde o dublê para, onde o real começa e o que prova o quê

A pergunta deste eixo é uma só, e ela se ramifica em oito: **em que ponto o dublê deixa de provar alguma coisa e o recurso real precisa entrar?** Responder isso decide a pirâmide (quem é testado com fake, quem é testado com Postgres de verdade), o gate que liga a infra real, a forma e o escopo do oráculo que impede o fake de mentir, onde cada arquivo de teste mora, como um caso é escrito, o que cobertura e mutation provam de fato, e como tempo e assincronia entram sem virar dublê-do-ambiente.

> Régua: toda posição abaixo passou pelo portão anti-cerimônia — cenário nomeado nos dois sentidos, garantia verificável, autoridade não preenche.

Três espécimes aparecem como evidência-caso ao longo do texto, nunca como justificativa. **O espécime gateado**: um backend Python 3.14 / FastAPI / uv, ~102 arquivos de código, 4 contextos de domínio, com pyright strict + ruff + import-linter gateando o merge e ~600 testes que rodam sem banco nenhum. **O espécime sem trava**: uma base de Lambdas sem type-checker e sem fake nenhum, que testa dublando o adapter concreto (`Mock(spec=AdapterConcreto)`) e aplicando `@patch` sobre a lib de terceiro. **O radar de produção**: seis backends Python reais, varridos para mapear o que a prática dominante faz — e ali testar use-case contra banco real é universal, fake é raro.

## Experimentos que decidiram

A régua manda verificar comportamento, não citar promessa. Quatro experimentos foram rodados contra as versões pinadas (CPython 3.14, pytest 8, pytest-asyncio 1.4.0, ruff e pyright pinados) e são o que sustenta quatro das posições abaixo.

1. **Fixture parametrizada com `marks` por parâmetro funciona.** Uma única suíte de asserções, parametrizada por implementação, com o sujeito real gateado no próprio parâmetro: sem `DATABASE_URL` no ambiente o resultado é `1 passed [fake], 1 skipped [real]`; com ela, `2 passed`. E os `ids` do parâmetro dizem, no relatório, **contra qual sujeito** o contrato falhou — a informação que torna o oráculo acionável.
2. **Cobertura como diagnóstico efêmero é possível sem sujar o projeto.** `uv run --with pytest-cov pytest --cov=…` produz o relatório completo e **não toca** `pyproject.toml` nem o lockfile — verificado por `git status` limpo depois da execução. Logo, medir cobertura não exige adotar cobertura como dependência nem como artefato.
3. **`ruff` TID251 (`banned-api`) pega o relógio.** A regra banindo `datetime.datetime.now` e `datetime.date.today` acusou **as duas** chamadas num arquivo de teste, com mensagem custom apontando o port `Clock`. A convenção "não leia o relógio real" vira erro de gate, não achado de review.
4. **Correção a um research anterior.** Um research afirmava que, sob `asyncio_mode = "strict"`, um teste `async` sem marker "silenciosamente não roda" — o clássico verde vazio. **Falso nas versões pinadas:** o mesmo arquivo sob strict deu `FAILED: async def functions are not natively supported`. Strict falha **alto**. A régua manda **realidade medida acima de promessa documentada**, e aqui isso matou uma alegação inteira de um research: o argumento a favor de `asyncio_mode = "auto"` é ergonomia, e só ergonomia.

---

### 1. A pirâmide — onde o fake para e o real começa

**REGRA.** Uma camada, um regime de dublê, sem mistura:

| Camada | Dublê | O que o teste prova |
|---|---|---|
| Domínio (funções puras sobre tipos nativos) | **nenhum** — chamada direta | a regra de negócio, determinística |
| Use-case / orquestração | **fake de port, sempre** | a decisão e o encadeamento, offline |
| Adapter | **nenhum** — infra real, gateada | que o SQL, o mapeamento e o driver funcionam |

**CONDIÇÃO.** Vale onde os três existem simultaneamente: (i) port explícito entre use-case e infra, (ii) type-checker strict gateando o merge, (iii) suíte de adapter rodando contra a infra **real**.

Faltando **qualquer um** dos três, a regra se inverte: o teste de use-case contra banco real passa a ser o correto, porque ali ele é a única rede que existe. Sem (i) não há o que fakear sem acoplar ao concreto. Sem (ii) nada garante que o fake e o real ainda têm a mesma assinatura — foi assim que o espécime sem trava chegou a dublar o adapter concreto com `Mock(spec=…)`, forma que fica verde mesmo quando o concreto muda de comportamento. Sem (iii) ninguém nunca exercitou o SQL, e o fake vira a única descrição executável do repositório.

**GARANTIA.** Compra uma suíte de use-case que roda **offline, em segundos, sem serviço de pé** — verificável por máquina de forma trivial: o comando de teste sem `DATABASE_URL` no ambiente passa, e passa no laptop, no container de build e no avião.

E não perde cobertura do caminho real, porque essa garantia foi colhida em outro lugar: o adapter é exercitado contra a infra de verdade (§2) e o fake é impedido de divergir pelo contract test (§3/§4). É a divisão de trabalho que faz o fake ser barato **sem** ser mentira — e é por isso que as três condições não são decoração: elas são literalmente os mecanismos que recolhem o que o fake não prova.

**CENÁRIO (incluindo).** Aplicar a regra sem (iii) presente: o fake diverge do SQL — devolve `None` onde o real levanta `IntegrityError`, mapeia coluna que não existe, ordena por inserção onde o banco não ordena — e a suíte fica verde enquanto produção quebra. É o modo de falha que o radar de produção implicitamente combate ao testar tudo contra banco real.

**CENÁRIO (excluindo).** Abandonar a regra e testar use-case contra banco real onde os três existem: no espécime gateado, **535 casos que hoje rodam offline em segundos passariam a exigir Postgres de pé** para qualquer execução local. O custo não é teórico nem futuro — é o tempo de ciclo de toda a suíte, todo dia. Nos dois sentidos há falha nomeada; o que decide é qual delas já está fechada por outro mecanismo.

**DISSENSO.** Vice = **banco real no use-case**. *Steelman:* prova o caminho inteiro numa tacada, é imune por construção à mentira do fake, e é o que a produção estudada de fato faz — no radar de produção esse é o padrão dominante, não a exceção. *Perdeu porque:* troca uma garantia **já colhida** (adapter contra real + contract test) por um custo **certo** (a suíte offline morre), com base em evidência cujo cenário não se reproduz: aquelas bases não têm hexágono com port explícito nem gate estático universal, então lá o teste de integração é a única garantia disponível. Empírico só é dispositivo quando o cenário se transfere; aqui ele rebaixa a informativo.

**GATILHO DE REABERTURA.** Sumir qualquer uma das três condições. **Ou** aparecer necessidade de provar **corrida concorrente real entre processos** — dois processos disputando o mesmo compare-and-set, `RETURNING` vazio de verdade, índice único parcial disparando. Note o estreitamento: o fake modela barato e fielmente o *resultado* da corrida (devolver `None` quando o estado não bate), e a compensação é caminho de código de primeira classe, testável com fake; o que fake nenhum reproduz é a corrida em si. Por isso, mesmo quando esse gatilho dispara, o teste que ele pede é de **adapter** (dois repositórios reais contra o mesmo Postgres), não de use-case.

### 2. Gate de infra — quando o skip é honesto e quando engana

**REGRA.** Serviço real subido **fora** do processo de teste (compose no dev, service container no CI), com **gate por variável de ambiente declarado em todo teste de infra** — nenhum estoura por ausência de serviço, todos skipam do mesmo jeito. E a trava que fecha o buraco: **no ambiente que promete a infra, skip é falha de build**, chaveada por **env própria do projeto** (`REQUIRE_INFRA=1` ou equivalente nomeado), nunca pela `CI` genérica.

As duas metades, na forma executável — o marcador que skipa e a trava que proíbe skipar:

```python
# tests/support/gates.py
_REQUIRE = os.getenv("REQUIRE_INFRA") == "1"

requires_postgres = pytest.mark.skipif(
    not _REQUIRE and not os.getenv("DATABASE_URL"),
    reason="sem Postgres: exporte DATABASE_URL ou rode o compose",
)
```

Com `REQUIRE_INFRA=1`, a condição de skip não pode mais ser satisfeita: a ausência do serviço vira erro de conexão vermelho, não skip verde. Um marcador irmão nasce para **cada** serviço — object storage, cache, fila —, sem exceção, porque a exceção é o buraco.

**CONDIÇÃO.** Vale com número pequeno e estável de serviços, que o desenvolvedor sobe à mão, sem matriz de versões e sem necessidade de ciclo de vida por teste. Fora disso — matriz de versões, infra que o dev não consegue subir localmente, provisionamento por caso — a resposta certa é testcontainers.

**GARANTIA.** A primeira metade da regra (gate declarado em todo teste de infra) é **verificável e insuficiente** — e essa distinção é o coração da posição. É exatamente o teste que o espécime sem trava impõe a qualquer regra: dá para cumprir "todo teste de infra tem gate declarado" em **100%** dos arquivos e a garantia prometida ainda falhar. Basta a variável sumir do workflow, ou um arquivo novo nascer gateado sem ninguém notar, e o CI fica **verde skipando tudo** — cumprimento perfeito, garantia zero.

A trava anti-skip é a única peça que amarra cumprimento a garantia: com ela ligada no ambiente que promete a infra, "a suíte de infra não rodou" vira vermelho, verificável por máquina, sem depender de alguém ler o resumo de skips. Sem ela, o gate é ritual bem-intencionado.

**CENÁRIO (incluindo).** Adotar o gate sem a trava: o espécime gateado, sem infra local, dá **535 passed / 60 skipped / 3 errors** — o Postgres skipa limpo, mas o round-trip contra o object storage **estoura** em vez de skipar, porque ninguém escreveu o marcador equivalente. É a mesma regra cumprida pela metade, e a metade que falta é justamente a que o CI silenciaria se a infra sumisse do workflow.

**CENÁRIO (excluindo).** Largar o gate e deixar o teste estourar sempre que a infra falta: a suíte local deixa de ser rodável e o desenvolvedor aprende a ignorar vermelho — o pior modo de falha que existe, porque destrói o sinal de todos os outros testes junto.

**CENÁRIO (chave errada).** Chavear a trava pela variável `CI` genérica: `CI=true` é setado por **todo** runner, inclusive por jobs que legitimamente não provisionam infra — lint-only, PR de fork sem services, execução local do runner. O resultado é falso-positivo, e falso-positivo é ruído que alguém desliga em duas semanas. **Quem promete a infra é quem liga a exigência**, e por isso a chave é uma env própria e nomeada por cenário.

**DISSENSO.** Vice = **testcontainers**. *Steelman:* a documentação oficial ataca exatamente a divergência que o dublê in-memory produz ("may lack features of production systems and behave differently"), e o ciclo de vida gerenciado elimina o gate-por-teste e o buraco do serviço que estoura **por construção**, não por disciplina — nenhuma trava anti-skip seria necessária. *Perdeu porque:* o cenário que o justificaria (matriz de versões, infra que o dev não sobe, ciclo por teste) não existe sob a condição acima, e o que ele vende — serviço **real**, não in-memory — já se tem com compose. Adotar sem cenário é cerimônia.

**GATILHO DE REABERTURA.** Entrar matriz de versões do serviço; nascer infra que o desenvolvedor não sobe à mão; o replay manual do schema no ambiente de teste virar dor de manutenção recorrente.

### 3. Contract test — a forma executiva

Este eixo é dono da **forma** e da **casa** do contract test. O *porquê ele é obrigatório* pertence a [`01-contratos-e-conformidade.md`](01-contratos-e-conformidade.md) — não duplicado aqui.

**REGRA.** **Uma** suíte de asserções, rodada contra os **dois** sujeitos por **fixture parametrizada por implementação**, com o sujeito real gateado no próprio parâmetro. Casa: **`tests/<contexto>/contracts/test_<port>_contract.py`**.

```python
@pytest.fixture(
    params=[
        pytest.param("fake", id="fake"),
        pytest.param("real", id="real", marks=requires_postgres),
    ]
)
def subject(request: pytest.FixtureRequest) -> BillRepo:
    if request.param == "fake":
        return FakeBillRepo()
    return SqlBillRepo(engine_from_env())
```

Regra de absorção: o contrato fica com as asserções **semânticas do port** (nasce no estado inicial certo; o segundo compare-and-set perde a corrida e devolve `None`; a listagem escopa pelo tenant); a suíte do adapter guarda **só o que é específico da implementação** (nome de coluna, índice parcial, migration) — e as asserções hoje duplicadas nas duas somem da suíte do adapter.

**CONDIÇÃO.** Suíte de estilo funcional (sem classes de teste) e runner que suporte marca por parâmetro. Em suíte orientada a classes, a forma canônica do xUnit — classe-base de asserções herdada por sujeito — é a equivalente legítima e deve ser preferida por consistência com o resto da suíte.

**GARANTIA.** Verificada pelo experimento 1: uma única suíte, dois sujeitos, e o sujeito real gateado sem que o fake deixe de rodar — `1 passed [fake], 1 skipped [real]` sem infra, `2 passed` com ela. Nenhuma suíte a mais para manter, nenhuma chamada que alguém pode esquecer.

O `ids` nomeado é o que torna a falha **acionável**: o relatório diz contra qual sujeito o contrato quebrou, que é a diferença entre "o contrato falhou" e "o adapter real falhou" — diagnósticos completamente diferentes, um aponta para a especificação, o outro para o SQL.

A casa fora do espelho de `src/` é deliberada: o subject **não é um módulo**, é um contrato que atravessa `tests/` (onde vive o fake) e `src/adapters/` (onde vive o real). Casa própria dá descoberta em dez segundos e, de quebra, mantém legível a divisa offline/online, já que `tests/<contexto>/application/` continua 100% livre de infra.

**CENÁRIO (incluindo na forma errada).** Uma **função de asserções compartilhada**, chamada pelas duas suítes, parece dedupe e não é: continuam existindo duas suítes, e **esquecer de chamá-la numa delas não falha nada**. É duplicação disciplinada com verniz de dedupe — cumprimento aparente, garantia nenhuma.

**CENÁRIO (excluindo).** Duas suítes espelhadas escritas à mão, uma para o fake e uma para o real: elas divergem em silêncio à primeira asserção que alguém acrescenta só de um lado — que é exatamente o modo de falha que o contract test existe para fechar.

**DISSENSO.** Vice = **classe-base abstrata de teste** (o *Abstract Test Case* de Meszaros). *Steelman:* é o padrão do livro, e a herança expressa "todo implementador deste port passa nestes testes" de forma mais explícita que uma lista de parâmetros — a relação fica no tipo, não numa string. *Perdeu porque:* gateia pior (pular só o sujeito real vira `pytestmark` na subclasse, uma indireção a mais que o `marks` no parâmetro resolve em linha) e quebra a consistência de forma de uma suíte com centenas de casos e **zero** classes — consistência de forma é garantia de legibilidade em escala, não gosto.

**GATILHO DE REABERTURA.** A suíte migrar para estilo orientado a classes; ou o runner deixar de suportar marca por parâmetro.

### 4. Contract test — o escopo da obrigação

**REGRA (profundidade).** O contrato cobre **todo método vivo do port**, e o fake é portanto **comportamento-completo**. Corolário operativo: **pedir isenção do contrato é sinal de método morto, não de dispensa** — a pergunta certa deixa de ser "preciso mesmo testar isto?" e vira "por que este método existe?".

**REGRA (alcance).** A obrigação atrela-se ao **papel do dublê** (na taxonomia de Meszaros), nunca à contagem de ports:

- **Fake de port com adapter real executável sob o gate** → contract test **obrigatório**. É o único caso em que o dublê afirma emular o real e pode mentir sobre isso.
- **Stub** (control point de entrada indireta — o relógio fixo, por exemplo) → **fora**. Não pretende emular comportamento; um "contrato do relógio" seria asserção vazia. Cerimônia, cortada pelo portão.
- **Port de terceiro não executável no gate** (mensageria de plataforma externa, matcher via LLM) → **sem contract test no CI**, e o fake fica **registrado como assumidamente não-verificado** — dívida nomeada, não dívida escondida. É a doutrina literal de Fowler: contract test contra serviço externo roda no ritmo de mudança do serviço, às vezes diário, nunca a cada commit.
- **Null-object promovido a adapter** → entra na primeira regra assim que ganhar comportamento; enquanto for no-op, fica fora pelo mesmo corte do Stub.

**CONDIÇÃO.** Vale onde os papéis são distinguíveis, isto é, onde existe port explícito e o dublê é escrito à mão. Onde o dublê é `Mock` da biblioteca sobre a classe concreta — o caso do espécime sem trava — não há papel nem contrato possível: o dublê não afirma nada sobre um port, porque não há port.

**GARANTIA.** A obrigação **para de escalar com o número de `Protocol`s e passa a escalar com o número de fakes que podem mentir** — que é a garantia real, e a única que interessa. Medido no espécime gateado: **16 `Protocol`s** contra **8 fakes com adapter real executável**. A conta cai pela metade sem perder nada, porque os outros oito ou não emulam comportamento (são stubs) ou não têm real executável no gate (são terceiros).

Efeito colateral verificado no mesmo espécime, e ele é o argumento mais forte a favor da regra de profundidade: os **15 `NotImplementedError("not used")`** espalhados por fakes parciais **morrem sozinhos** quando o fake vira compartilhado e comportamento-completo. Cada um desses era um método do port que algum teste declarou não precisar — e com eles morre o risco de um fake parcial divergir do real sem ninguém ver, porque não sobra método sem asserção.

**CENÁRIO (incluindo demais).** Exigir contrato para tudo que é `Protocol`: nascem suítes de asserção vazia sobre stubs — um "contrato do relógio" que afirma que o relógio devolve o que foi injetado nele. O custo sobe, a garantia não, e a regra perde credibilidade justamente onde ela importa.

**CENÁRIO (excluindo demais).** Dispensar contrato dos métodos "óbvios": é exatamente onde fake e real divergem sem alarde — forma do retorno, `None` versus chave ausente, mapeamento de coluna, ordenação implícita que o dicionário do fake tem e o `SELECT` sem `ORDER BY` não tem.

**DISSENSO.** Vice = **contrato apenas sobre métodos com semântica não-trivial**, poupando getters. *Steelman:* asserção sobre getter trivial é ruído, e o custo do contrato cresce com métodos que "não podem dar errado" — o esforço vai para onde o risco não está. *Perdeu porque:* é justamente nos triviais que a divergência passa despercebida, e **"trivial" não tem definição verificável** — o critério viraria julgamento caso a caso, que é o oposto de uma regra.

**GATILHO DE REABERTURA.** Aparecer port cujo contrato seja **puramente de forma** e já integralmente provado pelo type-checker strict — aí o contract test é redundante com o checker e sai. Ou: primeira quebra em produção por deriva de um terceiro não executável, que faz nascer um canário agendado (fora do gate de PR) para os fakes hoje registrados como não-verificados.

### 5. Estrutura física da suíte — espelho e suas três exceções

**REGRA.** `tests/` **espelha** `src/`, com `__init__.py` por nível (o que torna o suporte importável), e com exatamente **três** casas por papel fora do espelho:

| Papel | Casa | Por que não espelha |
|---|---|---|
| Teste de um módulo | espelho de `src/` | o default; o subject **é** o módulo |
| Dublê de port | `tests/<contexto>/fakes.py` | o subject é o *port*, consumido por N testes |
| Oráculo fake↔real | `tests/<contexto>/contracts/` | o subject é o *contrato*, que atravessa `tests/` e `src/adapters/` |
| Scaffolding de infra real | `tests/support/` | **não tem subject**; é maquinário (engine, replay de schema, cunhagem de identidade) |

Em árvore, num contexto qualquer:

```
tests/
  <contexto>/
    domain/            # espelho de src/<contexto>/domain/
    application/       # espelho; 100% offline, sem infra
    adapters/          # espelho; gateado por marcador de serviço
    contracts/         # oráculo fake↔real, um arquivo por port
    fakes.py           # dublês do contexto, comportamento-completos
  support/             # engine, replay de schema, cunhagem de identidade
```

A divisa entre as duas últimas casas, que costuma ficar tácita e produzir arquivo no lugar errado: **`support/` fala com infra de verdade; `fakes.py` existe justamente para não falar.** Caso-limite instrutivo do espécime gateado: um módulo de suporte monta objetos que parecem fixture de domínio, mas grava via repositório SQL contra Postgres — é maquinário, fica em `support/`, não em `fakes.py`.

**CONDIÇÃO.** Vale sob fatia vertical por contexto (o pacote de domínio como unidade de topologia). Projeto organizado layer-first globalmente muda o eixo do espelho, e as três exceções mudam de endereço junto.

**GARANTIA.** O espelho dá **localização por dedução**: dado um módulo, o arquivo de teste é derivável sem busca, e vice-versa. É verificável por inspeção mecânica — todo arquivo de teste tem contraparte em `src/`, salvo as três casas nomeadas, e a lista de exceções é fechada.

As exceções não enfraquecem a regra porque são exatamente os artefatos **sem subject de módulo**. O princípio é único e vale para os três: quando o subject é um *papel* e não um módulo, ele ganha casa por papel. Fake é papel (o port, consumido por N testes); contrato é papel (o oráculo, que atravessa duas árvores); scaffolding não tem subject nenhum.

**CENÁRIO (incluindo exceções demais).** Cada arquivo que foge do espelho por conveniência corrói a dedutibilidade: o espelho deixa de ser regra e vira convenção folclórica, e aí a pergunta "onde está o teste disto?" volta a exigir busca.

**CENÁRIO (excluindo as exceções).** Co-locar tudo, com o fake ao lado do teste que o usa, é literalmente o que produziu no espécime gateado os **15 `NotImplementedError("not used")`** e o mesmo fake de repositório **duplicado duas vezes** em arquivos diferentes — dois fakes do mesmo port divergindo em silêncio, sem nenhum mecanismo capaz de acusar a divergência.

**DISSENSO.** Vice = **tudo espelhado, sem exceção**, com fake e contrato ao lado do teste que os usa. *Steelman:* uma regra só, zero decisão na hora de criar arquivo, e o fake fica visível de onde é consumido. *Perdeu porque:* co-locar o dublê é a causa mecânica da duplicação e do fake parcial — o custo aparece medido acima, e nenhuma disciplina o evita em escala.

**GATILHO DE REABERTURA.** Topologia migrar para layer-first global.

### 6. A forma do caso de teste

**REGRA.** Três partes:

- **(a) Nome `test_<scenario>_<expected>`** — o caso vermelho conta o cenário sem que ninguém abra o arquivo.
- **(b) Corpo AAA separado por linha em branco**, com comentários `# given` / `# when` / `# then` **só onde há montagem real** (teste de use-case, teste de adapter) — nunca num teste de domínio de três linhas, onde o comentário é mais longo que o código.
- **(c) `parametrize` liberado** para variação de dado sobre a **mesma** asserção, **sob a condição de `ids` nomeados**. Função separada quando a asserção difere, ou quando o cenário tem nome próprio.

**CONDIÇÃO.** A parte (c) reverte uma regra anterior — "um teste por caso, `parametrize` só em teste novo" — que era **condicional** e cuja condição expirou: ela existia para o porte 1:1 de um oráculo externo com ordem de casos preservada. Terminado o porte, a condição sumiu, e **regra não sobrevive à condição dela**. Re-arma automaticamente no próximo porte 1:1 de oráculo externo. As partes (a) e (b) são incondicionais.

A forma que as três partes produzem, num teste de use-case (onde há montagem real, logo comentários):

```python
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        pytest.param("R$ 1.234,56", 123456, id="milhar-com-ponto"),
        pytest.param("1,00", 100, id="sem-simbolo"),
    ],
)
def test_parse_brl_with_valid_input_returns_cents(raw: str, expected: int) -> None:
    assert parse_brl(raw) == expected
```

**GARANTIA.** (a) é verificável por convenção de nome e fica visível em `pytest -v` — o relatório do caso vermelho é uma frase em inglês que descreve cenário e expectativa.

(c) só preserva a garantia de (a) por causa dos `ids`: sem eles o relatório vira `test_parse_brl_with_valid_input_returns_cents[0]` e o cenário se perde. A condição é verificável olhando a saída do runner, o que a torna checável em revisão sem abrir o arquivo.

**Rótulo honesto sobre (b): nada enforça AAA nem os comentários `# given` / `# when` / `# then` — nem lint, nem type-checker, nem gate nenhum.** Pelo portão anti-cerimônia isso **não** é ritual, porque cumprir a regra entrega de fato a legibilidade prometida — diferente da regra que se cumpre 100% e cuja garantia ainda falha. Mas é **convenção não-enforçável**, e como tal entra no **orçamento de cerimônia**: poucas, condicionadas (o "só onde há montagem real" é precisamente o que a impede de virar ruído) e **rotuladas como não-enforçáveis**, que é o que esta linha faz. Convenção não-enforçável que não se declara como tal é como o autor engana a si mesmo sobre quanta garantia ele tem.

**CENÁRIO (incluindo sem a condição).** `parametrize` sem `ids` nomeados: uma falha chega como `test_parses[7]`, alguém abre o arquivo e conta posições na lista para descobrir qual caso quebrou — a garantia de (a) morre inteira, e com ela a razão de existir da convenção de nome.

**CENÁRIO (excluindo).** Proibir `parametrize` sempre: cobram-se N funções para expressar a mesma asserção sobre dados diferentes. No espécime gateado isso significaria manter — e, sob retrofit, reescrever — **19 funções de um único módulo de testes de dinheiro** que hoje estão verdes e legíveis. Elas **não** serão reescritas: retrofit aqui custa e não colhe garantia nenhuma. Regra nova vale para teste novo.

**DISSENSO.** Vice de (c) = **manter "um teste por caso" sempre**. *Steelman:* nome único por caso é a garantia de (a) na forma mais forte possível, e `parametrize` sem disciplina de `ids` a destrói — a disciplina depende de quem escreve. *Perdeu porque:* a condição de `ids` recupera a garantia inteira e é observável no relatório, enquanto a alternativa cobra dezenas de funções para expressar a mesma asserção.

**GATILHO DE REABERTURA.** Novo porte 1:1 de oráculo externo com ordem de casos preservada — aí (c) sai temporariamente e "um teste por caso" volta enquanto o porte durar.

### 7. Cobertura e força da suíte

**REGRA.** Três partes:

- **(a) Threshold de cobertura no gate: proibido.**
- **(b) Cobertura existe como diagnóstico efêmero**, jamais como artefato do projeto: nada nas dev deps, nada na config, apenas um comando documentado (`uv run --with pytest-cov pytest --cov=…`).
- **(c) Mutation testing é gatilho, não adoção** — fica fora até que **um bug escape para produção com a suíte verde**; aí a ferramenta é apontada ao **domínio puro** (funções determinísticas sobre tipos nativos, baratas de mutar), nunca ao repositório inteiro, nunca no gate.

A forma efêmera, inteira:

```bash
uv run --with pytest-cov pytest --cov=src/<pacote> --cov-report=term-missing
```

Nada disso entra em `pyproject.toml`, em dev deps, em workflow ou em badge. É comando de diagnóstico, documentado onde o resto dos comandos mora.

**CONDIÇÃO.** O diagnóstico de cobertura só ganha valor quando o repositório passa do tamanho em que "o que não tem teste nenhum" é visível a olho nu. Antes disso é comando disponível, não prática. A restrição de (c) ao domínio puro pressupõe domínio efetivamente puro; onde o domínio é I/O-bound, mutation testing não é a ferramenta.

**GARANTIA.** (b) é verificável pelo experimento 2: o comando produz relatório completo e **não toca `pyproject.toml` nem o lockfile** — `git status` limpo depois de rodar. Ou seja, dá para responder "o que não tem teste nenhum" sem que a cobertura vire dependência, config, badge ou pressão. O que **não** se garante, e é o ponto: **cobertura mede execução, não verificação** — um teste sem `assert` que executa a linha sobe o número e não prova nada. A fonte-dona do argumento diz as duas coisas, e as duas valem: *"If you make a certain level of coverage a target, people will try to attain it… high coverage numbers are too easy to reach with low quality testing"*, e também *"it helps you find which bits of your code aren't being tested."*

**CENÁRIO (incluindo o threshold).** O modo de falha é nomeado e clássico: escreve-se teste para o número, não para a garantia. A suíte engorda com casos que executam sem verificar, e o número sobe exatamente enquanto a força da suíte não muda — o pior tipo de métrica, a que se move na direção certa por motivo errado.

**CENÁRIO (excluindo a ferramenta inteira).** Também tem modo de falha nomeado: a varredura de retrofit e o crescimento por novas áreas do produto precisam responder "o que não tem teste **nenhum**", e sem a ferramenta a resposta vira palpite de quem leu a árvore. Por isso a posição não é "nada", é **"diagnóstico sem número"** — o uso legítimo preservado, o modo de falha cortado.

**CENÁRIO (mutation).** Mutation testing é a única coisa que responde a pergunta que a cobertura não responde: *algum `assert` falharia se esta linha estivesse errada?* Isso justifica o gatilho. O custo de runtime, e o fato de que ele só é barato sobre código determinístico, justificam não ser adoção antecipada nem varredura de repositório inteiro.

**DISSENSO.** Vice = **cobertura como artefato permanente, com relatório publicado no PR, sem threshold**. *Steelman:* torna a tendência visível ao longo do tempo e pega o adapter novo que nasceu sem teste, tudo isso sem impor número nenhum — colhe o uso legítimo da ferramenta sem o modo de falha do alvo. *Perdeu porque:* relatório-sem-número vira ruído que ninguém lê e, quando alguém lê, a pressão social recria o threshold pela porta dos fundos; o modo efêmero entrega exatamente o mesmo diagnóstico no momento em que ele é pedido, a custo zero de manutenção.

**GATILHO DE REABERTURA.** A suíte passar a ser mantida regularmente por mais de um autor humano — aí a tendência visível compra coordenação que hoje não tem consumidor. E, para (c), o primeiro bug que escapar para produção com a suíte verde.

### 8. Async e relógio

**REGRA.** Duas partes:

- **(a) `asyncio_mode = "auto"`**, e **`async def` no teste só quando o SUT é awaitable** — que é a face-de-teste da doutrina de composição: domínio sempre síncrono, port `async` se e somente se o adapter real faz I/O.
- **(b) Tempo entra por port** (`Clock`), com **Stub** injetado (`FixedClock`), **nunca** com biblioteca de congelamento global do tipo `freezegun`. E a regra sobe de convenção para **trava de máquina**: `ruff` TID251 banindo `datetime.datetime.now` e `datetime.date.today` no código de produção, com exceção por arquivo para o único adapter que lê o relógio real. Os testes ficam fora da trava — cunhar um token com `now` real num teste de borda é legítimo.

**CONDIÇÃO.** (a) vale em projeto single-framework asyncio; entrando um segundo framework async no processo, `strict` volta a ser o correto. (b) é incondicional onde o tempo influencia decisão de domínio; onde o tempo é só carimbo de log, o port é cerimônia.

**GARANTIA.** (a) compra **ergonomia, e nada além disso** — no espécime gateado são **206 testes async sem decorator algum**, que é a economia inteira da posição. Ela **não** compra proteção contra verde vazio: o experimento 4 desmentiu essa alegação, porque `strict` **falha alto** (`async def functions are not natively supported`), não silencioso.

Registrar isso importa mais do que a posição em si. A régua manda **realidade medida acima de promessa documentada**, e essa medição matou uma alegação inteira de um research — um research que, note, defendia a mesma conclusão, pelo motivo errado. Conclusão certa com justificativa falsa é dívida: ela sobrevive à mudança de versão que deveria tê-la derrubado.

(b) tem garantia em dois níveis. A convenção sozinha é ritual pelo teste do espécime sem trava: dá para cumpri-la em 100% do código existente e alguém escrever `date.today()` num use-case novo sem que nada pie. A trava TID251 é o que amarra convenção a garantia — custa poucas linhas de config e transforma a violação em erro de gate, não em achado de revisão que depende de alguém estar atento.

Estado medido no espécime gateado: **uma única leitura de relógio real em todo o `src`**, dentro do `SystemClock` — **a trava nasce verde**, o que remove o único argumento de custo contra ligá-la. A materialização da config pertence a [`06-regua-de-maquina.md`](06-regua-de-maquina.md); a decisão de que ela existe, e por quê, é desta posição.

**CENÁRIO (incluindo sem a trava).** O próximo use-case lê o relógio direto porque era mais rápido, o teste correspondente fica não-determinístico perto da virada do dia ou do mês, e ninguém descobre até o flake — que chega dias depois, num PR que não tem nada a ver.

**CENÁRIO (excluindo o port).** Usar congelamento global de tempo: o teste passa, mas a dependência de tempo fica **invisível ao type-checker e ao composition root**. Nada no construtor diz que aquele use-case depende do tempo, e no dia em que o congelamento não cobrir um caminho — código executado fora do escopo do decorator, thread, task — a falha é remota e difícil de atribuir.

**CENÁRIO (para (a)).** O cenário do rival é concreto e estreito: dois frameworks async no mesmo processo, onde `auto` reivindica testes que não são dele. Fora dele, `strict` cobra um decorator por teste e devolve nada.

**DISSENSO.** Para **(a), sem rival vivo** — `strict` serve a quem mistura frameworks async, e fora desse cenário não há argumento em pé, já que o argumento antigo (evitar verde vazio) foi medido e é falso. Para **(b)**, vice = **`freezegun`**. *Steelman:* zero cerimônia no código de produção — não exige port, não exige injeção, não muda assinatura nenhuma — e congela também o tempo lido por **bibliotecas de terceiros**, que o port jamais alcança. *Perdeu porque:* torna a dependência de tempo invisível ao tipo e ao composition root, e o cenário que ele resolve melhor ("um terceiro lê o relógio e isso decide") não existe no núcleo, que é onde o tempo decide.

**GATILHO DE REABERTURA.** Para (a): entrar um segundo framework async. Para (b): precisar congelar o tempo **dentro** de uma biblioteca de terceiro num teste de adapter — aí `freezegun` local àquele teste, com o custo declarado no lugar, e não como política.

---

## O que esta doutrina encomenda num repositório que já existe

Adotar as oito posições sobre uma base já escrita produz uma lista curta e fechada de trabalho. No espécime gateado ela ficou assim, e a forma dela é portável:

- Nasce o marcador de gate do serviço que hoje **estoura** em vez de skipar (§2) — a regra cumprida pela metade é o achado mais comum.
- Nasce a **trava anti-skip** chaveada por env própria do projeto, ligada no job de CI que promete a infra (§2).
- Nascem os **contract tests dos fakes com adapter real executável** (§3/§4), absorvendo as asserções semânticas hoje duplicadas entre suíte de fake e suíte de adapter — e a suíte de adapter emagrece na mesma medida.
- Os `NotImplementedError("not used")` **morrem**, porque o fake vira compartilhado e comportamento-completo na casa por papel (§4/§5).
- Entra a **trava TID251 do relógio**, com exceção por arquivo no adapter que lê o relógio real (§8) — e nasce verde.
- Ficam **registrados como fake não-verificado** os ports de terceiro não executáveis no gate (§4): dívida nomeada, com gatilho de canário, não dívida escondida.
- `parametrize`: regra nova vale para teste novo, **sem retrofit** dos casos já verdes (§6).
