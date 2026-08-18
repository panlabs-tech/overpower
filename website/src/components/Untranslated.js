/**
 * `untranslated` — o marcador de página não traduzida.
 *
 * O EN cobre orientar-se e consultar; o pt-BR cobre também executar no mercado
 * local. As páginas sem contraparte são geradas **em silêncio**, com o texto em
 * português, sem aviso e sem relatório — e uma spec que nunca exercita esse
 * estado não decidiu nada sobre ele; só não esbarrou nele.
 *
 * A mecânica se resolve sozinha porque a tradução substitui o arquivo inteiro:
 * o marcador aparece em `/en/` exatamente enquanto não houver contraparte, e
 * some no instante em que houver. **Sem lista para manter, sem flag, sem drift
 * possível.**
 *
 * E ele não viola o *zero JS de interação*, que é regra sobre modelo de
 * interação — tecla, foco, estado. Ler o locale do contexto e devolver `null` é
 * renderização condicional.
 *
 * Procedência: shinydoc-docusaurus/docs/design/componentes/untranslated.md.
 */

import React from 'react';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Translate from '@docusaurus/Translate';
import Icon from './Icon';
import estilos from './catalogo.module.css';

export default function Untranslated() {
  const {
    i18n: {currentLocale, defaultLocale},
  } = useDocusaurusContext();

  // No locale de origem não há o que sinalizar, e o componente não deixa rastro
  // no DOM. É por isso que o autor pode escrevê-lo sem pensar em qual locale
  // está lendo.
  if (currentLocale === defaultLocale) {
    return null;
  }

  return (
    <aside className={estilos.untranslated} data-sd-component="untranslated">
      <Icon name="languages" size="sm" />
      <p>
        <Translate
          id="shinydoc.untranslated.aviso"
          description="Aviso no topo de uma página que ainda não foi traduzida">
          Esta página ainda não foi traduzida. O conteúdo abaixo está em português.
        </Translate>
      </p>
    </aside>
  );
}
