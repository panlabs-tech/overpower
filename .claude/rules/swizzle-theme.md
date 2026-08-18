---
paths:
  - "website/src/theme/**/*.js"
  - "website/src/theme/**/*.mjs"
  - "website/src/theme/**/*.css"
---

# `website/src/theme/` — swizzle, e o ledger que o cobra

Baixa frequência, **falha silenciosa alta**. A doc do Docusaurus é explícita: um componente renomeado no upstream faz o arquivo swizzlado ser **completamente ignorado**, sem erro. Nenhum build reprova, porque não há nada errado a reprovar — a customização simplesmente para de existir, o arquivo vira código morto, e nada avisa.

## A pegadinha que custa a CI

Swizzlou um componente novo, ou subiu a versão do `@docusaurus/theme-classic`? **Rode `npm run swizzle:congelar`** de dentro de `website/`. Ele reescreve `website/scripts/swizzle-list.txt` (220 linhas hoje), e o **portão 7** (`npm run portao:7`) confere `src/theme/` contra ela.

O portão 7 **não está em `npm run portoes`** — ele roda `docusaurus swizzle --list` de verdade, custa uma dezena de segundos, e a superfície que ele confere só muda quando o tema muda de versão. Verde no bundle local não diz nada sobre ele; quem o cobra é a CI.

## Zero `unsafe`

O orçamento de swizzle `unsafe` é **zero**, e o portão 7 o cobra. Um componente marcado `unsafe` no ledger do Docusaurus não entra por conveniência: `unsafe` quer dizer que o upstream reserva o direito de mudar a forma dele numa versão menor.

## Antes de descer para o swizzle

A escada tem degraus mais baratos, e a disciplina é subir até achar o que não alcança:

- **Degrau 0** — variável do Infima, via o adaptador no fim de `website/src/css/tokens.css`.
- **Degrau 1** — classe estável em `website/src/css/chrome.css`.
- **Degrau 2+** — swizzle.

O ícone de sidebar é o exemplo vivo do degrau 1 vencendo: ele é `mask-image` em CSS, e não React, porque **não existe ponto de swizzle `safe` para injetar um componente num item de sidebar**.

## O que já mora aqui

| Path | O que é |
| --- | --- |
| `website/src/theme/SearchBar/index.js` | **ejeção** — o modal `<dialog>` da busca local. Só funciona com o plugin `src/plugins/busca` ligado: ele lê o índice por `useGlobalData`. |
| `website/src/theme/SearchBar/escada.mjs` | a escada de pontuação, lógica pura — não é swizzle, é arquivo interno. |
| `website/src/theme/MDXComponents/index.js` | **ejeção** — o registro global do catálogo. É por causa dele que nenhum arquivo de conteúdo escreve `import`. |
| `website/src/theme/Admonition/Types.js` | **ejeção** — o mapa `tipo → componente`, reduzido a `note`/`info`/`tip`/`warning`. É quem alcança `src/components/Callout.js`, que não está em `MDXComponents`. |

Três coisas diferentes convivem nesta pasta e não se misturam: componente swizzlado, arquivo interno de um swizzle, e componente de tema próprio. A terceira categoria está **vazia** hoje — a lista `PROPRIOS` em `website/scripts/swizzle-list.mjs` não tem membro, e um componente novo que o `theme-classic` não conheça precisa ser declarado lá ou o portão 7 o acusa de código morto.

## De onde isto veio

Transplantado de [`panlabs-tech/shinydoc-docusaurus`](https://github.com/panlabs-tech/shinydoc-docusaurus) na [issue #130](https://github.com/panlabs-tech/overpower/issues/130), sem o `ApiDocItem`: ele servia referência **gerada** de um contrato JSON, e a geração ficou de fora por decisão — trazer o layout sem o gerador seria tema sem consumidor.

O número 7 do portão veio com o gabarito. Este site tem **quatro** portões — 1, 2, 3 e 7 —, e o buraco na numeração é deliberado: renumerar não compraria nada e quebraria a leitura cruzada com o repositório de onde o mecanismo veio.
