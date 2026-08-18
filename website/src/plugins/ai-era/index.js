/**
 * `sd-ai-era` — o `.md` por rota, o `llms.txt` e o `llms-full.txt`.
 *
 * Zero swizzle, zero dependência, zero serviço. O plugin lê a mesma porta que a
 * busca (`allContentLoaded`) e escreve três formatos no `outDir`.
 *
 * **Os permalinks saem de `allContentLoaded`, e não de `postBuild({routesPaths})`.**
 * Dois motivos verificados no fonte do 3.10.2, não deduzidos:
 *
 *   1. `routesPaths[0]` é **sempre `/404.html`** — a lista carrega rota que não
 *      é página, e filtrá-la exigiria saber de cor quais são;
 *   2. a API tem TODO de depreciação para a v4, escrito no próprio tipo.
 *
 * **`applyTrailingSlash` não é importado.** Ele existe e é exportado de
 * `@docusaurus/utils-common`, mas não tem página de documentação oficial nem
 * semver documentada — importá-lo é amarrar o build a um contrato que ninguém
 * prometeu. E sob `trailingSlash: false` (ADR 7 do shinydoc) ele seria no-op: o permalink
 * já vem sem barra, então `permalink + '.md'` é concatenação pura, sem uma
 * transformação no caminho.
 *
 * **Perda aceita e nomeada:** em `docusaurus start` as rotas `.md` não existem.
 * O servidor de desenvolvimento é uma SPA, então elas devolvem 200 com o shell
 * do site — não 404. É recurso de build, e quem o verifica é o portão 6 rota 2,
 * contra o host real. `npm run build && npm run serve` mostra o mesmo.
 *
 * https://github.com/panlabs-tech/overpower/issues/129
 */

import fs from 'node:fs/promises';
import path from 'node:path';

import {paginasDe, secoesDoNavbar} from '../paginas';

/**
 * O separador de documento do `llms-full.txt`, na forma do Neon.
 *
 * Das três referências que publicam o artefato, é a única inequívoca para
 * máquina: o separador carrega a URL de origem, então o parser não precisa
 * inferir onde um documento termina nem de onde ele veio.
 */
const separador = (url) => `--- [Document source](${url}) ---`;

/**
 * O corpo com o subtítulo emitido como citação abaixo do `h1`.
 *
 * O corpo servido é o MDX **sem front matter**, e o subtítulo mora no
 * `description` — então o `.md` sairia sem ele, enquanto a tela o pinta logo
 * abaixo do título (`@theme/MDXComponents`, o override de `h1`) e o `llms.txt`
 * o carrega em cada linha de listagem. Perder a informação só no formato lido
 * por máquina é o avesso do que os três artefatos existem para fazer.
 *
 * A forma é a do export do Devin, a única das três referências medidas que
 * resolve o caso: citação imediatamente abaixo do `h1`, na mesma posição em que
 * a tela a mostra. Adotar é herdar uma convenção que já circula entre parsers.
 *
 * **A âncora é o `h1`, e a falta dele estoura.** Uma citação no topo do
 * arquivo já significa outra coisa aqui — é o ponteiro de volta ao índice. Sem
 * `h1` para separá-los, os dois blocos se fundiriam num só e o subtítulo viraria
 * segunda linha do ponteiro, calado.
 *
 * **A busca é na PRIMEIRA linha com texto, e não pela primeira que casa.** A
 * diferença aparece no dia em que uma página abrir com bloco cercado:
 * `# comentário` de shell casaria a mesma marca, e a citação entraria no meio do
 * código — sem erro, sem aviso, e visível só para quem abrisse o `.md`. Como
 * `paginasDe` já tirou o front matter e o `import` do topo, a primeira linha com
 * texto é o `h1` do autor em todas as 73 páginas, e exigir isso troca a
 * inserção errada por uma mensagem.
 *
 * O `llms-full.txt` NÃO passa por aqui: lá a descrição já entra como
 * `> Summary:` acima do separador de documento, que é a forma do Neon. Duas
 * cópias do mesmo campo no mesmo documento seriam ruído para o parser.
 *
 * @param {{corpo: string, descricao: string, permalink: string}} pagina
 */
function comSubtitulo({corpo, descricao, permalink}) {
  // A carga também é conferida, e não só a âncora. O override de `h1` já
  // estoura sem `description` — mas ele é swizzle, e swizzle sai. Se saísse, o
  // `.md` passaria a emitir uma citação vazia: um `>` solto, sem erro e sem
  // aviso, que é o modo de falhar que esta função existe para não ter.
  if (!descricao?.trim()) {
    throw new Error(
      `Página sem \`description\`: ${permalink}\n` +
        'O subtítulo do `.md` servido sai desse campo, e ele é obrigatório em ' +
        'toda página. Ver a spec do site.',
    );
  }

  const linhas = corpo.split('\n');
  const indiceDoTitulo = linhas.findIndex((linha) => linha.trim() !== '');
  if (indiceDoTitulo === -1 || !linhas[indiceDoTitulo].startsWith('# ')) {
    throw new Error(
      `Página que não abre com \`# título\`: ${permalink}\n` +
        'O `.md` servido emite o subtítulo como citação abaixo do `h1`, e a ' +
        'âncora é a primeira linha com texto do corpo. ' +
        'Ver a spec do site.',
    );
  }

  return [
    ...linhas.slice(0, indiceDoTitulo + 1),
    '',
    `> ${descricao}`,
    ...linhas.slice(indiceDoTitulo + 1),
  ].join('\n');
}

/**
 * @param {import('@docusaurus/types').LoadContext} context
 * @param {{abas: string[]}} options
 * @returns {import('@docusaurus/types').Plugin}
 */
export default function pluginAiEra(context, options) {
  const {siteConfig, baseUrl, i18n} = context;
  /** @type {ReturnType<typeof paginasDe>} */
  let paginas = [];
  /** @type {ReturnType<typeof secoesDoNavbar>} */
  let secoes = [];

  const absoluta = (permalink) => `${siteConfig.url}${permalink}`;
  const urlDoIndice = absoluta(`${baseUrl}llms.txt`);

  /**
   * A rota `.md` de uma página.
   *
   * O permalink de uma página-ÍNDICE termina em barra — `/commands/` para
   * `conteudo/commands/index.md` — enquanto a URL que o leitor vê é `/commands`,
   * porque `trailingSlash: false`. Concatenar `.md` no permalink cru produziria
   * `/commands/.md`: um arquivo que existe e uma URL que ninguém digita, sob um
   * preâmbulo que promete *"acrescente `.md` à URL"*. A barra sai antes da
   * concatenação para que a promessa e o arquivo voltem a ser a mesma coisa.
   *
   * A RAIZ é a exceção, e ela não é descuido: o permalink dela é o próprio
   * `baseUrl`, e tirar a barra ali moveria o arquivo para fora do site —
   * `/overpower.md` não é servido por um Pages publicado em `/overpower/`.
   */
  const rotaMd = (permalink) =>
    permalink === baseUrl ? `${permalink}.md` : `${permalink.replace(/\/$/, '')}.md`;

  return {
    name: 'sd-ai-era',

    async allContentLoaded({allContent}) {
      secoes = secoesDoNavbar(siteConfig.themeConfig);
      paginas = paginasDe({
        allContent,
        siteDir: context.siteDir,
        abas: options.abas,
        secoes,
        localeTraduzido: i18n.currentLocale !== i18n.defaultLocale,
      });
    },

    async postBuild({outDir}) {
      const escrever = async (relativo, texto) => {
        const destino = path.join(outDir, relativo);
        await fs.mkdir(path.dirname(destino), {recursive: true});
        await fs.writeFile(destino, texto, 'utf8');
      };

      // --- o `.md` por rota ---------------------------------------------------
      //
      // Escritos no `outDir`, nunca em `static/`. O que se commita é artefato
      // que muda por DECISÃO; um `.md` que muda toda vez que a prosa muda seria
      // dezenas de arquivos de ruído em todo diff de conteúdo.
      //
      // O ponteiro de volta ao índice é o que transforma arquivos soltos em
      // grafo navegável: quem chega num `.md` por link direto descobre que
      // existe uma lista, e a máquina que o lê acha o resto do site.
      await Promise.all(
        paginas.map((pagina) =>
          escrever(
            rotaMd(pagina.permalink).slice(baseUrl.length),
            `> [Índice para máquinas](${urlDoIndice}) · [Página](${absoluta(pagina.permalink)})\n\n${comSubtitulo(pagina).trim()}\n`,
          ),
        ),
      );

      // --- llms.txt -----------------------------------------------------------
      //
      // `## Optional` NÃO é usada. Ela tem significado especial na spec do
      // llms.txt — *pode ser pulada se o contexto for curto* — e nenhuma das
      // três referências medidas a usa. Marcar uma seção inteira como
      // descartável é uma decisão sobre o conteúdo que este site não tomou.
      const blocos = secoes.map((secao) => {
        const linhas = paginas
          .filter((pagina) => pagina.secao === secao.id)
          .map((pagina) => `- [${pagina.titulo}](${absoluta(rotaMd(pagina.permalink))}): ${pagina.descricao}`);
        return `## ${secao.rotulo}\n\n${linhas.join('\n')}`;
      });

      const abertura = [
        `# ${siteConfig.title}`,
        '',
        `> ${siteConfig.tagline}`,
        '',
        preambulo({paginas, secoes, locale: i18n.currentLocale}),
      ];

      await escrever('llms.txt', [...abertura, '', blocos.join('\n\n'), ''].join('\n'));

      // --- llms-full.txt ------------------------------------------------------
      await escrever(
        'llms-full.txt',
        [
          ...abertura,
          '',
          ...paginas.map((pagina) =>
            [
              separador(absoluta(pagina.permalink)),
              '',
              `> Summary: ${pagina.descricao}`,
              '',
              pagina.corpo.trim(),
              '',
            ].join('\n'),
          ),
        ].join('\n'),
      );
    },
  };
}

/**
 * O preâmbulo global — o mesmo nos dois artefatos.
 *
 * Ele existe para dizer à máquina o que ela tem em mãos antes do primeiro
 * documento: quantas páginas, por qual eixo estão divididas, e onde achar o
 * resto. A nota de ficção do gabarito não veio — lá o conteúdo era demonstração
 * e a máquina precisava ser avisada; aqui a documentação descreve um pacote que
 * existe no PyPI, e o aviso seria falso.
 *
 * **Ele sai em inglês, como todo o resto do site.** Não há eixo de tradução:
 * `i18n` não é declarado, e o único locale é o default.
 */
function preambulo({paginas, secoes, locale}) {
  const contagem = secoes
    .map((secao) => `${paginas.filter((pagina) => pagina.secao === secao.id).length} in ${secao.rotulo}`)
    .join(', ');
  return [
    `Documentation for the \`overpower\` CLI. ${paginas.length} pages (${contagem}), locale \`${locale}\`.`,
    '',
    'Every page on this site is also served as Markdown: append `.md` to its URL.',
  ].join('\n');
}
