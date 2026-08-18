/**
 * O manifesto de ícones — CONTRATO.
 *
 * Os desenhos são skin e se trocam (`static/icons/*.svg`); estes nomes não.
 * O corporativo com iconografia própria substitui os arquivos e mantém os
 * nomes: nenhum componente e nenhum MDX é reescrito.
 *
 * Três papéis, UM registro, UM orçamento. **O papel é uma tag na entrada, não
 * uma pilha separada de desenhos** — é por isso que `package`, `layers`,
 * `workflow` e outros seis carregam duas tags e consomem um arquivo só.
 *
 *   19 sistema + 11 navegação + 40 autoria = 70 tags sobre 61 arquivos
 *
 * O teto é 64 — **teto, não meta**. Ele foi alcançado no mapa do `mint` e a
 * árvore do `panlabs` devolveu folga: **quatro cortes, quatro slots livres**.
 * **Um voltou a ser gasto**: `list`, o glifo do título do índice desta página,
 * é o 61º arquivo e deixa a folga em três. O teto NÃO desce junto.
 * `train-track` morreu com a marca, que ficou só com a palavra; `wallet` e
 * `receipt` nomeavam pagamentos, e o domínio inteiro morreu; `credit-card` já
 * estava sem consumidor desde que a grade de cinco cartões da landing morreu.
 *
 * A regra que decidiu os cortes: **sobrevive quem é neutro de domínio ou nomeia
 * o cenário fixado** — GitHub Actions, AWS, Python.
 *
 * Procedência: shinydoc-docusaurus/docs/design/icones.md.
 */

/**
 * `nome` é NOSSO nome — semântico, e é ele que o autor escreve no MDX. `lucide`
 * só aparece onde o upstream diverge, e é a prova de que o nome do contrato não
 * é refém do vocabulário de terceiro: o Lucide renomeia glifo entre versões, e
 * quem paga é o mapa de uma linha, não o MDX de dezenas de páginas.
 *
 * @typedef {'sistema' | 'navegacao' | 'autoria'} Papel
 * @typedef {{nome: string, papeis: Papel[], onde: string, lucide?: string}} Entrada
 */

/**
 * Sistema · 19 — o componente escolhe, o autor nunca.
 *
 * **Eram 19.** `train-track` saiu porque a marca ficou só com a palavra: sem
 * glifo ao lado do nome, o desenho perdeu o único consumidor que tinha, e
 * componente sem consumidor é o defeito que este projeto mata por nome.
 * @type {Entrada[]}
 */
const SISTEMA = [
  {nome: 'info', papeis: ['sistema'], onde: 'callout `info`'},
  {nome: 'lightbulb', papeis: ['sistema'], onde: 'callout `tip`'},
  {nome: 'triangle-alert', papeis: ['sistema'], onde: 'callout `warning`'},
  {nome: 'pencil-line', papeis: ['sistema'], onde: 'callout `note`'},
  {nome: 'chevron-right', papeis: ['sistema'], onde: 'caret de `Accordion` e de categoria de sidebar'},
  {nome: 'check', papeis: ['sistema'], onde: 'passo concluído em `Steps`'},
  {nome: 'copy', papeis: ['sistema'], onde: 'botão copiar do bloco de código'},
  {nome: 'wrap-text', papeis: ['sistema'], onde: 'toggle de quebra de linha do bloco de código', lucide: 'text-wrap'},
  {nome: 'external-link', papeis: ['sistema'], onde: 'link externo'},
  {nome: 'search', papeis: ['sistema'], onde: 'busca'},
  {nome: 'x', papeis: ['sistema'], onde: 'fechar modal'},
  {nome: 'menu', papeis: ['sistema'], onde: 'hambúrguer de tela estreita'},
  {nome: 'sun', papeis: ['sistema'], onde: 'tema claro'},
  {nome: 'moon', papeis: ['sistema'], onde: 'tema escuro'},
  {nome: 'monitor', papeis: ['sistema'], onde: 'tema do sistema'},
  {nome: 'languages', papeis: ['sistema'], onde: 'seletor de locale'},
  {nome: 'link', papeis: ['sistema'], onde: 'âncora de heading'},
  {nome: 'list', papeis: ['sistema'], onde: 'título do índice desta página', lucide: 'text-align-start'},
  {nome: 'arrow-right', papeis: ['sistema'], onde: 'paginação e CTA de card'},
];

/*
   Navegação · 6 tags sobre 6 arquivos, e **nenhum deles mora num array próprio**.
   
   O gabarito tinha dois órfãos de navegação — `code-xml` e `activity` — porque a
   árvore dele tinha onze seções e duas delas não achavam glifo que já estivesse
   no vocabulário do autor. A árvore daqui tem seis, e as seis acharam: `rocket`,
   `terminal`, `layers`, `book-open`, `wrench` e `package` já eram nomes de
   autoria e carregam a segunda tag na própria entrada. O array intermediário
   ficou sem habitante, e um array vazio que só documenta a própria vacuidade é
   ruído — ele saiu, e os dois órfãos voltaram a ser o que sempre foram: nomes
   que o autor escreve como string. */


/**
 * Autoria · 42 — o vocabulário escrito como STRING: o MDX do autor, por
 * `<Card icon="…">`.
 *
 * A tag é definida por FORMA e não por lugar: `autoria` é *"o nome escrito como
 * string"*, e não *"o MDX do autor"*. Este site não tem landing — `routeBasePath`
 * é `/` e a visão geral é a raiz —, então hoje a única superfície é o MDX; a
 * definição continua a que é, porque ela não dependia da segunda superfície.
 *
 * **Seis entradas carregam a segunda tag `navegacao` e moram aqui** — uma por
 * categoria de topo da árvore. Cada uma ficou com o glifo que nomeia o que a
 * seção guarda: `terminal` para os comandos, `layers` para os escopos e
 * runtimes, `package` para o que se publica.
 * @type {Entrada[]}
 */
const AUTORIA = [
  // Ações · 8
  {nome: 'play', papeis: ['autoria'], onde: 'vocabulário do autor'},
  {nome: 'download', papeis: ['autoria'], onde: 'vocabulário do autor'},
  {nome: 'upload', papeis: ['autoria'], onde: 'vocabulário do autor'},
  {nome: 'refresh-cw', papeis: ['autoria'], onde: 'vocabulário do autor'},
  {nome: 'send', papeis: ['autoria'], onde: 'vocabulário do autor'},
  {nome: 'trash-2', papeis: ['autoria'], onde: 'vocabulário do autor'},
  {nome: 'plus', papeis: ['autoria'], onde: 'vocabulário do autor'},
  {nome: 'filter', papeis: ['autoria'], onde: 'vocabulário do autor', lucide: 'funnel'},

  // Objetos · 16
  {nome: 'file-text', papeis: ['autoria'], onde: 'vocabulário do autor'},
  {nome: 'folder', papeis: ['autoria'], onde: 'vocabulário do autor'},
  {nome: 'terminal', papeis: ['navegacao', 'autoria'], onde: 'Guide › Commands · vocabulário do autor'},
  {nome: 'wrench', papeis: ['navegacao', 'autoria'], onde: 'Contributing › Development · vocabulário do autor'},
  {nome: 'database', papeis: ['autoria'], onde: 'vocabulário do autor'},
  {nome: 'code-xml', papeis: ['autoria'], onde: 'vocabulário do autor'},
  {nome: 'server', papeis: ['autoria'], onde: 'vocabulário do autor'},
  {nome: 'cloud', papeis: ['autoria'], onde: 'vocabulário do autor'},
  {nome: 'key', papeis: ['autoria'], onde: 'vocabulário do autor'},
  {nome: 'lock', papeis: ['autoria'], onde: 'vocabulário do autor'},
  {nome: 'mail', papeis: ['autoria'], onde: 'vocabulário do autor'},
  {nome: 'calendar', papeis: ['autoria'], onde: 'vocabulário do autor'},
  {nome: 'users', papeis: ['autoria'], onde: 'vocabulário do autor'},
  {nome: 'globe', papeis: ['autoria'], onde: 'vocabulário do autor'},
  {nome: 'package', papeis: ['navegacao', 'autoria'], onde: 'Contributing › Shipping · vocabulário do autor'},
  {nome: 'rocket', papeis: ['navegacao', 'autoria'], onde: 'Guide › Start · vocabulário do autor'},
  {nome: 'shapes', papeis: ['autoria'], onde: 'vocabulário do autor'},

  // Estados e sinais · 7
  {nome: 'zap', papeis: ['autoria'], onde: 'vocabulário do autor'},
  {nome: 'clock', papeis: ['autoria'], onde: 'vocabulário do autor'},
  {nome: 'circle-alert', papeis: ['autoria'], onde: 'vocabulário do autor'},
  {nome: 'circle-help', papeis: ['autoria'], onde: 'vocabulário do autor', lucide: 'circle-question-mark'},
  {nome: 'sparkles', papeis: ['autoria'], onde: 'vocabulário do autor'},
  {nome: 'trending-up', papeis: ['autoria'], onde: 'vocabulário do autor'},
  {nome: 'gauge', papeis: ['autoria'], onde: 'vocabulário do autor'},
  {nome: 'activity', papeis: ['autoria'], onde: 'vocabulário do autor'},

  // Conceitos · 9
  {nome: 'layers', papeis: ['navegacao', 'autoria'], onde: 'Guide › Targets · vocabulário do autor'},
  {nome: 'workflow', papeis: ['autoria'], onde: 'vocabulário do autor'},
  {nome: 'puzzle', papeis: ['autoria'], onde: 'vocabulário do autor'},
  {nome: 'bot', papeis: ['autoria'], onde: 'vocabulário do autor'},
  {nome: 'webhook', papeis: ['autoria'], onde: 'vocabulário do autor'},
  {nome: 'bell', papeis: ['autoria'], onde: 'vocabulário do autor'},
  // Aqui `book-open` é a família de `Reference`: a seção que guarda a tabela de
  // exit codes, o inventário do catálogo e as recusas.
  {nome: 'book-open', papeis: ['navegacao', 'autoria'], onde: 'Guide › Reference · vocabulário do autor'},
  {nome: 'repeat', papeis: ['autoria'], onde: 'vocabulário do autor'},
  {nome: 'undo-2', papeis: ['autoria'], onde: 'vocabulário do autor'},
];

/** @type {Entrada[]} */
export const ICONES = [...SISTEMA, ...AUTORIA];

/** Os 61 nomes de arquivo, em ordem de manifesto. */
export const NOMES = ICONES.map((i) => i.nome);

/**
 * O teto é duro. Ele existe porque conjunto que cresce sob demanda vira dívida:
 * ninguém audita 300 ícones em busca de coerência de família, mas 64 cabem numa
 * tela e a incoerência salta aos olhos.
 *
 * **O teto não desce junto com a contagem.** Ele é o limite do que se consegue
 * auditar de uma vez, não uma marca d'água do que já se gastou — descê-lo para
 * 60 seria trocar uma régua por um registro do passado.
 */
export const TETO = 64;

/**
 * Os seis pares seção→ícone. A chave é o `id` da categoria de topo — o mesmo
 * que vira `sidebar-icone--<chave>` no `className` da sidebar.
 *
 * O `className` mora na FOLHA, não na categoria: a âncora marca a folha e nunca
 * o cabeçalho de grupo. A folha herda a chave da categoria de topo que a contém,
 * e não ganha chave própria por estar num nível mais fundo.
 *
 * As duas tabs de navbar continuam sem ícone.
 */
export const PARES_SECAO = {
  start: 'rocket',
  commands: 'terminal',
  targets: 'layers',
  reference: 'book-open',
  development: 'wrench',
  shipping: 'package',
};

/**
 * A versão do Lucide de onde os desenhos foram copiados.
 *
 * O Lucide **renomeia glifo entre versões** — `code-xml` já foi `code-2`. Os
 * nomes deste manifesto se conferem contra esta versão no ato de copiar, e é
 * `scripts/vendorizar-icones.mjs` quem roda a conferência.
 */
export const LUCIDE_VERSAO = '1.30.0';
