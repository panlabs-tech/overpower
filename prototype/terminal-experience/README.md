# Prototype — overpower terminal experience

Throwaway. Built to resolve
[Prototipo da experiencia de terminal](https://github.com/panlabs-tech/overpower/issues/12).
**Not production code**, and it does not get promoted — the decision it settled gets
rebuilt properly under the repo's own gates.

It exists as a primary source: the four variants are the evidence for why one of them
won, and a later reader who disagrees can **run them** instead of arguing from prose.

---

# Roteiro de comparação visual

Siga na ordem. Cada passo diz **o que olhar** e **que decisão ele informa** — sem isso,
rodar os comandos só produz telas bonitas e nenhuma conclusão.

## Passo 0 — pegar o código sem mexer na sua `main`

Use um **worktree**, não `git checkout`: o worktree põe a branch numa pasta separada e
deixa sua `main` exatamente onde está.

```bash
cd <raiz-do-repo-overpower>
git worktree add /tmp/op-proto prototype/terminal-experience
cd /tmp/op-proto/prototype/terminal-experience
```

Nada mais para instalar. Os scripts carregam metadata PEP 723 inline, então o `uv`
resolve `typer`, `rich`, `questionary` e o pin de `prompt-toolkit` na primeira execução
(~2 s), e cacheia daí em diante.

Quando terminar: `git worktree remove /tmp/op-proto`.

## Passo 1 — a mesma tela nas quatro variantes

Este é **o** teste de comparação. Ele põe um único ecrã nos quatro tratamentos, um
debaixo do outro, para você comparar sem rolar a tela para trás.

```bash
uv run op.py compare list        # o catálogo — a tela que mais importa
uv run op.py compare detail      # list --ai-framework matt-pocock
uv run op.py compare summary     # o resumo depois de instalar
uv run op.py compare collision   # o erro que bloqueia (exit 3)
uv run op.py compare symlink     # o aviso que não bloqueia
uv run op.py compare plan        # o plano antes de escrever
uv run op.py compare banner      # os quatro banners
```

**O que olhar**: qual tratamento você consegue **ler** — não qual é mais bonito. As
quatro dizem a mesma coisa; a pergunta é onde seu olho encontra o nome, o tamanho e a
descrição sem procurar.

**Decisão que informa**: a direção visual. Hoje é a **D**.

> **Cuidado com pipe aqui.** As telas de erro escrevem no **stderr** e os títulos de
> separação no **stdout**. `compare collision | less` embaralha a ordem. Rode no
> terminal, ou acrescente `2>&1`.

## Passo 2 — uma variante inteira, ponta a ponta

`compare` mostra uma tela em quatro variantes; `all` mostra uma variante em seis telas.
É assim que você vê se um tratamento é **coerente consigo mesmo**.

```bash
uv run op.py all             # variante D — a decisão atual
uv run op.py -V a all        # A, Painel
uv run op.py -V b all        # B, Linha
uv run op.py -V c all        # C, Documento
```

**O que olhar**: se as seis telas parecem do mesmo produto. Um tratamento que acerta o
catálogo e erra o erro não serve.

## Passo 3 — largura estreita (o teste que decidiu contra a A)

```bash
uv run op.py -w 60 compare list
```

`--width`/`-w` força a largura no `rich` direto. **Não use `COLUMNS=60`** — a variável é
do shell, que a redefine, e o resultado fica não-determinístico.

**O que olhar**: reticências (`…`) e descrição espremida. Contagem exata do comando
acima — conte você mesmo, os números batem:

| | truncagens em `-w 60 compare list` | na corrida inteira (`-w 60 all`) |
| --- | --- | --- |
| A Painel | **5** | 7 |
| B Linha | **9** | 9 |
| C Documento | 0 | 0 |
| D Impacto | **0** | **0** |

(As duas colunas têm escopos diferentes: a primeira é só a tela do catálogo, a segunda
inclui `list --ai-framework`, que tem uma grade de nomes de skill.)

**Decisão que informa**: foi este passo que separou a A da D. As duas têm o mesmo
impacto visual; só a D atravessa 60 colunas sem cortar nada.

## Passo 4 — sem cor

```bash
NO_COLOR=1 uv run op.py all
```

**O que olhar**: se a hierarquia sobrevive sem cor — se você ainda distingue o nome do
artefato da descrição dele.

**O que já está medido e não precisa ser reconferido**: `NO_COLOR` remove **cor**, não
ANSI. Sobram `ESC[1m` (bold) e `ESC[2m` (dim). É comportamento do `rich`, não escolha
nossa, e vale igual nas quatro.

## Passo 5 — sob pipe, que é o que o CI vê

```bash
uv run op.py all | cat
uv run op.py install --ai-framework matt-pocock --yes | cat
```

**O que olhar**: log limpo. Banner suprimido, barra de progresso silenciosa, zero
sequência de escape.

**Medido**: as quatro emitem **0 escapes ANSI** sob pipe. O `rich.Progress` transiente
degrada sozinho.

## Passo 6 — o wizard, que exige TTY de verdade

```bash
uv run op.py install          # sem flags, com terminal = wizard
```

Setas para escolher, Enter para confirmar.

**O que olhar — e o que não adianta olhar**: as telas de seleção são **idênticas nas
quatro variantes**. Medido dirigindo as quatro por PTY com teclas enviadas. O
`questionary` é dono daquela tela inteira; a variante só aparece no plano (antes) e no
resumo (depois). **O wizard não é eixo de escolha visual** — não gaste tempo comparando.

Se quiser ver os frames sem digitar:

```bash
python3 drive.py d            # dirige por PTY e imprime frame a frame
```

## Passo 7 — a língua

```bash
uv run op.py --lang pt all    # o copy em pt-BR, que perdeu
uv run op.py --lang en all    # inglês, a decisão
```

**O que olhar no wizard em pt-BR**: pergunte-se `Escrever?` e aperte **`s`** de "sim".
Nada acontece. Aperte `y` e a resposta ecoa **`Yes`**.

**Por quê** — lido no fonte do `questionary 2.1.1`, não inferido: as teclas são fixas
(`@bindings.add("y")`, `"Y"`, `"n"`, `"N"`; **não existe binding para `s`**), o eco vem
de constante de módulo (`YES = "Yes"`), `instruction=` cobre o `(Y/n)` mas **não** o eco,
e patchar `questionary.constants.YES` não funciona porque o módulo já importou o nome.

**Decisão que informa**: a voz do produto. Foi este passo que decidiu inglês, e o motivo
é técnico antes de ser de gosto.

---

## Se você não quiser rodar nada

`captures/` tem tudo já renderizado, com ANSI removido — a 80 colunas, a 60 colunas e sob
pipe, por variante. É contra esses arquivos que a decisão foi tomada.

```bash
diff captures/variant-a-60cols.txt captures/variant-d-60cols.txt
```

---

## As quatro variantes

| | aposta | catálogo | corrida toda | @60 colunas |
| --- | --- | --- | --- | --- |
| **A** Painel | molduras em tudo, catálogo como tabela com borda | 42 linhas | 12,1 KB | descrição a ~18 chars, 5 linhas/item — 7 truncagens |
| **B** Linha | sem molduras, uma linha por coisa, erro no formato do cargo | 12 linhas | 2,8 KB | trunca a descrição, mantém tag + nome + tamanho |
| **C** Documento | réguas e indentação como estrutura, sem bordas | 45 linhas | 5,8 KB | reembrulha, 0 truncagens |
| **D** Impacto | as molduras da A, entrada de catálogo em bloco | 46 linhas | 12,5 KB | **reembrulha dentro da moldura, 0 truncagens** |

**A D venceu**, sob um critério que o dev forneceu depois de ver as três primeiras:
**impacto visual é requisito declarado do projeto** — o
[#8](https://github.com/panlabs-tech/overpower/issues/8) escreve isso —, e a primeira
passada o havia ranqueado abaixo de perda de informação a 60 colunas. A D existe porque a
A tinha exatamente um defeito medido, a tabela de três colunas, e ele sai sem devolver uma
única borda. Raciocínio completo no comentário de resolução do ticket.

## O que os dados são

- Números do framework são **medidos**: 22 skills / 68 arquivos / 196.849 bytes, do
  [#15](https://github.com/panlabs-tech/overpower/issues/15).
- Tamanhos do pool são **medidos** de `~/.agents/skills` na máquina do dev.
- Composição dos bundles é **ilustrativa** — nenhum ticket decidiu isso ainda.
