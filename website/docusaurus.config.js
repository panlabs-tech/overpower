// @ts-check

/**
 * O site de documentação do overpower.
 *
 * O tema é transplantado de `panlabs-tech/shinydoc-docusaurus`, cujo README
 * declara a premissa que autoriza o transplante: o conteúdo é ficção
 * descartável, o produto é a estrutura mais a customização visual. O que veio
 * do gabarito veio inteiro — os cinco CSS, os componentes, os ícones, as duas
 * fontes, as ejeções de `src/theme/` e os dois plugins locais. O que ficou lá
 * ficou por decisão registrada na spec, não por esquecimento.
 *
 * O projeto mora em `website/` e não na raiz, e isso não é gosto: o gabarito
 * põe React em `src/`, o `src/` deste repositório é o pacote Python, e o portão
 * P2 do `ci.yml` assere que o wheel carrega exatamente o que o git rastreia sob
 * `src/`. Um `src/css/tokens.css` versionado e ausente do wheel reprovaria o P2.
 *
 * Procedência: https://github.com/ThiagoPanini/overpower/issues/129
 */

/**
 * O tema do Prism, servido inteiramente por token.
 *
 * `theme` sozinho e sem `darkTheme`: as sete famílias apontam para
 * `var(--sd-code-*)`, e são os tokens que resolvem o modo. Declarar um
 * `darkTheme` reintroduziria uma segunda fonte de verdade para a mesma cor.
 */
const temaPrism = {
  plain: {
    color: 'var(--sd-code-fg)',
    backgroundColor: 'var(--sd-surface-code)',
  },
  styles: [
    {
      types: ['comment', 'prolog', 'doctype', 'cdata'],
      style: {color: 'var(--sd-code-comment)', fontStyle: 'italic'},
    },
    {
      types: ['keyword', 'atrule', 'selector', 'tag', 'important', 'builtin'],
      style: {color: 'var(--sd-code-keyword)'},
    },
    {
      types: ['string', 'char', 'attr-value', 'regex', 'inserted'],
      style: {color: 'var(--sd-code-string)'},
    },
    {
      types: ['function', 'class-name', 'function-variable'],
      style: {color: 'var(--sd-code-function)'},
    },
    {
      types: ['constant', 'symbol', 'number', 'boolean', 'deleted'],
      style: {color: 'var(--sd-code-constant)'},
    },
    {
      types: ['parameter', 'variable', 'property', 'attr-name'],
      style: {color: 'var(--sd-code-parameter)'},
    },
    {
      types: ['operator', 'punctuation', 'entity', 'url'],
      style: {color: 'var(--sd-code-operator)'},
    },
  ],
};

/**
 * As instâncias de docs que os plugins locais varrem.
 *
 * Aqui é UMA. O gabarito tinha três porque queria três prefixos de URL; este
 * site tem um produto só, e as duas faixas do navbar são duas sidebars da mesma
 * instância, comutadas por `sidebarId`. `'default'` é o id da instância que o
 * preset cria.
 */
const ABAS = ['default'];

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'overpower',
  tagline: 'Curated agent equipment, installed into a repository or a machine',
  url: 'https://thiagopanini.github.io',
  baseUrl: '/overpower/',
  organizationName: 'ThiagoPanini',
  projectName: 'overpower',
  favicon: 'favicon.svg',

  // Sem barra no fim. A rota que o `upload-pages-artifact` publica é a que o
  // Docusaurus escreve, e as duas convenções divergindo é 404 com a página
  // existindo no disco.
  trailingSlash: false,

  // Os três em `throw`. Link quebrado que só avisa é link quebrado que fica.
  onBrokenLinks: 'throw',
  onBrokenAnchors: 'throw',
  markdown: {
    hooks: {onBrokenMarkdownLinks: 'throw'},
  },

  // `future.v4` acende `useCssCascadeLayers`, e a arquitetura de especificidade
  // deste tema foi medida contra o Infima SEM `@layer`. Ligar não é migrar uma
  // flag: é reabrir a premissa contra a qual os cinco CSS foram escritos.
  future: {v4: false},

  // Nenhum `i18n`. O site é inglês inteiro, como o README, os helps do Typer e
  // as telas. O default do Docusaurus já é um locale `en` e é exatamente o que
  // se quer — declarar a tabela só para repetir o default cria a impressão de
  // que há um eixo de tradução que não existe.

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          // `docs/` deste repositório é briefing de agente, não rota. O conteúdo
          // servido mora em `conteudo/`, como no gabarito.
          path: 'conteudo',
          // Sem prefixo: com uma instância só, `/docs` é um segmento que não
          // distingue nada. A visão geral leva `slug: /` e é a raiz.
          routeBasePath: '/',
          sidebarPath: './sidebars.js',
        },
        blog: false,
        theme: {
          // A ordem é contrato: `tokens.css` primeiro, porque todos os outros o
          // referenciam por nome e nenhum deles declara um literal.
          customCss: [
            './src/css/tokens.css',
            './src/css/custom.css',
            './src/css/chrome.css',
            './src/css/componentes.css',
            './src/css/foco.css',
          ],
        },
      }),
    ],
  ],

  plugins: [
    // Busca local: índice montado em `allContentLoaded` e entregue como dado
    // global. Zero dependência npm, zero serviço externo, zero chave.
    ['./src/plugins/busca', {abas: ABAS}],
    // `llms.txt` e um `.md` por rota, escritos no `outDir` em `postBuild`. Para
    // uma CLI consumida por agentes isto vale mais aqui do que valia no
    // gabarito.
    ['./src/plugins/ai-era', {abas: ABAS}],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      colorMode: {
        defaultMode: 'dark',
        respectPrefersColorScheme: true,
        disableSwitch: false,
      },
      navbar: {
        // A marca é a palavra, monocromática, sem logo. `title` sem `logo` é o
        // caminho nativo do upstream: ele renderiza `<b class="navbar__title">`
        // e o CSS decide a cor.
        title: 'overpower',
        items: [
          // Este item não desenha nada: ele quebra a linha do flex e abre a
          // segunda faixa, onde as tabs moram. `value` não pode ser vazio — o
          // schema do navbar reprova o build.
          {
            type: 'html',
            position: 'left',
            className: 'quebra-de-faixa',
            value: '<!--quebra-->',
          },
          {
            type: 'docSidebar',
            sidebarId: 'guide',
            position: 'left',
            label: 'Guide',
          },
          {
            type: 'docSidebar',
            sidebarId: 'contributing',
            position: 'left',
            label: 'Contributing',
          },
          {type: 'search', position: 'right'},
          {
            href: 'https://github.com/ThiagoPanini/overpower',
            label: 'GitHub',
            position: 'right',
          },
        ],
      },
      footer: {
        // Lista plana, nunca `MultiColumn`. `style` fica no default.
        //
        // O `CHANGELOG.md` não entra no site: são 790 linhas em idioma misto, e
        // copiá-lo importaria o problema sem resolver nenhum. O link vai para o
        // GitHub, que já o renderiza.
        links: [
          {
            label: 'Changelog',
            href: 'https://github.com/ThiagoPanini/overpower/blob/main/CHANGELOG.md',
          },
          {label: 'llms.txt', href: 'pathname:///llms.txt', target: '_self'},
        ],
        copyright: '© 2026 panlabs',
      },
      prism: {
        theme: temaPrism,
        additionalLanguages: ['bash', 'toml'],
      },
    }),
};

export default config;
