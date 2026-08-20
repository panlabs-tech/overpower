# Um bundle não compõe um AI Framework

Um bundle lista **apenas** artefatos do pool. Não pode listar um AI Framework, nem apontar para dentro da árvore de um. Framework, bundle e artefato são escolhidos de forma independente pelo usuário.

## Considered Options

A alternativa era permitir que um item de manifesto fosse `artefato` **ou** `framework` — um `api-python` que trouxesse "o spec-kit inteiro mais estas 4 skills". Custava um tipo de item a mais e resolvia um caso plausível.

Foi rejeitada por **peso de decisão**: framework é escolha de *método*, bundle é escolha de *equipamento*. Adotar o spec-kit muda como a pessoa desenvolve; adicionar 4 skills só muda o que está disponível. Decisões de peso diferente não entram na mesma lista, senão a leve arrasta a pesada em silêncio. A escolha de usar um framework é do usuário, desacoplada de qualquer bundle — e há usuários que não vão querer framework nenhum.

Apontar *para dentro* da árvore de um framework foi rejeitado por um segundo motivo: reintroduziria o acoplamento que o [ADR 0001](0001-frameworks-autocontidos-e-pool-apartado.md) removeu. Mexer no recorte de um framework quebraria bundles em silêncio.

Como efeito, **"perfil" saiu do vocabulário**: seria a composição nomeada de frameworks, e no modelo não existe composição de frameworks em lugar nenhum.

## Consequences

Instalar um framework e um bundle que compartilham uma skill produz duas escritas no mesmo caminho, em comandos independentes, e o overpower não enxerga a sobreposição de antemão — o conteúdo pode até diferir, porque o artefato do pool é recortado e possivelmente customizado. A semântica dessa colisão é decidida em [Semântica de escrita: sobrescrita, symlink e fallback](https://github.com/ThiagoPanini/overpower/issues/9).

Um bundle pode **recomendar** um framework em prosa, na descrição. Preserva o conhecimento de que os dois casam, sem instalar nada e sem criar aresta de composição.
