/**
 * O registro global do catálogo — **degrau 3** do ADR 2 do shinydoc.
 *
 * Cabeçalho de versão obrigatório, porque o gerador do Docusaurus remove o
 * cabeçalho de licença ao ejetar e sem anotação não há contra o que diffar:
 *
 *   ejetado de @docusaurus/theme-classic@3.10.2
 *
 * É **registro, não swizzle**: o arquivo é um objeto, e o que se faz com ele é
 * espalhar o original e acrescentar chaves. Zero linha de lógica upstream
 * copiada — o próprio `getSwizzleConfig` diz *"meant to be ejected"*.
 *
 * O que o upgrade cobra: chave nova ou removida vira **erro de build**, não bug
 * de runtime.
 *
 * ---------------------------------------------------------------------------
 * Por que TUDO é global e nada se importa
 *
 * Nenhum arquivo de conteúdo escreve um `import`. A medição das referências
 * achou zero imports de snippet nos alvos: autor não importa. Catálogo que exige
 * import é catálogo que vira `export const` inline no arquivo — foram dezenas
 * delas nos dois sites medidos.
 *
 * **Custo aceito, registrado:** `MDXComponents` é importado por `MDXContent`,
 * que envolve todo conteúdo MDX, então este objeto entra no bundle de toda
 * página com MDX, sem tree-shaking. Se um dia doer, separar os três de
 * referência — `ParamField`, `ResponseField` e `Expandable` —
 * é mecânico e não muda a sintaxe dos outros.
 *
 * **Armadilha fechada:** não se anota este arquivo com
 * `import type {MDXComponentsObject} from '@theme/MDXComponents'`. O alias
 * resolveria para o próprio arquivo e criaria referência circular. Importa-se o
 * VALOR de `@theme-original/`.
 *
 * ---------------------------------------------------------------------------
 * DUAS CHAVES DE ELEMENTO, e a diferença entre elas vale nomeada
 *
 * `table` **substitui** o elemento por um componente nosso. `h1` **envolve** o
 * do upstream e acrescenta um irmão — o subtítulo. É a primeira vez que este
 * registro redefine elemento de HTML para acrescentar nó em vez de trocar
 * anatomia, e é a superfície nova que o ledger de swizzle registra.
 *
 * ---------------------------------------------------------------------------
 * Quem NÃO está aqui, e por quê
 *
 * · `callout` — é a admonition nativa. A sintaxe é `:::note`, e quem a alcança é
 *   `src/theme/Admonition/Types.js`, o outro registro de degrau 3.
 * · `code-block` — é a cerca de Markdown. O upstream já registra `pre` e `code`;
 *   o que falta é CSS sobre `.theme-code-block` (degrau 1) mais
 *   `themeConfig.prism` (degrau 2).
 *
 * Procedência: shinydoc-docusaurus/docs/design/componentes/README.md · shinydoc-docusaurus/docs/design/swizzle.md.
 */

import React from 'react';
import MDXComponents from '@theme-original/MDXComponents';
import {useDoc} from '@docusaurus/plugin-content-docs/client';
import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

import Accordion, {AccordionGroup} from '@site/src/components/Accordion';
import Card, {CardGroup} from '@site/src/components/Card';
import CodeGroup from '@site/src/components/CodeGroup';
import Expandable from '@site/src/components/Expandable';
import Frame from '@site/src/components/Frame';
import Icon from '@site/src/components/Icon';
import Steps, {Step} from '@site/src/components/Steps';
import Table from '@site/src/components/Table';
import Untranslated from '@site/src/components/Untranslated';
import Update from '@site/src/components/Update';
import {ParamField, ResponseField} from '@site/src/components/Campo';

/**
 * O SUBTÍTULO — a linha que toda página do site ganha abaixo do título.
 *
 * Ele sai do `description` do front matter, e a fonte é **uma só**: o mesmo
 * campo que já alimenta o `<meta name="description">`, o `llms.txt` e o índice
 * de busca. Um componente aqui obrigaria o autor a digitar a mesma frase duas
 * vezes e criaria a possibilidade de o subtítulo e o `<meta>` divergirem.
 *
 * **Por que ele cabe no degrau 3.** A alternativa era injetar nó no corpo da
 * página, que é a perda 1 do ledger e exige `DocItem/Layout` ou
 * `DocItem/Content` — os dois `unsafe`, os dois proibidos. Ancorar no `<h1>`
 * pelo registro alcança, e a condição que isso exige está conferida: **61 de 61
 * páginas escrevem o próprio `# Título`**, e nenhuma escreve dois. A conferência
 * deixou de ser varredura de mão: a cobrança 10 do portão 4 percorre `conteudo/`
 * e a árvore de tradução e reprova a primeira página sem `description`.
 *
 * **Superfície nova no mesmo degrau.** É a primeira vez que este registro
 * REDEFINE um elemento de HTML em vez de acrescentar componente. Não é degrau
 * novo — continua sendo objeto espalhado com chave a mais —, mas é uso novo, e
 * vai nomeado no ledger.
 *
 * **Por que ele mora AQUI e não num arquivo próprio**, e não é pelo portão: o
 * portão 7 varre `src/theme/`, então um `src/components/Titulo.js` passaria
 * igual. O motivo é que `src/components/` é o CATÁLOGO — dezessete componentes
 * contados, cada um com documento de nove seções e cada um alcançável do MDX
 * por tag. O subtítulo não é nenhuma das três coisas: ele é chrome, não tem
 * documento de catálogo, e o autor nunca o escreve. Pô-lo lá adicionaria um
 * décimo oitavo arquivo a uma pasta cuja contagem é afirmação da spec.
 *
 * **Ele é obrigatório, e a ausência QUEBRA O BUILD.** Mesma doutrina de nome de
 * ícone inexistente e de rótulo repetido em `CodeGroup`: falha alto, nunca
 * degradação silenciosa. Na âncora ele é condicional — presente em 5 de 8
 * páginas medidas; aqui não.
 *
 * **A ordem no topo da página** passa a ser `h1` → subtítulo → `<Untranslated />`
 * → corpo. O `<Untranslated />` é escrito pelo autor logo abaixo do título e o
 * subtítulo é injetado aqui, então ele nasce antes sem ninguém mexer no MDX.
 *
 * O termo `lead` fica morto e não volta. O nome é **subtítulo**: um termo que já
 * enganou uma vez não se recicla com significado novo.
 *
 * `useDoc` é API pública de `@docusaurus/plugin-content-docs/client`, já
 * consumida pelo `ApiDocItem`. Ele estoura fora de um `DocProvider`, e isso é
 * propriedade e não descuido: todo MDX deste site é documentação, e o dia em que
 * um `.mdx` nascer fora de `conteudo/` é o dia de decidir o que o subtítulo dele
 * é — não o dia de descobrir que a página saiu sem um.
 *
 * Procedência: shinydoc-docusaurus/docs/design/chrome.md · shinydoc-docusaurus/docs/design/swizzle.md.
 */
const H1Original = MDXComponents.h1;

function Titulo(props) {
  const {frontMatter, metadata} = useDoc();
  const {description} = frontMatter;

  if (!description) {
    throw new Error(
      `Página sem \`description\` no front matter: ${metadata.source}\n` +
        'O subtítulo abaixo do título sai desse campo, e ele é obrigatório em ' +
        'toda página. Ver shinydoc-docusaurus/docs/design/chrome.md.',
    );
  }

  return (
    <>
      <H1Original {...props} />
      <p className="subtitulo">{description}</p>
    </>
  );
}

export default {
  ...MDXComponents,

  // A segunda chave de ELEMENTO deste registro, e a que muda mais a tela: o
  // subtítulo nasce colado no título, dentro do mesmo `<header>` que o remark
  // do Docusaurus embrulha em volta do h1 do MDX.
  h1: Titulo,

  // A outra chave de elemento. Toda tabela de Markdown nasce dentro da região
  // rolável — o autor não escolhe, e é isso que faz a correção de
  // acessibilidade alcançar a tabela que ninguém lembrou de embrulhar.
  table: Table,

  // Consumidos do Docusaurus como estão, e globais para que `.md` os alcance sem
  // import. Zero swizzle: a anatomia que falta sai de CSS.
  Tabs,
  TabItem,

  // Os treze componentes com tag própria — CATORZE chaves, porque `steps` tem
  // duas. Os outros quatro do catálogo de dezessete não têm tag: `callout` é
  // `:::`, `code-block` é a cerca, `tabs` vem do Docusaurus acima, e `table` é a
  // chave de elemento acima.
  //
  // Inicial maiúscula não é estilo: em MDX v3 a tag minúscula é elemento HTML, e
  // um `<card>` sairia como tag desconhecida.
  Accordion,
  AccordionGroup,
  Card,
  CardGroup,
  CodeGroup,
  Expandable,
  Frame,
  Icon,
  ParamField,
  ResponseField,
  Step,
  Steps,
  Untranslated,
  Update,
};
