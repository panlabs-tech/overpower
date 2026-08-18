/**
 * `SearchBar` — **degrau 5** do ADR 2 do shinydoc, o primeiro `--eject` do projeto.
 *
 *   ejetado de @docusaurus/theme-classic@3.10.2
 *
 * Cabeçalho de versão obrigatório: o gerador do Docusaurus remove o cabeçalho de
 * licença ao ejetar, e sem anotação não há contra o que diffar no upgrade.
 *
 * **Zero linha de upstream copiada, e isso é fato e não disciplina.** O
 * `SearchBar` do `theme-classic` é `export {default} from '@docusaurus/Noop'` —
 * uma linha, que devolve `null`. O tema clássico não tem busca; ele tem o
 * ponto de extensão. É por isso que o degrau 5 aqui não carrega a dívida que o
 * degrau 5 costuma carregar: não há implementação upstream para reconciliar.
 *
 * > **Desvio de `--typescript` — o desvio 2, e hoje o único do repositório.** O
 * > desvio 1 saiu com `NavbarItem/ComponentTypes.js`, que era idêntico ao
 * > upstream nas nove chaves; a numeração não é remendada. O ADR 2 do shinydoc diz
 * > *sempre*, e a regra existe para o que a flag protege — **assinatura de
 * > props**. Medido no 3.10.2: os dois consumidores (`Navbar/Content` e
 * > `NavbarItem/SearchNavbarItem`) montam `<SearchBar />`, sem uma prop. E o
 * > repositório não tem `typescript` instalado: o que compila `.tsx` aqui é o
 * > `@babel/preset-typescript` do `@docusaurus/babel`, que **apaga** os tipos
 * > sem conferir nenhum. A flag entregaria a forma da garantia sem a garantia,
 * > e cobraria uma dependência de toolchain contra o axioma 2.
 * >
 * > O que fica no lugar dela: este arquivo tem superfície de props **zero**,
 * > então a mudança que a flag pegaria não existe. O que pode mudar é o nome do
 * > componente no upstream — e isso quem pega é o portão 7, diffando o
 * > `swizzle --list` congelado.
 *
 * ---------------------------------------------------------------------------
 * O que este arquivo NÃO escreve
 *
 * Armadilha de foco, camada superior sobre todo `z-index` da página,
 * `::backdrop`, `Escape` e restauração do foco ao elemento que abriu o modal.
 * Tudo isso vem de `<dialog>` + `showModal()`, do navegador. **Não há uma linha
 * de gestão de foco aqui**, e é o motivo de o modal ser um `<dialog>` em vez de
 * uma `<div>` com `position: fixed`.
 *
 * Este é o **único JS de interação que o projeto autora**, e ele mora no
 * chrome. O catálogo de conteúdo continua em zero — ver o *substrato nativo*
 * em `docs/agents/domain.md`.
 *
 * A escada de pontuação, a normalização e o cálculo do realce **não moram
 * aqui**: são lógica pura, vivem em `./escada.mjs` e são cobradas por
 * `scripts/busca.test.mjs`. O que sobra neste arquivo é JSX mais os ganchos do
 * `<dialog>` — que é a parte que só um navegador sabe conferir.
 *
 * Procedência: shinydoc-docusaurus/docs/design/busca.md · ADR 6 do shinydoc.
 */

import React, {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import {useHistory} from '@docusaurus/router';
import {usePluginData} from '@docusaurus/useGlobalData';
import Translate, {translate} from '@docusaurus/Translate';
import Icon from '@site/src/components/Icon';
import estilos from './estilos.module.css';
import {
  faixasDeRealce,
  normalizarIndice,
  pontuar,
  termosDe,
  trecho,
} from './escada.mjs';

const ID_LISTA = 'sd-busca-lista';
const idOpcao = (i) => `sd-busca-opcao-${i}`;

export default function SearchBar() {
  const dados = usePluginData('sd-busca');
  const history = useHistory();
  const dialogo = useRef(null);
  const entrada = useRef(null);
  const [consulta, setConsulta] = useState('');
  const [ativo, setAtivo] = useState(0);
  const [mac, setMac] = useState(false);

  // O índice normalizado, uma vez na montagem e não a cada tecla. `undefined`
  // quando o plugin não está na config — ver o `return null` lá embaixo.
  const indice = useMemo(() => dados && normalizarIndice(dados.registros), [dados]);

  const resultados = useMemo(() => (indice ? pontuar(indice, consulta) : []), [indice, consulta]);

  const abrir = useCallback(() => {
    dialogo.current?.showModal();
    // Não é gestão de foco: é pôr o cursor no único campo do modal. A armadilha,
    // a camada e a restauração continuam sendo do `<dialog>`.
    entrada.current?.select();
  }, []);

  const fechar = useCallback(() => dialogo.current?.close(), []);

  // O glifo da tecla só é decidido DEPOIS da montagem, e é de propósito: o
  // servidor não sabe em que plataforma a página vai abrir, e renderizar `⌘`
  // no HTML produziria divergência de hidratação. `Ctrl` é o estado inicial
  // porque é o da maioria; no Mac ele troca no primeiro quadro.
  useEffect(() => setMac(/mac|iphone|ipad/i.test(navigator.userAgent)), []);

  // `⌘K` / `Ctrl K` e NADA MAIS. `/` foi recusado: ele exige uma guarda de
  // *"estou dentro de um campo?"*, e o modo de falhar dessa guarda é invisível —
  // o leitor digita uma barra num formulário e o modal abre por cima.
  useEffect(() => {
    if (!indice) {
      return undefined;
    }
    const aoTeclar = (evento) => {
      if (evento.key.toLowerCase() === 'k' && (evento.metaKey || evento.ctrlKey)) {
        evento.preventDefault();
        if (dialogo.current?.open) {
          fechar();
        } else {
          abrir();
        }
      }
    };
    window.addEventListener('keydown', aoTeclar);
    return () => window.removeEventListener('keydown', aoTeclar);
  }, [indice, abrir, fechar]);

  // Sem teto de resultados, a lista rola — e a opção ativa precisa estar à
  // vista. Rolagem não é foco: o foco nunca sai do campo, que é o que
  // `aria-activedescendant` compra.
  useEffect(() => {
    document.getElementById(idOpcao(ativo))?.scrollIntoView({block: 'nearest'});
  }, [ativo]);

  const escolher = useCallback(
    (i) => {
      const alvo = resultados[i];
      if (alvo) {
        fechar();
        history.push(alvo.u);
      }
    },
    [resultados, fechar, history],
  );

  const aoTeclarNoCampo = (evento) => {
    if (evento.key === 'ArrowDown') {
      evento.preventDefault();
      setAtivo((i) => (i + 1) % Math.max(resultados.length, 1));
    } else if (evento.key === 'ArrowUp') {
      evento.preventDefault();
      setAtivo((i) => (i - 1 + resultados.length) % Math.max(resultados.length, 1));
    } else if (evento.key === 'Enter') {
      evento.preventDefault();
      escolher(ativo);
    }
    // `Escape` NÃO aparece aqui. O `<dialog>` o trata, fecha e devolve o foco
    // ao botão. Escrevê-lo seria escrever de novo o que o navegador já faz.
  };

  // **Quando a busca não existe, o navbar não muda.** Tirar o plugin da config
  // faz `usePluginData` devolver `undefined`; o componente devolve `null`, e o
  // `Navbar/Search` do upstream esconde o contêiner vazio pelo próprio
  // `:empty`. Sem botão, sem atalho, sem modal — e o navbar reflui sozinho.
  if (!indice) {
    return null;
  }

  const rotulos = dados.secoes;
  const termos = termosDe(consulta);

  return (
    <>
      <button
        type="button"
        className={estilos.botao}
        data-sd-component="busca"
        data-sd-part="gatilho"
        onClick={abrir}>
        <Icon name="search" size="sm" />
        <span className={estilos.rotulo}>
          <Translate id="shinydoc.busca.abrir" description="Rótulo do botão que abre a busca">
            Search
          </Translate>
        </span>
        <kbd className={estilos.atalho}>{mac ? '⌘' : 'Ctrl'} K</kbd>
      </button>

      <dialog ref={dialogo} className={estilos.modal} data-sd-component="busca" onClose={() => setAtivo(0)}>
        {/* ARIA por CITAÇÃO do padrão `Combobox With List Autocomplete` do
            WAI-ARIA APG, e não por invenção. É o único lugar do projeto onde a
            spec descreve ARIA em prosa, e ela aponta para um padrão publicado:
            `role="combobox"` no próprio campo (ARIA 1.2, não o invólucro do
            1.0), `aria-controls` para a listbox, `aria-autocomplete="list"`, e
            `aria-activedescendant` — que é o que mantém o FOCO no campo
            enquanto a seleção anda pela lista. */}
        <div className={estilos.campo} data-sd-part="campo">
          <Icon name="search" size="sm" />
          <input
            ref={entrada}
            type="text"
            role="combobox"
            autoComplete="off"
            spellCheck="false"
            aria-expanded={resultados.length > 0}
            aria-controls={ID_LISTA}
            aria-autocomplete="list"
            aria-activedescendant={resultados.length > 0 ? idOpcao(ativo) : undefined}
            aria-label={translate({
              id: 'shinydoc.busca.campo',
              message: 'Search the documentation',
              description: 'Nome acessível do campo de busca',
            })}
            value={consulta}
            onChange={(evento) => {
              setConsulta(evento.target.value);
              setAtivo(0);
            }}
            onKeyDown={aoTeclarNoCampo}
          />
          <button
            type="button"
            className={estilos.fechar}
            onClick={fechar}
            aria-label={translate({
              id: 'shinydoc.busca.fechar',
              message: 'Close search',
              description: 'Nome acessível do botão que fecha o modal de busca',
            })}>
            <Icon name="x" size="sm" />
          </button>
        </div>

        <ul
          id={ID_LISTA}
          role="listbox"
          className={estilos.lista}
          aria-label={translate({
            id: 'shinydoc.busca.resultados',
            message: 'Results',
            description: 'Nome acessível da lista de resultados da busca',
          })}>
          {resultados.map((r, i) => (
            <li
              key={r.u}
              id={idOpcao(i)}
              role="option"
              aria-selected={i === ativo}
              className={estilos.opcao}
              data-sd-part="resultado"
              onClick={() => escolher(i)}
              onMouseMove={() => setAtivo(i)}>
              <span className={estilos.titulo}>{realcar(r.t, termos)}</span>
              <span className={estilos.aba}>{rotulos[r.x]}</span>
              {r.f ? (
                <span className={estilos.fallback}>
                  <Translate
                    id="shinydoc.busca.fallback"
                    description="Marca de resultado cuja página ainda está em português">
                    untranslated
                  </Translate>
                </span>
              ) : null}
              <span className={estilos.trecho}>{realcar(trecho(r, termos), termos)}</span>
            </li>
          ))}
        </ul>

        <p role="status" className={estilos.aVozAlta}>
          {consulta.trim() === ''
            ? ''
            : translate(
                {
                  id: 'shinydoc.busca.contagem',
                  message: '{n} results',
                  description: 'Anúncio do número de resultados, para leitor de tela',
                },
                {n: resultados.length},
              )}
        </p>

        {/* As teclas são CARACTERES SOLTOS desde a #98 — nem ícone, nem
            elemento de teclado. Três setas desenhadas custariam três slots e
            estourariam o teto de 64 do manifesto — e `↑` já é a seta. */}
        <footer className={estilos.rodape}>
          <span>
            ↑↓{' '}
            <Translate id="shinydoc.busca.tecla.navegar" description="Legenda das setas no rodapé do modal">
              navigate
            </Translate>
          </span>
          <span>
            ↵{' '}
            <Translate id="shinydoc.busca.tecla.abrir" description="Legenda do Enter no rodapé do modal">
              open
            </Translate>
          </span>
          <span>
            esc{' '}
            <Translate id="shinydoc.busca.tecla.fechar" description="Legenda do Esc no rodapé do modal">
              close
            </Translate>
          </span>
        </footer>
      </dialog>
    </>
  );
}

/**
 * O realce — peso e, desde a #98, tinta de acento.
 *
 * A linha ativa deixou de ser `--sd-surface-wash` (ver `estilos.module.css`,
 * `.opcao[aria-selected]`), então o `<mark>` pode colorir sem cair acento
 * sobre acento no mesmo pixel. O elemento continua sendo `<mark>` porque é
 * ele que carrega o significado; o que o CSS troca agora é a tinta e o peso.
 *
 * Quem sabe ONDE cortar é `escada.mjs`, que devolve faixas já mapeadas para o
 * texto original. Aqui só se monta o JSX.
 */
function realcar(texto, termos) {
  const faixas = faixasDeRealce(texto, termos);
  if (faixas.length === 0) {
    return texto;
  }
  const pedacos = [];
  let cursor = 0;
  for (const [de, ate] of faixas) {
    pedacos.push(texto.slice(cursor, de));
    pedacos.push(<mark key={`${de}-${ate}`}>{texto.slice(de, ate)}</mark>);
    cursor = ate;
  }
  pedacos.push(texto.slice(cursor));
  return pedacos;
}
