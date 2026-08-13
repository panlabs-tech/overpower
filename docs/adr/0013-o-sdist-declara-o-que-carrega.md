# O sdist declara o que carrega

O `pyproject.toml` do overpower passa a ter um `[tool.hatch.build.targets.sdist]` com uma linha, `include = ["src/"]`. O sdist publicado deixa de ser o repositório inteiro e passa a ser o que o wheel precisa mais os metadados que o `hatchling` força.

Esta ADR existe por causa da [ADR 0004](0004-build-nao-forca-inclusao-de-conteudo.md), que registrou uma **ausência** como decisão: *"o `pyproject.toml` não tem `force-include`, não tem `artifacts`, não tem `ignore-vcs` e não tem `packages`"*, e mandou tratar como regressão qualquer configuração de build que aparecesse ali. Quem abrir o arquivo depois desta mudança acha um bloco de build e lê exatamente a regressão que a 0004 avisa. Não é: **a 0004 proíbe forçar inclusão, e isto é o oposto**.

Levantado em [O sdist publicado é o repositório inteiro](https://github.com/panlabs-tech/overpower/issues/64) e decidido em [O sdist declara o que carrega](https://github.com/panlabs-tech/overpower/issues/71).

## O achado não era o do título

O ticket abriu com dois problemas, e o que ele tratava como o grave é o menor dos dois.

**"O que entra no sdist depende da máquina que builda" é verdade como mecanismo e nunca se materializou.** O `hatchling` monta o sdist filtrando pelo `.gitignore`, então qualquer arquivo não rastreado e não ignorado entra — e o `.git/info/exclude`, que é por clone e nenhuma ferramenta além do git lê, escondia dez caminhos do Claude Code do `git status` sem escondê-los do build. Plantadas quatro sondas numa árvore suja, **as quatro entram no sdist e nenhuma aparece no `git status`**.

Só que o caminho de publicação nunca esteve exposto. Os sdists publicados foram baixados e contados: `0.1.0` com 164 arquivos e `0.5.0` com 172, **zero entradas `.claude` nos dois**. O `release.yml` builda em runner limpo, e o `actions/checkout` materializa só o que o git rastreia — rodados os passos que ele roda antes do `Build`, a árvore fica com **zero arquivos não rastreados**. A exposição é do build local, e o build local não é o publicado. Ela vira real no dia em que alguém rodar `uv build && uv publish` da própria máquina.

**"O sdist publicado é o repositório inteiro" é verdade e é o achado grande.** Medido na `0.5.0`:

| seção do sdist | arquivos | bytes | % da árvore |
| --- | ---: | ---: | ---: |
| `src/` | 97 | 692.413 | 52,9% |
| `tests/` | 38 | 314.881 | 24,1% |
| raiz | 12 | 146.780 | 11,2% |
| `docs/` | 17 | 125.854 | 9,6% |
| `.github/` | 3 | 24.994 | 1,9% |
| `licenses/` | 2 | 2.137 | 0,2% |
| `.vscode/` | 2 | 1.766 | 0,1% |

Extraído o sdist, removido tudo que não é `src/` nem metadado, e o wheel reconstruído a partir do resto: **105 entradas dos dois lados, zero bytes diferentes**. Os 67 arquivos que sobram não são lidos por nada a jusante.

## Considered Options

### Denylist — `exclude = ["tests/", "docs/", ...]`

Perde, e não por tamanho: os dois entregam o mesmo sdist hoje. Uma denylist **obriga a enumerar a ferramenta de amanhã**. As sondas deste levantamento moram em `.claude/mailbox/` e `.claude/checkpoints/` — caminhos que não estavam em lista nenhuma até serem inventados para o teste, e que só existem porque a ferramenta que os cria foi instalada depois do `.gitignore` ter sido escrito. Uma allowlist não admite o que ninguém declarou; é fechamento por construção, e não por vigilância.

### Portão sozinho, sem mexer no build

Foi o que o [#64](https://github.com/panlabs-tech/overpower/issues/64) pediu no item 4 — um irmão do P2 que assertasse o conteúdo do sdist e nada mais. **Fica vacuamente verde para sempre.** O único ambiente onde ele roda é a CI, e a CI é justamente onde o vazamento não pode ocorrer, pelo mesmo `actions/checkout` medido acima. É a armadilha que o [#45](https://github.com/panlabs-tech/overpower/issues/45) achou no P1 enquanto a raiz de conteúdo não existia: `exit 0`, saída vazia, portão sem sujeito. Rejeitado como *substituto*; entra como complemento, com a razão trocada — ver abaixo.

### Allowlist — `include = ["src/"]`

Foi essa.

| | arquivos | descomprimido | `.tar.gz` |
| --- | ---: | ---: | ---: |
| `0.5.0` como publicada | 172 | 1.308.825 | 424.699 |
| com a allowlist | 105 | 766.626 | 266.086 |
| **delta** | **−67** | **−542.199** | **−158.613 (−37,3%)** |

**A prova que a 0004 exige é a de clone limpo**, e é onde as duas mecânicas se separam. O `artifacts` da 0004 entregava 2 de 2 no build local e 1 de 2 no de CI, porque fura o filtro do `.gitignore` para o *build* sem tornar o arquivo visível para o *git*. A allowlist:

| build | sdist |
| --- | --- |
| árvore suja, 4 sondas plantadas invisíveis ao `git status` | 105 arquivos, **zero `.claude`** |
| clone limpo | 105 arquivos, **zero `.claude`** |
| **divergência** | **nenhuma** |

`include` não é nenhuma das quatro chaves proibidas, e a diferença é mecânica e não nominal: as quatro **forçam inclusão** e criam divergência local × CI; esta **restringe**, e por isso não pode divergir.

## O que o `hatchling` força, e por que isso importa

Oito arquivos entram no sdist independentemente do que estiver escrito no `include`/`exclude`:

```
.gitignore  LICENSE  NOTICE  PKG-INFO  README.md  pyproject.toml
licenses/mattpocock-skills.LICENSE  licenses/panlabs-tech-skills.LICENSE
```

Verificado de propósito: um `exclude` nomeando os oito **não remove nenhum**. A consequência é que a atribuição PEP 639 da [ADR 0003](0003-sem-atribuicao-no-alvo.md) — `NOTICE` e os dois `licenses/` — **não pode ser perdida por uma allowlist errada**. Não é sorte: é o que dispensa uma segunda regra dizendo "não esqueça de manter as licenças".

## O P3 entra com a razão trocada

**Quem fecha o vazamento é a allowlist, por construção. O P3 existe para pegar a allowlist envelhecendo** — o dia em que `src/` deixar de ser a expressão certa e um arquivo rastreado parar de viajar em silêncio. Essa direção a CI enxerga, e a outra não.

Duas cláusulas, rodadas contra quatro árvores:

```
todo arquivo no sdist, menos PKG-INFO, é rastreado pelo git
todo arquivo que o git rastreia sob src/ está no sdist
```

| árvore | veredito |
| --- | --- |
| `0.5.0` sem a allowlist, árvore suja | **vermelho** — 175 arquivos, 4 intrusos `.claude` |
| árvore suja, com a allowlist | verde — 104 arquivos, 0 intrusos, 0 ausentes |
| clone limpo, com a allowlist | verde — 104 arquivos, 0 intrusos, 0 ausentes |
| allowlist estreita demais (`src/overpower/content/`) | **vermelho** — 89 arquivos, 15 `.py` rastreados ausentes |

A primeira cláusula fica mesmo sendo a que a CI não consegue reprovar hoje: ela custa zero e é o que falha se alguém alcançar uma das quatro chaves da 0004, que é o único mecanismo que sobrou capaz de pôr arquivo não rastreado no sdist.

**O `src/` da segunda cláusula é escrito à mão de propósito, e a tentação de lê-lo do `include` foi medida.** Ela parece a mesma higiene que o `release-ready` pratica ao montar o mapa `título → tipo` a partir dos blocos `[[tool.towncrier.type]]` em vez de repeti-lo — mas os dois casos são opostos. Lá, o mapa e os tipos são duas grafias do mesmo fato. Aqui, o `include` é a **implementação** e a cláusula é a **asserção**: derivar uma da outra faz o portão sair **verde** com `include = ["src/overpower/content/"]`, porque uma allowlist estreitada é consistente consigo mesma. O portão passaria a assertar que o `hatchling` implementa `include`, que não é modo de falha de ninguém — a mesma vacuidade que esta ADR existe para recusar. O limite conhecido de escrever à mão é a direção contrária: um `include` que **cresça** só passa a ser asseverado quando esta linha crescer junto. Estreitar, que é o que perde arquivo, falha alto.

**Custo zero de build.** O passo do P2 já roda `uv build --no-sources`, que escreve o sdist ao lado do wheel; o P3 lê o `dist/` como está. E **não vai para o `lefthook`**: o hook local pega barato o erro barato, `uv build` não é barato, e a direção que só o local enxergaria já está fechada por construção.

## Consequences

**O gatilho do `release-ready` perde a premissa que o justificava.** O comentário sobre a tupla `WHEEL` no `ci.yml` dizia, com medição, que a leitura pelo sdist publicaria uma versão por vírgula mexida numa ADR — porque o sdist era o repositório. Com a allowlist as duas leituras **convergem** para a própria tupla, e o que sobra de divergência é `.gitignore` e a metade `[tool.*]` do `pyproject.toml`. A tupla não muda; o comentário passa a descrever os dois artefatos em vez de escolher entre eles.

**`tests/` sai do sdist, e a divergência fica registrada.** O argumento do distro packager — a suíte tem de viajar para quem empacota poder rodá-la — é real e perde por medição: não há distro package do overpower, o wheel sai byte-idêntico sem os testes, e a [doutrina de teste](../agents/testing.md) deste repo não trata o sdist como superfície de verificação. **Quem quiser rodar a suíte usa o repositório.**

**`docs/` sai do sdist.** Perde pela mesma medida: 125.854 bytes por release não compram acesso que um `git clone` não dê, e o arquivo de decisão mora no repositório e no tracker, que é para onde os links das ADRs apontam.

**Se um dia o sdist precisar carregar algo fora de `src/`** — um `conftest.py` de raiz, um arquivo gerado, uma suíte que passe a ser critério de terceiro — a linha ganha um segundo item, e o P3 continua sendo o que impede que ela envelheça calada. A escotilha é a mesma da 0004, e agora ela é uma linha em vez de uma chave proibida.
