# A fonte é endereço, não clone

Uma receita cujo servidor tem código-fonte próprio **declara o endereço, e o overpower renderiza o comando que o próprio ferramental resolve**. Nada é clonado, `~/.overpower/mcp/` deixa de existir, e o escopo volta a ser livre.

```yaml
source:
  git: https://github.com/ThiagoPanini/panlabs-mcp
  ref: v0.3.1
  runner: uvx
  entrypoint: panlabs-git
```

rende `uvx --from git+https://github.com/ThiagoPanini/panlabs-mcp@v0.3.1 panlabs-git`, com `server.args` aposto ao fim. `ref` é **obrigatório**. `runner` é conjunto fechado: `uvx` e `npx`.

Decidido na sabatina de instalação federada de MCP, 2026-08-21.

**Substitui a [ADR 0015](0015-receita-com-fonte-e-configuracao-de-maquina.md)** pelo gatilho que ela própria declarou: *"esta ADR se reabre […] se o clone deixar de existir, o que aconteceria se as receitas federadas passassem a declarar comandos que buscam sozinhos (`uvx --from git+…`)"*.

## O que foi medido

Contra remotos git locais, sem rede:

| forma | ref fixada | sem ref |
| --- | --- | --- |
| `uvx --from git+<url>@v0.3.1 panlabs-git` | tag e SHA resolvem; ref inexistente falha alto (`Git operation failed`) | — |
| `npx --yes --package git+<url>#v0.3.1 panlabs-node` | rodou a **0.3.1** com o HEAD já em `0.9.9` | rodou a **0.9.9-untagged** |

A segunda linha da coluna direita é o que faz `ref` ser campo obrigatório em vez de opcional: sem ela o servidor **muda de comportamento sem ninguém ter mudado nada**, e a versão em que mudou não está escrita em lugar nenhum. É o mesmo defeito que `@latest` já é proibido de cometer numa receita embutida.

## Considered Options

**Manter o clone**, como a 0015 desenhou. Perde por herança: o `command` renderizado carrega caminho absoluto da máquina que instalou, e é isso que obriga escopo de máquina, que impede o `.mcp.json` de ser commitável, e que faz o `doctor` ter de saber o que é clone sumido e clone órfão. Sob endereço, os quatro problemas somem de uma vez, e o arquivo escrito passa a ser o mesmo em toda máquina — que é o que o axioma 2 pede de um manifesto.

**`source` sumir, com o publicador escrevendo o incantamento literal em `server.args`.** É a forma que `coolify` e `hostinger-vps` já usam para pacote publicado, e custa zero vocabulário. Perdeu para a tabela acima: dentro de um array de strings, `ref` não é campo, é substring — o produto não consegue exigi-la, nem recusar a ausência, nem mostrá-la. Com `source` declarado, a procedência vira **dado**: o `list --from` mostra `github.com/o/r@v0.3.1` na linha do servidor, que é a única coisa que este campo compra sobre a string literal, e a razão de ele existir.

**`runner` aberto**, aceitando qualquer string. Reabre pela porta dos fundos o *comando livre vindo de manifesto federado* que o axioma 1 fecha. Um runner novo é uma linha numa tabela e um teste.

**Clone como segunda forma**, para servidor que nenhum runner resolve. Perdeu por preço de manutenção desproporcional ao alcance: manteria vivos o diretório em `~/`, a restrição de escopo e as duas checagens do `doctor` para atender o caso que nenhuma receita medida exercita. Um servidor que precisa de `make` recebe *"não instalamos"*, que é resposta honesta e não deixa dívida.

## Consequences

**Três campos deixam de ser declarados e passam a ser derivados**, e declará-los é recusa **por nome**: `command`, porque `runner` já o determina; `transport`, porque um servidor que sobe por runner é stdio e não pode ser outra coisa; e a precondição `command_exists` do runner, porque é o `runner` dito duas vezes. É a regra 4 do modelo aplicada — *o que é derivável é derivado, nunca declarado*, porque campo declarado envelhece calado.

**O escopo deixa de ser função da receita.** A forma que a 0015 tomou emprestada da [ADR 0009](0009-o-conjunto-de-runtime-e-funcao-do-escopo.md) — *o conjunto de escopos é função da receita* — some com o clone. Uma receita com `source` instala em projeto e em máquina, e o `.mcp.json` que ela escreve é commitável e igual para todo mundo.

**O `doctor` perde duas checagens e ganha uma.** `MissingClone` e `OrphanClone` morrem com o diretório. No lugar entra a precondição do runner, **re-rodada depois da instalação**: o `uvx` que a receita exige ainda está no PATH? É offline, e é a única das candidatas que responde à pergunta que o usuário de fato leva ao `doctor`. Verificar na **rede** se a `ref` ainda resolve foi recusado: transformaria um comando offline em cliente de rede para pegar um caso que o próprio runner reporta alto na primeira execução.

**`~/.overpower/mcp/` fica órfão em quem já instalou**, e nada o remove. Medido no dia da decisão: o diretório **não existe** na máquina do autor, e nenhuma receita publicada declara `[source]` — o parque é vazio.

**Esta ADR se reabre** se um servidor que a curadoria queira admitir não for alcançável por nenhum runner de vocabulário fechado, e a resposta *"não instalamos"* passar a custar mais que o clone custava.
