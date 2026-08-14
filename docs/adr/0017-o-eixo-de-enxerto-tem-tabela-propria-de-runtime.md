# O eixo de enxerto tem tabela própria de runtime

> **Emenda, 2026-08-14 ([ADR 0018](0018-vscode-ganha-linha-sem-destino-de-skill.md)):** a primeira opção considerada abaixo — dar a `vscode` uma linha em `RUNTIMES` — voltou a ser cogitada e desta vez venceu, mas não a mesma opção: a versão que ganhou não inventa `project_dir`, entra com `None` nos dois campos de destino, e por isso não fere a razão de perder registrada aqui. `RUNTIMES_BY_KEY` deixou de provar destino de skill; `runtimes_in` é quem prova agora. O resto desta ADR — a tabela de MCP como chave própria, a recusa por classe, a ordem da tela — continua de pé.

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

**Duas recusas simétricas, uma por classe.** `NoMcpDocumentError` já existia — runtime de skills numa linha com `--mcp`. Nasce a gêmea, `NoSkillsDestinationError` — runtime de enxerto numa linha com `--skill`. As duas saem **3** pela régua da [ADR 0009](0009-o-conjunto-de-runtime-e-funcao-do-escopo.md): o valor é real, a flag é real, o que não existe é o destino *daquela classe*. Numa linha que carrega **uma só** classe, cada uma recusa a **linha inteira** — não há segunda tabela a consultar por aquele runtime.

**Cada recusa dispara só quando a linha carrega a classe.** Perguntar a um alvo de enxerto onde ele guarda skills, numa linha que não pediu skill nenhuma, recusaria um install que não tem nada de errado.

**Emenda ([#100](https://github.com/panlabs-tech/overpower/issues/100)): numa linha mista, a recusa é por runtime, não mais pela linha inteira.** `--skill a --mcp b --runtime cursor,claude-code` costumava morrer inteira se `cursor` não tivesse documento de MCP, mesmo `cursor` tendo linha de skills e `claude-code` tendo as duas. Medido: isso recusava um install em que nada estava errado com `cursor` na classe que ele *tem*. A régua ficou: um runtime só é recusado quando não tem linha em **nenhuma** das classes que a linha carrega — `NoDestinationForEitherClassError`, ainda exit 3 pela mesma leitura da ADR 0009. Um runtime com linha numa classe e não na outra recebe o que tem, e o que não recebeu vira `SkippedClass`, nomeado na tela em exit 0 — nunca em silêncio. A frase *"as duas recusam a linha inteira"* do parágrafo acima ficou verdadeira só para a linha de classe única; numa linha mista, `_refuse_the_runtimes_neither_class_can_receive` substitui as duas chamadas de `plan_for`.

**A escopo continua valendo, e agora sobre a união.** À época, `--runtime vscode --global` saía 3 com a mensagem da ADR 0009: não havia documento de MCP em escopo de máquina e não há diretório de skills em lugar nenhum. **O primeiro membro dessa conjunção caiu em [#81](https://github.com/panlabs-tech/overpower/issues/81)** — `vscode --global` hoje aterrissa no `mcp.json` do perfil de usuário. A consequência não mudou, só o exemplo: quem sai 3 agora é `--runtime eve --global --skill <x>`, e a regra continua sendo *a união decide, e o que a união não alcança recusa a linha inteira*.

**`mcp_runtimes_in` passa a ler a tabela de MCP em vez de filtrar a de skills.** O filtro funcionava só enquanto todo runtime de MCP tivesse linha de skills; ele derrubaria `vscode` **em silêncio**, e o alvo existiria, renderizaria e seria innomeável.

**A ordem da tela não muda para quem já estava lá.** A união é a ordem do upstream primeiro, intacta, e depois os alvos de enxerto que o upstream nunca teve.

**Esta ADR se reabre** se o upstream passar a declarar `vscode` — aí a linha vem da transcrição e a união deixa de ter membro próprio —, ou se a escotilha `--dir` entrar, porque aí o destino de uma classe pode vir do usuário e a pergunta *"que classe esta chave recebe"* deixa de ser só tabela.
