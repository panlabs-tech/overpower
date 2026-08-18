/**
 * `expandable` — a mesma primitiva do `accordion`, sem a moldura.
 *
 * Ele existe para o aninhamento de campo de API: um objeto que tem
 * propriedades, dentro de um `param-field` ou de um `response-field`. A moldura
 * do accordion ali criaria cartão dentro de cartão a cada nível, e o teto de
 * aninhamento é quatro.
 *
 * **Nível 1 nasce aberto, nível 2 em diante fechado.** A escolha sobrevive a um
 * conflito de medição não adjudicado sobre `Ctrl+F` em `<details>` fechado: ela
 * funciona sob qualquer das duas leituras. Quem decide é o autor, por
 * `defaultOpen`, porque é ele que sabe em que nível está.
 *
 * Zero atributo de parte: `<summary>` alcança por tipo, e o corpo é o único
 * `<div>` filho de `<details>`.
 *
 * Procedência: shinydoc-docusaurus/docs/design/componentes/expandable.md.
 */

import React from 'react';
import estilos from './catalogo.module.css';

export default function Expandable({title, defaultOpen, children}) {
  return (
    <details
      className={estilos.expandable}
      data-sd-component="expandable"
      open={defaultOpen ? true : undefined}>
      <summary className={estilos.expandableSummary}>{title}</summary>
      <div className={estilos.expandableBody}>{children}</div>
    </details>
  );
}
