/**
 * A escada de pontuação e a normalização — a lógica pura da busca.
 *
 * Ela mora fora do componente por dois motivos, e o segundo é o que decidiu:
 *
 *   1. o `SearchBar` fica sendo o que ele é — JSX mais os ganchos de `<dialog>`;
 *   2. **é o único algoritmo não trivial do projeto inteiro**, e sem separá-lo
 *      não há como cobrá-lo por máquina. O resto do repositório é conferido por
 *      varredura porque o resto do repositório é CSS e conteúdo; ordenação de
 *      resultado não é varrível, e afirmar *"determinística"* em prosa é
 *      exatamente a classe de afirmação que este projeto recusa.
 *
 * A régua está em `scripts/busca.test.mjs`, no `node --test` do próprio runtime.
 * **Zero dependência nova** — é o mesmo critério que escolheu `<dialog>` e
 * `<details>` em vez de biblioteca.
 *
 * `.mjs` e não `.js`: `package.json` não declara `type`, então só a extensão
 * explícita faz o Node ler o arquivo como módulo. O webpack lê os dois.
 *
 * Procedência: shinydoc-docusaurus/docs/design/busca.md.
 */

/**
 * A escada — **potências de dois, e isso é a decisão**.
 *
 * Cada degrau vale mais do que a soma de todos abaixo dele (32 > 16+8+4+2+1),
 * então a ordem é lexicográfica de verdade: casar no título nunca perde para
 * casar em três campos fracos ao mesmo tempo. Uma escala linear inverteria isso
 * em algum ponto, e ninguém conseguiria explicar em qual.
 *
 * `prefixo` é casamento no começo de **palavra**, em qualquer ponto do campo — e
 * não no começo do campo. `webhook` casa no degrau alto tanto em `Webhooks`
 * quanto em `Sobre webhooks`, porque nos dois o leitor digitou o começo de uma
 * palavra que está lá. O degrau abaixo é o que sobra: o termo aparece no MEIO de
 * uma palavra, que é casamento verdadeiro e mais fraco.
 */
export const ESCADA = [
  {peso: 64, campo: 't', prefixo: true},
  {peso: 32, campo: 't'},
  {peso: 16, campo: 's', prefixo: true},
  {peso: 8, campo: 's'},
  {peso: 4, campo: 'd'},
  {peso: 2, campo: 'b'},
  {peso: 1, campo: 'u'},
];

/**
 * Minúsculas e `normalize('NFD')` sem diacrítico.
 *
 * São as poucas linhas que cobrem o erro mais comum do leitor brasileiro:
 * *conciliacao* acha `Conciliação`, *idempotencia* acha `Idempotência`. Ela roda
 * nos **dois lados** — no índice, uma vez, e na consulta, a cada tecla.
 * Normalizar só um lado é não normalizar.
 *
 * @param {string} texto
 */
export function normalizar(texto) {
  return texto
    .toLowerCase()
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '');
}

/** A consulta vira termos: normalizada, partida em espaço, sem vazio. */
export const termosDe = (consulta) => normalizar(consulta).split(/\s+/).filter(Boolean);

/** Casamento por prefixo de palavra: começo do campo, ou logo depois de um espaço. */
const comecaPalavra = (texto, termo) => texto.startsWith(termo) || texto.includes(` ${termo}`);

/**
 * O índice normalizado — uma vez, na montagem, não a cada tecla.
 *
 * @param {{u: string, t: string, d?: string, s?: string[], b?: string, x: number, f?: number}[]} registros
 */
export function normalizarIndice(registros) {
  return registros.map((r) => ({
    registro: r,
    t: normalizar(r.t),
    d: normalizar(r.d ?? ''),
    s: normalizar((r.s ?? []).join(' ')),
    b: normalizar(r.b ?? ''),
    u: normalizar(r.u),
  }));
}

/**
 * Os resultados, ordenados.
 *
 * **Todo termo precisa casar em algum degrau.** Um termo que não casa derruba o
 * registro inteiro — senão uma consulta de duas palavras devolveria tudo o que
 * casa com a mais comum das duas, que é o oposto de refinar.
 *
 * **Sem teto de resultados.** Truncar em dez seria esconder acerto sem dizer que
 * escondeu, e falha silenciosa é o que este projeto recusa em toda parte.
 *
 * Desempate: pontos, depois a aba, depois a ordem da sidebar — que é a ordem em
 * que `src/plugins/paginas.js` já entregou o índice.
 *
 * @param {ReturnType<typeof normalizarIndice>} indice
 * @param {string} consulta
 */
export function pontuar(indice, consulta) {
  const termos = termosDe(consulta);
  if (termos.length === 0) {
    return [];
  }
  return indice
    .map((entrada, posicao) => {
      let pontos = 0;
      for (const termo of termos) {
        const degrau = ESCADA.find(({campo, prefixo}) =>
          prefixo ? comecaPalavra(entrada[campo], termo) : entrada[campo].includes(termo),
        );
        if (!degrau) {
          return null;
        }
        pontos += degrau.peso;
      }
      return {...entrada.registro, pontos, posicao};
    })
    .filter(Boolean)
    .sort((a, b) => b.pontos - a.pontos || a.x - b.x || a.posicao - b.posicao);
}

/**
 * O trecho mostrado: a descrição, ou o corpo quando é ele quem casou.
 *
 * @param {{d?: string, b?: string}} registro
 * @param {string[]} termos
 */
export function trecho(registro, termos) {
  const descricao = registro.d ?? '';
  const casaNaDescricao = termos.some((termo) => normalizar(descricao).includes(termo));
  return casaNaDescricao || !registro.b ? descricao : registro.b;
}

/**
 * As faixas a realçar, em índices do texto **original**.
 *
 * A varredura é sobre o texto normalizado e as faixas voltam mapeadas para o
 * original, porque `normalize('NFD')` decompõe acento em dois pontos de código:
 * cortar pelo índice normalizado devolveria letra sem acento na tela, e o realce
 * apagaria o til de `informação` na frente do leitor.
 *
 * Quando a conta de deslocamento não fecha — um caractere cuja normalização por
 * pedaço difere da do todo —, a função devolve lista vazia. Perde-se ênfase,
 * nunca uma letra.
 *
 * @param {string} texto
 * @param {string[]} termos
 * @returns {[number, number][]} pares `[de, ate)` sem sobreposição, em ordem
 */
export function faixasDeRealce(texto, termos) {
  if (termos.length === 0 || !texto) {
    return [];
  }
  const alvo = normalizar(texto);

  // Um mapa `índice normalizado → índice original`. `origem` acumula o
  // comprimento em UNIDADES DE CÓDIGO e não a posição do laço: iterar uma
  // string por `for…of` anda por ponto de código, e um par substituto mede dois.
  const deslocamento = [];
  let origem = 0;
  for (const caractere of texto) {
    const largura = normalizar(caractere).length;
    for (let n = 0; n < largura; n += 1) {
      deslocamento.push(origem);
    }
    origem += caractere.length;
  }
  deslocamento.push(texto.length);

  if (deslocamento.length !== alvo.length + 1) {
    return [];
  }

  const cruas = [];
  for (const termo of termos) {
    let de = alvo.indexOf(termo);
    while (de !== -1) {
      cruas.push([de, de + termo.length]);
      de = alvo.indexOf(termo, de + termo.length);
    }
  }
  cruas.sort((a, b) => a[0] - b[0]);

  const faixas = [];
  let cursor = 0;
  for (const [de, ate] of cruas) {
    if (de < cursor) {
      continue;
    }
    faixas.push([deslocamento[de], deslocamento[ate]]);
    cursor = ate;
  }
  return faixas;
}
