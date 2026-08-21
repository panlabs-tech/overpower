# Receita com fonte é configuração de máquina

> **Substituída pela [ADR 0023](0023-a-fonte-e-endereco-nao-clone.md) em 2026-08-21**, pelo gatilho que esta ADR declarou na última linha: o clone deixou de existir, e as receitas passaram a declarar endereço que o próprio ferramental resolve. O escopo deixou de ser função da receita.

Uma receita de MCP que declara `[source]` — e portanto clona código para `~/.overpower/mcp/<slug>/` — **só aterrissa em escopo de máquina**. Pedir escopo de projeto é **exit 3**, comando inteiro recusado antes de qualquer escrita.

Decidido na sessão de grilling que produziu a spec de MCP.

## A razão

O `command` renderizado aponta para o clone, logo carrega um **caminho absoluto da máquina que instalou**. Escrito num arquivo commitável — `.mcp.json`, `.vscode/mcp.json`, `.devin/mcp_config.json` —, o repositório passa a carregar o `$HOME` de uma pessoa.

Isso não é hipótese: é textualmente o defeito que reprovou o `open-gsd/gsd-core` no [critério de curadoria](../agents/domain.md#critério-de-curadoria) — *"os hooks embutem o caminho absoluto do binário da máquina que instalou"*. Aceitá-lo aqui seria fazer com um artefato próprio o que reprovou um de terceiro.

E o enquadramento que torna a recusa natural em vez de arbitrária: **o corpo do artefato mora na máquina**. Uma configuração que aponta para ele **é** configuração de máquina. O escopo não está sendo restringido — está sendo dito em voz alta.

## Considered Options

### Renderizar `${HOME}` / `${env:HOME}`

Sedutor, e funciona em dois dos três alvos: medido, o Claude Code expande `${VAR}` em `command`, `args`, `env`, `url` e `headers`; medido, o `.vscode/mcp.json` expande `${env:VAR}` pelo `variableReplacement`. Como *"a linha de comando é o manifesto"*, cada colega que rodasse a mesma linha resolveria para o próprio `$HOME`.

**Perdeu por dois buracos, e os dois falham calados.**

**Windows não tem `HOME`.** Fora do Git Bash a variável é `USERPROFILE`, e a expansão de uma variável ausente é justamente o pior caso medido do espaço: no Claude Code a **string crua vai para o processo e para a rede**; no VS Code vira **string vazia, sem erro**.

**No Devin é doc, e a doc estreita.** Ela cita a expansão *"para campos sensíveis como `oauthClientSecret`"* — não afirma que vale em `command`. Apostar num alvo não medido, num campo que a doc não cobre, para produzir um caminho de execução, é a aposta errada.

### Renderizar absoluto e aceitar

É o que a CLI oficial de vários alvos faz. **Perdeu porque o axioma 2 cobra um preço que elas não pagam**: aqui o arquivo commitado é o manifesto, e um manifesto que só funciona na máquina de quem o escreveu não é manifesto.

## Consequences

**A forma é a da [ADR 0009](0009-o-conjunto-de-runtime-e-funcao-do-escopo.md), não uma invenção.** Lá, o conjunto de `--runtime` é função do escopo, o par inexistente sai **exit 3**, e a tela não oferece o que o passo seguinte recusaria. Aqui a mesma frase muda de eixo: **o conjunto de escopos é função da receita**, e o wizard não oferece projeto para uma receita com `[source]`.

**A recusa nomeia o conserto.** Como toda saída 3 deste produto, a mensagem diz qual receita, por quê — *ela traz código-fonte que mora na sua máquina* — e o que fazer: `--global`.

**Receita sem `[source]` não é afetada.** MCP de mercado renderiza config e não baixa uma linha de código; os dois escopos continuam abertos para ele. A partição é entre receitas, não entre procedências: uma receita federada que declare só `url` continua indo para o projeto.

**O clone é re-clonado, incondicionalmente, sem cache.** É a mesma doutrina do resto do produto — escrita incondicional, e *"remoto é fresco por decisão"* ([regra 5](../agents/domain.md#regras-do-modelo)). O que não existe é remoção: clone órfão em `~/.overpower/mcp/` é lixo que só a ferramenta sabe nomear, e o `doctor` o lista sem apagá-lo.

**Esta ADR se reabre** se existir um token de caminho portátil que os três alvos expandam e que resolva no Windows — aí o escopo de projeto volta a ser possível —, ou se o clone deixar de existir, o que aconteceria se as receitas federadas passassem a declarar comandos que buscam sozinhos (`uvx --from git+…`).
