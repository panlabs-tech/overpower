/**
 * `param-field` e `response-field` — **parâmetro de função** e **campo de
 * retorno**, os dois campos da referência de biblioteca.
 *
 * **Os dois sobreviveram à troca de contrato por nunca terem sido HTTP.** O
 * vocabulário deles é nome, tipo, obrigatoriedade, valor padrão e descrição — as
 * mesmas cinco informações de um argumento de função e de um campo devolvido —, e
 * a medição confirma a leitura: o `ParamField` da âncora usa **só `body=`**,
 * nunca `query`, `path` ou `header`. Quem era HTTP era o `VerbBadge`, e ele saiu
 * do catálogo.
 *
 * Um componente interno com uma prop de espécie, e não duas anatomias
 * paralelas: duplicar a anatomia inteira para ganhar duas props é como se
 * acumula divergência visual entre irmãos. Continuam sendo **dois componentes
 * autoráveis** e dois arquivos de spec — o gabarito é por tag, não por arquivo
 * de código.
 *
 * **Zero JS.** Nenhum dos dois alimenta playground: a edição do nível 1 mora no
 * painel do `ApiDocItem`, que é território da rota e não do catálogo. O
 * aninhamento é `expandable`, e a recursão de `response-field` é o autor
 * escrevendo outro `response-field` dentro do primeiro.
 *
 * Duas coisas que a âncora decidiu e nós herdamos: só `required` se marca — a
 * ausência é o sinal de opcional, e marcar as duas divide por dois a saliência
 * do que importa —, e o chip dele é **vermelho, com a palavra por extenso**.
 * `deprecated` continua tachado mais texto apagado, **sem cor**, por razão nova:
 * o vermelho passou a ser do chip de obrigatório.
 *
 * Procedência: shinydoc-docusaurus/docs/design/componentes/param-field.md · response-field.md.
 */

import React from 'react';
import clsx from 'clsx';
import Translate, {translate} from '@docusaurus/Translate';
import estilos from './catalogo.module.css';

// Só identificador de código como entrada — minúsculo e ASCII por contrato do
// gerador (`scripts/lib/assinatura.mjs`). Sem normalização de acento: não há
// acento a normalizar.
function slugificar(nome) {
  return nome.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
}

function Campo({especie, name, type, required, deprecated, padrao, children}) {
  const id = `campo-${especie}-${slugificar(name)}`;

  return (
    <div
      id={id}
      // Classe de módulo para o nosso CSS (0,1,0); `data-sd-variant` para a
      // skin (0,2,0). Nosso CSS nunca lê `data-sd-*`.
      className={clsx(estilos.field, deprecated && estilos.fieldDeprecated)}
      data-sd-component={especie}
      data-sd-variant={deprecated ? 'deprecated' : undefined}>
      <p className={estilos.fieldHead}>
        {/* A âncora de linha, no vão esquerdo — mesma ideia do `.hash-link` de
            heading (Infima), implementação própria porque aqui não há
            `remark-plugin` gerando o link: é um campo, não um heading. Parte
            publicada (`data-sd-part="ancora"`) para o fallback de toque em
            `foco.css` alcançar sem depender do hash de CSS Module. */}
        <a
          href={`#${id}`}
          className={estilos.fieldAncora}
          data-sd-part="ancora"
          aria-label={translate(
            {
              id: 'shinydoc.campo.ancora',
              message: 'Link para {nome}',
              description: 'Nome acessível da âncora de linha de um campo de API',
            },
            {nome: name},
          )}>
          #
        </a>
        <code>{name}</code>
        {/* `meta` é a única parte publicada do catálogo que a régua estreita
            NÃO obriga: ela é o único `<span>` do cabeçalho, e a skin a
            alcançaria por `> span`. Ela fica porque a rota gerada a nomeia
            verbatim no contrato de partes dela, e despublicar depois quebra quem
            já dependeu — o que a régua também diz. A condição é CONFERIDA, e não
            afirmada: o portão 5 casa esta linha com as páginas geradas de tipo e
            função — a do módulo não tem parâmetro nem retorno —, e reprova se o
            ramo gerado deixar de consumir o campo. */}
        <span className={estilos.fieldMeta} data-sd-part="meta">
          <span className={estilos.fieldChip}>{type}</span>
          {padrao === undefined ? null : (
            <span className={estilos.fieldChip}>
              <Translate id="shinydoc.campo.padrao" description="Rótulo do valor default de um campo de API">
                padrão
              </Translate>{' '}
              <code>{padrao}</code>
            </span>
          )}
          {required ? (
            <strong>
              <Translate
                id="shinydoc.campo.obrigatorio"
                description="Chip que marca um parâmetro obrigatório">
                obrigatório
              </Translate>
            </strong>
          ) : null}
        </span>
      </p>
      <div className={estilos.fieldBody}>{children}</div>
    </div>
  );
}

export function ParamField({default: padrao, ...resto}) {
  return <Campo especie="param-field" padrao={padrao} {...resto} />;
}

export function ResponseField({default: padrao, ...resto}) {
  return <Campo especie="response-field" padrao={padrao} {...resto} />;
}
