# O segredo é escrito onde o git não alcança, e nunca onde alcança

O overpower **pergunta o valor de um slot e o escreve literal** — em escopo de máquina, e só onde o alvo não sabe guardá-lo melhor. Em escopo de projeto o slot continua sendo o que ele sempre foi: `${VAR}` no documento, e nada mais.

A regra inteira em uma linha: **o overpower escreve o segredo quando o git não alcança *e* o alvo não sabe guardá-lo melhor.**

Decidido na sabatina de instalação federada de MCP, 2026-08-21.

## A razão

A regra que esta ADR estreita — *"slot é o que o overpower se recusa a escrever; `[server.env]` é o que ele escreve porque pode"* — foi comprada por um fato: em escopo de projeto o arquivo vai para o git. Em `~/.claude.json` esse fato não existe. Medido na máquina do autor: **110 KB, 21 projetos**, e a credencial do próprio Claude Code já dentro. Não há git alcançando esse arquivo, e não há segredo novo entrando num lugar que já não guarde um.

O que a recusa custava está do outro lado, e é o que a sabatina definiu como a propriedade a maximizar: **uma execução, e a configuração fica completa**. Hoje o `install` termina imprimindo *"not set here PANLABS_TOKEN — the server reads it when the runtime starts, so this variable is yours to export before you use the server"* e sai 0. O defeito que isso deixa não falha no produto: falha **dentro do agente**, meia hora depois, sem nomear quem o causou. É a mesma assimetria que fez `command_exists` virar precondição declarada em vez de suposição.

## A exceção que a regra carrega

Medido em [#79](https://github.com/ThiagoPanini/overpower/issues/79): o `inputs[]` do VS Code com `password: true` é a **única grafia do espaço inteiro** em que o segredo fica guardado sob proteção do SO, e não apenas referenciado; sem ela o valor vai em texto puro para o `state.vscdb`. Escrever literal em `.vscode/mcp.json` seria estritamente **pior** do que o produto já faz. Claude Code e Devin recebem o valor; VS Code mantém `inputs` e não recebe.

## Considered Options

**Não perguntar, e melhorar só o aviso** — `doctor` imprimindo o comando pronto para colar, `instructions` obrigatório quando há slot. Perdeu porque não fecha a propriedade: continua havendo um passo depois do comando.

**Perguntar e guardar num cofre do produto** — `~/.overpower/secrets.env`, com o comando renderizado passando por um lançador nosso que carrega o arquivo. Perdeu porque põe o overpower **dentro do caminho de execução** do servidor: a partir daí um defeito nosso derruba um servidor que já estava de pé, e o produto deixa de ser instalador.

**Perguntar sempre que houver tty, inclusive com `--yes`.** Perdeu porque `--yes` existe para script e CI, onde prompt trava processo.

**Literal nos três dialetos, por uniformidade.** Perdeu para a medição do `password: true` acima — uniformidade que piora um dos três não é uniformidade, é regressão distribuída.

## Consequences

**O prompt tem quatro bordas, e todas caem no comportamento de hoje.** Pergunta **só** com tty e sem `--yes`; fora disso escreve `${VAR}` e avisa, que é exatamente o que o produto já fazia — o ramo interativo é acrescentado por cima, não no lugar. Valor já gravado é **mantido** e não perguntado de novo; `--force`, que já significa *sobrescreva destino ocupado*, é o que reabre a pergunta. Se a variável já estiver no ambiente, ela é oferecida como default **sem ser ecoada**. `--dry-run` não pergunta, e o plano anuncia *"1 segredo será pedido"*.

**O prompt entra depois do plano e da confirmação, antes da primeira escrita.** O plano é a tela-contrato do produto — é ela que nomeia arquivo e chave antes de confirmar, e é a única defesa que a sobrescrita silenciosa da [ADR 0013](0013-a-chave-alheia-e-sobrescrita.md) tem. Pedir antes dela coletaria segredo para uma escrita que o usuário ainda pode recusar; pedir depois deixaria o arquivo existir com placeholder por um instante.

**O fallback não pergunta, mas também não desescreve** — precisão que a implementação ([#167](https://github.com/ThiagoPanini/overpower/issues/167)) cobrou da frase acima. *"Fora disso escreve `${VAR}` e avisa"* vale para o slot que **nunca** foi respondido, e só para ele. O enxerto substitui a chave inteira do servidor, então um slot deixado de fora do plano é um slot sobre o qual a referência é escrita por cima: se o fallback ignorasse o valor gravado, o segundo `install --yes` da mesma linha rebaixaria um segredo que funciona a placeholder, no exit 0 — exatamente a classe de defeito que esta ADR existe para não ter. Então **valor já gravado é relido e reescrito em toda execução, com terminal ou sem**; o que o terminal e o `--yes` decidem é a *pergunta*, nunca o que já está no arquivo. Nada disso alarga a regra: numa máquina que nunca respondeu a um prompt não há valor guardado para carregar, e a execução renderiza exatamente o que renderizava antes desta decisão.

**Um valor vazio no prompt grava `${VAR}` de volta.** É como o segredo sai do arquivo sem o produto ganhar um verbo de remoção ([ADR 0025](0025-nao-nasce-uninstall.md)): o estado para onde ela leva é exatamente o estado que o produto produzia antes desta decisão, e o servidor continua configurado para quem tem a variável exportada.

**A sobrescrita da [ADR 0013](0013-a-chave-alheia-e-sobrescrita.md) fica mais cara em escopo de máquina.** O que some sem registro ao sobrescrever uma chave alheia passa a poder ser um segredo do usuário, não só um endereço. A defesa continua sendo a mesma e continua sendo requisito: o plano nomeia arquivo e chave antes de confirmar.

**O `doctor` nunca imprime o valor.** A checagem `UnsetSlot` procura `${VAR}` no documento e o confere contra o ambiente; onde o valor é literal não há `${VAR}`, e a checagem simplesmente não dispara. O que o `doctor` pode dizer é que a chave existe, nunca o que ela contém.
