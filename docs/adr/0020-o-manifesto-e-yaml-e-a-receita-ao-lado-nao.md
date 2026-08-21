# O manifesto é YAML, e a receita ao lado dele não é

> **Substituída pela [ADR 0021](0021-um-arquivo-um-formato.md) em 2026-08-21.** A premissa desta decisão — *"o manifesto tem dois campos"* — deixou de valer quando o servidor MCP entrou em `items` ([ADR 0022](0022-servidor-mcp-e-artefato.md)), e a limitação que ela registrou como conhecida (*"um bundle caseiro não pode nomear um MCP"*) foi o que a reabriu.

Um repositório caseiro declara seus bundles em **`.overpower/catalog.yaml`**, com o **mesmo schema e o mesmo leitor** do arquivo escrito do embutido — que migra de `catalog.toml` para `catalog.yaml` no mesmo movimento. A receita de MCP, vizinha de diretório, **continua TOML** em `.overpower/mcp/<slug>.toml`.

O diretório `.overpower/` passa a carregar dois formatos, e isso é deliberado: ele é **namespace, não formato**. A extensão diz ao autor qual leitor ele está alimentando.

Decidido na sabatina de [Repositório caseiro](https://github.com/ThiagoPanini/overpower/issues/26).

## Considered Options

**Um schema, um leitor — a regra que decidiu o formato.** Com AI Framework fora do `--from` ([ADR 0019](0019-a-vitrine-e-ancorada-o-alcance-nao.md)), o manifesto federado carrega **uma tabela e dois campos**: `description` e `items` por bundle. É metade exata do arquivo escrito embutido. Remoto YAML com embutido TOML daria **dois leitores para um schema**, que é a coisa que este repositório recusou por escrito duas vezes: a receita federada passa pelo *"mesmo `read_recipe` da embutida — nenhum segundo validador que pudesse discordar do primeiro"* ([#83](https://github.com/ThiagoPanini/overpower/issues/83)), e `rendering.py` é função total sobre a saída de `recipes.py` *"rather than a second validator that could disagree"*. Sobraram duas opções coerentes — **os dois TOML** (custo zero) e **os dois YAML** (uma dependência) —, e o dev escolheu YAML.

**A familiaridade não desempatou, e o fato é que ela não podia.** O autor de repositório caseiro já escreve YAML — o frontmatter de todo `SKILL.md` — **e** já escreve TOML, desde que a receita federada shipou. Os dois formatos já estão na mão dele. O que desempata é qual arquivo é o **irmão** do manifesto, e o irmão é o arquivo escrito do embutido: mesmo schema, mesmo papel, mesma pergunta. Sob esta decisão os dois passam a ter o mesmo **nome**, `catalog.yaml`, dos dois lados.

**Por que a receita não vai junto.** `recipes.py` tem **855 linhas** e é a validação inteira de um contrato — allowlist fechada de chaves, transporte, papéis de slot, precondições, `[source]` — sob a promessa de que *"a recipe that gets past this module is a recipe that renders"*. Migrá-la é reescrever o decodificador desse contrato, mais converter as 4 receitas embutidas, por consistência cosmética e ganho funcional zero. A base instalada não foi o argumento, embora ela ajude: o endereço `.overpower/mcp/<slug>.toml` tem **zero ocorrências no README**, que menciona MCP 23 vezes — está documentado só em doc de agente, e tem dias de idade. O argumento é de natureza: a receita é contrato de chave fechada, onde a única-forma-de-escrever do TOML é feature; o manifesto tem dois campos.

**O endereço maximiza um namespace só.** A alternativa era `.overpower.yaml` na raiz — arquivo de raiz para a declaração do repositório, diretório para a coleção por slug —, que dissolveria a mistura de formatos ao custo de duas grafias da palavra `.overpower`. Perdeu para a simetria de nome: um autor que abrir o wheel encontra `catalog.yaml` com o mesmo schema que ele escreveu.

## Consequences

**A primeira dependência YAML do produto entra, e ela paga por duas coisas.** `_frontmatter_description` — o parser artesanal de ~30 linhas que existe justamente para evitar essa dependência — sai no mesmo PR, porque manter um parser de YAML à mão ao lado de um parser de YAML de verdade é a forma fraca do defeito que reprovou a opção mista. Ele tem defeito **medido**: `description: >` devolve `'> Primeira linha segunda linha.'` e `description: |` devolve `'| Primeira linha segunda linha.'` — o marcador de bloco vaza para dentro da descrição, e as duas grafias são YAML válido. Medido também: **0 das 26 skills vendorizadas** usam block scalar, então o defeito é **latente** hoje. Ele deixa de ser latente por causa do `--from`, que aponta para repositórios que ninguém curou.

**`TID251` ganha entrada nova, e ela é obrigatória.** O ban de `json.load`/`json.loads` existe porque pyright strict tem ponto cego com `Any` — medido no [#2](https://github.com/ThiagoPanini/overpower/issues/2): `return data["name"]` dentro de uma função `-> str` passa no type checker. `yaml.safe_load` devolve `Any` e cai no mesmo buraco, então a decodificação de YAML nasce confinada a um módulo que devolve `object`, com o ban a impor a confinação em vez de lembrá-la. `yaml.load` sem `Loader` entra no ban pelo motivo adicional de ser vetor de execução arbitrária.

**A migração do embutido tem raio medido**: `catalog.toml` aparece **26 vezes** fora do próprio arquivo — a constante em `packaged.py` e três arquivos de teste (`test_wizard` 14, `test_planning` 9, `test_catalog` 1) — mais o leitor em `written.py`, 133 linhas com **um** consumidor. Mecânico, e não é uma linha.

**O axioma 1 não é tocado.** Ele proíbe **binário de terceiro como requisito**; `pyyaml` tem caminho puro-Python e não é subprocesso. A obrigação que a [ADR 0007](0007-transporte-nao-e-instalador.md) acrescentou — todo caminho por subprocesso carrega fallback puro-Python — continua valendo e continua satisfeita.

**Um bundle caseiro não pode nomear um MCP**, e isso não é limitação do federado: `Bundle.artifacts` é `tuple[Artifact, ...]` e `Recipe` não é um `Artifact`, no embutido tanto quanto no remoto. O bundle mais natural de um repositório caseiro — *"minhas skills mais meu MCP interno"* — não cabe no modelo hoje. Consertar isso mexe nas duas pontas e fica fora deste esforço.
