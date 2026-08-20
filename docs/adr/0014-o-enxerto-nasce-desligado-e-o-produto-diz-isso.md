# O enxerto nasce desligado, e o produto diz isso

O overpower escreve o servidor MCP e **não o liga**. A aprovação do Claude Code e o Workspace Trust do VS Code são ato do usuário.

> Uma escrita por alvo, e mais nenhuma. Onde está medido que o artefato nasce inerte — Claude Code, escopo de projeto —, um **aviso ao final, exit 0**. O `doctor` responde **exit 3** para enxerto escrito e não aprovado.

Decidido na sessão de grilling que produziu a spec de MCP, fechando [Ativação do enxerto: a segunda escrita fora do repositório](https://github.com/ThiagoPanini/overpower/issues/21).

## O fato que criou a pergunta

Medido em [Formatos de configuração de MCP por runtime](https://github.com/ThiagoPanini/overpower/issues/17): servidor vindo de `.mcp.json` nasce `⏸ Pending approval` no Claude Code e **não conecta**. Nenhuma mensagem, nenhum exit code, nenhum sinal na sessão normal. É a primeira vez no produto em que o `git diff` não conta a história inteira de um artefato — e o [axioma 2](../agents/domain.md#axiomas) faz dele o manifesto.

## Considered Options

### Escrever `enabledMcpjsonServers` nas settings de usuário

Medido: settings de **usuário** aprovam sempre, independentemente do diálogo de confiança. Era a única opção que funcionaria em toda máquina, em todo clone.

**Perdeu por segurança, não por gosto.** A aprovação é **por nome de servidor, em todo projeto**. Um repositório clonado que declare um `.mcp.json` com um servidor de mesmo nome passa aprovado sozinho, sem diálogo, sem aviso. O produto teria criado um buraco de cadeia de suprimento para poupar um clique. E a variante larga, `enableAllProjectMcpServers`, é a mesma falha sem o disfarce do nome.

### Escrever em `<repo>/.claude/settings.local.json`

Escopo correto, arquivo convencionalmente não rastreado, e a aprovação morre junto com o repositório.

**Perdeu por duas medições.** Settings **de projeto** só valem depois de `hasTrustDialogAccepted: true` — *"a cloned repository can't approve its own servers"* —, então a escrita **não dispensa o humano**, só o adia. E o arquivo mora **dentro da árvore de trabalho**: se o `.gitignore` do usuário não o cobrir, a aprovação vaza para o git — e cobrir seria uma **terceira** escrita no repositório dele, por uma razão que não é a dele.

### E a razão que derruba as duas de uma vez

**O portão do VS Code é inalcançável.** O Workspace Trust mora em `state.vscdb`, um sqlite de estado do editor. Não existe versão desta decisão em que o overpower ligue o MCP nos três alvos.

Qualquer uma das opções acima entregaria *"às vezes ativamos, às vezes não"* — e o usuário aprenderia a confiar num mecanismo que cobre um alvo de três. Um produto que **nunca** ativa e **sempre** diz isso é previsível; um que ativa às vezes é pior que nenhum dos dois, porque ensina a não conferir.

## Consequences

**O aviso é requisito, não cortesia.** Sem ele o produto entrega exatamente o modo de falha que a pesquisa nomeou: arquivo escrito, exit 0, servidor inerte, nenhum sinal. É a classe *"sucesso com conteúdo errado"* que o [problema do mapa](https://github.com/ThiagoPanini/overpower/issues/35) mediu no `npx skills` e existe para não cometer.

**E ele só aparece onde é verdade.** Claude Code em escopo de projeto. No VS Code o usuário já atravessa o Workspace Trust ao abrir a pasta; no Devin não há portão documentado — e imprimir um aviso ali seria inventar um fato que a doc não dá. Aviso que aparece sempre não é lido.

**O `doctor` herda o caso principal.** *"Enxerto escrito e não aprovado"* é literalmente *"rodei, e a resposta é não"* — **exit 3**, a leitura fixada na [ADR 0009](0009-o-conjunto-de-runtime-e-funcao-do-escopo.md). Com esta decisão isso deixou de ser detalhe de diagnóstico e virou a principal razão de o `doctor` conhecer MCP.

**A trava do modelo continua paga.** O `domain.md` exigia que a v0.1.0 não fechasse a porta de *"um artefato pode custar mais de uma escrita, e a segunda pode ser fora do repositório"*. A porta segue aberta: o que mudou é que a segunda escrita **não é nossa**. O plano e o `--dry-run` continuam falando de escritas planejadas, e nenhum fluxo assume uma escrita por artefato.

**Esta ADR se reabre** se algum alvo passar a expor a ativação por arquivo que se possa escrever com escopo correto **nos três** — ou se o Claude Code deixar de exigir aprovação para servidor de projeto, o que apagaria o único caso do aviso.
