# Servidor MCP é artefato, e o bundle o alcança

Um servidor MCP **é um artefato**, como o vocabulário sempre disse, e um bundle pode nomeá-lo. Em `items`, cada entrada carrega o espaço de nomes como prefixo — `skill:panlabs-python-standards`, `mcp:panlabs-git` —, e a resolução acontece dentro do mesmo repositório, dos dois lados da procedência.

Decidido na sabatina de instalação federada de MCP, 2026-08-21.

## A razão

O glossário abre a definição de artefato com a lista dos que existem: *"uma skill, um comando, um agente, **um servidor MCP**, um hook. Vive no pool, instala-se sozinho, e é o único item que um bundle pode listar."* O código diz o contrário e **sabe que diz** — `discovery.py`, na docstring de `ArtifactType`: *"It is the closed set of type folders under a content root, **which is why the MCP server is not on it** even though the operation that lands one now exists."*

A [ADR 0020](0020-o-manifesto-e-yaml-e-a-receita-ao-lado-nao.md) já tinha registrado a consequência disso como limitação conhecida — *"o bundle mais natural de um repositório caseiro, minhas skills mais meu MCP interno, não cabe no modelo hoje"* — e adiado o conserto. A medição que fecha o adiamento é o `panlabs-skills`: ele oferece uma skill e dois servidores, e o único bundle que consegue declarar é `items: ["panlabs-python-standards"]`. O método que ele existe para distribuir são as três coisas juntas; o que ele consegue publicar é um terço, e o resto é README.

**Quem estava errado era o código.** `ArtifactType` foi definido como *"o conjunto fechado de pastas de tipo sob uma raiz de conteúdo"*, e essa definição é sobre **como o artefato é armazenado**, não sobre o que ele é. Ela exclui o MCP por uma razão verdadeira e irrelevante: a receita não aterrissa, logo não mora em `content/`. Continua não morando. Deixa de decidir se o bundle a alcança.

## Considered Options

**O código ganhar**, com o glossário passando a dizer que artefato é o que tem árvore. Perdeu porque essa definição já falha na própria lista: um bundle *"aponta nomes, não carrega conteúdo"* e ninguém propõe tirá-lo do modelo por isso. Ter árvore é propriedade de armazenamento, e o vocabulário deste repositório é sobre unidades de curadoria.

**Um terceiro termo** — kit, equipamento — que componha artefato e receita, deixando bundle como está. Custa uma unidade nova no vocabulário para dizer o que bundle já diz, e a [ADR 0002](0002-bundle-nao-compoe-framework.md) já fixou o que bundle é: *escolha de equipamento*.

**Nome nu em `items`**, resolvido nos dois espaços com colisão recusada por nome. Perdeu por um modo de falha assimétrico: o repositório que ganha uma skill homônima de um servidor **quebra um bundle que funcionava**, sem ter tocado nele. O prefixo também é o que faz a tela do plano ser legível antes de rodar — `mcp:panlabs-git` avisa que vem chave em documento, não pasta em disco.

**Duas listas dentro do bundle** — `skills:` e `mcp:` — perdeu porque `items` deixa de ser uma lista e a ordem de instalação some junto.

## Consequences

**`items` continua resolvendo só dentro do mesmo repositório.** Nem o catálogo embutido nem um terceiro repositório são alcançáveis por ali, sob pena de `items` virar carregador de endereço. O prefixo diz **espaço de nomes**, nunca procedência.

**Um bundle pode espalhar por mais de um documento e mais de um destino.** Um `items` com skill e MCP escreve pasta e chave na mesma execução — a v0.1.0 já tinha se proibido de assumir *"um artefato, uma escrita"*, e é aqui que a trava é cobrada.

**Escopo continua um por execução.** Um bundle com skill e servidor instalado em projeto escreve a skill no repositório e o servidor no `.mcp.json` com o slot; instalado em máquina, escreve nos destinos de máquina dos dois e o segredo entra literal ([ADR 0024](0024-o-segredo-mora-onde-o-git-nao-alcanca.md)). Nada no bundle escolhe escopo por item.

**`Bundle.artifacts` deixa de ser `tuple[Artifact, ...]`.** O que ele carrega passa a ser a união de artefato e receita, e todo lugar que soma `files` e `size` de um bundle tem de responder por um item que **não tem árvore para pesar** — uma receita pesa uma chave, não bytes.
