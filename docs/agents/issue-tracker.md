# Issue tracker

As issues deste repo vivem como **issues do GitHub** em `panlabs-tech/overpower`. Use a CLI `gh` para todas as operações.

> **Este tracker não é o da org.** `panlabs-tech/.github` hospeda trabalho sobre o **padrão panlabs**, e o próprio doc de lá diz que produto tem tracker próprio. O overpower é produto: nada dele entra lá.

## O que entra

Trabalho sobre o **overpower**: o CLI, o catálogo de AI Frameworks, o empacotamento, a publicação, a curadoria de conteúdo.

## O que não é superfície de triagem

**PRs externos.** Repo de um mantenedor; PR de fora não faz parte do fluxo de triagem.

## Convenções

- **Criar issue**: `gh issue create --title "..." --body-file <arquivo>`. Use arquivo para corpo multi-linha.
- **Ler issue**: `gh issue view <numero> --comments`
- **Listar**: `gh issue list --state open --json number,title,labels`
- **Comentar**: `gh issue comment <numero> --body-file <arquivo>`
- **Rotular**: `gh issue edit <numero> --add-label "..."` / `--remove-label "..."`
- **Fechar**: `gh issue close <numero> --comment "..."`

O `gh` infere o repo pelo `git remote` quando roda de dentro do clone.

## Wayfinding operations

O `/wayfinder` carta a rota de um esforço grande como um **mapa** (issue-raiz) com **tickets** (sub-issues). Este repo usa as relações **nativas** do GitHub — sub-issues e dependências — para que a fronteira apareça na própria UI, sem convenção de texto no corpo.

**Labels.** O mapa leva `wayfinder:map`. Cada ticket leva exatamente uma de `wayfinder:research`, `wayfinder:prototype`, `wayfinder:grilling`, `wayfinder:task`.

**Criar o mapa**: `gh issue create --title "..." --label "wayfinder:map" --body-file <arquivo>`.

**Criar tickets e ligar ao mapa.** As duas APIs de relação exigem o **`id`** interno da issue, não o número — resolva com `gh api repos/panlabs-tech/overpower/issues/<numero> --jq .id`.

```bash
# ticket como sub-issue do mapa
gh api -X POST repos/panlabs-tech/overpower/issues/<MAPA>/sub_issues -F sub_issue_id=<ID_TICKET>

# ticket A bloqueado pelo ticket B
gh api -X POST repos/panlabs-tech/overpower/issues/<NUM_A>/dependencies/blocked_by -F issue_id=<ID_B>
```

Crie todos os tickets primeiro e ligue as arestas num **segundo passe** — uma issue precisa existir antes de poder ser referenciada.

**Listar os filhos do mapa**: `gh api repos/panlabs-tech/overpower/issues/<MAPA>/sub_issues --jq '.[] | {number, title, state, assignees: [.assignees[].login]}'`

**Ler os bloqueadores de um ticket**: `gh api repos/panlabs-tech/overpower/issues/<NUM>/dependencies/blocked_by --jq '[.[] | select(.state=="open") | .number]'`

**A fronteira** — tickets tomáveis agora — são os filhos do mapa que estão **abertos**, **sem assignee** e cuja lista `blocked_by` não tem nenhuma issue aberta.

**Reivindicar um ticket**, antes de qualquer trabalho, para que sessões concorrentes o pulem: `gh issue edit <NUM> --add-assignee @me`.

**Resolver um ticket**: publique a resposta como comentário e feche — `gh issue close <NUM> --comment "<resposta>"` — e depois acrescente uma linha em **Decisions so far** no corpo do mapa, apontando para o ticket. A decisão mora no ticket; o mapa só a resume e linka.

**Referir-se a mapa e tickets** em texto para humano sempre pelo **título**, com o link embutido — nunca por `#42` solto.

## Quando uma skill diz "publique no issue tracker"

Crie uma issue do GitHub.

## Quando uma skill diz "busque o ticket relevante"

Rode `gh issue view <numero> --comments`.
