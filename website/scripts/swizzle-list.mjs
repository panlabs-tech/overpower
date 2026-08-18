#!/usr/bin/env node
/**
 * `swizzle --list` congelado como artefato, e conferido contra `src/theme/`.
 *
 * É o único mecanismo que enxerga a falha silenciosa que a própria doc do
 * Docusaurus descreve: **componente renomeado no upstream faz o arquivo
 * swizzlado ser completamente ignorado, sem erro.** O build passa, o site sobe,
 * e a customização simplesmente some — o arquivo vira código morto e nada avisa.
 * Nenhum erro de build pega isso, porque não há erro.
 *
 * Duas pernas, e a segunda é a que dá sentido à primeira:
 *
 *   1. **o artefato congelado bate com o `swizzle --list` de agora.** Diff aqui
 *      é a superfície de swizzle do tema mudando — nome novo, nome removido, ou
 *      componente que trocou de nível de segurança;
 *   2. **todo arquivo de `src/theme/` tem endereço.** Ou o nome dele está na
 *      lista (e aí é swizzle ou registro, e a ação que usamos precisa ser
 *      `Safe`), ou ele é componente de tema PRÓPRIO declarado aqui, ou é
 *      arquivo interno de um dos dois. Um arquivo que não é nada disso é
 *      exatamente o código morto que a perna 1 acabou de detectar.
 *
 * O artefato é NORMALIZADO — `nome<TAB>wrap<TAB>eject`, sem a coluna de
 * descrição. A descrição é prosa: uma vírgula nova nela reflui a tabela
 * inteira e produziria um diff de trinta linhas sem uma mudança de contrato.
 * O que este portão cobra é contrato.
 *
 *   node scripts/swizzle-list.mjs --congelar    reescreve o artefato
 *   node scripts/swizzle-list.mjs --verificar   falha se algo divergir
 *
 * A regra escrita que este portão cobra: `.claude/rules/swizzle-theme.md`.
 * https://github.com/panlabs-tech/overpower/issues/130
 */

import {execFileSync} from 'node:child_process';
import {
  closeSync,
  mkdtempSync,
  openSync,
  readdirSync,
  readFileSync,
  rmSync,
  statSync,
  writeFileSync,
} from 'node:fs';
import {tmpdir} from 'node:os';
import path from 'node:path';

const ARTEFATO = 'scripts/swizzle-list.txt';
const TEMA = '@docusaurus/theme-classic';
const RAIZ_DO_TEMA = 'src/theme';
const CLI = 'node_modules/@docusaurus/core/bin/docusaurus.mjs';

/**
 * As sequências de cor do CLI.
 *
 * O ESC vai como escape `\u001b`, e não como byte literal: literal no fonte é
 * um caractere de controle **invisível** no editor e no diff — e este arquivo
 * é justamente o que existe para cobrar o que passa despercebido.
 */
const ANSI = new RegExp('\\u001b\\[[0-9;]*m', 'g');

/**
 * Os componentes de tema PRÓPRIOS — os que o `theme-classic` não tem.
 *
 * Eles não aparecem no `swizzle --list` por construção: o Docusaurus só conhece
 * o nome que a nossa config deu a eles, e o acoplamento ao upstream é zero.
 *
 * Aqui a lista é VAZIA, e isso é resultado e não omissão: o único componente
 * próprio do gabarito era `ApiDocItem`, que serve referência gerada de um
 * contrato JSON — e a geração ficou de fora deste site por decisão registrada.
 * Trazer o layout sem o gerador seria tema sem consumidor.
 */
const PROPRIOS = [];

const modo = process.argv[2];
if (modo !== '--congelar' && modo !== '--verificar') {
  console.error('uso: swizzle-list.mjs --congelar | --verificar');
  process.exit(2);
}

/**
 * A saída bruta do CLI, capturada num ARQUIVO e não num pipe.
 *
 * **Medido nesta implementação, e não deduzido:** com `stdio: 'pipe'` a saída
 * volta **truncada no meio da tabela** — 80.173 bytes contra 115.270, cortada em
 * `Icon/Socials/Mastodon`, sem a borda que fecha a tabela. O Node escreve em
 * pipe de forma assíncrona, e o CLI termina antes de o pipe drenar; em
 * descritor de arquivo a escrita é síncrona e a saída sai inteira.
 *
 * Isto não é detalhe de performance — foi o defeito que congelou um artefato
 * com **157 dos 220 componentes** e o fez diffar contra outra leitura truncada.
 * Um portão que existe para pegar falha silenciosa tinha uma.
 *
 * `--typescript` está aqui porque sem a flag o CLI **pergunta a linguagem** e
 * fica esperando resposta que nunca vem. A escolha não altera a lista.
 */
function saidaDoCli() {
  const pasta = mkdtempSync(path.join(tmpdir(), 'sd-swizzle-'));
  const destino = path.join(pasta, 'list.txt');
  const fd = openSync(destino, 'w');
  try {
    execFileSync(process.execPath, [CLI, 'swizzle', TEMA, '--list', '--typescript'], {
      stdio: ['ignore', fd, 'ignore'],
    });
  } finally {
    closeSync(fd);
  }
  try {
    return readFileSync(destino, 'utf8');
  } finally {
    rmSync(pasta, {recursive: true, force: true});
  }
}

/** A saída do CLI, sem ANSI e sem a moldura da tabela. */
function listaDeAgora() {
  const todas = saidaDoCli().replace(ANSI, '').split('\n');

  // O CLI imprime TRÊS tabelas: os componentes, e depois duas legendas — as
  // ações (`Wrap`/`Eject`) e os níveis de segurança (`Safe`/`Unsafe`/
  // `Forbidden`). Só a primeira é contrato; as legendas são prosa do CLI e
  // entrariam no artefato como se fossem componentes.
  const fim = todas.findIndex((l) => l.startsWith('└'));

  // A borda que fecha a tabela é a prova de que a saída chegou inteira. Sem
  // esta guarda, uma leitura truncada vira artefato congelado, e o portão passa
  // a diffar um pedaço contra outro pedaço — que é exatamente o defeito que
  // esta versão do script corrige.
  if (fim === -1) {
    throw new Error(
      'O `swizzle --list` não fechou a tabela — a saída chegou truncada. ' +
        'O artefato NÃO foi tocado: congelar uma leitura parcial é pior que não congelar.',
    );
  }

  const linhas = [];
  for (const linha of todas.slice(0, fim)) {
    if (!linha.startsWith('│')) {
      continue;
    }
    const colunas = linha.split('│').map((c) => c.trim());
    const [, nome, wrap, eject] = colunas;
    if (!nome || nome === 'Component name') {
      // Linha de continuação: a descrição de um componente quebrou em duas, e a
      // primeira coluna dela vem vazia. Descrição é prosa e não entra no
      // artefato, então continuação se descarta inteira.
      continue;
    }
    // Nome sem as duas ações é formato de tabela que mudou, não componente novo.
    // Congelar `undefined` aqui produziria um artefato que passa a diffar contra
    // si mesmo para sempre — falha silenciosa dentro do portão que existe para
    // pegar falha silenciosa.
    if (!wrap || !eject) {
      throw new Error(
        `O \`swizzle --list\` devolveu "${nome}" sem as colunas de ação. O formato da tabela mudou; ajuste o parser.`,
      );
    }
    linhas.push(`${nome}\t${wrap}\t${eject}`);
  }
  if (linhas.length === 0) {
    throw new Error('O `swizzle --list` não devolveu componente nenhum — o formato da tabela mudou.');
  }
  return `${linhas.join('\n')}\n`;
}

/** Todo arquivo sob `src/theme/`, em caminho relativo à raiz do tema. */
function arquivosDoTema(dir = RAIZ_DO_TEMA, prefixo = '') {
  const saida = [];
  for (const entrada of readdirSync(dir).sort()) {
    const completo = path.join(dir, entrada);
    const relativo = prefixo ? `${prefixo}/${entrada}` : entrada;
    if (statSync(completo).isDirectory()) {
      saida.push(...arquivosDoTema(completo, relativo));
    } else {
      saida.push(relativo);
    }
  }
  return saida;
}

/** `SearchBar/index.js` → `SearchBar` · `Admonition/Types.js` → `Admonition/Types`. */
const nomeDeComponente = (relativo) =>
  relativo.replace(/\.[^./]+$/, '').replace(/(^|\/)index$/, '');

const agora = listaDeAgora();

if (modo === '--congelar') {
  writeFileSync(ARTEFATO, agora);
  console.log(`Congelado: ${ARTEFATO} <- swizzle --list de ${TEMA}`);
  process.exit(0);
}

let falhas = 0;

// --- perna 1: o artefato congelado ainda descreve o tema instalado -----------
const congelado = readFileSync(ARTEFATO, 'utf8');
if (congelado !== agora) {
  const de = new Set(congelado.trim().split('\n'));
  const para = new Set(agora.trim().split('\n'));
  const sumiram = [...de].filter((l) => !para.has(l));
  const surgiram = [...para].filter((l) => !de.has(l));
  console.error(`Portão 7 REPROVOU — ${ARTEFATO} não descreve mais o ${TEMA} instalado.`);
  console.error('');
  sumiram.forEach((l) => console.error(`  - ${l}`));
  surgiram.forEach((l) => console.error(`  + ${l}`));
  console.error('');
  console.error('Um nome REMOVIDO cujo arquivo existe em src/theme/ é a falha silenciosa:');
  console.error('o arquivo passa a ser ignorado, sem erro, e a customização some.');
  console.error(`Reconcilie o ledger (`.claude/rules/swizzle-theme.md`) e rode: node ${ARTEFATO.replace('.txt', '.mjs')} --congelar`);
  falhas += 1;
}

// --- perna 2: todo arquivo de src/theme/ tem endereço ------------------------
const catalogo = new Map(
  agora
    .trim()
    .split('\n')
    .map((l) => {
      const [nome, wrap, eject] = l.split('\t');
      return [nome, {wrap, eject}];
    }),
);

const orfaos = [];
const inseguros = [];

for (const relativo of arquivosDoTema()) {
  const nome = nomeDeComponente(relativo);
  const noCatalogo = catalogo.get(nome);

  if (noCatalogo) {
    // Nós escrevemos o arquivo inteiro, então a ação exercida é `eject`. A regra
    // proíbe `unsafe`; `Forbidden` seria proibição do próprio Docusaurus.
    if (noCatalogo.eject !== 'Safe') {
      inseguros.push(`${relativo}  (${nome}: eject ${noCatalogo.eject})`);
    }
    continue;
  }
  if (PROPRIOS.includes(nome)) {
    continue;
  }
  // Arquivo interno — CSS Module, submódulo — de um componente que já tem
  // endereço. `SearchBar/escada` e `SearchBar/estilos.module` caem aqui.
  const temDono = [...catalogo.keys(), ...PROPRIOS].some((dono) => nome.startsWith(`${dono}/`));
  if (!temDono) {
    orfaos.push(relativo);
  }
}

if (inseguros.length > 0) {
  console.error('Portão 7 REPROVOU — arquivo em src/theme/ sobre componente que não é `Safe` para eject:');
  console.error('');
  inseguros.forEach((l) => console.error(`  ${l}`));
  console.error('');
  console.error('O orçamento `unsafe` é ZERO, e ele não se gasta em silêncio.');
  falhas += 1;
}

if (orfaos.length > 0) {
  console.error('Portão 7 REPROVOU — arquivo em src/theme/ sem endereço:');
  console.error('');
  orfaos.forEach((l) => console.error(`  ${l}`));
  console.error('');
  console.error('Ou o nome saiu do `swizzle --list` (e o arquivo virou código morto,');
  console.error('que é a falha silenciosa que este portão existe para pegar), ou é um');
  console.error(`componente de tema próprio novo — e aí ele entra em PROPRIOS, aqui.`);
  falhas += 1;
}

if (falhas > 0) {
  process.exit(1);
}

console.log(
  `Portão 7 passou — ${catalogo.size} componentes no artefato, ` +
    `${arquivosDoTema().length} arquivos em ${RAIZ_DO_TEMA}/ com endereço, zero \`unsafe\`.`,
);
