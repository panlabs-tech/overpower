# Frameworks são autocontidos e apartados do pool de artefatos

O overpower guarda conteúdo de duas formas: artefatos curados individualmente num **pool** tipado, e **AI Frameworks** como corpos autocontidos, cada um no seu próprio contexto. A mesma skill pode existir nos dois lugares — dentro do recorte `matt-pocock` e solta no pool — e essa duplicação é deliberada.

## Considered Options

A alternativa era **uma mecânica só**: tudo no pool, e tanto framework quanto bundle sendo manifestos que apontam artefatos. Ela eliminaria a duplicação, que é da ordem de dezenas de KiB num wheel de ~900 KiB.

Foi rejeitada porque **dentro de um framework os artefatos são acoplados, e não são átomos**:

- O `speckit-plan` do `github/spec-kit` não funciona sem a árvore `.specify/templates/` que ele lê em runtime — 28 arquivos que não são skill, nem comando, nem MCP.
- Mesmo o caso que parece limpo não é. Das 22 skills promovidas do `mattpocock/skills`, **10 invocam outras skills por nome**; `wayfinder` sozinha arrasta 8 pelo fechamento transitivo.

Decompor um framework em átomos de pool exige inventar um mecanismo de acoplamento. Mantê-lo inteiro não exige nada.

## Consequences

O pool fica tratável: como o `.specify/` mora dentro do framework, ele nunca precisa virar um tipo de artefato.

O custo é curadoria, aceito conscientemente em troca de controle total sobre o recorte. Uma skill de origem de mercado só é instalável sozinha se for curada para o pool — e aí existe duas vezes no wheel.

A verificação por `diff` byte-idêntico contra o upstream, que a pesquisa de anatomia registrou como possível para o `mattpocock/skills`, não se aplica ao pool: lá o conteúdo é recortado e possivelmente customizado.
