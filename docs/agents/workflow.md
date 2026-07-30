# Fluxo de desenvolvimento

## Do problema à execução

```
/wayfinder  →  /to-spec  →  /to-tickets  →  /tdd  →  worktree  →  PR  →  merge no verde
```

Uma decisão grande demais para uma sessão vira **mapa** de wayfinding, resolvido um ticket de decisão por vez. Um mapa fechado vira **spec**. Uma spec vira **tickets** com arestas de bloqueio declaradas.

## O mapa da v0.1.0 carrega execução

O mapa que originou este repo declara, nas suas Notes, um **override do padrão do wayfinder**: ele não só decide, ele constrói. O destino dele é a v0.1.0 publicada no PyPI e validada nos dois caminhos de instalação — PyPI público e Artifactory corporativo.

Isso vale **para este mapa**. Mapas futuros voltam ao padrão: decidem, não executam.

## Modo de implementação autônoma

Disparado por "implementa as issues" ou equivalente:

1. Colete as issues `ready-for-agent` abertas, sem bloqueio pendente.
2. Um **git worktree por issue**, aninhado no próprio repo.
3. `/tdd`: RED → GREEN → refactor.
4. Commit (Conventional Commits) e push.
5. Abra o PR.
6. **Mergeie no verde** e encadeie até as issues acabarem.

## Portões

Quais portões este repo adota — local e de CI — é decisão em aberto, e sai do ticket de estruturação inicial do mapa. Enquanto não sair, o repo não tem portão declarado, e isso é ausência conhecida, não omissão.

## Referência de padrão Python

O `panlabs-python-standards` é a régua de forma de código consultada aqui. Onde ele e uma decisão do mapa divergirem, vence o mapa — e a divergência vira ADR em `docs/adr/`.
