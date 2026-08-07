---
name: panlabs-python-standards
description: Padrão de referência para backend Python — contratos e ports, composição e forma do código, topologia e kernel, modelo de erro, doutrina de testes e a régua de máquina. Use ao criar um serviço Python do zero, ao revisar um existente, ou ao decidir qualquer uma destas perguntas — que forma tem um use-case, onde o arquivo mora, o que o erro devolve, o que é fake e o que é real, que config trava a regra. Cada posição carrega a condição em que vale, a garantia que compra, o dissenso vencido e o gatilho que a reabre.
---

# panlabs-python-standards

O padrão de backend Python desta casa. **Não é um catálogo de boas práticas** — é o conjunto das posições que sobreviveram a uma adjudicação com régua explícita, cada uma com o cenário concreto que a justifica e a alternativa que perdeu.

A diferença importa na prática: um catálogo responde "o que é certo fazer"; esta referência responde "**sob que condição** isto é certo, e o que acontece quando a condição não vale". Metade das posições aqui **invertem** num projeto sem gate estático — e elas dizem isso, na própria posição.

## Como usar

**Escrevendo código novo.** Leia a lista de posições abaixo; ela é o normativo. Abra a referência do eixo só quando precisar do *porquê* — ao decidir um caso de fronteira, ou ao justificar a escolha pra alguém.

**Revisando código.** As posições com **garantia de máquina** são as que valem apontar em review: se ela não está travada na config, apontar em review é o modo de falha que este padrão inteiro existe pra evitar. Comece por [`references/06-regua-de-maquina.md`](references/06-regua-de-maquina.md) — ele traz um baseline literal copiável, e o que não está lá não é norma, é conversa.

**Discordando.** Toda posição tem um **gatilho de reabertura** — a mudança concreta de versão, contexto ou evidência que ressuscita a alternativa vencida. Se o teu caso bate no gatilho, a posição não se aplica e não há nada a defender. Se não bate, o ônus é apresentar cenário e medição, não autoridade.

## O contrato desta referência

Seis regras governaram toda adjudicação. Elas são o que separa esta referência de um blog post, e valem também pra qualquer posição que se acrescente depois. Detalhe em [`references/00-regua-de-adjudicacao.md`](references/00-regua-de-adjudicacao.md).

1. **Excluir por default.** Todo padrão está fora até que um **cenário concreto** o justifique. "Best practice reconhecida" não é razão — o cenário é. Daí as regras saírem **condicionais** (regra + quando-se-aplica), que é a forma que porta entre projetos heterogêneos.
2. **Evidência por tipo de alegação.** Comportamento de ferramenta se decide por **experimento** contra as versões pinadas, nunca por leitura de doc. Definição de um pattern vem da fonte-dona. Norma ("devemos usar aqui") exige cenário + empírico. Opinião de terceiro **nunca decide**.
3. **Realidade medida acima de promessa documentada**, e empírico só é dispositivo em **consenso**; fora do consenso, mapeia o espaço de opções e não decide.
4. **Sem "conforto".** Preferência **nomeável** é garantia e decide no mérito. Empate verdadeiro vira escolha **explicitamente arbitrária**, rotulada como tal. Sobrepor a evidência é permitido com rótulo brutal e sob orçamento — autor que sobrepõe eixo após eixo reabre a régua inteira.
5. **Dissenso registrado inline**: vice, steelman honesto dela, por que perdeu, gatilho de reabertura. Onde não houve rival, está escrito "sem rival — evidência unânime".
6. **Portão anti-cerimônia**, três checagens em toda posição: cenário nomeado **nos dois sentidos** (incluir *e* excluir precisam nomear a falha); **garantia verificável** — se dá pra cumprir a regra 100% e a garantia ainda falhar, é ritual e corta-se; e **autoridade não preenche** — "a spec manda" é insumo definitional, nunca justificativa.

> A régua se aplica a si mesma. Se qualquer parte dela for ritual que não amarra garantia, corta também.

## Os espécimes de evidência

Duas codebases reais foram auditadas linha a linha, e um radar de seis backends Python de produção foi levantado. Elas aparecem citadas nas referências como **evidência-caso**, nunca como justificativa.

- **O espécime gateado** — o backend `apps/api` do projeto LUC: Python 3.14 / FastAPI / uv, ~102 arquivos, 4 contextos delimitados, com pyright strict + ruff + import-linter gateando o merge e ~600 testes que rodam sem banco.
- **O espécime sem trava** — `b3stocks`: backend Python de Lambdas com vertical slices, ports em `abc.ABC` e Clean/Hexagonal nominal, **sem** type-checker (mypy foi removido) e sem import-linter. É a prova por ausência que atravessa a referência inteira: forma 10/10, garantia ~0.
- **O radar de produção** — Netflix Dispatch, Polar, Prefect, Warehouse/PyPI, Sentry e o template oficial de FastAPI. Serve pra descontar doutrina que ninguém pratica **e** pra encarar consenso que contraria o padrão daqui.

A frase que resume o que os dois primeiros ensinaram juntos: **o valor de um padrão não está no nome da arquitetura, está nas travas que o outro projeto optou por não ter.**

## As posições

Normativo condensado. O argumento, a medição e o dissenso de cada uma estão na referência do eixo.

### Contratos e conformidade → [`references/01-contratos-e-conformidade.md`](references/01-contratos-e-conformidade.md)

1. **O port é `Protocol`, e o adapter — junto com o seu dublê — herda o port.** *Condição:* type-checker strict gateia o merge **e** o conjunto de implementadores é fechado e in-repo. O híbrido colhe a conformidade na **definição**, o ponto que ninguém pula.
2. **A trava de runtime só entra quando o implementador é aberto** (plugin, entry-point, adapter escolhido por config, tipo de terceiro): aí `@abstractmethod` dentro do próprio `Protocol`; `abc.ABC` só quando precisa de `register()`. No conjunto fechado e gateado, a trava nunca dispara — é cerimônia.
3. **Se você usa fake em teste de use-case, o contract test é obrigatório.** Uma suíte de asserções rodada contra os **dois** sujeitos — fake e adapter real. Sem ele, o fake é um dublê não-verificado.
4. **Fake de port mora em `tests/`, chama-se `Fake<Port>` e herda o port.** Mock do que você mesmo possui é proibido. Null-object que embarca em produção **não é fake**: vira adapter `Null<Port>`.
5. **Port coeso por agregado é o default** — gordo tudo bem se coeso —, com **liveness** obrigatória: todo método tem consumidor vivo. Port gordo falha por método **morto**, e a cura é deletar, não segregar.
6. **Ports segregados em `application/ports/`**, nunca em `domain/`. A fronteira é a máquina (import-linter + type-checker); a pasta é descoberta. Nome por papel, sem prefixo `I`.

### Composição e forma do código → [`references/02-composicao-e-forma.md`](references/02-composicao-e-forma.md)

7. **Pure DI manual, um composition root por entry-point deployável**, com uma factory `provide_*` **tipada** por port — o tipo de retorno anotado *é* o seam onde o checker confere o adapter. Sem container. O `Depends` do framework não serve como seam: ele é `Any`, e cabeia "certo" com a garantia ausente.
8. **Use-case é função module-level**, ports primeiro, inputs depois; bundle `<UseCase>Deps` quando a aridade cresce. Classe só quando emergir um Assunto coeso multi-operação — aí já não é use-case-comando. *Rotulado honestamente como preferência nomeável, não garantia dura.*
9. **A transação nunca cruza a fronteira do port.** O adapter é dono, uma transação por método; tudo-ou-nada mora dentro de um método do repo; concorrência decide-se no banco (CAS + constraint); o que cruza store paga **compensação explícita** — efeito caro primeiro, commit por último, `claim → send → release`. **Sem Unit of Work**: ele entrega ilusão de atomicidade no fluxo multi-store.
10. **`async` é propriedade do I/O e do runtime, nunca estilo.** Domínio sempre síncrono. Port é `async` *sse* o adapter real faz I/O — manter `Clock` e `Calendar` síncronos é o que **protege** o domínio puro da coloração. Nunca `async` de mentira em volta de chamada bloqueante.
11. **Núcleo é `@dataclass(frozen=True)` sem lib de validação**; a validação é função explícita com **fronteira de tipo** entre cru e validado. Pydantic é legítimo **e só na borda** — barrá-lo do núcleo é regra, barrá-lo da borda seria minimalismo por esporte.
12. **Config resolve num ponto único, no boot, fail-closed — e a trava é parte da regra.** `os.environ` proibido fora do módulo de settings, por lint. Sem a trava, "config num lugar só" decai — e decaiu, medido, pra 1 de ~6 variáveis no próprio espécime gateado.

### Topologia e kernel → [`references/03-topologia-e-kernel.md`](references/03-topologia-e-kernel.md)

13. **O primeiro nível é o contexto delimitado**, não o conceito de domínio. O grão fino que domina o radar de produção existe pra que 80 pastas caibam na cabeça de times diferentes; ele não porta pra 4 contextos e 102 arquivos.
14. **Dentro do contexto, `application/` corta por papel: `ports/`, `use_cases/`, `projections/`.** É o único corte que espelha uma fronteira real — o que **muta estado** contra o que **deriva sobre fatos já persistidos** — e o único greppável pra pergunta "o que aqui pode escrever?".
15. **As três camadas (`domain`/`application`/`adapters`) valem sob condição**: existe lógica de derivação que vale testar sem infra **e** a fronteira é executada por import-linter. Faltando a execução, não adote. *Esta é a posição mais frágil do lote — o empírico é 6/6 contra, e ela sobrevive por um confundidor nomeável. O steelman está visível na referência.*
16. **O router mora dentro do contexto** (`<ctx>/adapters/http.py`). Assim ele herda o contrato de camadas de graça, e "a borda nunca fala com o store, fala com use-case" deixa de ser comentário e vira invariante executável.
17. **O kernel admite por natureza, não por contagem**: vocabulário ubíquo sem dono possível (dinheiro, data civil, taxonomia de erro) e port do ambiente (`Clock`, `Calendar`). Uso por 2+ contextos é filtro necessário, nunca autorização. Nada com dono identificável entra — **duplicar entre contextos é mais barato que um kernel que virou contexto**.
18. **Contextos formam um DAG declarado e executado** por contrato de camadas no container raiz. Escape hatch quando o DAG proíbe o que é preciso: **o port pertence a quem consome** — nunca inverta a aresta ad hoc, nunca promova ao kernel algo com dono.
19. **Tabela mora no contexto dono; o kernel guarda só o registro vazio.** Sem isso a fronteira de contexto fica executável na camada Python e **furada na camada SQL**. Registro central populado por import exige guarda de completude — sem a guarda, não faça o split.
20. **Dono do DDL é único e declarado**; quem não é dono adota por baseline no-op **mais teste de fidelidade**. Migrations moram na raiz do app (um banco, um head) — exceção explícita à fatia vertical, registrada pra ninguém "consertar". **Código de migração sem chamador é proibido**: ou liga no arranque, guardado por lock, ou apaga.
21. **A superfície pública do contexto é contrato executável entre contextos** — e a forma dela depende de um detalhe medido: sob a convenção "módulo com o nome do seu símbolo principal", a façade em `application/__init__.py` é **indistinguível de um import profundo** para o import-linter. Ver a colisão aberta abaixo.
22. **A raiz do pacote é o topo de composição e nada mais**: settings, `provide_*` e um módulo por entry-point. Nada de domínio, nada de rota.

### Modelo de erro → [`references/04-modelo-de-erro.md`](references/04-modelo-de-erro.md)

23. **A forma do erro segue a relação com o chamador imediato, não a camada.** A camada decide só *onde se traduz*: uma vez, na borda. Não existe seção "erro no domínio / no use-case / no adapter" — existe uma escada e um dispositivo.
24. **A escada, por quanta informação o insucesso carrega:** `X | None` (ou `bool`) quando é esperado e de modo único — e é a **única forma do modelo que o type-checker realmente força**; união discriminada consumida por `isinstance` **só** quando existe chamador que quer o veredito **sem** o efeito; exceção nomeada em todo o resto.
25. **O dispositivo de 4 peças**, em que cada uma tampa o furo da anterior: exceção semântica sob registro único → **catch-all na borda** (nenhuma resposta escapa do contrato) → **`Raises:` travado por máquina** → **`except Exception` com `# noqa` auditável e desfecho nomeado**. Removida qualquer uma, as outras três viram ritual.
26. **Traduza erro de infra em erro de domínio só onde existe chamador que se comporta diferente por causa dele.** Caso contrário, deixe chegar à rede de segurança.
27. **Acople o status HTTP ao erro *sse* a aplicação tem exatamente uma borda e ela é HTTP.** Com segunda borda heterogênea, separe categoria semântica de status. *Esta é a forma que porta: o consenso de produção é 6/6 a favor do acoplamento, e virou o antecedente da condicional em vez de ser descartado.*
28. **O erro mora com o contrato que o produz**, e o invariante é **registro** único, não **raiz** única — a borda distingue por tabela explícita, sem forçar herança falsa.

### Doutrina de testes → [`references/05-doutrina-de-testes.md`](references/05-doutrina-de-testes.md)

29. **Domínio sem dublê; use-case com fake de port, sempre; infra real confinada ao adapter.** *Condição:* existem port explícito, gate estático no merge e suíte de adapter contra o real. Faltando qualquer um dos três, o use-case contra banco real é o correto — ali ele é a única rede, e é por isso que a produção estudada faz assim.
30. **Serviço real sobe fora do processo de teste, com gate por env em todo teste de infra — e no ambiente que promete a infra, skip é falha de build.** A trava chaveia por env **própria do projeto**, nunca pela `CI` genérica, que todo runner seta. Sem ela o CI fica verde skipando tudo.
31. **O contract test é uma fixture parametrizada por sujeito**, com o real gateado no próprio parâmetro, morando em `tests/<contexto>/contracts/`. O contrato fica com as asserções **semânticas do port**; a suíte do adapter guarda só o específico da implementação.
32. **A obrigação do contract test atrela-se ao papel do dublê, não à contagem de ports.** Fake com real executável: obrigatório. Stub: fora. Port de terceiro não executável no gate: fake **registrado como assumidamente não-verificado**, com gatilho de canário. Pedir isenção é sinal de método morto.
33. **`tests/` espelha `src/`, com exatamente três casas por papel**: `fakes.py`, `contracts/` e `support/`. A divisa: **`support/` fala com infra de verdade; `fakes.py` existe justamente pra não falar.**
34. **Nome `test_<cenário>_<esperado>`; corpo AAA; `parametrize` liberado sob `ids` nomeados.** *Rotulado com todas as letras: AAA e os comentários de given/when/then não são enforçáveis por máquina alguma — são convenção, entram no orçamento de cerimônia, e só onde há montagem real.*
35. **Threshold de cobertura no gate é proibido.** Cobertura mede execução, não verificação, e existe como **diagnóstico efêmero** — comando documentado, zero dependência permanente. Mutation testing é **gatilho, não adoção**: entra quando um bug escapar com a suíte verde, apontado ao domínio puro.
36. **Tempo entra por port com stub injetado, nunca por congelamento global do processo** — e a regra sobe de convenção a **trava de lint**, banindo a leitura do relógio real fora do adapter que o lê.

### A régua de máquina → [`references/06-regua-de-maquina.md`](references/06-regua-de-maquina.md)

37. **A régua entrega baseline literal copiável.** É o único eixo onde a regra e o mecanismo que a força são o mesmo objeto — um config passa o portão anti-cerimônia por construção, porque cumprir *é* o CI verde. Prosa sem o bloco reproduz exatamente o modo de falha do espécime sem trava.
38. **Type-checker em `strict`, inegociável, cobrindo `src` e `tests`.** Relaxamento só como **escape local** com justificativa inline; desligar regra globalmente é proibido — o escape local é auditável e contável, o global é invisível e permanente.
39. **Lint em três camadas:** trava de classe-de-bug (inegociável), trava de consistência-em-escala, e heurística com escape — nesta última a garantia **não é a regra, é o `# noqa` com justificativa**, que força decisão nomeada. Zero adições fora das famílias medidas; exclusões justificadas por número, não por gosto.
40. **Fronteira de import é contrato executável, não prosa** — kernel não importa contexto, contexto não alcança o interior de outro contexto, borda alcança contexto só pela camada de aplicação. Exceção é sempre um `ignore_imports` nomeado, que **se auto-deleta** quando o código muda.
41. **Gate de CI que pode pular em silêncio não é gate**, e `continue-on-error` em passo de qualidade é proibido. Sem pre-commit: o CI é a única autoridade, e o comando local é idêntico ao dele — segundo caminho local já produziu falso-verde.
42. **Docstring obrigatório, com isenção cirúrgica onde o contrato é herdado.** Exigir docstring de método no adapter que herda o port fabrica um modo de falha novo — prosa duplicada que deriva em silêncio —, e a herança de docstring já entrega a informação sem cópia.
43. **Um idioma por codebase, escolhido uma vez, registrado.** Inglês é o default por empírico do próprio portfólio, não por dogma. Copy de produto vai na língua de quem lê — não é exceção à regra, é a regra.
44. **Porta-se o que a decisão consome; não se porta o que apenas a registra.** `Clock` é port porque o tempo é entrada da decisão; log é saída da qual nenhuma decisão depende, e a hierarquia de loggers da stdlib já é o seam. **Corte que evita o abuso:** se a linha de log é requisito — trilha que alguém precisa poder provar —, não é log, é **evento**, e vira port com teste.

## Colisões conhecidas e pendências

Honestidade de síntese: três pontos onde as posições, fechadas em sessões separadas, não encaixam sozinhas.

### 1. A superfície pública do contexto — **pendente de decisão**

Um eixo firmou a façade `application` como **contrato executável** entre contextos, via `forbidden_modules = ["myapp.<ctx>.application.*", …]`, apoiado num experimento com pacote de brinquedo. Outro eixo, medindo o código real, mostrou que `from myapp.finance.application import record_payment` é resolvido pelo grafo **como import do módulo `finance.application.record_payment`** — porque a convenção do padrão é nomear o módulo com o seu símbolo principal. As duas medições estão certas: no brinquedo o símbolo re-exportado não tinha nome de módulo; no código real tem.

Verificado por experimento próprio nesta síntese (import-linter 2.13), num pacote com os dois casos lado a lado:

| Como o consumidor importa | Contrato `forbidden ...application.*` |
|---|---|
| `from pkg.a.application import record_payment` (símbolo **com** nome de módulo) | **BROKEN** — a façade é indistinguível do import profundo |
| `from pkg.a.application import Thing` (símbolo **sem** nome de módulo) | KEPT |
| `from pkg.a.public import record_payment` (superfície num **módulo**, não no `__init__` do pacote) | **KEPT** |
| `from pkg.a.application.record_payment import record_payment` (controle, import profundo) | **BROKEN** |

Ou seja: **"só pela porta pública" é executável — mas só se a porta for um módulo cujo nome não possa colidir com um submódulo do pacote proibido.** Isso reconcilia os dois eixos em vez de escolher um: a façade de camada continua morta (92% do código já importa o módulo dono; o `__init__` vira docstring-mapa), a fronteira cross-contexto continua executável, e a porta pública sai de `application/__init__.py` pra um módulo (`<ctx>/public.py` ou nome equivalente).

**O que falta:** o dono decidir se adota essa terceira via — que muda a forma de todo contexto — ou se relaxa o contrato pra "contexto não alcança `domain`/`adapters` de outro contexto", que é o que a régua de máquina adotou e roda verde hoje, ao custo de o interior de `application/` ficar acessível de fora.

### 2. O formato do erro de campo — **já reconciliado**

Um eixo fechou `FieldError(field, message)` com copy na língua do usuário; o eixo de modelo de erro refinou depois pra `FieldError(field, code)`. Vale a versão refinada: `field` em camelCase sobrevive com lastro próprio (é contrato de ponta a ponta), `message` sai — a copy pertence a quem fala com a pessoa, e a segunda borda do espécime já ignorava a copy na prática. A tese normativa original sai intacta: **o formato do erro é nosso, não da lib**; muda só quem compõe a frase.

### 3. A fragilidade declarada das camadas

A posição 15 é a única do lote em que o empírico de produção é **unânime contra** (0 de 6 codebases tem camadas hexagonais dentro do pacote de feature) e que sobrevive por um confundidor nomeável. Está escrita com o steelman visível de propósito. Se o teu projeto tem domínio fino e ORM no centro — que é o perfil das seis —, **a posição não é pra ti**, e isso está na condição dela.

## Índice de referências

| Arquivo | Responde |
|---|---|
| [`00-regua-de-adjudicacao.md`](references/00-regua-de-adjudicacao.md) | Como uma posição entra, se defende e cai. Leia antes de propor mudança. |
| [`01-contratos-e-conformidade.md`](references/01-contratos-e-conformidade.md) | Ports, dublês e a prova de que o adapter cumpre o contrato. |
| [`02-composicao-e-forma.md`](references/02-composicao-e-forma.md) | Como as peças se ligam e que forma cada uma tem. |
| [`03-topologia-e-kernel.md`](references/03-topologia-e-kernel.md) | Onde cada arquivo mora e o que pode importar o quê. |
| [`04-modelo-de-erro.md`](references/04-modelo-de-erro.md) | Que forma o insucesso tem e onde ele se traduz. |
| [`05-doutrina-de-testes.md`](references/05-doutrina-de-testes.md) | Onde o dublê para, onde o real começa e o que prova o quê. |
| [`06-regua-de-maquina.md`](references/06-regua-de-maquina.md) | O baseline copiável — a config é a norma executando. |

## O que esta referência não é

Não é um framework, não é uma lib e não prescreve arquitetura por nome. Não diz "faça Clean Architecture" nem "faça Hexagonal" — diz que **pastas com nome de arquitetura sem trava de máquina entregam zero**, e isso foi medido num espécime que se descreve como seguindo Clean estritamente.

Também não cobre segurança de borda nem performance: nenhum dos dois tinha pergunta afiada quando esta referência foi fechada, e incluir posição sem cenário é exatamente o que a régua proíbe.
