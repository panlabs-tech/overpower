# A chave alheia é sobrescrita

Colisão de **chave** num enxerto resolve-se do mesmo jeito que colisão de **caminho** numa cópia: sobrescrevendo, sem perguntar, sem `--force`, exit 0.

> Se `mcpServers.github` já existe no `.mcp.json` do usuário, o overpower o substitui.

Decidido na sessão de grilling que produziu a spec de MCP, contra a recomendação registrada abaixo.

## O argumento que perdeu

A assimetria é real e foi levantada: **numa cópia, a pasta inteira é nossa** — sobrescrever destrói o que nós mesmos escrevemos numa execução anterior. **Num enxerto, a chave vizinha é do usuário**, e é prova viva disso. Um `github` que já está no `.mcp.json` provavelmente é dele, com o token dele e com os argumentos que ele ajustou.

A alternativa recomendada era **exit 3 pedindo `--force`**, reusando a forma que o produto já aplica a destino existente em escopo global ([história 47](https://github.com/panlabs-tech/overpower/issues/35)) — ali a razão declarada é *"não há git para desfazer"*.

Os alvos, aliás, discordam entre si, e a discordância foi medida em [Formatos de configuração de MCP por runtime](https://github.com/panlabs-tech/overpower/issues/17): o **Claude Code recusa** duplicata com exit 1 e sem `--force`; o **VS Code e o Codex sobrescrevem calados**. Não havia comportamento nativo a imitar — só dois campos opostos para escolher.

**O dev escolheu sobrescrever, e a razão é coerência**: a escrita incondicional é a mesma decisão em todo o produto ([#9](https://github.com/panlabs-tech/overpower/issues/9)), e um segundo regime de colisão obrigaria o usuário a saber de que classe é o artefato antes de prever o que o comando faz.

## O preço, declarado

**Um servidor homônimo do usuário é substituído sem pergunta.** Isso não é efeito colateral não previsto: é o custo aceito, e ele é assimétrico entre escopos.

Em **projeto** há git, e o `git diff` mostra a substituição — o axioma 2 continua a valer inteiro, e desfazer é `git checkout`. Em **máquina** não há git, e a configuração anterior daquele servidor **desaparece sem registro**. É a mesma condição que fez o escopo global exigir `--force` para destino existente; aqui ela foi lida e não prevaleceu.

## Consequences

**O plano nomeia arquivo e chave antes de confirmar.** `.mcp.json › mcpServers.github` é a única defesa que sobra, e ela é do usuário: ele vê o alvo exato antes de aceitar. Sem essa linha a decisão seria indefensável, o que faz dela requisito da tela e não ornamento.

**O `--force` continua existindo e não muda de sentido.** Ele governa destino existente em escopo global para **cópia**; enxerto não o consulta. Duas flags para a mesma palavra seria pior que uma regra assimétrica.

**Esta ADR se reabre** por qualquer um destes: um relato real de configuração perdida em escopo de máquina; a entrada de um comando de remoção, que hoje não existe e que mudaria o que "desfazer" custa; ou a decisão de o plano **marcar** a chave preexistente em vez de apenas nomeá-la — o conserto mais barato disponível se a defesa acima se mostrar fina na prática.
