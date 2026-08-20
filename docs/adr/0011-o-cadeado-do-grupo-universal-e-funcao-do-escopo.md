# O cadeado do grupo universal volta, e a sua composição é função do escopo

O grupo `Universal` do passo de runtime volta a ser **seção travada** — *always included*, não selecionável — como no [`vercel-labs/skills`](https://github.com/vercel-labs/skills). E a sua **composição depende do escopo**: em projeto são os **19** runtimes que leem `.agents/skills`; em global são os **6** que leem `~/.agents/skills`.

Isto **reverte** uma posição da [ADR 0008](0008-a-tela-e-herdada-a-escrita-nao.md), que dizia, sobre a seção travada do upstream:

> O [#9](https://github.com/ThiagoPanini/overpower/issues/9) removeu esse modelo: em projeto não há canônico, cada runtime recebe cópia real. **O grupo continua na tela; o cadeado sai.**

O cadeado volta. A ADR 0008 segue de pé em tudo o mais — o pulo silencioso, o default, a sonda e o lockfile continuam fora.

## O preço, medido antes de ser aceito

O cadeado do upstream é honesto **lá** porque lá existe um canônico: em modo symlink o `npx skills` escreve `.agents/skills/` sempre, antes de qualquer link, e desmarcá-lo seria mentira. É também por isso que a tela dele tem um passo que a nossa não tem — `Installation method · Symlink / Copy`.

O [#9](https://github.com/ThiagoPanini/overpower/issues/9) removeu esse modelo em projeto, com medição: sob `core.symlinks=false` — que a doc do git diz ser **auto-detectado no clone**, isto é, o padrão no Windows e não a exceção — o link materializa como arquivo de texto, o `git status` fica **limpo** e o equipamento está quebrado para quem clonou. Em projeto, cada runtime recebe **cópia real**.

Copiar o cadeado sem copiar o symlink cobra isto de quem só usa Claude Code, em escopo de projeto, com o `matt-pocock` de 74 arquivos:

| | `npx skills` | overpower com cadeado |
| --- | ---: | ---: |
| `.agents/skills/` | 74 arquivos reais | 74 arquivos reais |
| `.claude/skills/` | 1 symlink | **74 arquivos reais** |
| no `git status` | 75 | **148** |

Os 74 de `.agents/skills/` não são lidos por nada na máquina dessa pessoa: medido no Claude Code 2.1.223, headless, com skill plantada nas duas pastas — `.claude/skills/probe-beta` é descoberta e `.agents/skills/probe-alpha` **não**.

**O preço foi apresentado com esses números e aceito.** A razão é de produto: o `npx skills` é a inspiração declarada do wizard, e a seção *always included* é o que torna `.agents` legível **como default** em vez de como mais uma linha marcada entre 76. Uma linha pré-marcada e uma linha travada diferem por um toque de barra de espaço; o que a segunda compra é a pessoa entender, sem contar caixas, que existe um caminho que equipa vinte runtimes de uma vez.

## Por que a composição é função do escopo

Porque em global o cabeçalho não teria caminho para nomear. Medido: os 18 runtimes do grupo universal que existem em escopo global aterrissam em **11 diretórios distintos**, e só **6** — `cline`, `dexto`, `kimi-code-cli`, `loaf`, `warp`, `zed` — caem em `~/.agents/skills`. Os outros vão para o seu próprio: `codex` para `~/.codex/skills`, `cursor` para `~/.cursor/skills`, `amp` para `~/.config/agents/skills`. Os 74 runtimes globais produzem **66 lugares**.

Um cabeçalho `Universal (~/.agents/skills)` com 18 nomes embaixo afirmaria que aquela pasta equipa os 18. Equipa 6. É a classe *"a tela diz uma coisa e o resultado é outra"* que a ADR 0008 existe para recusar, chegando pela tela em vez de pela escrita — e travada ela seria pior, porque a pessoa não poderia sequer desmarcar o que não lhe serve.

A forma já existe no repositório: a [ADR 0009](0009-o-conjunto-de-runtime-e-funcao-do-escopo.md) fixou que **o conjunto que `--runtime` aceita é função do escopo**. Aqui o **grupo** também é. Mesma função, mesma razão — a tabela é parcial, e o que não existe naquele escopo não aparece.

Isto corrige, de passagem, um defeito que existia: `runtime_choices` montava o grupo sobre `project_dir` **nos dois escopos**, então a tela global já vinha nomeando `.agents/skills` para 18 runtimes dos quais 12 leem outro lugar.

## O cadeado é da tela, não do plano

O wizard põe as chaves travadas no `Request` que ele monta, e o `Request` continua sendo **o mesmo tipo** que as flags montam. Logo:

```
overpower install --runtime claude-code            → escreve .claude/skills/ e mais nada
(wizard, nada marcado em "Additional agents")      → escreve .agents/skills/
```

A flag continua literal. É o que preserva a decisão do [#8](https://github.com/ThiagoPanini/overpower/issues/8) de que **a linha de comando é o manifesto** — ela tem de caber num README, num Makefile e num passo de CI, e significar ali o mesmo que significa no terminal. Um cadeado que fosse regra de planejamento faria `--runtime claude-code` escrever duas árvores, e a flag pararia de dizer o que faz.

Também é o que mantém a asserção central: *o plano é igual ao disco*. O plano não ganha nada implícito; ele lista o que o `Request` carrega, e o `Request` carrega o que a tela mostrou travado.

## Consequences

**Quem só usa Claude Code paga 74 arquivos versionados que ninguém lê**, e a saída é a linha de flags: `overpower install --ai-framework matt-pocock --runtime claude-code`. O wizard não oferece essa saída, por construção. A [ADR 0003](0003-sem-atribuicao-no-alvo.md) e o axioma 2 continuam valendo — os arquivos aparecem no `git status`, então nada é invisível; o custo é de diff, não de auditoria.

**O grupo travado nunca é vazio**, nos dois escopos, então o wizard não consegue mais produzir seleção de runtime vazia. `NoRuntimeSelectedError` passa a ser alcançável só pelo caminho de flags — o que já era a sua razão de existir.

**Os números 19 e 6 são vendorizados como o 76 e o 74.** Vêm do upstream e envelhecem com ele; pela **regra 5** a versão do overpower é a versão da tabela. Um refresh que mude quem lê `.agents/skills` muda os números e não muda esta decisão.

**Esta ADR se reabre** se o método de escrita voltar a ser escolha — um `--copy`/symlink em projeto, que o [#9](https://github.com/ThiagoPanini/overpower/issues/9) matou —, porque aí o canônico volta e o cadeado deixa de ser preço e passa a ser consequência, como é no upstream. Reabre também se a tabela deixar de ter caminho compartilhado por muitos, porque aí não há grupo a travar.
