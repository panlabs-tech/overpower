# `vscode` ganha linha em `RUNTIMES`, sem destino de skill

O passo de runtime do wizard precisa nomear `VS Code` para a classe de enxerto (#97), e o único nome que este módulo já sabe dar a um runtime é `Runtime.display_name` — um campo de `RUNTIMES`. A ADR 0017 rejeitou pôr `vscode` nessa tabela porque a opção considerada então dava a ele um `project_dir` real (`.agents/skills`, carona com outros 19), o que destruiria a propriedade de transcrição que os testes fixam em 76.

**A decisão agora é outra, não a mesma revisitada**: `vscode` entra com `project_dir=None` e `global_dir=None` — nenhum destino de skill inventado, em nenhum escopo. `RUNTIMES` passa a ter 77 linhas: 76 transcritas do upstream, mais esta, que o próprio mapa desenha. `runtimes_in` deixa de ler "está na tabela" e passa a ler "tem `project_dir`/`global_dir` naquele escopo" — a mesma pergunta de sempre, feita ao campo certo em vez de à tupla inteira. `_refuse_a_runtime_with_no_skills` faz o mesmo ajuste. Todo o restante do modelo — `mcp_document_of` continua chaveado por `str`, `MCP_DOCUMENTS` continua tabela própria, a partição por classe (ADR 0009, ADR 0017) continua valendo — não muda: o que muda é só que pertencer a `RUNTIMES` para de ser prova de destino de skill.

`test_table_size_matches_the_transcribed_upstream` e `test_vs_code_has_no_row_although_the_map_measured_it` fixavam exatamente o fato que esta ADR inverte; foram reescritos para medir o novo (77; `vscode` presente e sem destino).

## Consequences

Todo ponto que iterava `RUNTIMES` cru assumindo que cada linha tem `project_dir` — `resolve_project_dir`, `_reads_universally`, `_that_take_skills`, e um punhado de teste — ganhou guarda de `None`. `known_runtimes()` fica mais simples: a união com a tabela de MCP não tem mais nenhum graft-only para acrescentar, já que os três alvos de enxerto (`claude-code`, `vscode`, `devin`) agora têm linha aqui.

Esta ADR se reabre se um segundo runtime precisar de nome sem destino de skill — nesse caso vale perguntar se o padrão é "linha com campos `None`" ou algo mais explícito — ou se o upstream passar a declarar `vscode`, quando a linha vira transcrição de verdade e o comentário que a distingue sai.
