# A vitrine é ancorada, o alcance não

O `--from` passa a responder duas perguntas diferentes, e elas têm regras de busca diferentes de propósito.

> **Enumerar** — `list --from <url>` e `install --from <url>` sem seletor — anda `<raiz-do-repositório>/skills/**`, e ignora a subpasta da URL.
> **Alcançar pelo nome** — `install --skill <nome> --from <url>` e `list --skill <nome> --from <url>` — segue como está: `rglob("SKILL.md")` a partir da raiz de busca, em qualquer profundidade.

A primeira responde *"o que este repositório oferta?"*, que é propriedade do **repositório**. A segunda responde *"você tem isto?"*, que é propriedade do **caminho que o usuário apontou**. Uma regra só não serve às duas, e a medição diz qual erra menos em cada uma.

Decidido na sabatina de [Repositório caseiro](https://github.com/ThiagoPanini/overpower/issues/26).

## Considered Options

**Medido em 6 repositórios de skills, 75 `SKILL.md`, árvore completa por `gh api`, nada truncado.** O conjunto correto — o que o autor *oferta*, por oposição ao que ele tem *instalado* — é **73**: tudo que está sob um `skills/` de primeiro nível.

| repo | total | sob `skills/` | sob diretório de runtime | outro lugar |
| --- | --- | --- | --- | --- |
| `panlabs-tech/skills` | 4 | 4 (`skills/<nome>/`) | 0 | 0 |
| `mattpocock/skills` | 35 | 35 (**`skills/<categoria>/<nome>/`**) | 0 | 0 |
| `obra/superpowers` | 14 | 14 | 0 | 0 |
| `anthropics/skills` | 20 | 19 | 0 | 1 (`template/`) |
| `vercel-labs/skills` | 1 | 1 | 0 | 0 |
| `github/spec-kit` | 1 | 0 | 1 (`.github/skills/`) | 0 |

| regra | acha | erro |
| --- | --- | --- |
| `<raiz>/skills/**` | **73** | **0** |
| `rglob` + deny-list dos destinos de runtime | 74 | 1 falso positivo (`anthropics/skills/template/`) |
| `<raiz>/skills/<nome>/` **plano** | 38 | **35 falsos negativos** |

**O número que decidiu é o 38.** A leitura literal de *"skills ficam em `skills/`"* devolve **zero** para o `mattpocock/skills`, que aninha dois níveis (`skills/<categoria>/<nome>/`) — o repositório mais importante do mercado, e o mesmo cujas 25 skills já viajam vendorizadas dentro deste wheel. A âncora tem de ser o `skills/` de primeiro nível **com profundidade livre abaixo dele**.

**O deny-list perdeu a enumeração e ganhou outro lugar.** Excluir os destinos que o próprio overpower escreve acerta 74 com um falso positivo, o que é pior que a âncora. Mas ele resolve um defeito que a âncora não toca: a busca **nomeada** devolve **exit 3 falso** num repositório que tenha `skills/alpha` e `.claude/skills/alpha`, que é o estado de todo repositório caseiro que já rodou `overpower install` em si mesmo. Isso é correção de defeito existente, não parte desta decisão.

**A alternativa de uma regra só** — ancorar também a busca nomeada — quebra a promessa de raiz de busca que o [#25](https://github.com/ThiagoPanini/overpower/issues/25) mediu e testou: `--from .../tree/main/skills/engineering/tdd` aponta para a pasta da própria skill, e sob a âncora não existiria `skills/` abaixo dela. As três profundidades de URL devolvendo a mesma resposta é comportamento shipado, com teste verde.

## Consequences

**O `list` mostra menos do que o `--skill` alcança, e isso é a decisão, não um defeito.** Medido: **2 dos 75** ficam de fora da vitrine e continuam instaláveis pelo nome — `anthropics/skills/template/SKILL.md`, que é gabarito e não oferta, e `github/spec-kit/.github/skills/add-community-extension/`, que está num diretório de runtime e portanto é *configurado*, não *armazenado*. A frase que o `--help` carrega é **"o `list` mostra a vitrine; `--skill` alcança o que você souber nomear"**.

**A enumeração ignora a subpasta da URL inteiramente.** `list --from https://github.com/o/r/tree/main/skills` responde igual a `list --from https://github.com/o/r`. Sem isso, um bundle declarado na raiz cujos itens moram fora da subpasta quebraria conforme a profundidade da URL — o mesmo repositório dando respostas diferentes, que é exatamente o que a regra de raiz de busca existe para impedir. A subpasta continua estreitando a busca **nomeada**, que é o uso que a mensagem de `AmbiguousRemoteSkillError` já recomenda: *"Point --from at one of them instead"*.

**Custa nada em rede.** A árvore inteira já está em disco nos dois transportes — `remote.py` obtém o repositório e só então estreita com `search_root` —, então enumerar da raiz é usar a variável que já existe, não uma segunda obtenção.

**Só `skills/` é enumerado.** `commands/` e `agents/` existem no conjunto fechado do embutido e ficaram de fora do federado: medido, **0 dos 75** vive neles, e um comando caseiro precisaria carregar um `SKILL.md` porque `_description_of` exige o arquivo em todo tipo. Admiti-los depois é aditivo — um repositório hoje ignorado em silêncio não reclama; um hoje listado que amanhã some, sim.

**No alcance, o deny-list é desempate e não filtro** — decidido na implementação ([#135](https://github.com/ThiagoPanini/overpower/issues/135)), porque esta ADR pesou o deny-list só na enumeração e o custo dele no alcance ficou sem medir. Filtrar responde *não achei* sobre a única coisa que existe sob a raiz, e isso não é canto: `github/spec-kit` — uma das 6 linhas medidas aqui — tem seu único `SKILL.md` sob `.github/skills/`, e duas linhas da tabela de runtime são nomes de pasta comuns que um repositório pode ofertar de verdade (`agent/skills` do `eve`, `data/skills` do `astrbot`). A regra que sai: **descarte as cópias, a menos que descartá-las não deixe nada**. Uma cópia nunca ganha de uma oferta, e nunca esconde a única resposta. Duas ofertas homônimas de verdade seguem ambíguas, que é o caso que a recusa existe para pegar.

**AI Framework não entra por `--from`.** Ele fica sendo conceito do que está embutido no código-fonte do overpower, e uma linha nomeando-o ao lado de `--from` segue recusada em **exit 2**. O que a [ADR 0006](0006-a-arvore-e-o-catalogo.md) exige de um framework — o nível de tipo repetido dentro dele, sendo a árvore a única fonte possível do tipo — não tem quem garanta num repositório alheio.
