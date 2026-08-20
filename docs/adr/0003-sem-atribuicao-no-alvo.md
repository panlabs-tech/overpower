# O overpower não escreve atribuição no repositório alvo

No alvo aterrissa exatamente o conteúdo da árvore dos artefatos, e nada mais: nenhum `NOTICE`, nenhum `LICENSE` acrescentado, nenhuma procedência.

## Considered Options

A objeção levantada foi jurídica. A MIT exige que o aviso de copyright acompanhe *"all copies or substantial portions of the Software"*, e copiar 41 skills do `mattpocock/skills` para o repositório de alguém é cópia de porção substancial. O destino deste mapa é ambiente corporativo, onde uma revisão de compliance é exatamente quem marca código de terceiro sem atribuição. A proposta era aterrissar um arquivo de atribuição por origem, idempotente e nunca mesclado, que carregaria a procedência de graça.

Foi rejeitada, e o fundamento é medido: **a dinâmica incumbente já é essa**. No `~/.agents/skills` deste dev, instalado por `npx skills`, há 22 skills aterrissadas e **zero** `LICENSE` de framework. O único arquivo de licença presente é `frontend-design/LICENSE.txt`, que está *dentro* da árvore daquela skill porque o upstream o pôs lá.

Isso dá uma regra melhor que a proposta: **o que está dentro da árvore do artefato viaja; nada é acrescentado.** A atribuição acontece na medida em que o upstream escolheu fazê-la. O `mattpocock/skills` mantém o `LICENSE` na raiz do repo, então ele fica para trás — e isso é fidelidade à árvore, não omissão.

## Consequences

**Divergência registrada.** A mesma medição mostrou que a dinâmica não é idêntica ao incumbente: o `npx skills` escreve `~/.agents/.skill-lock.json` (9,1 KB) e um `skills-lock.json` por projeto, e esse lock **registra procedência** — `source: "mattpocock/skills"`, `sourceType: "github"` por skill. Sob o axioma "sem estado no alvo" o overpower não escreve nada disso, o que o torna **mais estrito** que o incumbente, não igual. A perda dessa procedência foi aceita conscientemente.

O `NOTICE` do wheel, decidido em [Onde os assets vivem e como entram no wheel](https://github.com/ThiagoPanini/overpower/issues/11), segue valendo: ele cobre a distribuição da ferramenta, que é outra cópia e outra obrigação.
