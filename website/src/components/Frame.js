/**
 * `frame` — a moldura de **diagrama**, não de screenshot.
 *
 * A decisão de conteúdo vem antes da de anatomia, e ela não depende mais de o
 * produto ser fictício: sem CDN o asset binário entra no repositório, captura de
 * UI de terceiro apodrece sozinha, e **raster não herda `currentColor`**. Os três
 * cortam contra mídia binária de qualquer origem. O que a moldura enquadra é
 * fluxo, ciclo de vida, modelo de dados.
 *
 * Isso encolhe o componente: o fundo quadriculado da âncora existe para
 * enquadrar imagem com transparência, e sem screenshot ele perde a razão de ser.
 * Sobra o palco tingido — sem legenda: o alvo não renderiza `figcaption`, e
 * `research/paridade-devin` §11 mede isso contra o mesmo `mint` do Devin que
 * pediu o palco tingido.
 *
 * E cria a segunda das **duas** exceções do catálogo à regra de que nenhum
 * componente conhece modo de cor: o palco declara `color`, e o diagrama que
 * vive nele usa `currentColor` — **um arquivo para os dois modos**, nunca um
 * asset por modo. É a mesma regra que fecha a rota de entrega: o diagrama chega
 * ao MDX como SVG INLINE, porque `<img src="x.svg">` não herda `currentColor`.
 *
 * Procedência: shinydoc-docusaurus/docs/design/componentes/frame.md.
 */

import React from 'react';
import estilos from './catalogo.module.css';

export default function Frame({children}) {
  return (
    <figure className={estilos.frame} data-sd-component="frame">
      <div className={estilos.frameStage}>{children}</div>
    </figure>
  );
}
