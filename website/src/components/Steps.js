/**
 * `steps` — a sequência numerada.
 *
 * `<ol>` e `<li>`, e o número do marcador vem do contador `list-item` que o
 * próprio elemento já incrementa. Não há número renderizado por JavaScript: a
 * lista ordenada **é** a numeração, e é ela que o leitor de tela anuncia.
 *
 * Ícone SUBSTITUI o número, não o acompanha — e a substituição é `:has(svg)` no
 * CSS em vez de uma variante, porque a decisão é por passo e não por lista.
 *
 * Procedência: shinydoc-docusaurus/docs/design/componentes/steps.md · shinydoc-docusaurus/docs/design/icones.md §8.
 */

import React from 'react';
import Icon from './Icon';
import estilos from './catalogo.module.css';

export default function Steps({children}) {
  return (
    <ol className={estilos.steps} data-sd-component="steps">
      {children}
    </ol>
  );
}

export function Step({title, icon, children}) {
  return (
    <li className={estilos.step}>
      {/* Sem `data-sd-part`: o marcador é o único `<span>` filho do passo, e o
          irmão é um `<div>` — a skin alcança por `li > span`. */}
      <span className={estilos.stepMarker}>
        {icon ? <Icon name={icon} size="sm" /> : null}
      </span>
      <div className={estilos.stepBody}>
        {title ? (
          <p className={estilos.stepTitle} data-sd-part="title">
            {title}
          </p>
        ) : null}
        {children}
      </div>
    </li>
  );
}
