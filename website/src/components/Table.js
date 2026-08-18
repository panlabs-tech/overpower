/**
 * `table` — Markdown puro, mais o invólucro de rolagem.
 *
 * O autor escreve uma tabela de Markdown e não escreve tag nenhuma: este
 * componente entra pela chave `table` de `MDXComponents`, então **toda** tabela
 * do site nasce embrulhada.
 *
 * Ele é o **único lugar do catálogo onde ARIA aparece**, e aparece porque o HTML
 * não tem elemento para isto: sem `role="region"` mais `tabindex`, um leitor de
 * teclado não consegue rolar uma tabela larga. Região sem nome acessível é
 * defeito, então o rótulo vem da camada de i18n.
 *
 * Ele também corrige um defeito do Infima que ninguém tinha nomeado: o
 * framework declara `table { display: block; overflow: auto }`. Isso resolve o
 * transbordo e cobra caro — `display: block` **tira a semântica de tabela** da
 * árvore de acessibilidade, e o contêiner que rola não é focável. O invólucro
 * devolve as duas coisas: a rolagem sai do `<table>` e vai para uma região
 * nomeada e alcançável por Tab, e o `<table>` volta a ser `display: table`.
 *
 * A exceção de foco que este `[role="region"]` poderia disparar já está fechada:
 * o `:has()` de `foco.css` §2 exige o link de pular conteúdo como filho direto,
 * e aqui o filho é um `<table>`.
 *
 * Procedência: shinydoc-docusaurus/docs/design/componentes/table.md.
 */

import React from 'react';
import {translate} from '@docusaurus/Translate';
import estilos from './catalogo.module.css';

export default function Table({children, ...resto}) {
  return (
    <div
      className={estilos.table}
      data-sd-component="table"
      role="region"
      tabIndex={0}
      aria-label={translate({
        id: 'shinydoc.tabela.regiao',
        message: 'Tabela',
        description: 'Nome acessível da região rolável que envolve toda tabela',
      })}>
      <table {...resto}>{children}</table>
    </div>
  );
}
