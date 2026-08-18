/**
 * `sd-busca` — o índice local, sem serviço externo.
 *
 * O índice viaja como **dado global**, não como JSON no `outDir`. A alternativa
 * seria `postBuild` gravando um arquivo e o cliente buscando com `fetch()`, e
 * ela tem um modo de falhar invisível: sob `onBrokenLinks` e SPA, uma rota
 * ausente devolve **200 com o shell do site**, então o `fetch().json()` estoura
 * em parse — não em 404. Ninguém liga um parse error a um arquivo que não foi
 * escrito.
 *
 * Dado global também é o que faz a busca funcionar em `docusaurus start`, que
 * nenhum plugin de busca do ecossistema oferece: ele entra no bundle, e o bundle
 * existe no servidor de desenvolvimento.
 *
 * > **Correção de fato, medida nesta implementação.** A resolução do slice
 * > escreveu *`contentLoaded` + `setGlobalData`*. `contentLoaded` recebe o
 * > conteúdo do PRÓPRIO plugin, e este plugin não tem conteúdo nenhum — o que
 * > ele lê são as três instâncias de docs, que só chegam por `allContent`. O
 * > gancho certo é `allContentLoaded`, e ele expõe o mesmo `setGlobalData`
 * > (`server/plugins/actions.js` monta o mesmo objeto de ações para os dois
 * > ganchos). A decisão que a resolução tomou — dado global em vez de arquivo
 * > buscado — vale verbatim; só o nome do gancho estava errado.
 *
 * Zero dependência nova, zero serviço externo. Ver ADR 6 do shinydoc.
 *
 * Procedência: shinydoc-docusaurus/docs/design/busca.md.
 */

import {paginasDe, secoesDoNavbar} from '../paginas';

/**
 * Teto de 64 KB serializados, autoenforçado — **teto, não meta**.
 *
 * Ele não acrescenta portão de CI: o próprio build reprova. Um índice que
 * cresce sem limite vira megabyte no bundle principal de toda página do site,
 * e o sintoma é lentidão difusa que ninguém atribui à busca.
 */
const TETO = 64 * 1024;

/** Corpo indexado por página. Bem menos que a página; o suficiente para casar. */
const CORPO = 200;

/** Linha cercada — abre e fecha o bloco de código. */
const CERCA = /^\s*(?:```|~~~)/;

/** `## Título {#ancora}` — nível 2 a 4, com a âncora explícita opcional. */
const HEADING = /^(#{1,6})\s+(.+?)\s*(?:\{#[^}]*\})?\s*$/;

/**
 * MDX → o texto que a busca casa.
 *
 * Bloco cercado sai inteiro: uma consulta que casasse dentro de um `curl`
 * devolveria a página com um trecho ilegível, e o realce cairia no meio de uma
 * string JSON.
 *
 * @param {string} corpo o MDX sem front matter e sem `import` do topo
 */
function extrair(corpo) {
  const headings = [];
  const prosa = [];
  let dentroDeCerca = false;

  for (const linha of corpo.split('\n')) {
    if (CERCA.test(linha)) {
      dentroDeCerca = !dentroDeCerca;
      continue;
    }
    if (dentroDeCerca) {
      continue;
    }
    const h = HEADING.exec(linha);
    if (h) {
      // O `#` de nível 1 é o título, que já viaja em `t`. Os de 5 e 6 não
      // existem na árvore — o teto de profundidade da spec é 4.
      if (h[1].length >= 2 && h[1].length <= 4) {
        headings.push(h[2]);
      }
      continue;
    }
    prosa.push(linha);
  }

  return {headings, texto: aTextoPlano(prosa.join('\n'))};
}

/**
 * Tira a marcação e devolve prosa.
 *
 * Não é um parser: é o suficiente para que o trecho mostrado ao leitor não
 * comece com `<ParamField name=` nem com uma barra de tabela.
 *
 * @param {string} texto
 */
function aTextoPlano(texto) {
  return texto
    .replace(/<[^>]*>/g, ' ') // tag JSX do catálogo
    .replace(/^\s*:::.*$/gm, ' ') // marcador de admonition
    .replace(/^\s*\|.*$/gm, ' ') // linha de tabela
    .replace(/!?\[([^\]]*)\]\([^)]*\)/g, '$1') // link e imagem, fica o rótulo
    .replace(/[`*_>#]/g, '')
    .replace(/^\s*[-+]\s+/gm, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, CORPO);
}

/**
 * @param {import('@docusaurus/types').LoadContext} context
 * @param {{abas: string[]}} options
 * @returns {import('@docusaurus/types').Plugin}
 */
export default function pluginBusca(context, options) {
  return {
    name: 'sd-busca',

    async allContentLoaded({allContent, actions}) {
      const {i18n, siteDir} = context;
      const secoes = secoesDoNavbar(context.siteConfig.themeConfig);

      const registros = paginasDe({
        allContent,
        siteDir,
        abas: options.abas,
        secoes,
        localeTraduzido: i18n.currentLocale !== i18n.defaultLocale,
      }).map((pagina) => {
        const {headings, texto} = extrair(pagina.corpo);
        return {
          u: pagina.permalink,
          t: pagina.titulo,
          d: pagina.descricao,
          s: headings,
          b: texto,
          x: pagina.indiceSecao,
          // A página de fallback ENTRA no índice, marcada. Escondê-la faria a
          // busca em EN devolver menos do que o site tem — o leitor chegaria na
          // página por link e não pela busca, o que é pior que o português.
          ...(pagina.fallback ? {f: 1} : {}),
        };
      });

      const bytes = Buffer.byteLength(JSON.stringify(registros), 'utf8');
      if (bytes > TETO) {
        const maiores = [...registros]
          .sort((a, b) => JSON.stringify(b).length - JSON.stringify(a).length)
          .slice(0, 5)
          .map((r) => `  ${JSON.stringify(r).length} B  ${r.u}`)
          .join('\n');
        throw new Error(
          [
            `O índice de busca estourou o teto: ${bytes} B contra ${TETO} B (locale ${i18n.currentLocale}).`,
            'É teto, não meta — o índice viaja no bundle principal de toda página do site.',
            'As cinco maiores entradas:',
            maiores,
          ].join('\n'),
        );
      }

      // Os rótulos viajam junto porque quem os traduz é o servidor: eles saem
      // do navbar, que o core já traduziu quando este gancho roda. Resolvê-los
      // no cliente exigiria reimplementar a mesma regra num segundo lugar.
      actions.setGlobalData({
        registros,
        secoes: secoes.map((secao) => secao.rotulo),
      });
    },
  };
}
