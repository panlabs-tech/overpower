# A tela é herdada do `npx skills`; a escrita não

O overpower segue o padrão de seleção de runtime do [`vercel-labs/skills`](https://github.com/vercel-labs/skills) — a **tabela de caminhos**, as **ramificações** e a **tela**. Não segue o que ele faz **na hora de escrever**.

A divisão não é de gosto. Três comportamentos do `npx skills` foram medidos, e nos três o que ele **anuncia** diverge do que ele **põe em disco**, sempre com `exit 0`:

| comando (`skills@1.5.22`) | anunciado | escrito |
| --- | --- | --- |
| `-a devin` | `./.agents/skills/probe-skill` | `./.devin/skills/` — `.agents/` nem existe |
| `-a devin -a claude-code` | `.agents` + Claude Code | `.agents/` + `.claude/` — **`.devin/` nada, sem aviso** |
| `--yes`, `HOME` limpo | *"Installing to all agents"*, `universal: …+14 more`, `symlink → …+51 more` | **3 diretórios**, 3 arquivos — ~53 runtimes sem nada |

É a classe *"sucesso com conteúdo errado"* que a [ADR 0006](0006-a-arvore-e-o-catalogo.md) usou para recusar o catálogo declarativo e que o [#11](https://github.com/panlabs-tech/overpower/issues/11) gastou dois portões para pegar.

## O que é herdado

**A tabela de caminhos.** 76 runtimes, 55 caminhos de projeto distintos, transcritos de `src/agents.ts`. O pacote é MIT com `LICENSE` na raiz, então o portão legal do [#15](https://github.com/panlabs-tech/overpower/issues/15) passa com atribuição. A alternativa — só entrar linha com fonte primária lida — foi recusada: o mapa tinha **5** runtimes medidos, e o Devin, que o dev nomeou, não estava entre eles.

**As ramificações e a tela.** Lista completa com busca, grupo `Universal (.agents/skills)`, pré-marcação, ordem de conteúdo antes de destino.

## O que não é herdado, e por quê

**O pulo silencioso.** Em projeto, para runtime não-universal cuja pasta raiz não existe e que não seja `claude-code`, o `npx skills` retorna `success: true, skipped: true` e não escreve. O overpower escreve: runtime nomeado é runtime equipado. Segue a **regra 7** ([#16](https://github.com/panlabs-tech/overpower/issues/16)) — *"o comando é o contrato"* — e a escrita incondicional do [#9](https://github.com/panlabs-tech/overpower/issues/9). O `exit 3` do [#8](https://github.com/panlabs-tech/overpower/issues/8) é *"rodei, e a resposta é não"*, e não é este caso: aqui a resposta é sim e o alvo foi nomeado.

**O default.** O `npx skills` instala em **todos os 76** quando nada é detectado e `--yes` está presente. Isso só sobrevive **porque** ele pula — sob escrita incondicional, criaria 55 diretórios no repositório. Sem TTY, o overpower exige `--runtime` e sai 2, pelo mesmo precedente que o [#8](https://github.com/panlabs-tech/overpower/issues/8) já aplicou a escopo fora de repo git: *"tem de ser explícito"*.

**A seção travada.** Lá, `Universal (.agents/skills)` é travada porque `.agents/skills/` é o **canônico** — em modo symlink ele é escrito sempre, antes de qualquer link, e desmarcá-lo seria mentira. O [#9](https://github.com/panlabs-tech/overpower/issues/9) removeu esse modelo: em projeto não há canônico, cada runtime recebe cópia real. O grupo continua na tela; o cadeado sai. Medido, o cadeado custaria **+76 arquivos versionados e +480 KiB** na árvore de quem seleciona só Claude Code — que, medido no Claude Code 2.1.223, **não lê `.agents/skills/`**.

**A sonda de detecção.** **65 dos 76** `detectInstalled` do `npx skills` sondam o `~`; 7 sondam o `cwd`. Em escopo de projeto o que se decide é o que o **repositório** carrega, e isso é propriedade do time — que nem o `~` nem uma memória de última seleção enxergam, porque as duas são da máquina de quem instala. A sonda do overpower olha a **raiz do alvo**: projeto sonda o repo, global sonda o `~`, com fallback para o `~` num repo ainda sem diretório de runtime.

**O lockfile de pré-seleção.** O `npx skills` guarda `lastSelectedAgents` em `$XDG_STATE_HOME/skills/.skill-lock.json` — ou, sem a variável, em `~/.agents/.skill-lock.json`, isto é, **dentro da zona de aterrissagem**. O overpower não tem arquivo de estado nenhum: versionamento de schema, migração, corrupção e deleção não se pagam para poupar dois toques de espaço. A pré-marcação vem da detecção.

## Consequences

**O plano lista caminho, não nome de runtime.** Selecionar Cursor escreve `.agents/skills/`, que Codex, Copilot, VS Code e outros 15 também leem. Anunciar *"Cursor"* prometeria um alvo e entregaria vinte. A tela de confirmação mostra o caminho e quem o consome — `.agents/skills/ ← cursor, codex, github-copilot (+16)`.

**Não existe caminho único que cubra todos os runtimes.** Medido em 2026-08-06: o Claude Code 2.1.223 **não** descobre skill em `.agents/skills/`, e o Codex não lê `.claude/skills/`. Cobertura total custa duas escritas, sempre.

**Em global o colapso do universal vale igual, e o pulo não existe.** Medido: `~/.agents/skills/<nome>/` real, `~/.claude/skills/<nome>` e `~/.config/devin/skills/<nome>` como link, e nada em `~/.cursor`, `~/.codex` ou `~/.copilot` — o campo `globalSkillsDir` é declarado e **não usado** para os universais.

**A tabela envelhece por fora, e isso é datável.** Entre a `1.5.21` que a pesquisa do [#5](https://github.com/panlabs-tech/overpower/issues/5) leu em 2026-07-30 e a `1.5.22` de hoje: **+1 runtime** (`minimax-code`), nenhum removido. Cresce ~1 por semana e nunca encolhe. Pela **regra 5** ([#7](https://github.com/panlabs-tech/overpower/issues/7)) a versão do overpower é a versão da tabela, e `uvx overpower@latest` já é requisito de correção — então a defasagem é a cadência de release, não o infinito. Não há escotilha `--dir` na v0.1.0: o `npx skills` também não tem uma.

**Esta ADR se reabre se a divergência virar manutenção.** Ela não trava a tabela nem a tela — as duas são cópia consciente e crescem com o upstream. O que ela trava é a **fronteira**: qualquer comportamento do `npx skills` que dependa do canônico, do lockfile ou do pulo silencioso não atravessa, porque as três premissas não existem aqui.
