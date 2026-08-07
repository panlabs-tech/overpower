# Transporte não é instalador

O overpower invoca `git` como subprocesso para obter o conteúdo de `--from`. O [axioma 1](../agents/domain.md#axiomas) dizia *"nada de subprocesso alheio; todo buscar-e-posicionar é código Python do próprio overpower"*, e esta decisão o emenda.

A emenda troca uma proibição por uma proibição **mais estreita** e uma **obrigação** que não existia:

> **Proibido: instalador de terceiro** — qualquer coisa que decida *o que* aterrissa ou *onde*.
> **Obrigatório: nenhum binário de terceiro pode ser requisito** — todo caminho por subprocesso carrega um fallback puro-Python que entrega o mesmo resultado.

`git fetch` move bytes para um diretório temporário que nós nomeamos. Quem procura o `SKILL.md`, quem resolve ambiguidade e quem copia para o destino continua sendo código nosso. `npx <instalador>` — o exemplo que o axioma dá — roda código de terceiro que decide o layout. A linha que separa os dois é a **autoria da aterrissagem**, e ela permanece integralmente nossa.

Decidido em [Busca remota: mecanismo de obtenção e autenticação do `--from`](https://github.com/panlabs-tech/overpower/issues/25).

## Considered Options

A leitura literal do axioma sobrevive tecnicamente: `urllib` + `tarfile` obtêm o mesmo conteúdo em **14 linhas**, e foram construídos e rodados. Ela foi recomendada e perdeu para uma escolha do dev; o que se segue é o que a medição diz sobre o preço de cada lado, não uma reconstrução do argumento vencedor.

**A razão declarada do axioma passou a estar satisfeita pelos dois lados.** Ele se justifica dizendo *"o alvo de replicação é um ambiente corporativo sem esse ferramental"*. Com o fallback obrigatório, o overpower funciona inteiro numa máquina sem `git` — a obrigação da emenda existe precisamente para manter isso verdadeiro, e é ela que impede a emenda de virar licença para o próximo binário.

**O que o `git` alcança e o puro-Python não.** Medido em ambiente limpo, contra repositório privado real: `git clone` com `GH_TOKEN` **e** `GITHUB_TOKEN` no ambiente **falha** — git não lê essas variáveis; o mesmo token via `Authorization: Bearer` no `urllib` devolve **200**. E na direção oposta, um clone com `HOME` e ambos os gitconfigs zerados **funcionou**, porque `GIT_ASKPASS` estava setado pelo editor e respondeu por IPC. Os conjuntos de credencial são **disjuntos, não aninhados**:

| | alcança |
| --- | --- |
| `git` | credential helper, chave SSH, `GIT_ASKPASS` do editor |
| `urllib` | `GH_TOKEN`/`GITHUB_TOKEN`, `~/.netrc`, `~/.config/gh/hosts.yml` |

**O que o puro-Python alcança e o `git` não** é velocidade e ausência de scratch: 0,53 s contra 1,80 s no caminho exato, e zero byte em disco contra 224.786 B.

**O forge-agnosticismo não pesou, porque o escopo o dispensou.** Medido, `git clone --depth 1 --filter=blob:none --sparse <url>` roda igual em `github.com`, `gitlab.com` e `codeberg.org`, enquanto a forma de tarball do GitHub contra o GitLab dá **403** e a forma de árvore dá **404** — um código por forge. O dev fixou que a fonte é **apenas GitHub**, e o argumento caiu junto.

## Consequences

**A obrigação vale para o próximo caso, não só para este.** Qualquer futuro subprocesso — `gh`, um binário de sync, um descompressor externo — nasce devendo um caminho puro-Python equivalente. Sem ele, não entra.

**`git credential fill` está morto para este desenho, por construção.** Se o `git` está ausente, ele também está; e se o `git` está presente **com** credencial, o primário já a usou e não teria caído no fallback. Ele não acrescenta nada que o primário não tenha tentado.

**Classificar falha de subprocesso exige `LC_ALL=C`.** Os três erros de obtenção — ref inexistente, repo inexistente, sem credencial — saem todos com `exit=128`; só o texto do stderr distingue. Este host traz **20 catálogos `git.mo`**, logo as strings são traduzíveis. O teste de tradução saiu **inconclusivo** (nenhum locale não-C gerado; o controle com `git status` também não traduziu), então a guarda é obrigatória por precaução, não por medição. É a mesma armadilha que pesou contra o `mklink /J` na [pesquisa de junction](https://github.com/panlabs-tech/overpower/issues/19), aqui ao custo de uma variável de ambiente.

**Sem credencial nenhuma, `git` não distingue repositório privado de inexistente** — os dois dão `could not read Username`, porque ele pede usuário antes de poder saber se o repo existe. Com credencial presente vira `repository '…' not found`, que o GitHub usa para os dois casos por desenho. A única discriminação que sobrevive sempre é `couldn't find remote ref <ref>`.
