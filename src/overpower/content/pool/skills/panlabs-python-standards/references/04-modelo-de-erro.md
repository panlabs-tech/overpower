# Modelo de erro — que forma o insucesso tem e onde ele se traduz

Duas perguntas, e só duas: **que forma** um insucesso assume quando sai de uma função (`None`? um objeto de resultado? uma exceção?) e **onde** essa forma vira a resposta que o mundo externo vê (status HTTP, mensagem de bot, linha de log). Tudo o mais neste eixo — hierarquia de exceções, `Raises:`, catch-all, formato do payload de erro — é consequência dessas duas.

> Régua: toda posição abaixo passou pelo portão anti-cerimônia — cenário nomeado nos dois sentidos, garantia verificável, autoridade não preenche.

**Espécimes citados neste arquivo.** *O espécime gateado*: o backend `apps/api` do projeto LUC — Python 3.14 / FastAPI, com pyright strict e import-linter travando o merge, ~600 testes, e duas bordas vivas (uma HTTP e um bot de WhatsApp). *O espécime sem trava*: `b3stocks` — Lambdas, sem type-checker no caminho do merge. *O radar de produção*: seis backends Python reais de produção lidos no código (FastAPI síncrono e assíncrono, Pyramid, Django/DRF), escolhidos diversos de propósito pra separar sinal de idiossincrasia de framework.

---

## A tese que reorganiza o eixo

A pergunta natural é "que forma de erro cada camada usa" — erro no domínio, erro no use-case, erro no adapter. **Esse recorte foi rejeitado no mérito**, não respondido.

A forma do insucesso **não é escolhida pela camada**. É escolhida pela **relação com o chamador imediato**: quantos modos de falha existem, se o modo é esperado no caminho normal, e se o chamador se comporta diferente por causa dele. Uma função de domínio e um método de repositório com a mesma relação com quem os chama têm a mesma forma de erro; duas funções da mesma camada com relações diferentes têm formas diferentes. A camada decide uma coisa só, e é uma coisa **ortogonal** à forma: **onde se traduz** — uma vez, na borda.

O teste que expõe o recorte errado é este: dois métodos do **mesmo** repositório, na mesma camada, com formas legitimamente diferentes.

```python
class BillRepo(Protocol):
    def find(self, bill_id: UUID) -> Bill | None: ...          # ausência é caminho normal
    def close(self, bill: Bill, expected_version: int) -> Bill | None: ...  # perdeu o CAS é caminho normal
    def append_event(self, event: BillEvent) -> None: ...      # colidir aqui é bug: levanta
```

Nenhuma regra por camada explica isso. A regra por relação com o chamador explica em uma frase: nos dois primeiros o chamador **ramifica normalmente** no insucesso; no terceiro, não há ramo — só há bug.

Por isso este arquivo não tem seção "erro no domínio / no use-case / no adapter". Tem uma **escada** (a forma, por relação com o chamador) e um **dispositivo** (o que faz a escada valer alguma coisa).

Registre o movimento, porque ele se repete: **a régua permite recusar o recorte da pergunta, não só a resposta.** Quando a evidência insiste em agrupar os casos por um eixo diferente do que o enunciado propôs, reescreva o eixo — responder no recorte errado produz uma tabela que ninguém consegue aplicar.

---

## O dispositivo de 4 peças

Não são quatro boas práticas somáveis. É **um mecanismo**: cada peça tampa o furo que a anterior deixa. **Removida qualquer uma, as outras três viram ritual** — cumpríveis a 100% com a garantia falhando mesmo assim, que é exatamente o modo de falha do espécime sem trava (ports como `abc.ABC` em 10/10 dos casos, e os bugs passando, porque a garantia prometida não tinha check que a fizesse cumprir).

### Peça 1 — exceção semântica primária, sob registro único

O primário é **exceção nomeada**, semanticamente categorizada, sob um **registro único** de categorias que a borda consome com resolução por MRO — o handler central procura a superclasse mais próxima, e não uma lista de tipos concretos.

```python
# kernel: a taxonomia, e só ela
class NotFoundError(Exception): ...
class ConflictError(Exception): ...
class ValidationError(Exception): ...

# borda: o registro único, por categoria — não por tipo concreto
_CATEGORY_STATUS: Final[tuple[tuple[type[Exception], int], ...]] = (
    (NotFoundError, 404),
    (ConflictError, 409),
    (ValidationError, 422),
    (AuthenticationError, 401),  # não herda de erro de domínio; está no registro (regra (d))
)

def _status_for(exc: Exception) -> int | None:
    return next((s for cls, s in _CATEGORY_STATUS if isinstance(exc, cls)), None)
```

A propriedade que importa: um erro **novo** de contexto — `DuplicateProposalError(ConflictError)` — passa a ser servido corretamente **sem tocar na borda**. Corolário afiado: um erro concreto que herda de `Exception` puro em vez de uma categoria não é "não mapeado ainda"; é um **500 silencioso** onde deveria haver 409. Foi exatamente o que a auditoria do espécime gateado encontrou.

*O furo que ela deixa:* **pyright strict dá zero garantia sobre exceções.** Python não tem checked exceptions; a exceção é **invisível ao tipo de retorno**. O contrato de falha vive só no docstring, e docstring não trava merge. Uma função pode passar a levantar um tipo novo e nenhum call-site quebra.

### Peça 2 — catch-all de `Exception` na borda

A borda captura `Exception` — nunca `BaseException`, porque `SystemExit`, `KeyboardInterrupt` e `GeneratorExit` herdam dele **de propósito**, justamente pra atravessarem um `except` genérico — e devolve o erro genérico do contrato: no HTTP, um `problem+json` 500. A mensagem original **nunca** entra no corpo da resposta; vai pro log.

```python
@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception) -> Response:
    logger.error("unhandled error at %s", request.url.path, exc_info=exc)
    return problem(status=500, title="Internal Server Error",
                   detail="An unexpected error occurred.")  # nada de str(exc) aqui
```

E existe **teste** de que uma exceção desconhecida sai no formato do contrato — o teste é a peça, não o handler. Um handler de catch-all sem teste é indistinguível de um handler que o framework nunca chama (ordem de registro, middleware que captura antes, exceção levantada durante a serialização da resposta): três modos de falha reais que só o teste de ponta a ponta separa.

*Tampa o furo de (1):* nenhuma resposta escapa do contrato, ainda que a exceção seja de um tipo que ninguém previu. No espécime gateado o buraco era literal e medido: `ClientError` do cliente de object storage, `ValueError` de linha corrompida no parse de um repositório, `IntegrityError` de índice não mapeado e `RuntimeError` saíam como **500 `text/plain`** — fora do contrato, sem nenhum teste cobrindo — enquanto o erro de domínio *sem mapeamento* recebia tratamento explícito e cuidadoso. Ou seja: o caminho previsto era cuidado, o imprevisto era o que vazava.

*O furo que ela deixa:* garante a **resposta**, não o **conhecimento**. O consumidor a montante continua sem saber o que existe pra capturar.

### Peça 3 — `Raises:` travado por máquina

O docstring do **contrato publicado** (ports e use-cases) declara seção `Raises:`, e isso é **verificado por lint** — `DOC501` (raise não documentado) e `DOC502` (documentado e não levantado), via as regras de docstring do ruff, que hoje são **preview**:

```toml
[tool.ruff]
preview = true

[tool.ruff.lint]
explicit-preview-rules = true
extend-select = ["DOC501", "DOC502", "BLE"]

[tool.ruff.lint.per-file-ignores]
# interior do contexto: dispensado — a trava vale no contrato publicado
"src/**/infrastructure/*.py" = ["DOC501", "DOC502"]
```

A seção declara o **quando**, não só o tipo — é o que separa contrato de repetição do nome da classe:

```python
def close_bill(self, bill_id: UUID, *, closed_at: date) -> Bill:
    """Close a bill and stamp the closing date.

    Raises:
        BillNotFoundError: no bill with this id in the caller's tenant scope.
        BillAlreadyClosedError: the bill was closed by a concurrent request.
    """
```

*Tampa o furo de (2):* é o que torna **operável** a regra de tradução-por-consumidor. "Traduza só onde alguém decide diferente" pressupõe que esse alguém **saiba o que há pra capturar** — sem `Raises:` travado, a regra é um convite a adivinhar. No espécime gateado, antes do retrofit, havia `Raises:` em **5** lugares (4 deles no mesmo par de arquivos de um único contexto) contra ~20 sítios de `raise` no contrato publicado.

*O furo que ela deixa:* a trava é **parcial**, e isso foi verificado por experimento contra a versão pinada do ruff — **`DOC501` dispara no `raise` direto e não dispara na função que apenas propaga**. Quem só deixa a exceção passar não é cobrado. Declare o limite em vez de fingir cobertura total: a peça cobre a origem, não a cadeia.

### Peça 4 — `BLE` com `# noqa` auditável

`BLE001` (captura larga de `Exception`) fica **ligado**, e toda captura larga legítima carrega `# noqa: BLE001`. O `noqa` só é aceitável com **desfecho nomeado**: a captura **registra** (`logger` com `exc_info`) **e decide algo** — compensa um efeito parcial, degrada com um fallback nomeado, ou acumula a falha como dado (um campo tipo `ImportResult.attachment_failures`). Nunca `pass`. Nunca `except:` nu.

```python
try:
    store.delete(key)
except Exception:  # noqa: BLE001 — compensação: o fato já foi criado, o órfão vira dado
    logger.error("compensation failed for key=%s", key, exc_info=True)
    result.orphaned_keys.append(key)
```

*Tampa o furo de (3) e fecha o arco:* um `except Exception` mal colocado engole o erro nomeado que a regra de tradução mandou propagar, apaga o contrato que a peça 3 travou e **impede que a exceção chegue ao catch-all** da peça 2. É o único ponto do desenho onde as três outras peças podem ser desligadas em silêncio.

*O `noqa` é o instrumento, não a dívida.* Ele torna o escape **contável**: `grep -c` vira o orçamento de cerimônia em forma executável. No espécime gateado a medição deu **exatamente 6 sítios** de `BLE001`, **zero** `except BaseException` e **zero** `except:` nu — e os 6 são todos legítimos. A regra não existe pra chegar a zero; existe pra que o número seja **conhecido** e cada item tenha desfecho nomeado. Uma regra que mirasse zero estaria proibindo compensação, que é minimalismo-por-esporte — a mesma cerimônia, com o sinal trocado.

---

## A escada

**Um eixo só:** quanta informação o insucesso carrega, e **quem decide** sobre ela.

| Rung | Predicado | Forma |
|---|---|---|
| 1 | esperado no caminho normal ∧ **modo único** ∧ sem payload | `X \| None` — ou `bool` quando não há valor a devolver |
| 2 | esperado ∧ plural/estruturado ∧ **o chamador quer o veredito sem o efeito** | união discriminada, consumida por `isinstance` |
| 3 | tudo o mais | exceção nomeada |

```python
# rung 1 — modo único, esperado, sem payload
def find(self, bill_id: UUID) -> Bill | None: ...
def revoke(self, token: str) -> bool: ...        # nada a devolver: só deu ou não deu

# rung 2 — plural e estruturado, e existe quem queira o veredito sem o efeito
type BillValidation = Valid[Bill] | Invalid
match repo_validate(payload):
    case Invalid(errors=errors): show_inline(errors)   # o menu só quer saber, não cometer
    case Valid(value=bill): commit(bill)

# rung 3 — tudo o mais
raise BillAlreadyClosedError(bill_id)
```

**Gatilho de promoção embutido na escada.** No instante em que aparece um **segundo modo de falha sobre o qual o chamador decide diferente**, a forma sobe: pra exceção nomeada, ou — se ambos os desfechos forem esperados e o chamador ramifica entre eles — pra um `Literal[...]` de desfechos nomeados, que é a rung 1 esticada sem virar hierarquia de exceção:

```python
@dataclass(frozen=True)
class DigestSendResult:
    status: Literal["no-household", "nothing-to-send", "sent"]
    sent_count: int = 0
```

O gatilho é o que impede a rung 1 de virar desculpa: um `bool` que precisa responder "não achei" **e** "achei mas não pude" já está mentindo, e o `Literal` custa três linhas.

**O fato de typing que sustenta a rung 1, contra a intuição.** `X | None` é a **única forma do modelo que o pyright strict realmente força**: `is not None` narrowa trivialmente, e o call-site que esquece de checar **quebra o gate**. A exceção é invisível ao tipo de retorno — não há checked exceptions, e o checker jamais cobra o tratamento. A união com tag booleana **não narrowa nada**, e isso foi medido, não suposto:

```python
r: Valid[int] | Invalid = validate(x)

if r.ok:
    r.value        # ERRO sob pyright strict: r segue Valid[int] | Invalid
if r.ok is True:
    r.value        # ok — `is True` narrowa
if isinstance(r, Valid):
    r.value        # ok — isinstance narrowa
```

Consequência prática dupla. Primeira: a tag `ok` é **campo morto** quando todo consumidor já usa `isinstance` — e usa, porque é a única coisa que funciona; um campo que existe pra ser lido e que ninguém pode ler é cerimônia paga em manutenção. Segunda, e contraintuitiva: **o `None` é a forma mais garantida do repositório, não a mais frouxa.** A ordem de garantia estática, do mais forte pro mais fraco, é `X | None` → união por `isinstance` → exceção — exatamente o inverso da ordem de "sofisticação" aparente. (`TypeGuard` narrowa só o ramo positivo; `TypeIs`, da stdlib recente, narrowa os dois — vale quando o predicado precisa ser função.)

Isso vindica a decisão de repositório que parece frouxa e não é: *um `RETURNING` vazio significa que o repo perdeu a corrida — nunca uma exceção*. Sob concorrência, perder o CAS é caminho **normal**, e o tipo `Row | None` obriga o chamador a encarar isso.

**A rung 2 tem um quarto teste, porque os três primeiros não bastam.** A exceção nomeada **já pode carregar a lista plural** (um `InvalidBillError.errors`), então "preciso devolver 5 erros de validação de uma vez" **não** justifica o objeto de resultado. O que justifica é um chamador que quer o **veredito sem executar o efeito**: um menu de edição conversacional validando o campo digitado sem cometer nada; um importador em lote acumulando linhas inválidas **como dado** e seguindo. Sem esse consumidor, corta — a rung 2 sem consumidor de veredito-sem-efeito é um tipo, um alias por agregado, um `isinstance` por call-site e um campo morto, comprando nada.

**Consequência declarada, pra a escada não virar catálogo.** Aplicado ao espécime gateado, o predicado da rung 2 **cortou** o par `Valid`/`Invalid` de um contexto inteiro: os seis consumidores traduziam o `Invalid` imediatamente pra exceção, nenhum queria o veredito sem o efeito. A rung sobrevive **na skill** porque tem predicado de entrada nomeado e cenário previsto; sobrevive **num projeto** só quando o consumidor aparecer.

---

## Regras condicionais portáveis

Quatro regras, cada uma com o seu **quando** — é o que faz elas portarem entre projetos heterogêneos em vez de virarem doutrina de um projeto só. Uma regra sem predicado ou vira dogma no projeto seguinte, ou é descartada na primeira fricção.

**(a) Tradução por consumidor.** *Traduza um erro de infraestrutura num erro nomeado do port quando — e só quando — existir código a montante que se comporta diferente por causa dele; caso contrário, deixe-o chegar à rede de segurança (peça 2).* Traduzir um `IntegrityError` de índice único em `DuplicateProposalError` se paga porque há chamador que ramifica nesse caso. Traduzir o `ClientError` do object storage não se paga se ninguém a montante decide nada com ele — ele vira 500 genérico no catch-all, e está certo. Regra tem custo declarado: a garantia "nenhum tipo de terceiro atravessa o núcleo" **não** é verificável por máquina (o import-linter barra o *import*, não a exceção que atravessa em runtime), então esta regra é deliberadamente mais fraca que a versão total, e sabe disso.

```python
# traduza: identity e o bot ramificam neste caso
except IntegrityError as exc:
    if _violates(exc, "uq_proposal_open_per_sender"):
        raise DuplicateProposalError(sender_id) from exc
    raise
# não traduza: ninguém a montante decide nada sobre falha do object storage
store.put(key, blob)   # ClientError sobe; a peça 2 responde 500 no contrato
```

**(b) Status acoplado ao erro *se e somente se* borda única HTTP.** *Acople o status HTTP ao erro de domínio quando a aplicação tem exatamente uma borda e ela é HTTP; separe categoria semântica de status quando existem duas ou mais bordas heterogêneas.* O custo da indireção (uma tabela categoria→status na borda, e a chance de esquecer de mapear uma categoria nova) só se paga com a segunda borda. **6/6** dos backends do radar de produção carregam o status HTTP no erro de domínio — consenso praticamente universal, portanto **dispositivo**, não informativo. E todos os seis são de **borda única, toda HTTP**. O espécime gateado tem uma segunda borda **viva** e não-HTTP, onde o erro vira mensagem de chat e um `404` embutido seria lixo carregado por toda a hierarquia. Daí a condicional: um projeto de borda única (como o espécime sem trava, todo Lambda/HTTP) **deve** acoplar; um projeto com segunda borda não-HTTP não deve.

**(c) O erro mora com o contrato que o produz.** Exceção de port, no módulo do port. Exceção de use-case, no módulo do use-case. Invariante de domínio, no módulo do conceito. Um `errors.py` de kernel compartilhado é **só** a taxonomia de categorias — nunca depósito de tipos concretos. É "estrutura por conceito de domínio, nunca por tipo de artefato" levado ao erro: quem lê o port vê, no mesmo arquivo, tudo o que ele promete, inclusive o que ele quebra.

**(d) O invariante não é "raiz única", é "registro único".** Não exija que toda exceção herde de uma raiz comum — exija que toda exceção que **a borda distingue** esteja numa **tabela explícita** de categorias. A diferença importa: um `AuthenticationError` **não** deve herdar de `DomainError` (autenticação é protocolo de borda, não conceito de domínio), mas **deve** estar no registro. A formulação por registro dissolve a tensão sem forçar herança falsa; a formulação por raiz obriga a mentir na hierarquia ou a manter um caso especial fora do handler central.

---

## O que a borda promete

Este é o contrato que o dispositivo torna cumprível. Vale para a borda HTTP; uma segunda borda promete outra coisa, na sua própria linguagem, a partir das **mesmas** categorias.

```json
{
  "type": "about:blank",
  "title": "Unprocessable Entity",
  "status": 422,
  "detail": "The bill could not be created.",
  "errors": [
    { "field": "dueDate", "code": "invalid_format" },
    { "field": "amountCents", "code": "out_of_range" }
  ]
}
```


- **Toda resposta de erro é `application/problem+json` (RFC 9457), sem exceção.** É o catch-all da peça 2 que faz o "sem exceção" ser verdade — sem ele, a frase é aspiracional.
- **Payload estruturado viaja na extensão `errors` (§3.2 da RFC); `detail` é uma frase, nunca a lista.** Este é o ponto mais fácil de prometer no docstring e quebrar no código: no espécime gateado, o serializador de erro de domínio guardava só o `str(exc)` e **descartava silenciosamente** o `.errors` das exceções de validação, enquanto o docstring do módulo prometia o contrário. Teste o corpo, não o status.
- **`FieldError(field, code)`.** `field` em **camelCase**, mantido como contrato de ponta a ponta (a representação *é* o contrato; é o mesmo critério que autoriza um primitivo no lugar de um value object quando a representação atravessa todas as camadas inalterada). `code` de **vocabulário fechado e pequeno** — `required`, `invalid_format`, `out_of_range`, … A copy de produto, em qualquer idioma humano, mora em quem fala com a pessoa.
- **`detail` em inglês**, voltado ao **consumidor da API** (tipicamente o próprio BFF), não à pessoa final. Quem escreve na língua da pessoa é a borda de UI. É o corolário direto de "o código do backend é integralmente em inglês; copy de produto é emitida pela borda".
- **Conjunto de categorias fechado**, e ampliá-lo é ato deliberado no kernel: `NotFound` / `Conflict` / `Validation` / `InvalidInput`, mais autenticação, mais o genérico do catch-all.
- **403 fica deliberadamente de fora.** O escopo por tenant colapsa "existe, mas não é seu" em **não-encontrado**, de propósito, pra não vazar existência entre tenants. É decisão de domínio tomada, não lacuna da tabela — e é por isso que ela aparece **escrita** aqui: uma categoria ausente sem justificativa vira, meses depois, alguém "consertando o buraco" e abrindo um canal de enumeração. Escreva a ausência deliberada com o mesmo cuidado com que escreve a presença.

Nota de conformidade que economiza uma tarde: a RFC **9457** obsoleta a 7807, mantendo o media type `application/problem+json` e o modelo de extensões. Uma implementação conformante à 9457 é trivialmente compatível com clientes de 7807 — o que costuma estar desatualizado é a **referência no docstring**, não o código.

---

## Dissenso

Cada posição acima teve rival vivo. Abaixo, a vice-campeã, o steelman honesto dela, por que perdeu, e o gatilho concreto que a ressuscita.

**Espinha exceção-primária.** *Vice:* objeto de resultado como primário no núcleo (railway-oriented programming). *Steelman:* a falha entra no tipo de retorno e o checker **obriga** a tratá-la — é a única forma que dá garantia estática de verdade, e é a que a comunidade funcional defende com mais rigor. *Perdeu porque:* medida, a ergonomia não traduz pro Python — `if r.ok:` **não narrowa** sob pyright strict nas versões pinadas; a biblioteca de resultado madura vaza `KindN[...]` (`reportUnknownMemberType`) e o `match Success/Failure` acusa `reportMatchNotExhaustive`; sem exaustividade real de união, paga-se a cerimônia inteira sem levar a garantia. A tag `ok` morta encontrada no espécime gateado é a prova local. O próprio autor do padrão, em "Against Railway-Oriented Programming", recomenda o híbrido: resultado só pra erro de domínio esperado, exceção pra infra, `None` pra ausência. *Gatilho:* Python/pyright ganharem narrowing por tag **ou** exaustividade real de união; ou a biblioteca de resultado passar limpa sob strict.

**Tradução por consumidor.** *Vice:* contrato de tradução total — nenhum tipo de terceiro chega ao núcleo, ponto. *Steelman:* é o único desenho que preserva a dependência-pra-dentro do hexágono **também para o erro**, que é o furo clássico de arquitetura limpa e que quase toda base ignora sem perceber. *Perdeu porque:* a garantia **não é verificável por máquina** — nem pyright nem import-linter provam que nenhum `ClientError` escapa; o import-linter barra o import, não a exceção que atravessa em runtime. Regra sem trava é ritual. *Gatilho:* aparecer trava que verifique a fronteira em runtime, ou um incidente concreto em que erro de infra não traduzido custe caro.

**`None`/`bool` como sinal (rung 1).** *Vice:* purista semântico — `None` significa só ausência, e todo insucesso é exceção. *Steelman:* um significado por forma, leitura local sem ambiguidade, e "perdeu o CAS" ganha nome próprio em vez de um `None` mudo que o leitor precisa decodificar pelo contexto. *Perdeu porque:* transforma fluxo **normal e esperado** em exceção (perder a corrida é o caso comum sob concorrência), e troca a **única** forma checada por máquina pela única invisível ao tipo — o custo é pago exatamente na direção errada. *Gatilho:* um `None` mudo causar bug real de interpretação; e aí o caso sobe pra `Literal[...]` de desfechos nomeados, **não** pra exceção.

**Rung 2 (objeto de resultado) mantida com quarto teste.** *Vice:* cortar a forma inteira — `validate_*` levanta direto, com a lista dentro da exceção. *Steelman, o mais forte da grelha:* não há **nenhuma** garantia estática que o resultado entregue e a exceção não; nos dois desenhos, a função ou devolve o dado bom ou não devolve. O resultado custa um tipo, um alias por agregado, um `isinstance` por call-site e um campo morto — e o que compra, medido no espécime gateado, foi zero. *Perdeu por pouco porque:* a rung nomeada **com predicado de entrada** custa uma frase e evita que a forma volte sem critério (que é como ela entrou na primeira vez), e existe cenário previsto no escopo — veredito-sem-efeito em edição conversacional, importador acumulando inválidas como dado. *Gatilho:* nenhum consumidor de veredito-sem-efeito aparecer na prática; aí a rung sai da skill, não só do projeto.

**Categoria semântica × status no erro.** *Vice:* o erro de domínio carrega o status HTTP. *Steelman:* **6/6** das codebases de produção estudadas fazem assim — consenso praticamente universal, que a régua trata como dispositivo; some uma indireção e fica impossível "esquecer de mapear" uma categoria nova. *Perdeu porque:* os seis espécimes são todos de borda única HTTP, e o espécime gateado tem uma segunda borda não-HTTP viva, onde o status embutido é peso morto. **Não foi descartado** — virou o **antecedente** da regra condicional (b), que manda acoplar em projeto de borda única. *Gatilho:* o projeto colapsar pra borda única, ou a segunda borda passar a ser HTTP também.

**`FieldError(field, code)`.** *Vice:* copy de produto (pt-BR) dentro do erro, como `message`. *Steelman:* fonte única — quem sabe *por que* reprovou é a validação, e um `code` sem dicionário é inútil pro cliente; o dicionário é uma tabela nova que hoje não existe em lugar nenhum e alguém vai ter que manter. *Perdeu porque:* viola a regra de inglês integral no código do backend (copy só emitida pela borda) **e** foi demonstrado insuficiente na prática — a segunda borda do espécime gateado captura a exceção de validação, **ignora** o `.errors` e escreve as próprias mensagens. A segunda borda já votou com os pés. Sintoma correlato: um `field` escrito `"arquivo"` em pt-BR provava que o vocabulário já estava incoerente. *Gatilho:* o vocabulário de `code` crescer até espelhar 1:1 cada frase — um code por mensagem é tabela de tradução com nome de enum, e aí a posição colapsa de volta pra `message`.

**Onde mora o tipo.** *Vice:* um `errors.py` por contexto, concentrando a taxonomia local. *Steelman:* um lugar só pra ver a taxonomia inteira do contexto, e "módulos por papel" (`errors.py`, `events.py`) é explicitamente permitido pela regra de estrutura. *Perdeu porque:* o benefício seria de quem mantém o mapeamento da borda — mas a borda **não enumera** exceção por contexto: resolve por MRO sobre categorias. Sem consumidor, a concentração reprova no teste de liveness. *Gatilho:* surgir consumidor que precise enumerar os erros de um contexto — geração de documentação de API por contexto, por exemplo.

**`Raises:` travado.** *Vice:* prosa livre no docstring (o estado anterior). *Steelman:* a prosa costuma comunicar **melhor** que uma seção seca, porque explica o *quando*; seção obrigatória tende a degenerar em `Raises: BillNotFoundError: se não encontrar` — ruído que repete o nome do tipo e não acrescenta nada. *Perdeu porque:* reprova no teste do espécime sem trava de forma exemplar — lá os ports são `abc.ABC` em 10/10 e os bugs passam justamente porque a garantia prometida não tinha check; "documente suas exceções" sem verificação é o mesmo dispositivo com o mesmo desfecho. *Gatilho:* o ruff estabilizar as regras `DOC` mudando a semântica, **ou** a prática mostrar que a maioria das seções virou repetição vazia do nome do tipo — aí o steelman ganha e a peça 3 volta pra mesa.

**`BLE` auditável.** *Vice:* captura larga livre, sem lint. *Steelman:* os sítios existentes são todos bons, e uma regra que precisa de seis `# noqa` logo de cara é regra errada — "auditabilidade" vira ruído de lint fingindo governança. *Perdeu porque:* sem a trava, "compensação deliberada" e "engoli porque estava com pressa" ficam **indistinguíveis na revisão de código**, e o custo aparece meses depois como falha silenciosa em produção. O `noqa` não é dívida: é o contador. *Gatilho:* a contagem de `noqa` crescer com sítios **sem** desfecho nomeado — mas aí o eixo que reabre é o de concorrência e compensação, não este.

---

## Nota de método

O achado empírico mais forte deste eixo apontava **contra** o desenho adotado: 6/6 dos backends de produção estudados carregam o status HTTP dentro do erro de domínio. Consenso praticamente universal, que a régua trata como **dispositivo** — não como informação de fundo que se cita e se ignora.

A saída **não** foi descartar a evidência por conveniência ("o nosso caso é especial"), nem capitular contra o desenho que a segunda borda exige. Foi transformar a evidência no **antecedente de uma regra condicional que vale nos dois mundos**: um projeto de **borda única HTTP deve** acoplar o status ao erro — é o que os seis fazem, e está certo pra eles; um projeto com **segunda borda não-HTTP não deve** — é o que o espécime gateado precisa, e está certo pra ele. A evidência sobreviveu inteira, virou norma pro caso dela, e o desenho local sobreviveu pelo motivo certo em vez de sobreviver por teimosia.

**Essa é a forma que porta.** Uma regra incondicional extraída de um único projeto viaja mal: ou vira dogma no projeto seguinte, ou é descartada na primeira fricção. Uma regra com predicado — *faça X quando P; faça Y quando ¬P* — carrega junto o critério de aplicação, e por isso é a única forma de padrão pessoal que sobrevive à mudança de projeto. Quando a evidência empírica contradiz o desenho, o movimento certo é quase sempre procurar **qual predicado separa os dois mundos**, antes de decidir quem tem razão.
