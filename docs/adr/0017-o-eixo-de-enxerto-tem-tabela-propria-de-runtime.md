# O eixo de enxerto tem tabela própria de runtime

O VS Code lê `.vscode/mcp.json`, e **nenhum outro runtime lê esse arquivo**. Ele também não tem linha na tabela de skills: o upstream do `vercel-labs/skills` não declara nenhuma para ele, e a nossa tabela é uma **transcrição** ([#27](https://github.com/panlabs-tech/overpower/issues/27)). Para o [Alvo VS Code](https://github.com/panlabs-tech/overpower/issues/79) existir é preciso que `--runtime vscode` seja aceitável, e isso obriga a escolher entre duas coisas que pareciam a mesma.

> **O conjunto de runtimes de enxerto é a chave de `MCP_DOCUMENTS`, e não um subconjunto de `RUNTIMES`.**
> O que `--runtime` aceita é a **união** das duas tabelas. Qual classe cada chave consegue receber é pergunta **por classe**, feita só quando a linha carrega aquela classe.

`vscode` tem documento de MCP e nenhum diretório de skills; `cursor` tem diretório de skills e nenhum documento de MCP. As duas tabelas se **intersectam sem que nenhuma contenha a outra**, e é isso que a decisão registra.

## Considered Options

### Acrescentar uma linha `vscode` à tabela de skills

Era a mudança de menos linhas: `project_dir = .agents/skills` é **verdade medida** — o VS Code lê esse caminho de carona com outros 19 — e `global_dir = None` também. **Perdeu porque destrói a propriedade que dá valor à tabela.**

A tabela é uma transcrição de um commit nomeado (`a4d243c`, `v1.5.22`), com atribuição no `NOTICE`, e a integridade dela é **corresponder ao upstream**. Uma linha nossa no meio faz o `test_table_size_matches_the_transcribed_upstream` deixar de medir o que o nome dele diz: `76` passaria a significar *"75 transcritas mais uma inventada"*, e o próximo refresh não teria como saber qual é qual. Os outros números do mapa — 55 caminhos distintos, 19 no grupo universal, 74 com destino global — mudariam todos pela mesma razão errada.

E o custo não pararia aí: `vscode` entraria na lista que `--runtime` oferece **para skills**, num caminho que ninguém mediu e que o mapa registra explicitamente como não nomeável.

### Mapear o documento do VS Code numa chave que já existe

`github-copilot` está na tabela. **Perdeu porque é outro runtime.** Medido: o Copilot CLI lê `.mcp.json` no CWD e **não** lê `.vscode/mcp.json`; o VS Code lê os dois, em dialetos diferentes. Uma chave que respondesse pelos dois erraria o arquivo para um deles em silêncio — que é o modo de falha 5 da pesquisa, arquivo válido e inerte.

### Manter `mcp_document_of` recebendo `Runtime`

Era o que estava escrito. **Perdeu por assinatura:** receber `Runtime` declara, no tipo, que o eixo de enxerto é subconjunto do eixo de cópia. Medido, não é. O sinal de que a decisão já estava tomada estava no código: `MCP_DOCUMENTS` sempre foi chaveado por `str`, num módulo que tem o tipo `Runtime` à mão.

## Consequences

**Duas recusas simétricas, uma por classe.** `NoMcpDocumentError` já existia — runtime de skills numa linha com `--mcp`. Nasce a gêmea, `NoSkillsDestinationError` — runtime de enxerto numa linha com `--skill`. As duas saem **3** pela régua da [ADR 0009](0009-o-conjunto-de-runtime-e-funcao-do-escopo.md): o valor é real, a flag é real, o que não existe é o destino *daquela classe*. E as duas recusam a **linha inteira**, nunca a metade que tem destino.

**Cada recusa dispara só quando a linha carrega a classe.** Perguntar a um alvo de enxerto onde ele guarda skills, numa linha que não pediu skill nenhuma, recusaria um install que não tem nada de errado.

**A escopo continua valendo, e agora sobre a união.** `--runtime vscode --global` sai 3 com a mensagem da ADR 0009: não há documento de MCP em escopo de máquina ([#81](https://github.com/panlabs-tech/overpower/issues/81)) e não há diretório de skills em lugar nenhum.

**`mcp_runtimes_in` passa a ler a tabela de MCP em vez de filtrar a de skills.** O filtro funcionava só enquanto todo runtime de MCP tivesse linha de skills; ele derrubaria `vscode` **em silêncio**, e o alvo existiria, renderizaria e seria innomeável.

**A ordem da tela não muda para quem já estava lá.** A união é a ordem do upstream primeiro, intacta, e depois os alvos de enxerto que o upstream nunca teve.

**Esta ADR se reabre** se o upstream passar a declarar `vscode` — aí a linha vem da transcrição e a união deixa de ter membro próprio —, ou se a escotilha `--dir` entrar, porque aí o destino de uma classe pode vir do usuário e a pergunta *"que classe esta chave recebe"* deixa de ser só tabela.
