#!/usr/bin/env node
/**
 * Vendoriza os desenhos do manifesto de ícones.
 *
 *   node scripts/vendorizar-icones.mjs            baixa o que falta
 *   node scripts/vendorizar-icones.mjs --conferir não baixa; só confere
 *
 * Não é portão de CI — precisa de rede, e a rede é exatamente o que o ambiente
 * corporativo alvo não tem. É a ferramenta do **ato de copiar**, e ela existe
 * por um motivo específico: o Lucide **renomeia glifo entre versões**
 * (`code-xml` já foi `code-2`). Um nome que sumiu vira 404 aqui, alto, em vez
 * de virar quadrado vazio na sidebar seis meses depois.
 *
 * O manifesto é lido do fonte, não redigitado: `src/icons/manifest.js` é o
 * contrato, e duplicar a lista aqui criaria a segunda versão da mesma verdade
 * que o espelho de tokens existe para impedir.
 */

import {existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync} from 'node:fs';
import {join} from 'node:path';

const MANIFESTO = 'src/icons/manifest.js';
const CSS_DA_SIDEBAR = 'src/css/chrome.css';
const DESTINO = 'static/icons';

const fonte = readFileSync(MANIFESTO, 'utf8');

const versao = fonte.match(/LUCIDE_VERSAO = '([^']+)'/)?.[1];
if (!versao) {
  console.error(`${MANIFESTO} não declara LUCIDE_VERSAO.`);
  process.exit(2);
}

// O teto vem do manifesto, não redigitado aqui. Um teto com duas versões é um
// teto que vale o menor dos dois, e ninguém saberia qual.
const TETO = Number(fonte.match(/TETO = (\d+)/)?.[1]);
if (!TETO) {
  console.error(`${MANIFESTO} não declara TETO.`);
  process.exit(2);
}

const entradas = [...fonte.matchAll(/\{nome: '([^']+)', papeis: \[([^\]]*)\][^}]*\}/g)].map((m) => ({
  nome: m[1],
  papeis: [...m[2].matchAll(/'([^']+)'/g)].map((p) => p[1]),
  // O nome do upstream só existe onde ele diverge do nosso.
  lucide: m[0].match(/lucide: '([^']+)'/)?.[1] ?? m[1],
}));

// ---------------------------------------------------------------------------
// A aritmética do orçamento, conferida antes de qualquer download.
// ---------------------------------------------------------------------------

const arquivos = new Map(entradas.map((e) => [e.nome, e.lucide]));
const tags = entradas.reduce((n, e) => n + e.papeis.length, 0);
const porPapel = (papel) => entradas.filter((e) => e.papeis.includes(papel)).length;

// Os seis pares seção→ícone existem em três lugares: `PARES_SECAO` no
// manifesto, o `className` de cada categoria nos arquivos de sidebar, e a regra
// de máscara no CSS. Três cópias da mesma verdade e nenhuma marcada como errada
// é o defeito que este repositório mais recusa — então aqui elas se conferem.
const pares = [...(fonte.match(/PARES_SECAO = \{([^}]*)\}/s)?.[1] ?? '').matchAll(
  /'?([a-z-]+)'?:\s*'([a-z0-9-]+)'/g,
)].map((m) => ({secao: m[1], icone: m[2]}));

const cssDaSidebar = readFileSync(CSS_DA_SIDEBAR, 'utf8');

// O TERCEIRO lado, que este script afirmava conferir e não conferia.
//
// Ele casava `PARES_SECAO` contra o manifesto e contra o CSS — dois lados —, e o
// comentário acima já prometia três. O `className` das sidebars ficava de fora, e
// o modo de falhar é exatamente o que a máscara tem de pior: **mudo**. Renomear
// uma categoria no arquivo de sidebar sem mexer no manifesto não quebra build,
// não some com a página, e não tira o item da lista; ele só deixa de ter ícone,
// e a sidebar continua parecendo certa para quem não conhece a árvore.
//
// A varredura é barata porque o `className` é escrito à mão, literal, em toda
// folha — e é por isso que `sidebars.js` NÃO monta a classe por template. Uma
// função `icone(familia)` leria melhor e apagaria esta conferência inteira: o
// regex abaixo procura o nome da família no fonte, e nome montado em runtime não
// está no fonte.
const SIDEBARS = ['sidebars.js'];
// O `'` de fechamento no fim NÃO é enfeite: `[a-z0-9-]+` casa PREFIXO, então
// `sidebar-icone--startX` extrairia `start` e a conferência passaria
// achando que o par existe. Medido escrevendo o rename de propósito.
const declaradasNaSidebar = new Set(
  SIDEBARS.flatMap((arquivo) =>
    [...readFileSync(arquivo, 'utf8').matchAll(/sidebar-icone--([a-zA-Z0-9-]+)'/g)].map((m) => m[1]),
  ),
);

const problemas = [];
if (arquivos.size !== entradas.length) {
  problemas.push('há nome repetido no manifesto — papel é tag na entrada, não entrada nova');
}
if (arquivos.size > TETO) {
  problemas.push(`${arquivos.size} arquivos contra o teto duro de ${TETO}`);
}
if (pares.length !== porPapel('navegacao')) {
  problemas.push(
    `PARES_SECAO tem ${pares.length} pares contra ${porPapel('navegacao')} tags de navegação`,
  );
}
for (const {secao, icone} of pares) {
  const entrada = entradas.find((e) => e.nome === icone);
  if (!entrada) {
    problemas.push(`o par \`${secao}\` aponta para \`${icone}\`, que não está no manifesto`);
  } else if (!entrada.papeis.includes('navegacao')) {
    problemas.push(`\`${icone}\` é usado por \`${secao}\` mas não carrega a tag \`navegacao\``);
  }
  if (!cssDaSidebar.includes(`.sidebar-icone--${secao} `)) {
    problemas.push(`o par \`${secao}\` não tem regra \`.sidebar-icone--${secao}\` em ${CSS_DA_SIDEBAR}`);
  } else if (!cssDaSidebar.includes(`/icons/${icone}.svg`)) {
    problemas.push(`${CSS_DA_SIDEBAR} não mascara \`${icone}.svg\`, que o par \`${secao}\` pede`);
  }
  if (!declaradasNaSidebar.has(secao)) {
    problemas.push(
      `o par \`${secao}\` não é declarado por nenhuma sidebar — nenhum nó carrega \`sidebar-icone--${secao}\``,
    );
  }
}
// E o sentido contrário, que é o que pega o rename: uma categoria que pede um
// ícone que o manifesto não conhece fica sem máscara, calada.
for (const secao of declaradasNaSidebar) {
  if (!pares.some((p) => p.secao === secao)) {
    problemas.push(
      `uma sidebar declara \`sidebar-icone--${secao}\` e \`PARES_SECAO\` não tem esse par`,
    );
  }
}
if (problemas.length) {
  console.error('Manifesto REPROVOU:');
  problemas.forEach((p) => console.error(`  · ${p}`));
  process.exit(1);
}

console.log(
  `Manifesto: ${porPapel('sistema')} sistema · ${porPapel('navegacao')} navegação · ` +
    `${porPapel('autoria')} autoria = ${tags} tags sobre ${arquivos.size} arquivos ` +
    `(teto ${TETO}, folga ${TETO - arquivos.size}).`,
);
console.log(`Os ${pares.length} pares seção→ícone batem com o manifesto e com ${CSS_DA_SIDEBAR}.`);

if (process.argv[2] === '--conferir') {
  const ausentes = [...arquivos.keys()].filter((n) => !existsSync(join(DESTINO, `${n}.svg`)));
  // O terceiro lado da bijeção: desenho em `static/icons/` que ninguém declarou.
  // O registro React pega os outros dois; este só o vendorizador vê, porque um
  // arquivo órfão não é importado por ninguém e viaja calado.
  const orfaos = readdirSync(DESTINO)
    .filter((f) => f.endsWith('.svg'))
    .map((f) => f.replace(/\.svg$/, ''))
    .filter((n) => !arquivos.has(n));

  if (ausentes.length || orfaos.length) {
    if (ausentes.length) {
      console.error(`Faltam ${ausentes.length} desenhos em ${DESTINO}: ${ausentes.join(', ')}`);
    }
    if (orfaos.length) {
      console.error(`${orfaos.length} desenhos sem entrada no manifesto: ${orfaos.join(', ')}`);
    }
    process.exit(1);
  }
  console.log(`Os ${arquivos.size} desenhos estão em ${DESTINO}, e nenhum a mais.`);
  process.exit(0);
}

// ---------------------------------------------------------------------------
// O download, contra a tag fixada.
// ---------------------------------------------------------------------------

mkdirSync(DESTINO, {recursive: true});

const base = `https://raw.githubusercontent.com/lucide-icons/lucide/${versao}/icons`;
const faltando = [];

for (const [nome, upstream] of arquivos) {
  const alvo = join(DESTINO, `${nome}.svg`);
  if (existsSync(alvo)) {
    continue;
  }
  const resposta = await fetch(`${base}/${upstream}.svg`);
  if (!resposta.ok) {
    faltando.push(nome === upstream ? nome : `${nome} (via ${upstream})`);
    continue;
  }
  // O SVG do Lucide já nasce pronto para herdar cor: `stroke="currentColor"`,
  // `fill="none"`, `viewBox="0 0 24 24"`. Nada a reescrever.
  writeFileSync(alvo, await resposta.text());
  console.log(`  ↓ ${nome}.svg`);
}

if (faltando.length) {
  console.error(
    `\nO Lucide ${versao} não tem ${faltando.length} destes desenhos: ${faltando.join(', ')}\n` +
      'Ou o glifo foi renomeado entre versões, ou o nome está errado.\n' +
      'Confira em https://lucide.dev/icons e acrescente o campo `lucide:` na entrada.\n' +
      'O nome do manifesto é NOSSO contrato e não se move por renomeação de terceiro.',
  );
  process.exit(1);
}

console.log(`\nOs ${arquivos.size} desenhos do Lucide ${versao} estão em ${DESTINO}.`);
