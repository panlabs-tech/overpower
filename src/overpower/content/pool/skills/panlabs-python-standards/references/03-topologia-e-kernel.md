# Topologia e kernel — onde cada arquivo mora e o que pode importar o quê

Este eixo responde a uma pergunta só, com dez posições: dado um backend Python que já decidiu ter domínio próprio, **qual é a unidade da fatia no primeiro nível, o que mora dentro dela, o que sobe pro kernel compartilhado, e qual aresta de import é legal** — com a fronteira executada por máquina em vez de prometida em prosa.

> Régua: toda posição abaixo passou pelo portão anti-cerimônia — cenário nomeado nos dois sentidos, garantia verificável, autoridade não preenche.

## Os três corpos de evidência citados aqui

**O espécime gateado** — o backend `apps/api` do projeto LUC: Python 3.14 / FastAPI / uv, ~102 arquivos, 4 contextos delimitados (`finance`, `identity`, `whatsapp`, `shared`), com pyright strict + ruff + import-linter gateando o merge e ~600 testes. É o único espécime onde a fronteira de camada é executada por máquina, e por isso é o laboratório de quase toda medição abaixo.

**O espécime sem trava** — `b3stocks`: backend Python de Lambdas com vertical slices e ports declarados em ABC, **sem** type-checker e **sem** import-linter. Serve como prova por ausência: mesmas pastas, mesmos nomes de pattern, garantia inexistente. Toda vez que uma regra deste eixo puder ser cumprida 100% com a garantia falhando, é este espécime que demonstra o modo de falha.

**O radar de produção** — 6 backends Python reais estudados: Netflix Dispatch, Polar, Prefect, Warehouse (PyPI), Sentry e o template oficial de FastAPI. É dispositivo de decisão apenas quando o consenso é ~universal; abaixo disso mapeia o espaço de opções sem decidir.

Nos snippets de `pyproject.toml`, o pacote se chama `myapp` para portar; `finance`, `identity` e `whatsapp` aparecem como **exemplos de contexto delimitado** — troque pelos seus.

## A forma que as dez posições produzem

```
myapp/
  settings.py            # ponto único de leitura de ambiente (posição 10)
  composition.py         # provedores tipados Settings -> adapter concreto (10)
  main.py                # entry-point ASGI; jobs/<nome>.py para agendados (10)
  http/                  # transversal sem dono: problem+json, deps, health (4)
  finance/               # contexto delimitado (1)
    domain/              # planos, módulo por conceito (2, 3)
    application/
      ports/             # (2)
      use_cases/         # muta estado, carrega invariante (2)
      projections/       # deriva sobre fatos persistidos; só quando povoado (2)
    adapters/            # repos, http.py da borda, tables.py do schema (4, 7)
  identity/              # mesma forma
  whatsapp/              # mesma forma
  shared/                # kernel: vocabulário ubíquo + ports de ambiente (5)
    application/         # Clock, Calendar
    adapters/db/         # engine.py, metadata.py (registro vazio) (7)
migrations/              # na raiz do app, nunca por contexto (8b)
tests/                   # espelha src/
```

Cada aresta desse desenho é executada por um contrato de import-linter, não por convenção — é o que separa esta topologia da mesma topologia sem trava.

---

### 1. Unidade da fatia no primeiro nível

**REGRA.** O primeiro nível do pacote é o **contexto delimitado**, não o conceito de domínio.

**CONDIÇÃO.** Vale enquanto a base tiver ordem de grandeza de poucos contextos e ~100 arquivos, com um ou dois donos. O corte por conceito no topo — dominante no radar de produção — é a unidade certa quando dezenas de conceitos disputam atenção de times diferentes: Polar tem ~80 pacotes de conceito, Netflix Dispatch ~50, Sentry ~140, e o grão fino existe justamente para que 80 pastas caibam na cabeça de gente que não se conhece.

**GARANTIA.** Contexto no topo é o que faz cada container do import-linter corresponder a uma fronteira que alguém defende. Com 4 contextos, 4 containers; no grão de conceito seriam ~10 containers de ~5 arquivos cada — dez fronteiras declaradas sem nenhum modo de falha demonstrado atrás delas. Verificável: o número de containers do contrato deve bater com o número de fronteiras que você consegue nomear com um cenário de violação.

**CENÁRIO.** Contra o conceito no topo: o espécime gateado viraria ~10 pastas de 5 arquivos, cada uma importando as outras em todas as direções — o custo da pasta sem a fronteira que a pasta promete, exatamente o que o `cross/` do espécime sem trava demonstrou. A favor do conceito: a dor de "um contexto virou grande demais" **é real e medida** — `finance/application` tem **37 módulos num nível só** — mas é local a uma camada de um contexto, e a resposta certa é a posição 2, não estilhaçar o topo.

**DISSENSO.** Vice = conceito de domínio no primeiro nível. *Steelman:* é a topologia dominante em 4 das 6 codebases de produção estudadas, e é a que comprovadamente sobrevive a crescimento real de time e de superfície. *Perdeu porque:* a escala que justifica o grão fino não existe no espécime, e a dor medida é intra-contexto — resolver no topo trata o sintoma na camada errada.

**GATILHO DE REABERTURA.** Um contexto passar de ~15 conceitos, ou dois contextos precisarem de deploy/ownership separados ⇒ conceito vira o primeiro nível e o contexto vira agrupador.

---

### 2. Estrutura dentro do contexto — corte por papel

**REGRA.** Dentro do contexto: `application/{ports/, use_cases/, projections/}`, com `domain/` e `adapters/` planos, módulo por conceito. `ports/` e `use_cases/` sempre; **`projections/` só quando povoado**. Conceito não vira subpasta enquanto não emergir um Assunto com ciclo de vida próprio.

**CONDIÇÃO.** O corte por papel dentro de `application/` só compra algo onde existe a distinção "muta estado" × "deriva interpretação sobre fatos já persistidos". Numa base que é CRUD sobre tabela, os dois papéis coincidem e a subpasta é decoração. A regra geral "estrutura por conceito de domínio, nunca por tipo DDD" continua valendo **em `domain/`** — dentro de `application/` ela é explicitamente emendada, porque ali a fronteira que existe é de papel.

**GARANTIA.** Compra a resposta greppável para a pergunta "o que aqui dentro pode escrever?". Medido no espécime gateado: `finance/application/` tem **37 módulos planos** — 7 ports, 13 use-cases de escrita e **17 módulos de leitura/derivação** (projeção de agenda, cenário do mês, mapa do ano, pontualidade, atenção do painel). Hoje `list_bills.py` fica ao lado de `close_bill.py` e nada distingue os dois por inspeção. É também o único candidato **verificável por máquina**: um contrato proibindo `projections/` de tocar port de escrita é escrevível no dia em que valer a pena. Os outros contextos do espécime têm 6 e 7 módulos e não sentem dor nenhuma — daí o hedge de `projections/`.

**CENÁRIO.** Contra o corte: aos 6 módulos, três pastas com um ou dois arquivos cada comunicam estrutura que não está lá. A favor: aos 30+ módulos num nível, a pergunta "o que aqui pode escrever?" não tem resposta mecânica, e numa base que guarda dado irreplicável essa é a pergunta que mais importa. Nome importa: `projections/`, não `read_models/` nem `queries/` — o verbo do domínio é "derivar interpretações", e o nome carrega a invariante.

**DISSENSO.** Vice = subpasta por conceito (`application/{bill,payment,attachment}/`). *Steelman:* é o que a doutrina "estrutura por conceito de domínio" diz literalmente, e é o que Dispatch e Polar praticam em escala, inclusive com sub-conceitos aninhados. *Perdeu porque:* os conceitos daquele contexto **não são separáveis** — pagamento é sempre contra ocorrência de conta, e as projeções de agenda e de cenário do mês leem os três conceitos juntos; fatiar produz ~4 pastas se importando em todas as direções.

**GATILHO DE REABERTURA.** Um conceito ganhar ciclo de vida próprio — anexo com storage, OCR e retenção, sem leitura cruzada — ⇒ graduou para sub-fatia.

---

### 3. As três camadas, sob condição — **a posição mais frágil deste eixo**

**REGRA.** `domain/` / `application/` / `adapters/` dentro do contexto **quando** (i) existe lógica de derivação ou invariante que vale testar sem infra **e** (ii) a fronteira é executada por import-linter. Nomes: `adapters/`, não `infra/`, não `service_layer`/`entrypoints`.

**CONDIÇÃO.** Faltando (ii), **não adote** — camada sem trava é o espécime sem trava. Faltando (i) — contexto que é CRUD sobre tabela — o certo é arquivo-por-papel dentro do pacote de feature (`models.py`, `service.py`, `views.py`, `repository.py`), como faz o radar inteiro.

**GARANTIA.** O que a camada compra é suíte que roda sem infra e núcleo que não conhece o mundo — e isso só é garantia se um contrato `layers` do import-linter falhar o build quando alguém importa ao contrário. No espécime gateado o contrato existe (4 containers) e ~600 testes rodam sem banco. É verificável por máquina de ponta a ponta; **sem o contrato, não é verificável por nada** e a regra vira decoração de pastas.

**CENÁRIO.** Contra as camadas, e este é o ponto frágil: **0 das 6 codebases de produção do radar** tem camadas hexagonais dentro do pacote de feature. Empírico 6/6 **contra**. A favor, o contra-exemplo é o espécime sem trava: mesmas pastas (`domain/`, `use_cases/`, `infra/`), sem type-checker e sem import-linter ⇒ `import awswrangler` dentro de use-case, `os.getenv` e `datetime.now` no núcleo de quatro use-cases, mypy removido do projeto. A pasta prometeu isolamento e entregou zero.

**Fragilidade declarada, e o confundidor que a sustenta.** Esta é a única posição do eixo que sobrevive **contra** o empírico, e ela é assim rotulada de propósito. O confundidor é nomeável: as 6 bases do radar são web-CRUD de domínio fino com o ORM no centro — no mesmo radar, 6/6 testam use-case contra Postgres real e ninguém usa fake, porque **não há núcleo separável para separar**. O espécime gateado está do outro lado desse confundidor: 17 derivações puras num contexto, compare-and-swap com compensação, dinheiro em centavos. O desempate é "realidade medida > promessa documentada", e a realidade medida no espécime-alvo é favorável. Se o confundidor cair — se aparecer no radar uma base com núcleo rico **e** sem camadas — esta posição cai com ele.

**DISSENSO.** Vice = arquivo-por-papel dentro do pacote de feature, sem camadas. *Steelman:* 6 de 6 codebases de produção fazem assim, e o eixo de testes do mesmo radar mostra que elas também abandonaram o fake-atrás-de-porto — não é desleixo isolado, é um **pacote coerente de decisões** que se sustentam mutuamente. *Perdeu porque:* o confundidor (domínio fino, ORM-cêntrico, time grande) é nomeável e o alvo está do outro lado dele — mas com a ressalva de fragilidade acima, não como vitória confortável.

**Como decidir num projeto novo, sem re-litigar o eixo:**

| (i) núcleo separável? | (ii) import-linter no CI? | Forma |
|---|---|---|
| sim | sim | três camadas dentro do contexto |
| sim | **não** | arquivo-por-papel — e adote a trava antes de adotar as camadas |
| não (CRUD sobre tabela) | qualquer | arquivo-por-papel dentro do pacote de feature |

O quadrante "sim/não" é o único que costuma ser preenchido errado: é onde as pastas comunicam uma promessa que nada sustenta, e é exatamente onde o espécime sem trava vive.

**GATILHO DE REABERTURA.** Contexto novo que seja CRUD puro não ganha camadas; **2+ contextos assim invertem a regra geral**. Idem: aparecer no radar uma base de domínio rico sem camadas.

---

### 4. Borda HTTP dentro do contexto

**REGRA.** O router mora **dentro** do contexto: `<ctx>/adapters/http.py`, plano ao lado dos repositórios, sem split `inbound/`/`outbound/` enquanto ambos os papéis não estiverem povoados. A montagem final é central (`main.py`). O pacote HTTP central guarda **só o transversal sem dono de contexto**: mapeamento de erro para `problem+json`, dependências compartilhadas (identidade, token interno) e health.

**CONDIÇÃO.** Vale desde o dia zero, e vale mais quanto mais borda ainda estiver por nascer. Vira pacote `http/` com módulo por recurso quando o contexto passar do limiar de dor de um arquivo só.

**GARANTIA.** É de máquina, não de gosto: `finance/adapters/http.py` cai automaticamente dentro do container do contexto e do contrato `layers` que já existe — a borda passa a ser **impedida** de importar `finance/domain/` sem escrever contrato novo. Converte a regra mais central da arquitetura ("borda nunca fala com o store direto, fala com use-case") de convenção em invariante executável. Com borda central, ela continua comentário.

**CENÁRIO.** A favor: no espécime gateado a auditoria encontrou, num use-case, um comentário explicando por escrito que uma regra de fronteira não era executada — regra-comentário é exatamente o que apodrece. Contra: em escala, convenção de borda (auth, paginação, envelope de erro) deriva por feature; Sentry, com ~140 pacotes por feature, está **ativamente re-centralizando** endpoints. O que o Sentry centraliza, porém, é a **convenção** (classe base, dependências), não o corpo do endpoint — e a convenção aqui já é central.

**DISSENSO.** Vice = borda central com um módulo por contexto. *Steelman:* a re-centralização do Sentry é evidência de que, passando de certa escala, só o centro recupera uniformidade de convenção de borda. *Perdeu porque:* centralizar o **corpo** do endpoint abre um buraco de import-linter que hoje é real e gratuito de fechar, enquanto a uniformidade que o Sentry busca já está garantida pelo módulo transversal compartilhado.

**GATILHO DE REABERTURA.** Convenção de borda começar a derivar entre contextos apesar do módulo transversal compartilhado.

---

### 5. Critério do kernel — natureza, não contagem

**REGRA.** Entra no kernel compartilhado o que (a) é **vocabulário ubíquo sem dono possível** — dinheiro, data civil, taxonomia semântica de erro — ou (b) é **port do ambiente, não do domínio** (`Clock`, `Calendar`), mais sua implementação. **Filtro necessário:** 2+ contextos consomem de fato — passar nele não autoriza nada sozinho. **Exclusão explícita:** nada com dono de contexto identificável entra, por mais compartilhado que seja; ou o dono expõe pela sua camada `application`, ou **duplica-se**. **Trava:** o kernel não pode importar contexto (executada pelo contrato da posição 6).

**CONDIÇÃO.** Universal para qualquer pacote com um diretório `shared`/`common`/`core`. O item (b) pressupõe que o projeto tenha decidido portar o ambiente; sem isso, o kernel é só (a).

**GARANTIA.** Amarra o kernel a uma propriedade que não muda com o crescimento (natureza do conceito) em vez de a um contador que sobe sozinho. A parte greppável — "quem importa quem" — é recuperada no lugar certo, no contrato de fronteira da posição 6, não numa regra de admissão que ninguém consegue conferir depois.

**CENÁRIO.** **A régua antiga foi reprovada, e o registro dessa reprovação é parte da regra.** O critério anterior era "2+ contextos usam". Ele **falha no teste do espécime sem trava**: o `cross/` de lá cumpre a regra em 100% dos habitantes — o repositório DynamoDB de controle de lote e o adapter HTTP genérico são de fato usados por várias fatias — e a garantia prometida ("shared é mínimo") falhou mesmo assim; a auditoria concluiu que aquele diretório "é um contexto por si só". Regra cumprida integralmente + garantia falhando = ritual, e ritual se corta. O kernel do espécime gateado usava a mesma régua e só não falhou por sorte de escala. No outro sentido: sem o filtro de uso, "ubíquo por natureza" autoriza um kernel especulativo de conceitos que ninguém consome ainda.

**Habitantes sob a regra nova, no espécime gateado.** A tabela é o exemplo trabalhado do critério — repare que dois itens passam por natureza raspando no filtro de uso, e um item **cumpre o filtro folgado e é reprovado mesmo assim**.

| Habitante | Natureza | Filtro (2+ contextos) | Veredito |
|---|---|---|---|
| taxonomia semântica de erro | ubíqua, sem dono | 4 contextos | fica |
| data civil | ubíqua, sem dono | 2 contextos, 6 arquivos | fica |
| dinheiro em centavos | ubíqua, sem dono | 1 arquivo por contexto — raspando | fica |
| `Clock` + implementação de sistema | port de ambiente | todos | fica |
| `Calendar` + fake | port de ambiente | 2 contextos, hoje duplicado | **sobe** (posição 6) |
| fábrica de conexão do banco | infra sem dono | todos os adapters | fica |
| definições de tabela | **tem dono por contexto** | todos | **sai** (posição 7) |
| módulo de migração | infra sem dono | nenhum — 0 chamadores | liga ou apaga (posição 8) |

**DISSENSO.** Vice = manter "2+ contextos usam" como critério único. *Steelman:* é objetivo, greppável e não exige julgamento humano, enquanto "ubíquo sem dono" pede adjudicação caso a caso e convida a disputa. *Perdeu porque:* objetividade que não amarra a garantia é exatamente o que o portão anti-cerimônia corta — e o contrato da posição 6 devolve a objetividade onde ela funciona.

**GATILHO DE REABERTURA.** Disputa recorrente de "tem dono?" ⇒ passa a exigir registro explícito de dono por item do kernel.

---

### 6. Dependência entre contextos — DAG declarado e executado

**REGRA.** Contextos formam um **DAG declarado e executado** por um contrato `layers` no container raiz do pacote.

```toml
[[tool.importlinter.contracts]]
name = "top-level dependency order (composition > edge > contexts > kernel)"
type = "layers"
containers = ["myapp"]
layers = ["main", "composition", "http", "whatsapp", "finance", "identity", "shared"]
```

Três regras acompanham. **(1)** A aresta permitida é a camada `application` do contexto abaixo; nenhum contexto importa `domain` **nem `adapters`** de outro. **(2)** Escape quando a DAG proibir o que é preciso: **o port pertence a quem consome** — o consumidor declara o port na própria `application` e traz o próprio adapter; nunca se inverte a aresta ad hoc, nunca se promove ao kernel algo que tem dono. **(3)** Não re-derivar o que o contexto dono já deriva.

**CONDIÇÃO.** Aplica-se a qualquer pacote com 2+ contextos e um kernel. A ordem entre os contextos é decisão de projeto, mas tem que ser **uma** ordem declarada — a garantia vem de ser total e fixa, não de ser esta.

**GARANTIA.** Um contrato compra quatro coisas que antes não existiam: o kernel não importa contexto (a trava da posição 5), não há ciclo entre contextos, o topo (`main`/`composition`/`http`) fica coberto, e cada aresta cruzada deixa de ser comentário e vira **decisão declarada com direção fixa**. Verificação: `lint-imports` no CI, bloqueante.

**CENÁRIO.** Estado real medido no espécime gateado, antes: duas arestas vivas e não-guardadas, uma delas com um comentário no código dizendo "aceito por ora; não existe contrato de independência entre contextos" — precisamente onde deveria haver invariante. E o contexto `whatsapp` **re-derivava a data esperada de vencimento que o contexto `finance` já deriva**, com a própria docstring admitindo que aquilo deveria ser absorvido pelo dono em vez de redefinido. No outro sentido: sem a regra (2), a primeira necessidade cruzada que a DAG proibir vira uma inversão ad hoc, e o DAG que não é DAG não garante nada.

**Consequência que cai aqui.** Dois contextos do espécime tinham cada um o seu `calendar.py` com **contrato idêntico** — mesmo `Protocol` de um método, mesmo fake com a mesma semântica. Calendário bancário é o mundo, não o domínio do produto: port de ambiente, gêmeo exato do `Clock`. Sobe para o kernel como definição única. Não é "promover porque dois usam" — é natureza, pela posição 5.

**DISSENSO.** Vice = **independência total** entre contextos (aresta zero; tudo que cruza vira port do consumidor, sempre). *Steelman:* é o hexágono puro, dá autonomia real de evolução ao contexto delimitado, elimina o ripple de um tipo de domínio quebrar o consumidor, e o mecanismo já existe — contract test do fake contra o adapter real cobre o adapter duplicado, então duplicar é seguro. *Perdeu porque:* o custo é imediato e concreto (dois adapters lendo a mesma tabela de lar, dois lendo a mesma tabela de conta) contra benefício que só aparece em escala de time; e a DAG executada já elimina os modos de falha reais — ciclo silencioso, kernel inchado, topo livre.

**GATILHO DE REABERTURA.** Um contexto acumular 3+ arestas de entrada, ou uma mudança em `domain` quebrar consumidor de outro contexto duas vezes ⇒ independência total.

---

### 7. Schema — tabelas por contexto, registro no kernel

**REGRA.** O kernel guarda **só o registro vazio** de metadados (`metadata = MetaData()`) — infra sem dono, mesma natureza da fábrica de conexão. As definições de tabela vão para `<ctx>/adapters/tables.py`, uma por contexto dono. Chave estrangeira cruzando contexto usa **referência por string**, resolvida preguiçosamente pelo registro compartilhado — zero import entre contextos.

**CONDIÇÃO.** Vale quando cada tabela tem um contexto dono identificável. Tabela genuinamente transversal e sem dono (outbox, log de auditoria) fica no kernel, pela posição 5.

**GARANTIA.** A decisiva não é arrumação de pastas. Com todas as tabelas no kernel, **qualquer contexto pode importar a tabela de outro e fazer `SELECT` direto** — atravessando o contexto dono inteiro por baixo, com todos os contratos verdes, porque importar o kernel é legal para todo mundo. A fronteira era executável na camada Python e **furada na camada SQL**. Com as tabelas dentro do dono e a regra 6(1) estendida a `adapters`, o bypass vira import ilegal, pego pela máquina. Sem essa extensão, o split não compra nada.

**CENÁRIO.** A favor: no espécime gateado o schema era o **maior habitante do kernel — 283 das 770 linhas** — e cada uma das 7 tabelas tem um contexto dono; pelo critério da posição 5 o arranjo reprovava. Contra, e é um risco real: registro populado por import quebra silenciosamente. Esquecer de importar um módulo de tabelas no `env.py` do Alembic faz o autogenerate propor `DROP TABLE`. **Trava obrigatória:** teste que afirma que o registro contém exatamente os N nomes esperados. Regra portátil: *registro central populado por import exige guarda de completude; sem a guarda, não faça o split.*

**DISSENSO.** Vice = manter o registro de tabelas central. *Steelman:* quando o schema não é emitido por este app — no espécime gateado o DDL é de outra base de código, com migrations próprias — o arquivo é **espelho de um artefato externo único**, com um teste de fidelidade único; espelho de uma coisa só quer ser uma coisa só, e espalhar por três pastas embaralha a comparação. *Perdeu porque:* o que se espelha é a **forma física**, o que se fatia é a **propriedade conceitual**, e a propriedade não muda com quem emite o DDL — o teste de fidelidade continua sendo um só, porque lê o registro, não os arquivos.

**GATILHO DE REABERTURA.** O teste de fidelidade acusar falso-diff por causa do split.

---

### 8. Migração e dono do DDL

**REGRA.** Quatro sub-regras. **(a)** O **dono do DDL é único e declarado**; todo o resto adota — quem não é dono entra por revisão-baseline no-op **mais** teste de fidelidade. **(b)** Migrations moram na **raiz do app, nunca por contexto** — é a exceção explícita à fatia vertical, registrada como exceção para ninguém "consertar" depois. **(c)** **Código de migração sem chamador é proibido**: ou liga ou apaga; ligado, roda no arranque do processo, guardado por advisory lock. **(d)** **Autogenerate propõe, humano dispõe**, e evolução destrutiva se parte em duas releases — aditiva primeiro, remoção depois de o código velho sumir (expand→contract nunca na mesma release).

**CONDIÇÃO.** (a), (b) e (d) são incondicionais. (c) condiciona-se a **deployable único**: migrar no arranque acopla disponibilidade a DDL, o que só é aceitável sem pipeline de job separado e com lock protegendo réplicas concorrentes.

**GARANTIA.** (a) evita o único desastre irrecuperável da categoria: duas ferramentas de migração contra o mesmo banco. (b) é fato da ferramenta, não gosto — a cadeia de revisões é linear e global (um banco, um `head`); fatiar por contexto produz múltiplos heads e merges de revisão para comprar nada. (c) transforma o caminho de migração em **passo observável do arranque**, exercitado a cada deploy. (d) reconhece o que o autogenerate não enxerga: rename, check constraint semântica, e dado.

**CENÁRIO.** O caso (c) foi medido no pior estado possível: a função `migrate_on_boot` existia, era testada, dava sensação de garantia e **tinha 0 chamadores** — o comando do container era só o servidor ASGI. Ligar era barato (advisory lock já implementado) e, enquanto o DDL é de outro dono, `upgrade head` é no-op inofensivo que **exercita o seam** em vez de deixá-lo apodrecer até o dia em que importa. Regra portátil: *caminho de migração não-exercitado não conta como garantia.* No outro sentido, o risco de ligar é nomeável: migração mais lenta que o healthcheck derruba o deploy.

**DISSENSO.** Só (c) teve rival vivo. Vice = apagar o módulo e rodar migração como passo separado do deploy (job ou entrypoint). *Steelman:* separar migração de arranque é a prática de quem tem réplicas e rollback; boot que migra acopla disponibilidade a DDL, e um `upgrade` lento segura o healthcheck. *Perdeu porque:* com deployable único e sem pipeline de job separado, o lock mais o no-op cobrem o risco real, e a alternativa exige infra que não existe. Em **(a), (b) e (d): sem rival — evidência unânime** (um `head` por banco é fato da ferramenta; dois donos de DDL não têm defensor).

**GATILHO DE REABERTURA.** Primeira migração mais lenta que o healthcheck, ou primeiro deploy com 2+ réplicas ⇒ (c) vira passo de deploy.

---

### 9. A façade `application` como superfície pública do contexto

**REGRA.** Entre contextos, a camada `application` é a **superfície pública** do contexto: nenhum contexto alcança `domain` ou `adapters` de outro. **Tipo de domínio pode atravessar** essa superfície — exigir DTO e mapper entre contextos do mesmo deployable, com um dev, é cerimônia. O `__all__` da porta pública é **sinal diagnóstico**: quando a porta incha, a fronteira está no lugar errado — não se conserta alargando a porta.

**CONDIÇÃO.** Vale a partir de 2 contextos. O composition root e os entry-points ficam **fora** das fontes de qualquer contrato de fronteira: conhecer concretos é o trabalho deles, e root que respeita a fronteira é root que não compõe.

**GARANTIA.** A parte incondicional é executável hoje e roda verde: um contrato `forbidden` de **contexto ↛ `domain`/`adapters` de outro contexto**, que generaliza e absorve os `forbidden` pontuais par-a-par.

```toml
[[tool.importlinter.contracts]]
name = "contexts reach each other only through the application layer"
type = "forbidden"
source_modules = ["myapp.whatsapp", "myapp.finance", "myapp.identity", "myapp.http"]
forbidden_modules = [
    "myapp.finance.domain", "myapp.finance.adapters",
    "myapp.identity.domain", "myapp.identity.adapters",
    "myapp.whatsapp.domain", "myapp.whatsapp.adapters",
]
allow_indirect_imports = true
```

**CENÁRIO.** A favor da superfície pública: sem ela, um contexto lê a tabela do outro direto (posição 7) e o dono perde a capacidade de mudar qualquer coisa. Contra o excesso: o modo de falha "mudar um tipo de domínio quebra o consumidor" é real, mas é **barato e pego pelo CI no mesmo commit** — pagar DTO+mapper para evitá-lo é cerimônia com um dev.

**DISSENSO.** Vice = fronteira só por revisão humana, sem contrato. *Steelman:* fronteira mecanizada acopla o design a arquivo de fachada e a convenções do grafo de imports, que mudam com a ferramenta. *Perdeu porque:* a auditoria mediu regra-de-fronteira-em-comentário apodrecendo dentro do próprio código, e o contrato acima custou zero migração — rodou verde no dia em que foi escrito.

**GATILHO DE REABERTURA.** A porta pública de um contexto precisar expor ~15+ nomes para um único consumidor ⇒ reabre junto com a fronteira daquele contexto.

#### Colisão aberta — a façade cross-contexto

**(a) O que este eixo decidiu, e com que experimento.** A posição original ia além do contrato acima: transformava a **façade** `application` em contrato executável, proibindo também o import profundo de submódulos com `forbidden_modules = ["myapp.finance.application.*", ...]`, de modo que só `from myapp.finance.application import X` fosse legal. O comportamento foi verificado por experimento contra a versão pinada do import-linter (2.13), com um pacote de brinquedo: `pkg/a/__init__.py` reexportando `pkg.a.inner`; o wildcard **pegou** o import profundo (`pkg.c -> pkg.a.inner`, contrato BROKEN) e **liberou** a façade (`pkg.b -> pkg.a`, zero cadeias ilegais). Conclusão do experimento: "só pela façade" é executável, não aspiracional.

**(b) O que a medição posterior, no código real, mostrou.** O eixo de régua de qualidade mediu a façade no espécime gateado e encontrou o oposto: `from myapp.finance.application import record_payment` é resolvido pelo grafo do import-linter **como import do módulo `finance.application.record_payment`** — porque a convenção do padrão é "módulo com o nome do seu símbolo principal". Sob essa convenção, **o import pela façade e o import profundo são indistinguíveis para a máquina**. O mesmo eixo matou a façade de camada por dois fatos medidos: 92% dos imports do repositório já vão ao módulo dono (40 imports por façade contra 457 diretos) e havia 1010 linhas de `__init__.py` mantidas à mão.

**(c) Por que as duas medições não se contradizem.** No pacote de brinquedo, o símbolo re-exportado **não tinha nome de módulo** — a façade expunha um nome que não correspondia a nenhum submódulo, então o grafo distinguia `pkg.a` de `pkg.a.inner`. No código real, **tem**: cada módulo de `application/` se chama como o seu símbolo principal, exatamente a convenção "estrutura por conceito" que este padrão adota e mantém. Os dois experimentos mediram a mesma ferramenta em duas topologias de nome diferentes, e ambos estão certos.

**(d) A consequência.** Se **todo** módulo de `application/` tem nome de símbolo, o contrato `forbidden ...application.*` **barra também a façade** — ele não implementa "só pela façade", implementa "não fale com a camada `application` do outro contexto", que não é o que se quis.

**(e) O terceiro experimento, que dá saída.** A pergunta "existe forma de porta pública que a máquina distinga do import profundo?" é alegação de comportamento, e a régua manda medir. Um pacote de brinquedo com os quatro casos lado a lado, sob import-linter 2.13, com o contrato `forbidden_modules = ["pkg.a.application.*"]` e `allow_indirect_imports = True`:

| Como o consumidor importa | Veredito do contrato |
|---|---|
| `from pkg.a.application import record_payment` — símbolo **com** nome de módulo | **BROKEN** (`pkg.b.consumer -> pkg.a.application.record_payment`) |
| `from pkg.a.application import Thing` — símbolo **sem** nome de módulo | KEPT |
| `from pkg.a.public import record_payment` — porta pública num **módulo**, não no `__init__` do pacote | **KEPT** |
| `from pkg.a.application.record_payment import record_payment` — controle, import profundo | **BROKEN** |

O resultado é decisivo nos dois sentidos: confirma que a façade em `application/__init__.py` é indistinguível do import profundo sob a convenção de nomes deste padrão, **e** mostra que "só pela porta pública" volta a ser executável quando a porta é um **módulo** cujo nome não pode colidir com um submódulo do pacote proibido. A linha de controle prova que o contrato continua mordendo o import profundo na mesma configuração — a porta não abre um buraco.

**(f) O que fica pendente.** Restam duas saídas, e a escolha entre elas **é adjudicação do dono do padrão, não deste documento**: (i) a fatia de contexto expõe a superfície pública num módulo de nome não-colidente — `<ctx>/public.py` ou equivalente —, tornando "só pela porta" executável de fato, ao custo de mudar a forma de todo contexto; ou (ii) o contrato **relaxa** para "contexto ↛ `domain`/`adapters` de outro contexto" — a forma mostrada no bloco acima, que **roda verde hoje com zero migração**, ao custo de deixar o import profundo dentro de `application` alheia tecnicamente legal.

Enquanto a adjudicação não vem, vale a saída (ii) — é a que existe em código e passa. O resto da posição 9 sobrevive intacto às três medições: o `__all__` da porta pública como sinal diagnóstico de fronteira mal colocada, e tipo de domínio podendo atravessar.

---

### 10. O topo do pacote

**REGRA.** A raiz do pacote é o **topo de composição, e só isso**: `settings.py` (ponto único de leitura de ambiente, alvo da trava de lint que bane acesso direto a variável de ambiente no resto do código), `composition.py` (os provedores tipados que traduzem `Settings` em adapter concreto, compartilhados por todos os entry-points) e **um módulo por entry-point** — `main.py` para o ASGI, `jobs/<nome>.py` para cada processo agendado. Cada entry-point faz a **sua** montagem final. Nada de domínio, nada de rota na raiz — endpoint transversal desce para o pacote HTTP central.

**CONDIÇÃO.** Universal. A forma de pasta é que é condicional: com um entry-point, módulo; com dois ou mais, pacote `jobs/`.

**GARANTIA.** *Quem sabe de concreto mora aqui; o resto do pacote não sabe que "aqui" existe.* Isso já é executado pelo contrato da posição 6, onde `main` e `composition` são as camadas de cima — nenhum contexto pode importá-los. Com um segundo entry-point, a lista de camadas vira `[["main", "jobs"], "composition", "http", ...]`: irmãos independentes no mesmo nível, e o contrato passa a proibir também que um entry-point importe o outro.

**CENÁRIO.** A favor de manter tudo na raiz enquanto há um entry-point: pasta `entrypoints/` com um arquivo dentro comunica estrutura que não existe, e promover depois é um `git mv`. Contra: quando o segundo entry-point nasce e não há lugar declarado para ele, ele tende a nascer pendurado no `main.py` do primeiro — e aí o processo agendado carrega a aplicação HTTP inteira sem precisar.

**DISSENSO.** Vice = pacote `entrypoints/` (ou `bootstrap/`) desde já. *Steelman:* é o que o cânone Python de arquitetura em camadas separa explicitamente, e um projeto que **sabe** que terá um segundo entry-point está adiando trabalho conhecido. *Perdeu porque:* com um entry-point é pasta de um arquivo, e a diferença entre os dois estados é um `git mv` — o custo de adiar é zero e o custo de antecipar é comunicar estrutura falsa.

**GATILHO DE REABERTURA.** Terceiro entry-point, ou `jobs/` com 2+ jobs.

---

## As travas de máquina que este eixo produz

1. **Contrato `layers` no container raiz** (posição 6) — kernel não importa contexto, sem ciclo entre contextos, topo coberto, cada aresta cruzada declarada com direção fixa em vez de comentada.
2. **Contrato `forbidden` de fronteira entre contextos** (posição 9) — nenhum contexto alcança `domain`/`adapters` de outro; generaliza e substitui os `forbidden` pontuais par-a-par. A variante mais estrita ("só pela façade") está pendente da colisão registrada acima.
3. **Contrato `layers` por contexto** (posição 3) — `domain` < `application` < `adapters`. Sem ele, a posição 3 não se sustenta e não deve ser adotada.
4. **Teste de completude do registro de metadados** (posição 7) — o registro contém exatamente as N tabelas esperadas. Pré-condição para fatiar o schema por contexto.

## Ordem de adoção num projeto novo

A ordem importa porque cada passo é pré-condição do seguinte, e porque adotar a forma antes da trava produz o espécime sem trava.

1. **Instale a trava antes da forma** — import-linter no CI, bloqueante, com um contrato qualquer que já passe. Sem isso, as posições 3, 6, 7 e 9 não têm garantia e não devem ser adotadas.
2. **Corte o topo por contexto** (posição 1) e declare a DAG (posição 6) — mesmo com dois contextos, mesmo que a ordem pareça óbvia.
3. **Decida as camadas pelo quadrante** da posição 3, contexto a contexto; contextos diferentes podem ficar em formas diferentes, e isso é a regra, não exceção.
4. **Sub-estruture `application/` só quando doer** (posição 2): `ports/` desde o início, `use_cases/` desde o início, `projections/` quando houver o que pôr dentro.
5. **Ponha a borda dentro do contexto desde o primeiro endpoint** (posição 4) — é a decisão mais barata de tomar cedo e mais cara de reverter depois.
6. **Fatie o schema só depois da guarda de completude** (posição 7), e só se as tabelas tiverem dono.
7. **Declare o dono do DDL por escrito** (posição 8a) antes da primeira migration, e ligue o caminho de migração (8c) no mesmo dia em que ele nascer.

## Três regras portáteis, destacadas

- *Registro central populado por import exige guarda de completude; sem a guarda, não faça o split.* (posição 7)
- *Caminho de migração não-exercitado não conta como garantia — migração é passo observável do arranque, guardado por lock.* (posição 8)
- *A raiz do pacote hospeda config, provedores e entry-points; quem sabe de concreto mora lá, e o resto do pacote não sabe que "lá" existe.* (posição 10)

## Nota de método

Duas coisas neste eixo valem mais que as posições em si. **Primeira:** a régua de admissão do kernel do próprio espécime gateado ("2+ contextos usam") foi **reprovada pelo teste do espécime sem trava** e substituída — a referência auditando a si mesma em vez de canonizar o que já praticava. **Segunda:** o único claim de comportamento de ferramenta do lote (semântica do wildcard no `forbidden`) foi decidido por experimento contra a versão pinada, não por leitura de documentação — e foi justamente esse claim que uma medição posterior no código real complicou, o que é o argumento mais forte possível a favor de medir em vez de assumir.
