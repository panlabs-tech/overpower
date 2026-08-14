---
paths:
  - "tests/*.py"
  - "tests/**/*.py"
---

# Ao escrever teste neste repo

A doutrina inteira está em `docs/agents/testing.md`: leia o **§ Resumo
executável**, depois só a posição que ele citar. As duas que mais decidem a forma
de um teste novo — **o disco é real** e **rede nunca entra em portão**. O `git`
roda de verdade, contra um remoto construído em disco.

## O andaime já existe — clone dele

| Módulo | O que entrega |
| --- | --- |
| `tests/support/project.py` | Uma árvore de conteúdo real, um alvo real e a CLI entre os dois — `source`, `target`, `workspace`, `catalog_of`, `pinned`, `terminal`. |
| `tests/support/screens.py` | Renderiza uma tela como tela, não como bytes — `console`, `render`. |
| `tests/support/snapshots.py` | O comparador de snapshot, um arquivo por tela, atualizado só quando pedido — `assert_matches_snapshot`. |
| `tests/support/git_remote.py` | Um remoto `git` real em disco, para o caminho de fetch rodar sem rede — `LocalRemote`, `instead_of_github`, `planting`. |
| `tests/support/gates.py` | O único portão da suíte, e ele guarda a rede. |
| `tests/conftest.py` | As opções que a suíte adiciona ao pytest. |

O teste irmão mais próximo é o melhor molde. `head` no docstring de um
`tests/test_*.py` diz o que ele cobre, sem abrir o arquivo inteiro.
