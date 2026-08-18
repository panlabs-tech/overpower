/**
 * `update` — a entrada de changelog.
 *
 * O changelog é o **único** canal de comunicação de versão da API neste site: o
 * conteúdo não é versionado, a API é — por cabeçalho. Esta é a anatomia dessa
 * comunicação.
 *
 * Um `<section>` com `<header>`, e o header é o que evita atributo de parte:
 * dois `<div>` irmãos precisariam de nome, um `<header>` alcança por tipo. A
 * etiqueta também não ganha atributo — é o único elemento dentro do `<header>`,
 * e a skin a alcança por `header > span`. **Zero partes publicadas.**
 *
 * Procedência: shinydoc-docusaurus/docs/design/componentes/update.md.
 */

import React from 'react';
import estilos from './catalogo.module.css';

export default function Update({label, tag, children}) {
  return (
    <section className={estilos.update} data-sd-component="update">
      <header className={estilos.updateHead}>
        {label}
        {tag ? <span className={estilos.updateTag}>{tag}</span> : null}
      </header>
      <div className={estilos.updateBody}>{children}</div>
    </section>
  );
}
