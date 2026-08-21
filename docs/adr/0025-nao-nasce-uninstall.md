# Não nasce `uninstall`, e o risco fica nomeado

O produto continua com dois verbos: `install` escreve, `doctor` diz se o que foi escrito continua sendo o que foi escrito. **Não nasce um comando de remoção**, nem para chave de enxerto, nem para árvore de cópia.

Decidido na sabatina de instalação federada de MCP, 2026-08-21, **contra a recomendação registrada**.

## A razão que ganhou

`uninstall` é um **terceiro verbo**, e a identidade do produto são dois. E a garantia de splice aditivo da [ADR 0016](0016-o-diff-aditivo-e-requisito.md) **não tem gêmea subtrativa pronta**: remover uma chave de um documento JSONC preservando comentário e formatação é trabalho novo, não a mesma função ao contrário.

Há também simetria com a classe de cópia, que nunca teve remoção: uma skill instalada some com `rm -rf .claude/skills/<nome>`.

## O dissenso, e o risco que fica

A recomendação era `uninstall` nascer para enxerto, e o argumento era um risco **que este desenho cria** — os outros quatro abaixo já existiam.

**1. O produto passa a criar um segredo que se recusa a destruir.** Com a [ADR 0024](0024-o-segredo-mora-onde-o-git-nao-alcanca.md), `~/.claude.json` — medido: **110 KB, 21 projetos, ~40 chaves de topo** — passa a carregar o token literal. Antes dela o arquivo carregava `${VAR}` e desfazer era `unset`, fora do arquivo. O produto que faz inserção cirúrgica para não estragar o arquivo do usuário devolveria a remoção como *"abre e edita"*.

**Este risco tem conserto sem verbo novo, e ele foi tomado**: um valor vazio no prompt do segredo grava `${VAR}` de volta ([ADR 0024](0024-o-segredo-mora-onde-o-git-nao-alcanca.md)). O segredo sai do arquivo, o servidor continua configurado, e o produto não ganhou a capacidade de remover.

Os quatro que ficam sem conserto, e que a decisão aceita:

**2. Chave que entrou não sai, e o `doctor` não sabe que ela existe.** As checagens são `PendingApproval`, `UnsetSlot` e a precondição de runner da [ADR 0023](0023-a-fonte-e-endereco-nao-clone.md) — nenhuma pergunta *"esta chave ainda corresponde a alguma receita"*. Um servidor cuja receita sumiu do repositório de origem fica no documento para sempre, e o produto não tem palavra para descrevê-lo.

**3. O `inputs[]` do VS Code só cresce.** Medido em [#79](https://github.com/ThiagoPanini/overpower/issues/79): enxerto em lista é idempotente por campo, então reinstalar não duplica — mas nada retira. E limpar em lote é caro de um jeito visível: o VS Code confia no arquivo por `TrustedOnNonce` sobre o hash do launch, e reescrever a lista faz ele pedir reaprovação de **todo** servidor.

**4. Instalar nos dois escopos deixa dois vivos.** Projeto e máquina escrevem documentos diferentes e o agente carrega os dois; desfazer é saber qual dos dois abrir.

**5. A assimetria com a cópia não é simetria de verdade.** `rm -rf` numa pasta de skill é óbvio e seguro. O alvo de um enxerto é uma **chave dentro de um documento que também guarda os servidores que o usuário escreveu à mão**, e a operação equivalente não tem forma segura à mão.

## Esta ADR se reabre

Se aparecer relato real de configuração perdida por edição manual; se o risco 2 virar defeito relatado — servidor fantasma que ninguém consegue nomear; ou se a metade subtrativa do `grafting.py` precisar existir por outra razão, aí o custo que sustenta esta decisão já terá sido pago por outro motivo.
