// @ts-check

/**
 * As duas sidebars do site, na mesma instância de docs.
 *
 * O gabarito usou três instâncias de `plugin-content-docs` porque queria três
 * prefixos de URL. Aqui não é o caso: há um produto, e as duas faixas do navbar
 * separam audiência, não eixo de URL. `sidebarId` escolhe entre sidebars da
 * mesma instância, e o item `{type:'html', className:'quebra-de-faixa'}` do
 * navbar continua abrindo a segunda faixa exatamente como abria lá.
 *
 * Três invariantes, e as três são cobradas por leitura e não por script:
 *
 *   1. **A ordem mora aqui e em nenhum outro lugar.** Nenhuma página escreve
 *      `sidebar_position` no front matter: com lista explícita ele é ignorado,
 *      e uma fonte de verdade ignorada é uma fonte de verdade que mente.
 *   2. **Toda categoria é clicável** e aponta para a própria página por
 *      `link: {type:'doc'}`. Essa página não vira linha própria na sidebar —
 *      o rótulo da categoria já é o link para ela.
 *   3. **Toda folha carrega ícone**, e categoria não carrega. São seis famílias,
 *      uma por categoria, resolvidas por `mask-image` em `src/css/chrome.css`.
 *
 * Procedência: https://github.com/ThiagoPanini/overpower/issues/129
 */

/*
 * O `className` é escrito por extenso em toda folha, e uma função que o montasse
 * a partir do nome da família leria melhor. Ela não entra: `npm run icones`
 * confere o par seção→ícone em três lugares — `PARES_SECAO` no manifesto, a
 * regra de máscara no CSS, e o nome da família AQUI —, e a varredura daqui é um
 * regex sobre o fonte. Nome montado em runtime não está no fonte, e a terceira
 * perna da conferência morreria calada.
 */

/** @type {import('@docusaurus/plugin-content-docs').SidebarItemConfig[]} */
const guide = [
  {
    type: 'category',
    label: 'Start',
    collapsed: false,
    link: {type: 'doc', id: 'start/overview'},
    items: [
      {type: 'doc', id: 'start/install', className: 'sidebar-icone sidebar-icone--start'},
      {type: 'doc', id: 'start/concepts', className: 'sidebar-icone sidebar-icone--start'},
    ],
  },
  {
    type: 'category',
    label: 'Commands',
    collapsed: false,
    link: {type: 'doc', id: 'commands/index'},
    items: [
      {type: 'doc', id: 'commands/list', className: 'sidebar-icone sidebar-icone--commands'},
      {type: 'doc', id: 'commands/install', className: 'sidebar-icone sidebar-icone--commands'},
      {type: 'doc', id: 'commands/doctor', className: 'sidebar-icone sidebar-icone--commands'},
    ],
  },
  {
    type: 'category',
    label: 'Targets',
    collapsed: false,
    link: {type: 'doc', id: 'targets/index'},
    items: [
      {type: 'doc', id: 'targets/mcp', className: 'sidebar-icone sidebar-icone--targets'},
      {type: 'doc', id: 'targets/from', className: 'sidebar-icone sidebar-icone--targets'},
    ],
  },
  {
    type: 'category',
    label: 'Reference',
    collapsed: false,
    link: {type: 'doc', id: 'reference/index'},
    items: [
      {type: 'doc', id: 'reference/exit-codes', className: 'sidebar-icone sidebar-icone--reference'},
      {
        type: 'doc',
        id: 'reference/troubleshooting',
        className: 'sidebar-icone sidebar-icone--reference',
      },
    ],
  },
];

/** @type {import('@docusaurus/plugin-content-docs').SidebarItemConfig[]} */
const contributing = [
  {
    type: 'category',
    label: 'Development',
    collapsed: false,
    link: {type: 'doc', id: 'development/index'},
    items: [
      {type: 'doc', id: 'development/tests', className: 'sidebar-icone sidebar-icone--development'},
      {type: 'doc', id: 'development/screens', className: 'sidebar-icone sidebar-icone--development'},
    ],
  },
  {
    type: 'category',
    label: 'Shipping',
    collapsed: false,
    link: {type: 'doc', id: 'shipping/index'},
    items: [
      {type: 'doc', id: 'shipping/curation', className: 'sidebar-icone sidebar-icone--shipping'},
      {type: 'doc', id: 'shipping/releasing', className: 'sidebar-icone sidebar-icone--shipping'},
    ],
  },
];

export default {guide, contributing};
