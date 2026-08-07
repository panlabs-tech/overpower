# A árvore é o catálogo

O overpower não mantém um registro do que ele contém. O `install` e o `list` descobrem os artefatos embutidos olhando a estrutura de diretórios — `src/overpower/content/pool/<tipo>/<nome>/` e `src/overpower/content/frameworks/<nome>/`. **Nenhum caminho é registrado em lugar nenhum.**

> *Emendado em [Conteúdo vendorizado](https://github.com/panlabs-tech/overpower/issues/45), ao construir a árvore que esta ADR descreve. O nível de tipo **repete-se dentro do framework** — `content/frameworks/<nome>/<tipo>/<artefato>/` —, com o mesmo conjunto fechado de nomes do pool. A redação original tratava o framework como uma pasta opaca, e ela não fecha: o `list --ai-framework` mostra o tipo de cada artefato como prefixo, e esta ADR proíbe entrada de artefato no arquivo escrito, logo a árvore é a **única fonte possível** do tipo. É também o que faz um framework de tipos misturados — o `.specify/` do spec-kit ao lado de skills renderizadas — caber sem mecanismo novo, já que destino é função de (tipo, runtime, escopo). Não muda nenhuma posição desta ADR; corrige o desenho da convenção que ela decidiu.*
>
> *A mesma curadoria fixou o endereço do arquivo escrito, que a decisão tinha deixado implícito: `src/overpower/catalog/catalog.toml`, a raiz irmã de `content/` que o [#11](https://github.com/panlabs-tech/overpower/issues/11) nomeou. Ele **não ganha portão**, e a razão é a assimetria de falha medida no [#10](https://github.com/panlabs-tech/overpower/issues/10): conteúdo perdido é silencioso — skill pela metade e ninguém percebe, que é o que P1 e P2 existem para pegar —, catálogo perdido é alto — o bundle some do `list` e o `install` responde que não conhece o nome. O que falha ruidosamente não precisa de verificação.*

Existe um arquivo escrito, e a regra que decide o que entra nele vale para sempre:

> **O que o overpower escreve só carrega o que a árvore não pode saber. Caminho, nunca.**

Na v0.1.0 isso são duas coisas: os **bundles**, que por definição não têm árvore, e **uma linha de descrição por AI Framework**, que não tem `SKILL.md`. Não existe entrada de skill, de comando nem de agente.

Como a [ADR 0004](0004-build-nao-forca-inclusao-de-conteudo.md), o artefato desta decisão é em boa parte uma **ausência** — quem procurar o arquivo que lista as skills não vai encontrar, e precisa saber que não foi esquecimento.

## Considered Options

A alternativa era um catálogo que registrasse onde cada artefato está dentro do pacote. Ela parece mais segura: torna explícito o que existe, e não depende de ninguém pôr a pasta no lugar certo. Os dois lados foram construídos e quebrados de propósito.

**O risco da convenção é alto, não silencioso.** Skill posta em `content/pool/skill/` (singular) levanta `LayoutError: content/pool/skill/ is not an artifact type` na primeira chamada, com o diretório errado na mensagem — a convenção é um conjunto fechado de nomes, e o que está fora dele é erro, não omissão.

Um caso passa calado, e ficou registrado porque é o único: um `README.md` solto em `content/pool/skills/` **vira artefato** e aparece na lista junto com as skills. Fecha ignorando o que não é diretório, ou exigindo o arquivo marcador do tipo.

**O risco do catálogo é silencioso, e é o modo de falha que este projeto já decidiu combater.** Skill nova no disco sem entrada no catálogo: **5 no disco, 4 no catálogo**, e a quinta invisível — não aparece no `list`, não instala, e nada avisa. É a classe *"sucesso com conteúdo errado"* que o [#11](https://github.com/panlabs-tech/overpower/issues/11) gastou um ticket construindo os portões P1 e P2 para pegar, e a mesma do `hatch-vcs` sob clone raso registrada no [#2](https://github.com/panlabs-tech/overpower/issues/2).

E o custo não para aí: **o catálogo exige um terceiro portão**. P1 e P2 comparam git ↔ wheel; com catálogo é preciso comparar também catálogo ↔ árvore, **nos dois sentidos**. Sob a convenção, essa comparação é tautologia — não há dois lados para divergir.

**A distinção que decidiu.** A palavra "catálogo" cobria duas coisas de natureza oposta:

| | é duplicação? | por quê |
| --- | --- | --- |
| registrar **caminho** | **sim** | o sistema de arquivos já sabe; duas fontes para o mesmo fato derivam |
| escrever **descrição** | não | não existe em lugar nenhum; fonte única, nada com que divergir |

É por isso que a regra proíbe **caminho** por nome, e não "arquivo". O custo prático dessa formulação é o que se queria: acrescentar um arquivo dentro de uma skill existente não toca em nada, e acrescentar uma skill nova não toca em nada. Só vendorizar uma unidade que não tem árvore — um bundle — custa uma linha escrita.

A descoberta custa **42 linhas**, já com a checagem de tipo desconhecido.

## Consequences

**A descrição de uma skill vem do próprio `SKILL.md`**, com o custo aceito conscientemente. O `description:` do frontmatter é gatilho de roteador, não texto de vitrine: mediana 179 caracteres, máximo 517, e cortar na primeira frase não resolve — **13 de 22** continuam passando de uma linha. Na tela aprovada em [Protótipo da experiência de terminal](https://github.com/panlabs-tech/overpower/issues/12), 4 skills ocupam **32 linhas** com a descrição do upstream contra **15** com uma linha curada. O ganho é que embutido e remoto ficam idênticos, sem uma qualidade que só o embutido pode ter.

**Um AI Framework precisa da linha escrita, e uma skill não** — ele é uma pasta com skills dentro e nenhum frontmatter próprio. O upstream do `mattpocock/skills` mantém uma descrição em `.claude-plugin/plugin.json`, mas esse arquivo está fora do recorte vendorizado, e trazê-lo para dentro de `content/` não seria possível: `content/` **100% aterrissa** e a [ADR 0003](0003-sem-atribuicao-no-alvo.md) proíbe acrescentar qualquer coisa ao que aterrissa.

**O `NOTICE` do wheel não vira dado.** Ele continua sendo o arquivo de texto que o [#11](https://github.com/panlabs-tech/overpower/issues/11) decidiu — escrito à mão na curadoria, carregando repo, SPDX, titular e ref por origem vendorizada. O programa nunca o lê, e o `list` não mostra origem.

**A regra explica a assimetria entre MCP e hook** que o [#11](https://github.com/panlabs-tech/overpower/issues/11) mediu sem nomear. *"MCP é só contrato; hook é contrato e árvore"* deixa de ser fato solto e vira consequência: MCP não tem árvore, logo é **inteiro** entrada escrita; hook tem árvore e uma parte que a árvore não sabe, logo é os dois. A árvore de um hook é descoberta em `content/pool/hooks/<nome>/` como todo o resto, e a entrada casa com ela **pelo nome** — o mesmo mecanismo que um bundle usa para nomear artefatos do pool. Nenhum campo aponta para a árvore; se apontasse, seria caminho.

**O destino não é campo de entrada nenhuma.** Destino é função de (tipo, runtime, escopo) — igual para toda skill, igual para todo MCP —, logo é tabela em código. Pô-lo na entrada repetiria o mesmo valor em todas as entradas do mesmo tipo, que é a duplicação que esta ADR proíbe. Os valores dessa tabela é que carregam as duas formas exigidas pela primeira trava do `domain.md`: **pasta** (cópia) ou **arquivo + chave** (enxerto).

**A convenção precisa de uma guarda que a medição encontrou**: descoberta ignora o que não é diretório, senão arquivo solto na pasta de tipo vira artefato em silêncio.
