# Composição e forma do código — como as peças se ligam e que forma cada uma tem

Este eixo responde a uma pergunta só: dado um domínio já modelado, **que forma cada peça tem e por onde elas se ligam** — quem cabeia dependência, que forma tem um use-case, quem abre transação, quando `async` entra, que tipo atravessa cada camada e por onde a configuração chega. Não é sobre onde os arquivos moram (topologia) nem sobre como se testa; é sobre a forma e o encaixe.

> Régua: toda posição abaixo passou pelo portão anti-cerimônia — cenário nomeado nos dois sentidos, garantia verificável, autoridade não preenche.

**Os dois espécimes citados como evidência.** *O espécime gateado* é um backend Python 3.14 / FastAPI / uv, ~102 arquivos, 4 contextos de domínio, com `pyright` strict + `ruff` + `import-linter` gateando o merge e ~600 testes. *O espécime sem trava* (`b3stocks`) é um backend Python de funções Lambda organizado em vertical slices, com ports em `ABC` e Clean/Hexagonal nominal, **sem** type-checker (`mypy` foi removido) e sem trava de import. Os dois são código de produção; as diferenças entre eles são o laboratório de quase toda posição abaixo.

---

## DI e composition root

### 1. Pure DI manual com factory tipada por port, sem container

**REGRA.** Cabeie as dependências à mão no composition root. Uma factory `provide_<port>` por port, com **o tipo de retorno anotado como o port**. Sem container de DI.

**CONDIÇÃO.** Vale enquanto houver type-checker em modo strict gateando o merge — é ele que converte a anotação em verificação. Sem checker, esta regra vira convenção e a garantia evapora; então o primeiro passo não é o DI, é o checker.

**GARANTIA.** O tipo de retorno anotado **é o seam**: um adapter que não implementa o port barra em dois sítios independentes — dentro da factory e no call-site que a consome. Verificação por máquina, no CI, antes de qualquer teste rodar.

**CENÁRIO.** Incluir: sem o seam tipado, o encaixe adapter↔port só é descoberto na primeira execução daquele caminho — no espécime sem trava o wiring também é manual, mas o único seam é o trap de runtime do `ABC` na instanciação, e o método com assinatura errada passa. Excluir o container: ele **move** o seam de estático para runtime/boot e acopla o vocabulário do framework ao grafo do domínio, sem devolver nada que a factory tipada não dê. Nem o espécime gateado (3 de 10 sítios com `provide_*`; ~8 adapters de repo/store instanciados direto) nem o sem trava sentiram falta de container — sentiram falta de checker.

**DISSENSO.** Vice = injeção nativa do framework (`Depends` do FastAPI para tudo). *Steelman:* é o idioma nativo, zero código de wiring, cache por-request e teardown de `yield` de graça, e `dependency_overrides` trivializa o teste de borda. *Perdeu porque:* `Depends(f)` tem tipo `Any` — o retorno do provider nunca é cruzado com a anotação do parâmetro, e `dependency_overrides` é um `dict` não tipado. Cabeia-se "certo" com a garantia ausente **exatamente no ponto de wiring**, que é o único lugar onde ela importava.

**GATILHO DE REABERTURA.** (i) Lifecycle de recurso com cleanup por-request virar dor real → reavaliar `svcs`; (ii) o grafo crescer a ponto de a ordem manual de construção ficar frágil → reavaliar `wireup` (fail-fast no boot), **desde que** preserve ou substitua o seam estático. E a garantia toda cai se o strict deixar de vigorar.

### 2. Um composition root por entry-point deployável

**REGRA.** Exatamente um composition root por **entry-point deployável** — o único módulo autorizado a conhecer adapter concreto e framework. `Depends` fica confinado à borda HTTP e só a escopo-de-request; nunca cabeia dependência de domínio.

**CONDIÇÃO.** Processo ASGI longo = um root (a função que monta o app). Deploy de função-por-feature (uma Lambda por caso de uso) = um root por função, no módulo de entrada dela. A unidade é o deploy, não o repositório.

**GARANTIA.** Não é o checker que garante isto sozinho: é a trava de import (`import-linter` ou equivalente), com um contrato proibindo `domain`/`application` de importarem `adapters` ou o framework. Sem essa trava, "só o root conhece adapter" é convenção — e convenção decai (ver posição 19, que mede a decadência num caso irmão).

**CENÁRIO.** Incluir: roots demais = wiring espalhado, e perde-se justamente o que o DI centraliza — trocar um adapter vira caçada. Excluir o root único global: num deploy multi-entry-point, forçar um root só obriga cada função a importar o grafo inteiro das outras — cold start e acoplamento sem contrapartida. A regra tem de valer nos dois formatos, porque os dois espécimes têm formatos diferentes.

**DISSENSO.** Vice = root único por repositório. *Steelman:* um lugar só para olhar, invariante trivial de auditar, e nenhuma pergunta sobre "qual root é esse". *Perdeu porque:* não porta para shape de deploy heterogêneo, e a portabilidade entre projetos é requisito, não bônus.

**GATILHO DE REABERTURA.** Entry-points passarem a compartilhar um grafo quase idêntico → um módulo de wiring compartilhado importado pelos roots, mantendo um root nominal por deploy.

---

## Forma do use-case

### 3. Use-case é função pura module-level, ports primeiro

**REGRA.** Escreva use-case como função module-level: **ports primeiro, inputs depois**. Sem classe, sem `execute()`. Bind-once é `functools.partial` ou closure no root, nunca uma classe.

**CONDIÇÃO.** Vale para use-case-comando: uma operação, invocada tipicamente uma vez por requisição/invocação. Não vale quando emergir um Assunto coeso multi-operação — aí não é mais use-case-comando, e classe é legítima.

**GARANTIA.** Aqui a honestidade obriga: **não há garantia verificável por máquina**. É preferência nomeável — menos peças (sem construir-para-chamar em seguida), forma uniforme entre N use-cases, composição direta com o root, encaixe com a linguagem. Decide no mérito por ser nomeável, não por ser mais confortável.

**CENÁRIO.** Incluir: a ordem ports-antes-de-inputs existe para `partial(use_case, port)` amarrar os deps líderes limpo — invertida, `partial` deixa de servir e volta a cerimônia de construção. Excluir a classe: numa borda que invoca uma vez por unidade de trabalho, construir para chamar logo em seguida é peça a mais sem trabalho — no espécime sem trava, `execute()` é chamado exatamente uma vez por invocação de Lambda.

**DISSENSO.** Vice = classe `@dataclass` com `execute()` e injeção por construtor (o que o espécime sem trava faz). *Steelman:* deps amarrados na construção; vira command object passável; separa visualmente deps (construtor) de inputs (`execute`); é o cânone Clean, em que o Interactor é um objeto; e há familiaridade de ecossistema real, além de consistência com outros projetos do mesmo autor. *Perdeu porque:* na taxa de invocação real a construção é cerimônia, e `partial` cobre bind-once sem introduzir um tipo novo.

**GATILHO DE REABERTURA.** (i) Use-case genuinamente invocado muitas vezes por processo com deps fixas, onde `partial` fique canhestro; (ii) emergir o Assunto coeso multi-operação da CONDIÇÃO.

**Nota de método — a régua aplicada a si mesma.** Na primeira redação desta posição, "a assinatura é o contrato completo, sem estado escondido" foi apresentada como **garantia dura**. Sob pressão, foi rebaixada: `frozen=True` no dataclass da classe rival **já mata** o risco de estado mutável, então a vantagem da função não é verificável — é preferência nomeável. O rebaixamento fica registrado porque é o comportamento que a régua exige de si mesma: quando o portão de garantia é apontado contra a própria posição, ele vale.

**Nota — não é divergência do campo.** Não existe *uma* recomendação oficial: Clean/Uncle Bob diz classe (e classe é o workaround de linguagem sem função de primeira classe e closure — insumo definitional, nunca normativo); Hexagonal é agnóstico (governa port/adapter, não a forma da lógica); e o cânone **Python** de arquitetura — o porte autoritativo desses mesmos padrões para a linguagem — prescreve funções de service layer recebendo o repositório por parâmetro, que é literalmente esta posição. Seguir o rendering Python não é ir contra as fontes.

### 4. Aridade alta vira bundle de ports frozen, não vira classe

**REGRA.** Quando a lista de ports deixa de caber na cabeça, agrupe-os num `@dataclass(frozen=True) <UseCase>Deps` passado como **primeiro parâmetro**. Continua função.

**CONDIÇÃO.** Só ports entram no bundle; inputs seguem parâmetros. Use-case de um ou dois ports não ganha tipo novo.

**GARANTIA.** `frozen=True` mata estado mutável compartilhado, e o tipo do bundle é conferido no estático como qualquer port — a economia de aridade não custa verificação.

**CENÁRIO.** Incluir: no espécime gateado há um use-case de resposta a proposta com 10 ports e um de digest de vencimentos com 7, e a docstring de um deles registra *"this use-case's arity earns the bundle"* — nessa faixa, lista posicional é sítio de erro por ordem. Excluir por default: bundle num use-case de dois ports (o de criar conta a pagar, que toma o repositório direto) é um tipo a mais para ler e nada a mais garantido.

**DISSENSO.** Vice = deixar a aridade forçar a virada para classe. *Steelman:* aridade alta é exatamente o sintoma que o Interactor resolve — o construtor **é** o bundle, sem inventar um tipo `Deps`. *Perdeu porque:* o bundle entrega o mesmo agrupamento sem trocar a forma de invocação nem introduzir ciclo de vida, e mantém uniformidade com os use-cases de aridade baixa, que continuam funções de dois parâmetros.

**GATILHO DE REABERTURA.** O bundle ganhar métodos (deixar de ser só dados) → é o Assunto coeso; promova a classe e assuma que aquilo não é mais use-case-comando.

---

## Transações e atomicidade

### 5. A transação nunca cruza a fronteira do port

**REGRA.** Quem abre e commita transação é o **adapter**, por método: cada método do repositório é a sua própria transação. Tudo-ou-nada multi-escrita vive **dentro** de um método.

**CONDIÇÃO.** Vale sempre. Ports falam só domínio — nenhum aceita ou devolve sessão, conexão ou handle de transação.

**GARANTIA.** Verificável pela ausência de tipo: se nenhuma assinatura de port menciona sessão/transação, é **impossível** um use-case controlar transação; o checker recusa. A garantia não depende de disciplina de quem escreve o use-case.

**CENÁRIO.** Incluir: no espécime gateado, o método que marca uma pendência como aguardando faz o CAS no alvo **e** libera as outras pendências da mesma pessoa numa transação só — *"either both land or neither"*. Excluir a transação na camada de aplicação: ela injeta o conceito de persistência no lugar que existia justamente para não conhecer persistência, e o fake do port passa a ter de fingir transação.

**DISSENSO.** Vice = **Unit of Work** injetado no use-case. *Steelman (sem cherry-picking):* é o padrão ensinado pelo cânone Python de arquitetura, dá tudo-ou-nada explícito no nível de aplicação e um ponto único de commit legível. *Perdeu porque:* o UoW do livro pressupõe **store transacional único**, e os fluxos reais são multi-store — um UoW em volta do banco não cobre a cópia do objeto no object storage nem o envio pela API externa. O fluxo de confirmação do espécime gateado toca Postgres → object storage → Postgres → CAS; o UoW entregaria **ilusão** de atomicidade na fatia SQL. É o teste da garantia falhando alto e claro: dá para cumprir "use UoW" 100% e a atomicidade prometida não existir.

**GATILHO DE REABERTURA.** Invariante tudo-ou-nada **single-store** atravessando dois repositórios que não devam se fundir num método → UoW (ou fundir os repositórios), com o custo declarado.

**Nota de método — o mesmo cânone dos dois lados.** O cânone Python de arquitetura foi usado **a favor** da posição 3 (service layer como função recebendo o repositório) e aparece como **rival** aqui (Unit of Work). Não há cherry-picking: uma fonte definitional pode ganhar num eixo e perder no vizinho, porque o que decide é o cenário local, não o crachá da fonte.

### 6. Concorrência é decidida pelo banco: CAS, e perder a corrida é valor

**REGRA.** Transição de estado sob concorrência = `UPDATE ... WHERE state = <esperado> ... RETURNING`. `RETURNING` vazio significa que a corrida foi perdida: o port devolve `None`. **Nunca exceção** para corrida perdida.

**CONDIÇÃO.** Vale para transição de estado com escritor concorrente. Corrida de check-then-insert é o caso irmão e fecha diferente — posição 7.

**GARANTIA.** Verificável no estático: um retorno `X | None` obriga todo call-site a tratar o caminho perdido, e o checker recusa quem ignora. Exceção não obriga ninguém a nada. Bônus de fidelidade: o fake do repositório só precisa devolver `None` quando o estado não bate — semântica de CAS cabe em poucas linhas e é fiel; um fake de UoW teria de modelar **rollback**, que é onde fake e real divergem sem ninguém ver.

**CENÁRIO.** Incluir: sem CAS, duas invocações simultâneas leem o mesmo estado e ambas escrevem — a segunda sobrescreve a decisão da primeira em silêncio. Excluir CAS onde não há corrida: escrita de fato novo sem estado anterior não ganha `WHERE` condicional; seria cerimônia SQL sem falha a evitar.

**DISSENSO.** Vice = ler-decidir-escrever no use-case, com ou sem lock aplicativo. *Steelman:* a decisão fica legível na camada que a possui, sem SQL condicional escondido no adapter, e o teste do use-case cobre a regra inteira. *Perdeu porque:* read-modify-write entre processos perde escrita silenciosamente, e o lock aplicativo é um segundo sistema de coordenação para manter e observar.

**GATILHO DE REABERTURA.** Transição que dependa de mais estado do que cabe num predicado de `WHERE` → transação explícita com nível de isolamento declarado, ainda **dentro** do adapter.

**Reconciliação com a doutrina de testes.** O gatilho original para descer ao banco real era amplo ("use-case contra banco real"); ele foi depois **estreitado** para o caso de **corrida concorrente real entre processos** — e mesmo nesse caso o teste que ela pede é de **adapter**, não de use-case, porque é o SQL que se está provando. Detalhe em `05-doutrina-de-testes.md`.

### 7. Unicidade fecha por constraint, não por leitura prévia

**REGRA.** Unicidade é garantida por índice único (parcial quando o predicado é condicional); o adapter traduz `IntegrityError` num erro de domínio nomeado.

**CONDIÇÃO.** Sempre que a unicidade for invariante de negócio e o store souber impor constraint.

**GARANTIA.** O banco é o único ponto que enxerga todas as transações; a checagem prévia em Python é uma janela de corrida por construção. A trava é declarativa — o índice existe ou não existe na migração — e é provável por teste de adapter com duas conexões.

**CENÁRIO.** Incluir: sem constraint, duas mensagens iguais chegando ao mesmo tempo criam duas propostas para o mesmo comprovante, e a deduplicação por hash em Python não vê a concorrente. Excluir a checagem prévia: ela não some do código por elegância, some porque **não garante** — cumprir a rotina 100% e ainda gravar duplicata é o modo de falha clássico.

**DISSENSO.** Vice = checar antes de inserir, no use-case. *Steelman:* o erro de domínio nasce no lugar certo, sem depender de dialeto de banco, e o caminho feliz não gasta exceção. *Perdeu porque:* sob concorrência a checagem prévia é decorativa; e a tradução de `IntegrityError` para erro de domínio já devolve o erro no lugar certo, sem vazar o dialeto para fora do adapter.

**GATILHO DE REABERTURA.** Store sem constraint de unicidade (parte dos key-value) → a unicidade passa a ser propriedade da **chave** (escrita idempotente por chave), nunca uma leitura prévia.

### 8. Efeito que cruza store exige compensação explícita; commit por último

**REGRA.** Ordene: efeito caro primeiro, **commit por último** (o CAS). Undo em ordem reversa, cada passo best-effort, nunca re-lançando. Com envio externo, o padrão é **claim → send → release**.

**CONDIÇÃO.** Vale quando uma operação toca mais de um sistema e nenhum deles pode absorver o outro na sua transação. Não vale para operação single-store.

**GARANTIA.** A compensação é caminho de código de primeira classe — nomeada, invocável, coberta por teste com fakes. É verificável no sentido que importa: existe um teste que falha se o undo sumir. Um UoW, em contraste, seria invisível no ponto exato em que falha.

**CENÁRIO.** Incluir: no espécime sem trava, `get_active_stocks` grava no DynamoDB e depois publica no SNS sem nenhum dispositivo; se o publish falha, a exceção sobe, a Lambda re-tenta, o DynamoDB reescreve igual (salvo pelo PUT na hash key) mas o **SNS republica** — efeito duplicado a jusante, e a idempotência que salva metade do fluxo é **acidental e não nomeada**. Excluir: não invente compensação para operação single-store — a transação do adapter já resolve, e o undo vira código morto que ninguém exercita.

**DISSENSO.** Vice = confiar no retry do runtime somado à idempotência natural das escritas. *Steelman:* no serverless o retry é gratuito e muitas escritas são naturalmente idempotentes (PUT por chave); código de compensação é código a manter. *Perdeu porque:* "naturalmente idempotente" precisa valer para **todos** os efeitos do fluxo, e basta um envio ou publish para a propriedade cair — como o caso acima mostra. Quando ela de fato vale, tem de estar nomeada, não descoberta por leitura de código.

**GATILHO DE REABERTURA.** Todos os efeitos do fluxo se tornarem idempotentes por chave, **declaradamente** e por adapter → o retry substitui a compensação, com a idempotência documentada onde é implementada.

---

## Doutrina de async

### 9. `async` é propriedade do I/O — o domínio é sempre síncrono

**REGRA.** Domínio: síncrono, sempre. Port: `async` **se e somente se** o adapter real faz I/O. Use-case: `async` se e somente se toca port `async`.

**CONDIÇÃO.** Incondicional para o domínio. Para port sem I/O — relógio, calendário — o síncrono é obrigatório, não preferência.

**GARANTIA.** É esta regra que **protege** a pureza do domínio. `Clock` e `Calendar` são Protocols síncronos porque são consumidos por funções puras de derivação; bastaria um deles ser `async` para toda a cadeia de derivação virar `async` e a coloração comer o núcleo inteiro. Verificável: o checker recusa `await` em função síncrona, então a fronteira aparece sozinha e não pode ser contornada por descuido.

**CENÁRIO.** Incluir: a coloração é viral **na direção de dentro** — um port async no lugar errado converte funções puras em corrotinas, e testes de derivação passam a precisar de event loop sem nenhum I/O envolvido. Excluir o síncrono onde há I/O: adapter de rede ou banco declarado síncrono num processo ASGI trava o event loop, e a regra não é "prefira sync", é "declare o que é verdade".

**DISSENSO.** Vice = "async por precaução": todo port `async`, inclusive relógio, pela estabilidade do contrato. *Steelman:* quebrar a assinatura de um port depois é viral e atinge todo use-case de uma vez — o seguro compra imunidade a isso. *Perdeu porque:* o custo do seguro é **certo e imediato** (poluir o domínio inteiro) contra um custo **hipotético**; e se a quebra vier, o conserto é mecânico, com o checker apontando cada sítio.

**GATILHO DE REABERTURA.** Um port hoje síncrono passar a precisar de I/O real.

### 10. Nunca `async` de mentira

**REGRA.** Lib bloqueante vai no driver async de verdade **ou** em `asyncio.to_thread`. Jamais `async def` embrulhando chamada bloqueante. Em FastAPI, handler com corpo bloqueante fica `def` (roda em threadpool); `async def` só quando o corpo é de fato não bloqueante.

**CONDIÇÃO.** Vale em qualquer runtime com event loop. Em código sem loop, a pergunta não existe.

**GARANTIA.** Esta é **não verificável por type-checker**, e vale dizer com todas as letras: um `async def` que bloqueia tem exatamente o mesmo tipo de um honesto — **a mentira não aparece no tipo**. O que é verificável é o efeito, sob carga, tarde demais. Por isso a regra é explícita e a revisão a procura à mão. *(Que `def` vá para threadpool e `async def` para o event loop é claim de comportamento do framework: documentado, e decidível por experimento se virar load-bearing.)*

**CENÁRIO.** Incluir: `async def` com chamada bloqueante dentro trava o loop e degrada **todas** as requisições concorrentes, não só a sua — e some em desenvolvimento, onde não há concorrência. Excluir o `to_thread` por default: embrulhar em thread código que já tem driver async paga troca de contexto e perde cancelamento, sem falha a evitar.

**DISSENSO.** Vice = uniformidade — tudo `async def` na camada HTTP. *Steelman:* uma forma só na borda, sem decidir caso a caso, e nada quebra visivelmente em desenvolvimento. *Perdeu porque:* justamente por só aparecer sob concorrência, é o defeito que passa por todos os gates e chega em produção como latência inexplicada.

**GATILHO DE REABERTURA.** A lib bloqueante ganhar cliente async mantido → troque o `to_thread` pelo driver async e simplifique o adapter.

### 11. Async paga por formato de runtime, não por estilo

**REGRA.** Processo ASGI longo com requisições concorrentes → async paga. Serverless com uma invocação = uma unidade de trabalho, sem fan-out → **sync é o correto**. Fan-out de I/O dentro da mesma invocação → concorrência paga **mesmo em serverless**, e a forma (async × thread pool) segue a posição 10.

**CONDIÇÃO.** O predicado é o formato do runtime somado à existência de fan-out — não o gosto do time nem a idade do código.

**GARANTIA.** Mensurável: latência de ponta a ponta e, no serverless, **custo** — a cobrança é por duração, então I/O serializado é dinheiro. Não é argumento de elegância.

**CENÁRIO.** A regra **vindica** o síncrono onde ele está certo (o handler de Lambda sem fan-out do espécime sem trava) e **morde** no `get_fundamentus_eod_stock_metrics` do mesmo espécime: N scrapes HTTP **serializados** numa única invocação, cada um com `timeout=10` e até 3 retries — latência e custo crescem lineares em N. E a prescrição ali **não é "vira async"**: é paralelizar o I/O, e como o cliente HTTP é bloqueante, a resposta de menor ruptura é `ThreadPoolExecutor`. É o caso que prova que a doutrina não é "async em tudo".

**DISSENSO.** Vice = async como default de projeto, independentemente do runtime. *Steelman:* uniformidade de estilo e "já está pronto quando escalar". *Perdeu porque:* paga coloração e complexidade de teste onde não há concorrência a explorar; num modelo de uma invocação por unidade de trabalho não existe sobreposição a ganhar.

**GATILHO DE REABERTURA.** O runtime mudar de formato: a mesma lógica passar a rodar num processo longo, ou a invocação passar a ter fan-out.

---

## DTOs e validação por camada

### 12. Núcleo com `dataclass` frozen puro, zero lib de validação

**REGRA.** Domínio e application usam `@dataclass(frozen=True)` puro; nenhuma lib de validação atravessa a fronteira do núcleo. `frozen=True` por default em tudo que atravessa camada.

**CONDIÇÃO.** Incondicional para tipos de domínio e de aplicação. Dentro de um adapter, mutabilidade local é assunto do adapter.

**GARANTIA.** Verificável por trava de import (contrato proibindo o núcleo de importar a lib), e o `frozen` é conferido pelo checker no ponto da atribuição — reatribuir campo é erro estático, não convenção de revisão.

**CENÁRIO.** Incluir: sem `frozen`, um objeto que atravessa três camadas pode ser mutado na borda e a origem do valor deixa de ser rastreável — no espécime sem trava, o modelo principal é mutável e **normaliza mutando** em `__post_init__`, então o valor que entrou não é o valor que está lá. Excluir a lib do núcleo: ela traz validação em runtime e semântica de coerção para dentro de código já conferido no estático, e prende o domínio a uma dependência de terceiro que muda de major.

**DISSENSO.** Vice = pydantic de ponta a ponta, um modelo só, da borda ao domínio. *Steelman:* validação garantida por construção, serialização de graça, some a camada de tradução, é o que o framework empurra e a comunidade pratica em massa. *Perdeu porque:* acopla o domínio a terceiro; **não modela entrada parcial** — no espécime gateado uma proposta de lançamento vive **dias** com campos `None` até a pessoa responder, o que obrigaria a um segundo modelo "parcial" e mata a premissa do modelo único; e entrega o formato do erro para a lib decidir.

**GATILHO DE REABERTURA.** Entrada parcial deixar de existir (todo agregado nascendo completo) **e** a serialização virar custo dominante → reavaliar o modelo único, com o acoplamento assumido por escrito.

### 13. Validação é função explícita com fronteira de **tipo** entre cru e validado

**REGRA.** `<X>Raw` → `validate_<x>` → `<X>Data`: dado cru e dado validado são **tipos distintos**, e a única passagem entre eles é a função.

**CONDIÇÃO.** Vale para toda entrada externa que o núcleo consome. Não vale entre dois pontos internos que já trocam tipos validados.

**GARANTIA.** É impossível passar dado não validado onde se espera validado — os tipos são diferentes e o checker força a travessia. É a garantia mais dura deste eixo: não depende de ninguém lembrar de chamar nada.

**CENÁRIO.** Incluir: com um tipo só, "já validei" é fé — e o sítio que esqueceu não aparece em lugar nenhum até o dado ruim chegar ao banco. Excluir a duplicação de tipos onde não há fronteira: criar `Raw`/`Data` para estrutura que nasce dentro do núcleo é dois tipos e nenhuma travessia a proteger.

**DISSENSO.** Vice = validar no construtor do próprio tipo — um tipo só, e o inválido simplesmente não instancia. *Steelman:* menos tipos, impossível esquecer, e é o "parse, don't validate" clássico. *Perdeu porque:* joga o erro no formato de exceção do construtor, um campo por vez, e não **acumula** a lista de erros que um formulário precisa devolver de uma vez; a fronteira de tipo entrega a mesma impossibilidade com o resultado acumulado.

**GATILHO DE REABERTURA.** O erro passar a ser sempre único e fatal (sem formulário atrás) → o construtor que valida volta a bastar.

**Nota de método — ritual detectado dentro da própria referência.** O tipo de resultado da validação carregava um campo `ok: bool` com **forma** de tag de união discriminada. Só que ele **não narrowa** no pyright: o código de produção narrowa por `isinstance(res, Invalid)` em 7 sítios, e `ok` só é lido em **teste** (~25 `assert res.ok is True`). Não é código morto — é uma **tag que não faz trabalho de tag**, e que convida alguém a escrever `if res.ok:` sem narrowing nenhum. É o teste da garantia aplicado ao próprio padrão: cumpre-se a forma 100% e a garantia (narrowing) não existe nesta linguagem. Decidido: **sai**, e os testes passam a `isinstance`, alinhando teste e produção. Peso honesto: é papercut mecânico — o valor é o exemplar.

### 14. O formato do erro de validação é nosso — `FieldError(field, code)`

**REGRA.** A função de validação devolve erros num tipo próprio com dois campos: `field` (o id do campo como a borda o conhece, camelCase) e `code` (código estável, de máquina). Copy de produto **não** entra.

**CONDIÇÃO.** Vale para validação de entrada vinda de formulário ou payload, onde há uma borda humana atrás.

**GARANTIA.** O par `(field, code)` é contrato entre núcleo e borda: versionável, comparável por igualdade em teste, e independente de idioma. A copy fica com quem fala com a pessoa e varia por borda sem tocar o núcleo.

**CENÁRIO.** Incluir: o erro de uma lib entrega `loc`/`msg`/`type` em inglês, e a borda teria de remapear campo a campo para o id que o formulário de fato usa — trabalho que a lib não pode fazer porque não conhece o formulário. Excluir a mensagem: uma segunda borda já ignorava a copy na prática e montava a própria, então `message` no núcleo era peso morto fingindo contrato.

**DISSENSO.** Vice = `FieldError(field, message)` com a copy pronta em pt-BR — a forma originalmente fechada neste eixo, refinada depois pelo eixo de modelo de erro. *Steelman:* a borda não precisa de tabela de tradução, e a mensagem nasce junto da regra que a produziu, onde o contexto é maior. *Perdeu porque:* copy é decisão de produto **por borda**, e com duas bordas a frase do núcleo vira a frase de ninguém. A tese normativa original — **o formato do erro é nosso, não da lib** — sai intacta; muda só quem compõe a frase. O detalhe de como `code` viaja até a resposta HTTP está em `04-modelo-de-erro.md` e não é duplicado aqui.

**GATILHO DE REABERTURA.** Voltar a existir exatamente uma borda humana, com copy genuinamente única → `message` pode voltar, sabendo que sai de novo na segunda borda.

### 15. Pydantic é legítimo — na borda, e só nela

**REGRA.** Parsing e coerção de payload HTTP e geração de schema OpenAPI podem usar a lib; o handler traduz para o tipo **cru** do domínio, que nunca a vê.

**CONDIÇÃO.** Quando houver payload externo real. Não vale para wiring interno nem para tipo que nasce e morre no núcleo.

**GARANTIA.** É a mesma trava de import da posição 12 lida ao contrário: a lib é permitida em `adapters`/borda e proibida no núcleo. A linha é declarativa e checada por máquina, não cultural.

**CENÁRIO.** Incluir: sem a lib na borda, o parsing de payload grande vira código repetitivo e o schema OpenAPI passa a ser escrito à mão — a mesma informação em dois lugares, divergindo. Excluir do núcleo: modelo de lib no domínio é validação em runtime dentro de código já conferido no estático. E **barrá-la também da borda seria minimalismo por esporte** — a régua proíbe as duas cerimônias simétricas, e o cenário de exclusão na borda não tem falha concreta a nomear.

**DISSENSO.** Vice = zero pydantic no repositório, parsing manual em toda parte. *Steelman:* uma dependência a menos, nenhuma coerção mágica, e o tipo cru do domínio existe de qualquer jeito. *Perdeu porque:* paga tradução manual e schema à mão para não usar a ferramenta exatamente onde ela é boa.

**GATILHO DE REABERTURA.** Payloads ficarem pequenos e estáveis a ponto de o parsing manual custar menos que a dependência → a lib sai da borda sem prejuízo.

### 16. Nunca ambiente nem relógio no default de um tipo

**REGRA.** `default_factory` não lê ambiente e não lê hora. Timestamp entra por parâmetro, vindo de um port `Clock`.

**CONDIÇÃO.** Incondicional para tipos que atravessam camada ou que aparecem em asserção de teste.

**GARANTIA.** Determinismo: o mesmo construtor com os mesmos argumentos produz o mesmo valor, então o teste não precisa congelar o tempo do processo. `Clock` com implementação fixa nos testes é a única forma sancionada; congelar o relógio global (freezegun e afins) é proibido porque **esconde** exatamente o acoplamento que se quer enxergar.

**CENÁRIO.** Incluir: no espécime sem trava, o modelo principal embute o relógio real num `default_factory` — toda construção é não determinística, e testar exige congelar o tempo do processo inteiro. Excluir: passar o timestamp por parâmetro custa um argumento a mais por construção; é o preço, e é pequeno.

**DISSENSO.** Vice = `default_factory` com o relógio real. *Steelman:* elimina um argumento repetitivo, e "criado em" é quase sempre agora mesmo. *Perdeu porque:* transforma todo teste num teste sobre o relógio do processo, e impede reconstruir um objeto a partir de um fato histórico (importação, replay) sem sobrescrever o default.

**GATILHO DE REABERTURA.** O tipo deixar de atravessar camada e de aparecer em asserção — puramente local a um adapter. Mesmo aí o ganho é um argumento.

### 17. Cada use-case devolve o seu próprio resultado tipado

**REGRA.** Sem envelope genérico de saída. O retorno de cada use-case é um tipo específico, ou uma união específica.

**CONDIÇÃO.** Vale para todo use-case. Uniformizar formato de resposta é trabalho da borda, sobre o tipo específico que ela recebeu.

**GARANTIA.** O checker confere o consumo do resultado em cada borda. Um envelope com payload `Any` apaga o tipo na saída de **todos** os use-cases de uma vez — um único ponto que desliga a verificação do sistema inteiro.

**CENÁRIO.** Incluir: no espécime sem trava, um `OutputDTO` com `data: Optional[Any]` é a saída de todo use-case — a versão de **saída** do mesmo buraco que as auditorias acharam na entrada; nenhuma borda sabe o que recebeu, e renomear um campo não quebra nada até a resposta HTTP sair errada. Excluir o medo de proliferação: um tipo por use-case não cria formas novas, apenas **nomeia** as formas que já existiam implícitas.

**DISSENSO.** Vice = envelope uniforme com `data` genérico. *Steelman:* a borda serializa tudo com um handler só, e status, erro e metadados viajam juntos num formato estável — é padronização real, não capricho. *Perdeu porque:* uniformidade de serialização **não exige** apagar o tipo; um envelope parametrizado entregaria as duas coisas. O que perde é a versão com `Any`.

**GATILHO DE REABERTURA.** Envelope parametrizado por tipo, conferido no estático → aceitável, porque a garantia volta intacta.

---

## Configuração e acesso a ambiente

### 18. Config num ponto só, lida no boot, fail-closed

**REGRA.** Um `Settings` resolve **toda** a configuração numa passada, no composition root, e o processo **recusa subir** se faltar variável obrigatória. Nada mais em `src` toca `os.environ`.

**CONDIÇÃO.** Vale para qualquer processo com mais de um adapter configurável — na prática, sempre.

**GARANTIA.** Misconfig vira falha de **boot**: o deploy quebra na hora, visível, com a variável faltante nomeada. Sem isso, vira falha de **primeiro uso** — descoberta dias depois, pelo usuário, no pior momento possível.

**CENÁRIO.** Incluir: no espécime gateado, o segredo do JWT interno está no `Settings` e sua ausência derruba o boot; as cinco variáveis do object storage são lidas por uma função local dentro do adapter, então o processo sobe normal e **explode no primeiro upload**. Mesmo shape de defeito parcial do DI: o padrão existe e cobre uma fração. Excluir a leitura tardia deliberada: nenhum caso do laboratório precisou de configuração descoberta em runtime — quando precisar, é feature flag, e feature flag é adapter, não config de boot.

**DISSENSO.** Vice = leitura local no adapter. *Steelman:* config coesa com quem a usa, sem objeto-deus, e adicionar adapter não exige tocar num arquivo central — não é irracional, e é o que o espécime gateado de fato faz num dos adapters. *Perdeu porque:* troca falha-no-boot por falha-no-primeiro-uso, que é a troca ruim em qualquer sistema com deploy automatizado.

**GATILHO DE REABERTURA.** `Settings` virar objeto-deus → quebre por contexto (`FinanceSettings`, `WhatsappSettings`) **mantendo** a leitura única no boot; nunca volta para leitura dispersa.

### 19. A trava é parte da regra: `os.environ` proibido fora do módulo de settings

**REGRA.** Proíba `os.environ` e `os.getenv` fora do módulo de settings, por trava de lint (banned-api do `ruff` — a regra `TID251` — ou equivalente).

**CONDIÇÃO.** Vale a partir do segundo adapter. A forma exata da trava é claim de comportamento de ferramenta: confirme por experimento na versão pinada antes de adotar.

**GARANTIA.** Sem trava-máquina, "config num ponto só" é convenção — e convenção decai, com número: no espécime gateado, **com o padrão escrito e entendido, a leitura única cobria 1 de ~6** grupos de variáveis. Com a trava, cumprir a regra implica ter a garantia; sem ela, não implica nada.

**CENÁRIO.** Excluir a trava (ficar só na convenção): no espécime sem trava há **~25 sítios** de leitura de ambiente — dentro de use-case (quatro features), no `Meta` de um model **no tempo de import** e de novo no `__init__` (workaround que denuncia o problema), em adapters e em mappers. O caso que fecha o argumento: `os.getenv("S3_EMAIL_TEMPLATES_FOLDER_PREFIX").strip("/")` levanta `AttributeError` em runtime se a variável faltar; existe um `check_required_env_vars`, mas roda só em *alguns* handlers, com lista mantida à mão, e sem type-checker o `str | None` não é pego no estático. Incluir sem exagero: a trava não impede configuração nenhuma — impede **leitura fora de um arquivo**.

**DISSENSO.** Vice = convenção documentada, sem trava. *Steelman:* uma configuração de ferramenta a menos, e a revisão de código pega os casos. *Perdeu porque:* a medição diz que não pega — 1 de ~6 num repositório com o padrão escrito e o autor atento.

**GATILHO DE REABERTURA.** A trava produzir falso-positivo estrutural (um módulo de bootstrap legítimo) → amplia-se a allowlist do banned-api, **não** se remove a trava.

### 20. Config chega ao adapter por parâmetro; domínio e use-case nunca leem ambiente

**REGRA.** Adapter recebe o que precisa como argumento (`make_async_engine(database_url)`), e as factories `provide_*` são o **único** lugar que traduz `Settings` em argumento de adapter. Domínio e use-case não leem ambiente, incondicionalmente.

**CONDIÇÃO.** Incondicional. Não há caso em que um use-case precise da variável e não do valor.

**GARANTIA.** O adapter fica testável sem preparar ambiente e reusável com outra configuração; e a trava da posição 19 torna a violação um erro de lint, não uma observação de revisão. A dependência aparece na assinatura, que é onde o checker olha.

**CENÁRIO.** Incluir: use-case que lê ambiente esconde uma dependência que não está na assinatura e não é testável sem montar o ambiente — no espécime sem trava isso ocorre dentro de quatro features. Excluir: nenhum custo real do lado oposto; passar o valor é um argumento, e é ele que torna o adapter substituível.

**DISSENSO.** Vice = passar o objeto `Settings` inteiro ao adapter. *Steelman:* uma assinatura só, estável, e acrescentar variável não muda nenhuma chamada. *Perdeu porque:* reintroduz a dependência larga que se quis remover — o adapter passa a conhecer configuração que não é dele, e o teste tem de montar um `Settings` completo para exercitar uma conexão.

**GATILHO DE REABERTURA.** Adapter que precise de mais de meia dúzia de valores → um `<Context>Settings` coeso, passado como um objeto, ainda montado no root.
