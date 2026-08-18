/**
 * `icon` — o veículo dos 40 ícones de autoria dentro do MDX.
 *
 * Ele não resolve desenho: delega ao registro de `src/icons/registry.js`, que é
 * quem lança com sugestão de vizinho quando o nome não existe. Nome inexistente
 * é **erro de build**, porque o Docusaurus prerenderiza toda página.
 *
 * A compensação óptica por tamanho só existe porque a técnica é SVGR e não
 * `mask-image`: com máscara o interior não se restiliza, e a alternativa seria
 * um arquivo por tamanho.
 *
 * Procedência: shinydoc-docusaurus/docs/design/componentes/icon.md · shinydoc-docusaurus/docs/design/icones.md §2.1.
 */

import React from 'react';
import clsx from 'clsx';
import {resolverIcone} from '@site/src/icons/registry';
import estilos from './catalogo.module.css';

/**
 * Um mapa por tamanho, e não dois com as mesmas chaves.
 *
 * `traco` é a tabela de compensação óptica de `icones.md` §2.1, e ela é **prop,
 * nunca token de CSS** — o valor precisa restilizar o interior do desenho.
 * `classe` é como o nosso CSS dimensiona; `data-sd-variant` é o gancho da skin.
 */
const TAMANHOS = {
  sm: {traco: 2.25, classe: estilos.iconSm},
  md: {traco: 2, classe: estilos.iconMd},
  lg: {traco: 1.75, classe: estilos.iconLg},
};

export default function Icon({name, size = 'sm'}) {
  const Desenho = resolverIcone(name);
  const {traco, classe} = TAMANHOS[size] ?? TAMANHOS.sm;

  // O ícone é SEMPRE decorativo e sai da árvore de acessibilidade — o que está
  // certo em toda a autoria medida: o significado está no texto ao lado.
  // `focusable="false"` fecha a armadilha do IE legada que ainda vive em
  // leitores de tela sobre `<svg>` dentro de link.
  //
  // HAVIA uma prop `label` que virava `role="img"` mais `aria-label`, e ela
  // saiu por não ter consumidor: zero chamadas em `conteudo/` e `role="img"`
  // em ZERO dos 108 HTML publicados. Um ramo de ARIA que nunca roda é pior que
  // ausente — ele parece cobertura de acessibilidade numa leitura de código, e
  // não é. Se um ícone um dia carregar significado sozinho, a prop volta com o
  // call site junto; sem call site ela não tem como ser conferida.
  return (
    <Desenho
      data-sd-component="icon"
      data-sd-variant={size}
      className={clsx(estilos.icon, classe)}
      strokeWidth={traco}
      focusable="false"
      aria-hidden="true"
    />
  );
}
