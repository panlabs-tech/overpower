# A transformação acontece na curadoria, não no produto

Quando o conteúdo que aterrissa **não** é a árvore versionada do upstream — porque o instalador original o *gera* —, a transformação roda **uma vez, na curadoria**, e a saída é vendorizada no wheel. O produto continua fazendo cópia de árvore e nada mais.

A regra vale para qualquer framework futuro. Ela foi decidida com um caso real na mão, o `github/spec-kit`, que acabou **fora da v0.1.0** por escopo — mas a decisão sobre *como* ele entraria já estava tomada quando isso aconteceu, e é ela que fica.

## Considered Options

O `specify init --integration claude --script sh` produz 28 arquivos, e eles se separam em três grupos, medidos em [Anatomia dos AI Frameworks candidatos](https://github.com/panlabs-tech/overpower/issues/6):

| grupo | arquivos | o que é |
| --- | ---: | --- |
| renderizado | **10** | `.claude/skills/speckit-*/SKILL.md` |
| cópia pura | 14 | `.specify/{memory,scripts/bash,templates,workflows}` |
| omitido pelo axioma 2 | 4 | `init-options.json`, `integration.json`, `integrations/*.manifest.json` |

A alternativa era o overpower **renderizar na instalação**, reproduzindo as quatro regras de transformação: troca de frontmatter, resolução de `{SCRIPT}` a partir do `scripts:` da fonte, reescrita de três prefixos de caminho, e `ARGUMENT_HINTS` por integração.

Foi rejeitada porque **a saída não depende de nada que só exista na máquina do usuário**. A pesquisa registra: *"nenhum passo consulta a rede, e nenhum depende de resposta do usuário além de `--integration` e `--script`"*. Se a saída não depende do usuário, ela não precisa ser produzida na máquina dele.

O que renderizar na curadoria compra, medido:

- **O motor de render some do produto** — nada de quatro regras, nada de tabela de destino por integração, nada do eixo `--script` na CLI.
- **O teste de caracterização some**, e não por dispensa: o conteúdo vendorizado **é** o fixture. Não sobram dois jeitos de gerar para comparar.
- **O conteúdo encolhe 26%.** Vendorizar a fonte são 31 arquivos / 297.259 bytes (`templates/` 16 + `scripts/` 15, com bash *e* PowerShell *e* Python). Vendorizar a saída são **24 arquivos / ~215 KiB**, porque as variantes não escolhidas não viajam.
- **O axioma 1 fica intocado.** Ele proíbe o *overpower* invocar instalador de terceiro. O `specify` roda na mão do curador — o mesmo lugar onde a [ADR 0001](0001-frameworks-autocontidos-e-pool-apartado.md) já admite conteúdo *"recortado e possivelmente customizado"*.

O custo é real e foi aceito: **o vendorizado deixa de ser a árvore do upstream** e passa a ser saída de ferramenta de terceiro, o que torna o diff de refresh mais barulhento. Não fere nenhuma verificação, porque [Onde os assets vivem e como entram no wheel](https://github.com/panlabs-tech/overpower/issues/11) já **recusou o P3** — diff byte-idêntico contra o upstream — sob o argumento de que *"o que estiver lá dentro será replicado"* não admite espelho a verificar.

## Consequences

**O catálogo tem uma transformação só: cópia.** Não há campo de "transformação" a inventar no [formato do catálogo](https://github.com/panlabs-tech/overpower/issues/10), e essa simplicidade é resultado de desenho, não de ter tirado o caso difícil da frente.

**Um runtime não pré-renderizado não é suportável.** O catálogo declara o que sabe atender; não há render em tempo de instalação para cobrir o que a curadoria não cobriu.

**Mudança nas regras do upstream só aparece no refresh de curadoria** — o mesmo regime de qualquer conteúdo vendorizado.

**A regra é o terceiro portão de elegibilidade.** Um candidato cujo conteúdo aterrissado dependa de uma resposta do usuário — o `_bmad/config.toml` do BMAD sai de entrevista — não é transformável na curadoria, e reprova aqui. Ver [Critério de elegibilidade e o conjunto de frameworks da v0.1.0](https://github.com/panlabs-tech/overpower/issues/15).
