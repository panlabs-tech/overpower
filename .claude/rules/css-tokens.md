---
paths:
  - "website/src/css/*.css"
  - "website/src/**/*.module.css"
---

# CSS do site — a camada de token

Os cinco arquivos de `website/src/css/` são o layout do site, e três portões os cobram por varredura: passam ou reprovam, sem julgamento. Nenhum deles opina sobre estética — todos os três checam a mesma coisa por ângulos diferentes, que é se o valor nasceu onde devia.

## O andaime já existe — clone dele, não invente

| Arquivo | O que mora nele |
| --- | --- |
| `website/src/css/tokens.css` | as três camadas. **O único arquivo do site com literal de cor, comprimento, tempo ou curva.** |
| `website/src/css/foco.css` | o contrato de estado de entrada. **O único arquivo que escreve `outline`.** |
| `website/src/css/chrome.css` | navbar, faixa de tabs, sidebar, TOC, footer, paginação |
| `website/src/css/componentes.css` | os componentes MDX de autoria |
| `website/src/css/custom.css` | a entrada |

A ordem em que o `docusaurus.config.js` os declara é contrato, e `tokens.css` é o primeiro porque todos os outros o referenciam por nome.

## A regra de referência

Três camadas, e a direção é uma só. O cabeçalho de `tokens.css` a escreve por extenso — leia-o antes de acrescentar um token.

- **Camada 1, raiz.** Literais. Bloco de troca (`SKIN … /SKIN`, o que se re-marca) + base (escalas e a forma da rampa).
- **Camada 2, semântica.** **Só cor.** Oito papéis de lista fechada — `surface`, `text`, `border`, `accent`, `shadow`, `focus`, `state`, `code` — e é o único ponto do sistema onde os dois modos divergem.
- **Camada 3, componente.** Declarada no escopo do próprio componente, **nunca** em `:root`.

**Cor sempre desce pela camada 2** — nenhum componente lê a rampa ou a marca direto. **Dimensão vem direto da camada 1.** O Infima fica do outro lado de um adaptador de mão única no fim de `tokens.css`: o adaptador escreve `--ifm-*`, e nenhuma regra do projeto lê `--ifm-*`.

Faltou o papel na camada 2? O degrau default nunca é um literal novo — é o papel que falta, declarado.

## Os três portões desta área

Rodam de `website/`, cada um em menos de meio segundo. Rode o que a mudança ativa enquanto trabalha; `npm run portoes` roda os três.

- **Portão 1** (`npm run portao:1`) — cor, comprimento, tempo ou curva fora de `tokens.css`. `0`, número sem unidade, `%`, `fr`, `ch`, `lh` e `auto` ficam fora do escopo: são layout, e flagrá-los transformaria o portão em ruído. A segunda perna cobra a **lista fechada de limiares de media query** — `996px`, `997px` e `1280px`, e nada mais.
- **Portão 2** (`npm run portao:2`) — duração ou curva cravada numa transição ou animação. Os seis movimentos nomeados (`--sd-move-{state,enter,expand,showcase,reveal,ambient}`) são o vocabulário fechado, e é o que faz `prefers-reduced-motion` alcançar o Infima e o `theme-classic`, que não escrevemos. A segunda perna recusa transição de cor sobre `html`, `body` ou `:root`.
- **Portão 3** (`npm run portao:3`) — `outline` fora de `foco.css`. Ele existe contra o `outline: none` escrito para "limpar" um botão, que apaga acessibilidade de teclado sem sintoma visível para quem o escreveu.

A varredura cobre `website/src/` inteiro, **CSS Module de componente incluído**.

## De onde isto veio

O tema foi transplantado inteiro de [`panlabs-tech/shinydoc-docusaurus`](https://github.com/panlabs-tech/shinydoc-docusaurus) na [issue #130](https://github.com/ThiagoPanini/overpower/issues/130). Os comentários do CSS citam `shinydoc-docusaurus/docs/design/*.md` e "ADR *n* do shinydoc": esses arquivos moram no gabarito, não aqui, e o prefixo existe justamente para que o ponteiro continue resolvível. A spec de design **não** foi transplantada — o que precisava valer aqui está escrito nesta regra e no cabeçalho de `tokens.css`.

Junto com ela ficaram de fora os portões que dependiam daquela spec: `espelho-tokens`, `contraste`, `paridade` e os portões 4 e 5. Reintroduzir qualquer um deles significa trazer o `docs/design/` correspondente — não vale acrescentar o script sozinho e deixá-lo reprovando por falta do arquivo que ele compara.
