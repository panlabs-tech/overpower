/**
 * O mapa `tipo → componente` da admonition — **degrau 3** do ADR 2 do shinydoc.
 *
 * Cabeçalho de versão obrigatório, porque o gerador do Docusaurus remove o
 * cabeçalho de licença ao ejetar e sem anotação não há contra o que diffar:
 *
 *   ejetado de @docusaurus/theme-classic@3.10.2
 *
 * ---------------------------------------------------------------------------
 * Por que aqui e não em `Admonition/Layout`
 *
 * `Admonition/Layout` seria **degrau 5** — `--eject` de componente `safe`, com
 * reconciliação manual a cada upgrade e correção de a11y do upstream que não
 * chega e nada avisa. Não precisa: este arquivo é um **objeto**, e nada obriga
 * as entradas dele a apontarem para `@theme/AdmonitionLayout`. Elas apontam
 * direto para o nosso `Callout`, e a partir daí o DOM inteiro é nosso **sem
 * copiar uma linha de upstream**.
 *
 * O `Admonition` raiz continua `unsafe` e continua **intocado**: ele despacha
 * por tipo para dentro deste mapa, e é só disso que precisamos.
 *
 * ---------------------------------------------------------------------------
 * Por que quatro chaves e não nove
 *
 * O upstream registra cinco tipos mais quatro apelidos legados. Aqui ficam
 * `note`, `info`, `tip` e `warning`, e cada ausência tem motivo:
 *
 * · `danger` tem uso ZERO nas 1.740 páginas medidas;
 * · `caution` está deprecado no próprio código do Docusaurus (`TODO remove
 *   before v4`);
 * · `check` foi fundido no `tip` — a medição mostrou os dois **pixel a pixel
 *   idênticos** em dois sistemas diferentes, e manter dois nomes para o mesmo
 *   desenho é dívida de vocabulário;
 * · `secondary`, `important` e `success` são apelidos legados que o upstream
 *   mantém com rótulo cravado e não traduzido.
 *
 * O que acontece com um tipo ausente é conhecido e aceito: o `Admonition` raiz
 * avisa no console e cai em `info`. Não há tela quebrada.
 *
 * **Restaurar um tipo é uma linha aqui.** `admonitions.keywords` é opção pública
 * (degrau 2), declarada por instância de plugin de conteúdo. O mecanismo fica
 * documentado e não exercido.
 *
 * Procedência: shinydoc-docusaurus/docs/design/componentes/callout.md · shinydoc-docusaurus/docs/design/swizzle.md.
 */

import React from 'react';
import Callout from '@site/src/components/Callout';

const AdmonitionTypes = {
  note: (props) => <Callout variant="note" {...props} />,
  info: (props) => <Callout variant="info" {...props} />,
  tip: (props) => <Callout variant="tip" {...props} />,
  warning: (props) => <Callout variant="warning" {...props} />,
};

export default AdmonitionTypes;
