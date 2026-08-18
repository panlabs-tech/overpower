/**
 * `callout` — o corpo da **admonition nativa**.
 *
 * Este componente não é registrado em `MDXComponents`: quem o alcança é
 * `src/theme/Admonition/Types.js`, o registro de degrau 3 que troca o mapa
 * `tipo → componente` do Docusaurus. O `Admonition` raiz — que é `unsafe` —
 * continua intocado e despacha por tipo para dentro do mapa; a partir daí o DOM
 * é inteiramente nosso, **sem uma linha de upstream copiada**.
 *
 * Consequência de anatomia: a barra lateral de 5px e a faixa de título
 * MAIÚSCULA do Infima não existem porque não as escrevemos. O `.alert` também
 * não — este DOM não é um `.alert`.
 *
 * Quatro variantes, e o autor não escolhe ícone: os tipados da âncora não
 * aceitam prop nenhuma, e o ícone é o que carrega a semântica da variante.
 *
 * Procedência: shinydoc-docusaurus/docs/design/componentes/callout.md.
 */

import React from 'react';
import clsx from 'clsx';
import Icon from './Icon';
import estilos from './catalogo.module.css';

/**
 * O glifo por variante — fixo, do papel `sistema` do manifesto.
 *
 * `info` é a variante NEUTRA e `note` é a azul. A inversão é deliberada e é o
 * que faz o sistema ler como a âncora; ver `componentes/callout.md`.
 */
/**
 * Um mapa por variante, e não dois mapas com as mesmas chaves: duas tabelas
 * paralelas é como uma variante ganha glifo e não ganha classe.
 *
 * A variante entra no DOM duas vezes, e é de propósito. Como classe de módulo,
 * porque é assim que o nosso CSS pinta — especificidade (0,1,0). Como
 * `data-sd-variant`, porque é assim que a skin corporativa repinta — (0,2,0),
 * que vence sem um único `!important`. Nosso CSS nunca lê `data-sd-*`: se lesse,
 * as duas camadas empatariam e a ordem de carga passaria a decidir.
 *
 * `info` não tem classe porque ela é a variante NEUTRA, e neutro é o default
 * declarado no próprio `.callout`.
 */
const VARIANTES = {
  note: {glifo: 'pencil-line', classe: estilos.calloutNote, tamanho: 'sm'},
  info: {glifo: 'info', classe: undefined, tamanho: 'md'},
  tip: {glifo: 'lightbulb', classe: estilos.calloutTip, tamanho: 'md'},
  warning: {glifo: 'triangle-alert', classe: estilos.calloutWarning, tamanho: 'md'},
};

/* Sem prop `id`. Ela existiu como repasse para o atributo do `<div>` e saiu por
   não ter consumidor: ZERO call sites em `conteudo/`. Um callout não é destino
   de link neste site — os âncoras de navegação são os headings, que o
   Docusaurus já ancora sozinho —, e um `id` que ninguém escreve rendia
   `id={undefined}` em toda instância. Volta com o call site junto no dia em que
   um callout precisar de endereço próprio. */
export default function Callout({variant, title, children}) {
  const {glifo, classe, tamanho} = VARIANTES[variant] ?? VARIANTES.info;
  return (
    <div
      className={clsx(estilos.callout, classe)}
      data-sd-component="callout"
      data-sd-variant={variant}>
      <Icon name={glifo} size={tamanho} />
      {/* Sem `data-sd-part` no corpo: ele é o único `<div>` filho, e o irmão é
          um `<svg>` — a skin alcança por `> div`. O título, não: ele é um `<p>`
          entre os `<p>` que o autor escreve, e nenhum seletor de tipo o separa
          deles. */}
      <div className={estilos.calloutContent}>
        {title ? (
          <p className={estilos.calloutTitle} data-sd-part="title">
            {title}
          </p>
        ) : null}
        {children}
      </div>
    </div>
  );
}
