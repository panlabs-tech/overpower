# Modelo de aterrissagem: projeto x global, symlink e fallback de cópia

> Pesquisa da [issue #5](https://github.com/panlabs-tech/overpower/issues/5). Consultas feitas em **2026-07-30**.
>
> **Decisão já tomada, que esta pesquisa detalha e não reabre**: multi-runtime via symlink, com fallback para cópia real quando symlink não estiver disponível.
>
> **Restrição dura** ([axioma 1](../agents/domain.md#axiomas)): o overpower **nunca invoca o `npx skills`**. Ele é estudado aqui como referência de desenho e reimplementado em Python.

---

## Resumo executivo

1. **`.agents/skills/` é caminho de leitura oficial de Cursor, Codex, Copilot e VS Code** — cada um documenta isso na sua própria doc. Não é convenção do `npx skills`; é o alvo real. Consequência que reordena o problema: **quatro dos cinco runtimes dispensam symlink por completo**. Só o Claude Code, que lê `.claude/skills/`, precisa de um link. Toda a complexidade de detecção e fallback existe para **um** runtime.

2. **Symlink de skill é mecanismo de primeira classe, documentado, e deduplicado.** O Claude Code afirma explicitamente que a entrada `<skill-name>` pode ser um symlink e que ele segue o link para ler o `SKILL.md` do alvo — e que, se o mesmo alvo é alcançável por mais de um caminho, a skill é carregada **uma vez só**. Isso não é um truque tolerado; é contrato publicado.

3. **A precedência do Claude Code é o inverso da intuição do ticket.** A doc afirma: *enterprise > pessoal > projeto*. Uma cópia velha versionada num repo **não** sombreia a fresca do global — é a **pessoal que sombreia a de projeto**. O perigo real é o simétrico e mais silencioso: você edita `.claude/skills/x` no repo e o Claude continua rodando o `~/.claude/skills/x` obsoleto, sem aviso. Nos outros runtimes não há regra publicada: o Codex diz explicitamente que **não** resolve, e os demais silenciam.

4. **No Windows a escada tem três degraus, não dois.** *Directory junction* dispensa o privilégio que o symlink exige — "Directory junctions can be created by non-administrator users by default" (Git for Windows). O `npx skills` nunca tenta symlink no Windows: vai direto a junction. Isso empurra a cópia real para o último recurso de verdade.

5. **A detecção de capacidade tem que ser um probe real, no diretório de destino exato.** Não existe na stdlib um `os.supports_*` que responda a pergunta — `os.supports_follow_symlinks` é sobre aceitar um *parâmetro*, não sobre ter privilégio. E heurística por plataforma erra: provei que WSL2 **cria symlink com sucesso em `/mnt/c`** (NTFS via 9p/drvfs). O probe também precisa separar *não consigo escrever* de *não consigo linkar* — o `npx skills` funde os dois num `catch` genérico, e o diagnóstico piora.

6. **A identidade de uma skill é o nome do diretório.** A spec exige que `name` **case com o nome do diretório pai**. Colisão de nome é colisão de caminho, detectável por inspeção antes de escrever — e renomear na aterrissagem para evitar colisão é proibido.

7. **No git, symlink é `mode 120000` e o blob é o texto do caminho.** Verificado empiricamente e confirmado na doc. Sob `core.symlinks=false` o clone materializa um **arquivo de texto comum**, e `git status` fica **limpo** — o repo parece íntegro enquanto o equipamento está quebrado. Pior: a doc do git diz que `clone`/`init` **detectam e gravam essa config sozinhos**, então o estado silencioso é o padrão no Windows, não a exceção. Para links, `git status` limpo não prova integridade — e é daí que sai a necessidade de um verificador próprio (§7.6).

---

## 1. O que a fonte primária diz sobre skills no Claude Code

Fonte: <https://code.claude.com/docs/en/skills.md>, consultada em 2026-07-30.

### 1.1 Onde as skills moram

A doc publica esta tabela:

| Location | Path | Applies to |
| :--- | :--- | :--- |
| Enterprise | See managed settings | All users in your organization |
| Personal | `~/.claude/skills/<skill-name>/SKILL.md` | All your projects |
| Project | `.claude/skills/<skill-name>/SKILL.md` | This project only |
| Plugin | `<plugin>/skills/<skill-name>/SKILL.md` | Where plugin is enabled |

### 1.2 Precedência — citação literal

> "When skills share the same name across levels, enterprise overrides personal, and personal overrides project. A skill at any of these levels also overrides a bundled skill with the same name. For example, a `code-review` skill in your project's `.claude/skills/` replaces the bundled `/code-review`. Plugin skills use a `plugin-name:skill-name` namespace, so they cannot conflict with other levels. If you have files in `.claude/commands/`, those work the same way, but if a skill and a command share the same name, the skill takes precedence."

Três consequências para o overpower:

- **A ordem é `enterprise > pessoal > projeto > bundled`.** O ticket pergunta se "uma cópia velha versionada num repo pode sombrear a fresca". Para o Claude Code, **não**: quem sombreia é a pessoal. O risco existe, mas com o sinal trocado — uma pessoal obsoleta cala uma de projeto recém-editada.
- **Skills de plugin não colidem**, porque vivem sob namespace `plugin-name:skill-name`.
- **Skill vence comando** de mesmo nome.

### 1.3 Skills aninhadas não seguem essa regra

> "If a nested skill shares a name with another skill, both stay available."

Uma skill em `apps/web/.claude/skills/deploy/` **coexiste** com a da raiz e aparece como `apps/web:deploy`. Ou seja: colisão entre níveis **substitui**, colisão entre diretórios aninhados **qualifica**. São dois regimes distintos, e o overpower só interage com o primeiro.

### 1.4 Symlink — citação literal

> "A `<skill-name>` entry in the enterprise, personal, or project locations can be a symlink to a directory elsewhere on disk. Claude Code follows the symlink and reads `SKILL.md` from the target directory, and if the same target is reachable from more than one location, Claude Code loads the skill once. Plugin skills handle symlinks differently."

Esta frase é a licença explícita para o modelo escolhido. Note o alcance: symlink vale para **enterprise, pessoal e projeto** — os três escopos em que o overpower escreve. E a deduplicação por alvo significa que linkar a mesma skill em projeto **e** em pessoal não a duplica no contexto.

Vale registrar o limite: a doc fala em symlink **de diretório**. Não há afirmação sobre linkar o `SKILL.md` isolado. O overpower deve linkar o diretório.

### 1.5 O escape hatch para skills versionadas: `skillOverrides`

> "The `skillOverrides` setting controls skill visibility from your settings instead of the skill's own frontmatter. Use it for skills whose SKILL.md you don't want to edit, such as ones checked into a shared project repo."

Estados: `"on"`, `"name-only"`, `"user-invocable-only"`, `"off"`. Gravado em `.claude/settings.local.json`.

**Limite importante**: a chave é o **nome da skill**, não o caminho. Então `skillOverrides` **não consegue** desligar seletivamente a cópia de projeto mantendo a pessoal — desliga a skill por nome. Serve para silenciar equipamento herdado, não para resolver precedência. O overpower não deve depender disso.

### 1.6 Detecção de mudança ao vivo

> "Claude Code watches skill directories for file changes. (…) If you create a top-level skills directory that didn't exist when the session started, restart Claude Code so it can watch the new directory."

Consequência operacional direta: **se o overpower cria `.claude/skills/` do zero, a sessão em curso precisa de restart.** Isso tem que aparecer na saída do CLI, senão o usuário instala e conclui que não funcionou.

---

## 2. A spec do Agent Skills — o formato que atravessa runtimes

A doc oficial do Claude Code aponta para a spec:

> "Claude Code skills follow the [Agent Skills](https://agentskills.io) open standard, which works across multiple AI tools."
>
> — <https://code.claude.com/docs/en/skills.md>, consultada em 2026-07-30

Seguindo esse ponteiro: <https://agentskills.io/specification>, consultada em 2026-07-30. Repositório da spec: <https://github.com/agentskills/agentskills>. Há uma biblioteca de referência, `skills-ref`, com `skills-ref validate ./my-skill`.

> **Nota de procedência.** Esta pesquisa não faz afirmação sobre autoria ou origem do padrão Agent Skills. A cadeia sustentada aqui é apenas: a doc oficial do Claude Code declara seguir a spec, e a spec publica as restrições de formato abaixo. Ambas as pontas são fonte de primeira mão para o que este documento afirma.

### 2.1 Layout

```
skill-name/
├── SKILL.md          # Required: metadata + instructions
├── scripts/          # Optional: executable code
├── references/       # Optional: documentation
├── assets/           # Optional: templates, resources
└── ...
```

### 2.2 Frontmatter

| Campo | Obrigatório | Restrição |
| :--- | :--- | :--- |
| `name` | Sim | Máx. 64 caracteres. Minúsculas, números e hífens. Não começa nem termina com hífen. |
| `description` | Sim | Máx. 1024 caracteres. Não vazio. |
| `license` | Não | Nome da licença ou referência a arquivo empacotado. |
| `compatibility` | Não | Máx. 500 caracteres. |
| `metadata` | Não | Mapa string→string arbitrário. |
| `allowed-tools` | Não | String separada por espaços. Experimental. |

A regra que mais importa para a aterrissagem:

> "Must match the parent directory name"

**O nome do diretório é a identidade da skill.** Renomear o diretório na aterrissagem quebra a skill. Isso elimina qualquer ideia de "prefixar o nome do framework no diretório para evitar colisão" — não é permitido pela spec.

Também: `name` não admite maiúsculas nem hífens duplos, o que dá ao overpower um validador barato e determinístico antes de escrever.

### 2.3 O que a spec NÃO padroniza

A spec é de **formato**, não de instalação. Ela não diz onde as skills ficam no disco, não define escopo pessoal x projeto, e **não menciona symlink**. Toda a questão da aterrissagem é, por construção, território de cada runtime — que é precisamente por que este documento precisa existir.

### 2.4 `metadata` é o gancho legítimo para procedência

O campo `metadata` é "arbitrary key-value mapping", e a spec recomenda chaves razoavelmente únicas para evitar conflito. É o lugar previsto pela spec para o overpower carimbar origem — sem inventar campo novo e sem quebrar validador de terceiro. Ver §6.

### 2.5 Onde cada runtime lê skills — e a descoberta que simplifica tudo

Cada linha abaixo vem da doc oficial do próprio runtime, consultada em 2026-07-30.

| Runtime | Projeto | Usuário/global | Lê `.claude/skills`? | Fonte |
| :--- | :--- | :--- | :--- | :--- |
| Claude Code | `.claude/skills/` | `~/.claude/skills/` | (é o dele) | `code.claude.com/docs/en/skills.md` |
| Cursor | `.cursor/skills/`, **`.agents/skills/`** | `~/.cursor/skills/`, **`~/.agents/skills/`** | **sim** (compat) | `cursor.com/docs/skills` |
| Codex | **`.agents/skills`** (cwd → raiz do repo) | **`$HOME/.agents/skills`**; admin `/etc/codex/skills` | **não** | `developers.openai.com/codex/skills` |
| GitHub Copilot | `.github/skills`, `.claude/skills`, **`.agents/skills`** | `~/.copilot/skills`, **`~/.agents/skills`** | **sim** | `docs.github.com/.../about-agent-skills` |
| VS Code | `.github/skills/`, `.claude/skills/`, **`.agents/skills/`** | `~/.copilot/skills/`, `~/.claude/skills/`, **`~/.agents/skills/`** | **sim** | `code.visualstudio.com/docs/copilot/customization/agent-skills` |

**`.agents/skills/` não é uma convenção de staging inventada pelo `npx skills` — é caminho de leitura oficial de Cursor, Codex, Copilot e VS Code, documentado por cada um deles.**

Isto reescreve o problema. O modelo ingênuo — "escreva no canônico e faça um link por runtime" — assume que cada runtime tem seu próprio diretório. Não é o caso: **quatro dos cinco runtimes leem o canônico diretamente**. Para eles, o número de links necessários é **zero**. Sobra o Claude Code, que lê `.claude/skills/` e é o único que exige um link.

Confirmação independente no código do `npx skills` (`src/agents.ts`, `src/installer.ts:121-149`, commit `7cb7db64`): ele classifica como *universal agent* todo runtime cujo `skillsDir === '.agents/skills'` — Cursor, Codex, GitHub Copilot, OpenCode, Gemini CLI, Amp e outros — e para esses, em modo global, **pula deliberadamente** a criação do link:

```ts
// For universal agents with global install, the skill is already in the canonical
// ~/.agents/skills directory. Skip creating a symlink to the agent-specific global dir
// (e.g. ~/.copilot/skills) to avoid duplicates.
if (isGlobal && isUniversalAgent(agentType)) {
  return { success: true, path: canonicalDir, canonicalPath: canonicalDir, mode: 'symlink' };
}
```

Consequência de desenho para o overpower, e é a mais importante deste documento: **a superfície exposta a falha de symlink é muito menor do que parece.** Um usuário que só usa Cursor, Codex ou Copilot nunca precisa de um symlink — logo nunca encontra o modo de falha do Windows. O fallback de cópia é necessário só para quem usa **Claude Code**.

### 2.6 Precedência nos outros runtimes: silêncio, e um "não há"

- **Codex** é o único explícito, e diz que **não há** resolução: *"If two skills share the same `name`, Codex doesn't merge them; both can appear in skill selectors"* (`developers.openai.com/codex/skills`). Duas skills homônimas coexistem como opções distintas.
- **Cursor, Copilot e VS Code** não declaram regra de precedência entre projeto e usuário para skills de mesmo nome.

Portanto o aviso de sombreamento do overpower (§7.5) só pode ser **afirmativo para o Claude Code**. Para os demais, o correto é avisar de **coexistência** — sem dizer quem vence, porque a doc não diz.

### 2.7 `AGENTS.md`: o que padroniza de fato

O ticket pergunta o que o `AGENTS.md` padroniza e quem o consome de verdade. Fonte: <https://agents.md>, consultada em 2026-07-30.

**Padroniza muito pouco, e de propósito**: não há frontmatter, não há estrutura obrigatória. *"AGENTS.md is just standard Markdown. Use any headings you like; the agent simply parses the text you provide."* A única regra real é de resolução: *"Agents automatically read the nearest file in the directory tree, so the closest one takes precedence"* — mais próximo vence, ao contrário da precedência por escopo das skills.

Quem consome, confirmado na doc oficial de cada um:

- **Codex** — a hierarquia mais elaborada: concatena de raiz até o cwd, "Files closer to your current directory override earlier guidance because they appear later in the combined prompt", com `AGENTS.override.md` tendo prioridade por nível e limite de 32 KiB.
- **Cursor** — "Cursor supports AGENTS.md in the project root and subdirectories", apresentado como alternativa a `.cursor/rules`.
- **GitHub Copilot** — suportado, mas **não uniformemente**: vale no cloud agent, CLI e VS Code; não vale nas superfícies "Chat" de Visual Studio, JetBrains, Xcode e Eclipse.
- **Claude Code** — lê `CLAUDE.md`, **não** `AGENTS.md`. A doc oficial recomenda importar: *"If your repository already uses `AGENTS.md` for other coding agents, create a `CLAUDE.md` that imports it"*, via `@AGENTS.md`. E acrescenta uma nota que ecoa toda esta pesquisa: *"On Windows, creating a symlink requires Administrator privileges or Developer Mode, so use the `@AGENTS.md` import instead."*

**Implicação para o overpower**: `AGENTS.md` é prosa livre de projeto, não equipamento empacotado. Não é unidade instalável, não tem identidade nem versão, e sobrescrevê-lo destruiria conteúdo autoral do usuário. **Fica fora do modelo de aterrissagem.** É contexto que o dev escreve, não artefato que a ferramenta entrega.

---

## 3. Evidência viva desta máquina

Tudo nesta seção foi observado diretamente, não lido.

### 3.1 O diretório canônico e os links

`~/.agents/skills/` tem 22 skills. `~/.claude/skills/` tem 22 entradas, **todas symlinks**, todas relativas:

```
lrwxrwxrwx  ask-matt -> ../../.agents/skills/ask-matt
lrwxrwxrwx  research -> ../../.agents/skills/research
```

Verificado em Python: `os.readlink()` devolve `'../../.agents/skills/ask-matt'` — caminho **relativo**; `is_symlink()` e `is_dir()` ambos `True`; `os.lstat().st_mode` = `0o120777`, cujo tipo é `S_IFLNK` (`0o120000`).

O link ser **relativo** é uma escolha de desenho que vale copiar: `~/.claude/skills/x → ../../.agents/skills/x` sobrevive a mover o `$HOME` inteiro, e sobrevive a um repo clonado em caminho diferente. Um link absoluto não sobreviveria a nenhum dos dois.

### 3.2 O lockfile do `npx skills`

`~/.agents/.skill-lock.json`, chaves de topo: `version` (= 3), `skills`, `dismissed`, `lastSelectedAgents`.

Por skill, os campos observados:

```json
"research": {
  "source": "mattpocock/skills",
  "sourceType": "github",
  "sourceUrl": "https://github.com/mattpocock/skills.git",
  "skillPath": "skills/engineering/research/SKILL.md",
  "skillFolderHash": "972a34cd8128b7952b7eb279b06715862db906a7",
  "pluginName": "mattpocock-skills",
  "installedAt": "2026-07-19T14:38:37.206Z",
  "updatedAt": "2026-07-19T14:38:37.206Z"
}
```

Observações que só a evidência dá:

- **`pluginName` é opcional e condicional.** Presente nas 17 skills vindas de `mattpocock/skills` — repo que **tem** `.claude-plugin/plugin.json` e `.claude-plugin/marketplace.json`, confirmado via API do GitHub. Ausente nas 4 vindas de `panlabs-tech/skills` — repo que **não tem** `.claude-plugin/`. O campo espelha uma propriedade da origem, não da instalação.
- **`skillPath` aponta para o `SKILL.md`**, não para a pasta, e é relativo à raiz do repo de origem. É o que permite reencontrar a skill num repo com layout arbitrário (`skills/engineering/...` no Matt Pocock, `skills/...` no panlabs).
- **`skillFolderHash` não é calculado localmente.** É o **SHA da árvore (tree) do git** daquela pasta, obtido da API do GitHub (`GET /repos/{owner}/{repo}/git/trees/{ref}?recursive=1`) e guardado como veio (`src/blob.ts:225-244`). O `update` compara o hash guardado com o atual da origem e reinstala quando diferem. Isto explica os 40 hex chars sem precisar supor algoritmo: é a SHA-1 que o próprio git já mantém.
- **Este lockfile só existe para instalação global.** Instalação de projeto grava um arquivo diferente, `skills-lock.json`, na raiz do repo — ver §7.4.
- **`dismissed`** = `{"findSkillsPrompt": true}` — o wizard memoriza recusas.
- **`lastSelectedAgents`** tem 14 runtimes: `amp`, `antigravity`, `antigravity-cli`, `cline`, `codex`, `cursor`, `deepagents`, `gemini-cli`, `github-copilot`, `kimi-code-cli`, `opencode`, `warp`, `zed`, `claude-code`. É o estado que pré-seleciona o wizard na próxima execução.

### 3.3 O lockfile já derivou do disco

**`handoff` está em `~/.agents/skills/` e symlinkada em `~/.claude/skills/`, mas não consta do lockfile.** 22 diretórios, 21 entradas.

Isto é evidência empírica a favor do [axioma 2](../agents/domain.md#axiomas) ("sem estado no alvo"): um manifesto paralelo diverge do disco em uso normal, e quando diverge não há quem reconcilie. O disco é a verdade; o lockfile é uma opinião sobre o disco.

### 3.4 O modo projeto existe em campo, e é versionado

Em `panlabs-tech/panlabs`:

```
$ git ls-files -s .claude/skills
120000 9016aac9… 0  .claude/skills/caveman
120000 712f694a… 0  .claude/skills/frontend-design
120000 d7287a2e… 0  .claude/skills/to-issues
120000 3e4d639f… 0  .claude/skills/to-prd
…
$ git ls-files -s .agents
100644 073d6bb1… 0  .agents/skills/caveman/SKILL.md
100755 5be498e2… 0  .agents/skills/frontend-design/SKILL.md
…
```

O padrão em campo é: **conteúdo vendorizado e commitado em `.agents/skills/`, symlinks commitados em `.claude/skills/`**. Ambos versionados.

E é exatamente o cenário de sombreamento do ticket: `caveman` e `frontend-design` existem simultaneamente aqui (versão de 21 Jun) e no global (atualizadas em 28 Jul). Pela precedência documentada, **as globais frescas vencem** — o repo carrega cópias mortas que ninguém executa. `to-prd` e `to-issues`, por outro lado, só existem no projeto: segundo o README de `panlabs-tech/skills`, são as revisões anteriores de `to-spec` e `to-tickets`. São equipamento obsoleto ainda executável, sob outro nome, sem colisão que o denuncie.

Isto valida a **cláusula de zero redundância** de `panlabs-tech/skills`:

> "Uma skill candidata a global **não existe em repo nenhum**. A cópia global é a única. (…) Sem colisão de nome possível, não há como uma cópia divergente e esquecida rodar no lugar da que alguém edita."

O overpower não pode impor essa cláusula — ele é ferramenta genérica ([axioma 3](../agents/domain.md#axiomas)). Mas pode **detectar e reportar** a condição que ela previne. Ver §7.5.

### 3.5 O diretório de aterrissagem pode ser misto

Em `campfire/.claude/skills/`, seis entradas são symlinks para `../../.agents/skills/…` e duas (`start-ai-assisted-project`, `start-ai-assisted-project-workspace`) são **diretórios reais**.

Consequência de desenho: o alvo da aterrissagem **não é homogêneo**. O overpower tem que tratar cada entrada individualmente e nunca raciocinar sobre o diretório inteiro — nem "isto é um diretório de links" nem "isto é um diretório de cópias".

### 3.6 Um diretório de backups de origem desconhecida

`~/.agents/skill-backups/` contém diretórios com nome `<motivo>-<YYYYMMDD-HHMMSS>`, ex.: `enable-codex-skills-20260720-205257`.

**Correção de uma atribuição minha.** Supus inicialmente que fosse do `npx skills`. Não é: a busca pela string `backup` em toda a árvore do `vercel-labs/skills` (commit `7cb7db64`) devolve **zero ocorrências**. O diretório foi criado por outra coisa — provavelmente uma sessão de agente ou script ad-hoc desta máquina.

Fica registrado como **convenção de nomenclatura observada, sem procedência atribuída**. A ideia (`<motivo>-<timestamp>`) continua boa para o caso de sobrescrita destrutiva; ela só não tem o respaldo de desenho que eu supus.

---

## 4. Symlink no git — verificado empiricamente

Laboratório: repo git criado do zero, com um symlink relativo e uma cópia real da mesma skill.

### 4.1 O modo e o blob

```
$ git ls-files -s
100644 01b98131… 0  .agents/skills/demo/SKILL.md
120000 f8513f5a… 0  .claude/skills/demo
100644 01b98131… 0  .cursor/skills/demo/SKILL.md

$ git cat-file -p f8513f5a…
../../.agents/skills/demo
$ git cat-file -s f8513f5a…
25
```

O symlink é uma entrada de **modo `120000`** cujo blob contém **literalmente o texto do caminho de destino**, 25 bytes, sem newline final. Não há nada mágico: é um arquivo de texto com um bit de tipo diferente no índice.

A doc oficial do git confirma a semântica do modo (<https://git-scm.com/docs/git-fast-import>, consultada em 2026-07-30):

> "`120000`: A symlink, the content of the file will be the link target."

Note também que a cópia real e o original compartilham o **mesmo blob** (`01b98131…`): o git deduplica conteúdo idêntico por hash. O custo em disco de repositório do fallback de cópia é próximo de zero; o custo é de **manutenção**, não de armazenamento.

### 4.2 O que acontece no clone sem suporte a symlink

Clonando com `core.symlinks=false`:

```
$ ls -la .claude/skills/
-rw-r--r-- 1 paninit paninit 25 .claude/skills/demo     ← arquivo comum

$ file .claude/skills/demo
.claude/skills/demo: ASCII text, with no line terminators

$ cat .claude/skills/demo
../../.agents/skills/demo
```

O symlink vira um **arquivo de texto regular contendo o caminho**. Para o Claude Code, `.claude/skills/demo` deixa de ser um diretório com `SKILL.md` — a skill simplesmente **não existe**. Silenciosamente.

### 4.3 O detalhe que quase passa batido

Rodando `git status` nesse clone:

- **Com `core.symlinks=false` em vigor**: saída **vazia**. O git aceita o arquivo-texto como satisfazendo o modo `120000`. O repo parece perfeitamente limpo.
- **Sem a config em vigor** (ex.: alguém removeu, ou clonou com `-c` que não persistiu): `git status --short` mostra ` T .claude/skills/demo` — *typechange*.

Confirmei que `git clone -c core.symlinks=false` **não persistiu** a config no repo clonado (git 2.50.1), o que produz justamente o segundo estado. Ou seja, há dois modos de falha opostos:

| Estado | `git status` | Skill funciona? | Diagnóstico |
| :--- | :--- | :--- | :--- |
| `core.symlinks=false` consistente | limpo | **não** | pior: invisível |
| config inconsistente | ` T` (typechange) | não | ruim, mas visível |

O primeiro é o cenário Windows corporativo real, e a doc oficial do git confirma por quê (<https://git-scm.com/docs/git-config>, `core.symlinks`, consultada em 2026-07-30):

> "If false, symbolic links are checked out as small plain files that contain the link text. `git-update-index` and `git-add` will not change the recorded type to regular file. Useful on filesystems like FAT that do not support symbolic links.
>
> The default is true, except `git-clone` or `git-init` will probe and set core.symlinks false if appropriate when the repository is created."

Duas coisas ficam provadas por esse texto:

1. **O git detecta e persiste sozinho.** "`git-clone` or `git-init` will probe and set core.symlinks false if appropriate" — no Windows sem suporte, o repo do colega nasce com a config gravada. O estado silencioso é o **padrão**, não a exceção.
2. **O git nunca conserta sozinho.** "`git-update-index` and `git-add` will not change the recorded type to regular file" — o índice continua dizendo `120000` para sempre. É por isso que o `git status` fica limpo: o arquivo-texto é a materialização *esperada* daquele modo.

O repo fica limpo, o `git diff` fica vazio, e o equipamento está quebrado. **Nenhum sinal do git denuncia.**

Some-se a isto o comportamento do Git Bash, documentado em <https://gitforwindows.org/symbolic-links> (consultada em 2026-07-30):

> "By default, the `ln -s` command in *Git Bash* does *not* create symbolic links. Instead, it creates copies."

Ou seja: no ambiente Windows típico, nem a ferramenta de linha de comando que o dev usaria para consertar à mão cria um symlink de verdade.

Isso é decisivo: no ambiente-alvo de replicação, **o git não é manifesto suficiente para symlinks**. O [axioma 2](../agents/domain.md#axiomas) continua de pé para conteúdo — mas para links, `git status` limpo não prova integridade. O overpower precisa de um comando de verificação próprio que resolva os links (§7.6), e essa é a razão pela qual ele existe.

---

## 5. Detectar em runtime, em Python, se symlink é possível

Este é o ponto mais acionável do ticket. A resposta curta: **não infira, tente**.

### 5.0 A stdlib não tem um probe declarativo — e é fácil achar que tem

`os` expõe conjuntos com cara de *capability probing*, e eles não respondem esta pergunta. A doc do Python (<https://docs.python.org/3/library/os.html#os.supports_follow_symlinks>, consultada em 2026-07-30) define `os.supports_follow_symlinks` como:

> "A `set` object indicating which functions in the `os` module accept `False` for their *follow_symlinks* parameter on the local platform."

É sobre **aceitar um parâmetro**, não sobre **ter privilégio**. O mesmo vale para `os.supports_dir_fd`. `os.symlink` nem sequer tem parâmetro `follow_symlinks`. **Não existe na stdlib um `os.supports_*` que responda "consigo criar um symlink aqui"** — a capacidade só é descobrível em tempo de execução, tentando.

A doc de `os.symlink` (<https://docs.python.org/3/library/os.html#os.symlink>, consultada em 2026-07-30) confirma que a exceção é a única sinalização:

> "On newer versions of Windows 10, unprivileged accounts can create symlinks if Developer Mode is enabled. When Developer Mode is not available/enabled, the *SeCreateSymbolicLinkPrivilege* privilege is required, or the process must be run as an administrator.
>
> `OSError` is raised when the function is called by an unprivileged user."

> "Changed in version 3.8: Added support for unelevated symlinks on Windows with Developer Mode."

E sobre por que `target_is_directory` importa:

> "On Windows, a symlink represents either a file or a directory, and does not morph to the target dynamically. If the target is present, the type of the symlink will be created to match. Otherwise, the symlink will be created as a directory if *target_is_directory* is `True` or a file symlink (the default) otherwise. On non-Windows platforms, *target_is_directory* is ignored."

Sobre o código numérico: a doc de `OSError.winerror` diz que ele "gives you the native Windows error code", e a Microsoft lista `ERROR_PRIVILEGE_NOT_HELD — 1314 (0x522) — "A required privilege is not held by the client."` (<https://learn.microsoft.com/en-us/windows/win32/debug/system-error-codes--1300-1699->). O valor 1314 é, portanto, **encadeamento de duas fontes primárias**, não uma frase única que ligue `os.symlink` a 1314. Tratar como forte, mas não como citação direta.

### 5.1 Por que heurística por plataforma erra

Provei nesta máquina (WSL2, kernel `6.6.87.2-microsoft-standard-WSL2`):

| Destino | Filesystem | Resultado do probe |
| :--- | :--- | :--- |
| `/home/paninit` | ext4 | `supported=True` |
| `/mnt/c` | NTFS via 9p/drvfs | **`supported=True`** |
| `/mnt/c/Users` | NTFS via 9p/drvfs | `supported=False`, motivo `dest-not-writable` (errno 13) |
| dir com `chmod 0500` | ext4 | `supported=False`, motivo `dest-not-writable` (errno 13) |

Duas lições:

1. **"WSL + `/mnt/c` ⇒ sem symlink" seria falso.** O drvfs monta com `symlinkroot=/mnt/` e aceita criação de link. Uma regra por plataforma teria degradado para cópia um caso que funciona.
2. **Falha de escrita ≠ falha de symlink.** `/mnt/c/Users` falhou por permissão, não por capacidade. Se o probe não distinguir os dois, o overpower cai em fallback de cópia num diretório onde a cópia **também** vai falhar — e o erro real só aparece depois, deslocado.

### 5.2 O probe

Regra: criar um symlink de diretório **dentro do diretório de destino real**, verificar que ele **resolve e é legível através**, e desfazer.

Três exigências não óbvias:

- **No destino exato, não em `tempfile.gettempdir()`.** A capacidade é propriedade do *filesystem de destino* e da ACL daquele caminho. `/tmp` costuma ser outro filesystem e responde outra pergunta.
- **Criar não basta; tem que resolver.** Sob `core.symlinks=false` num checkout, ou num filesystem que representa links de forma degradada, a criação pode "funcionar" e o link não abrir. O probe escreve um `SKILL.md` canário no alvo e o lê **através do link**.
- **`target_is_directory=True` é obrigatório no Windows.** No POSIX o parâmetro é ignorado; no Windows, um symlink de diretório criado como se fosse de arquivo não resolve.

```python
import errno, os, shutil, uuid
from dataclasses import dataclass
from pathlib import Path

WIN_ERROR_PRIVILEGE_NOT_HELD = 1314
WIN_ERROR_INVALID_FUNCTION = 1


@dataclass(frozen=True)
class LinkCapability:
    supported: bool
    reason: str
    detail: str = ""


def probe_symlink(dest_dir: Path) -> LinkCapability:
    """Decide se dá para criar symlink de diretório DENTRO de `dest_dir`."""
    if not hasattr(os, "symlink"):
        return LinkCapability(False, "no-symlink-api")

    probe = dest_dir / f".overpower-probe-{uuid.uuid4().hex[:8]}"
    target, link = probe / "target", probe / "link"
    try:
        # mkdir do destino E do probe no MESMO bloco guardado: um destino que
        # existe mas não aceita escrita só se revela ao criar o probe.
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
            target.mkdir(parents=True)
        except OSError as exc:
            return LinkCapability(False, "dest-not-writable",
                                  f"errno={exc.errno} {exc.strerror}")
        try:
            os.symlink(target, link, target_is_directory=True)
        except OSError as exc:
            win = getattr(exc, "winerror", None)
            if win == WIN_ERROR_PRIVILEGE_NOT_HELD:
                reason = "windows-privilege-not-held"
            elif win == WIN_ERROR_INVALID_FUNCTION or exc.errno == errno.ENOSYS:
                reason = "fs-unsupported"
            elif exc.errno == errno.EPERM:
                reason = "eperm"
            elif exc.errno == errno.EACCES:
                reason = "eacces"
            else:
                reason = "oserror"
            return LinkCapability(False, reason,
                                  f"errno={exc.errno} winerror={win} {exc.strerror}")
        except NotImplementedError as exc:
            return LinkCapability(False, "not-implemented", str(exc))

        # Criar não basta: o runtime precisa CONSEGUIR SEGUIR o link.
        if not link.is_symlink():
            return LinkCapability(False, "created-but-not-a-link")
        if not link.is_dir():
            return LinkCapability(False, "link-does-not-resolve")
        (target / "SKILL.md").write_text("probe", encoding="utf-8")
        if (link / "SKILL.md").read_text(encoding="utf-8") != "probe":
            return LinkCapability(False, "link-not-readable-through")
        return LinkCapability(True, "ok")
    finally:
        shutil.rmtree(probe, ignore_errors=True)
```

Esta implementação foi executada e validada nos quatro casos da tabela de §5.1, mais um teste de higiene que confirma que o probe **não deixa resíduo** no diretório de destino.

> Registro de um erro cometido e corrigido durante a pesquisa: na primeira versão, o `mkdir` do destino e o do probe estavam em blocos separados. Como `mkdir(exist_ok=True)` **não** testa escrita num diretório que já existe, um destino somente-leitura escapava do guard e explodia com `PermissionError` não tratada. O teste negativo pegou. Por isso os dois `mkdir` têm que estar sob o mesmo `except OSError`.

### 5.3 Os motivos de falha e o que cada um implica

| `reason` | Causa típica | Próximo degrau |
| :--- | :--- | :--- |
| `windows-privilege-not-held` | Windows sem Developer Mode e sem admin | **junction** (§5.4), depois cópia |
| `fs-unsupported` | FAT32/exFAT, alguns SMB/CIFS | cópia |
| `eperm` / `eacces` | política corporativa, ACL, container restrito | cópia |
| `dest-not-writable` | permissão no diretório de destino | **abortar** — cópia também falha |
| `not-implemented` / `no-symlink-api` | Python sem `os.symlink` na plataforma | cópia |
| `link-does-not-resolve` | link criado mas degradado | cópia |

Note que `dest-not-writable` é o único que **não** deve virar cópia. Confundi-lo com os outros produz um erro deslocado e um diagnóstico ruim.

### 5.4 O degrau intermediário no Windows: directory junction

Esta pesquisa começou supondo dois estados — symlink ou cópia. São **três**.

A doc oficial do Git for Windows (<https://gitforwindows.org/symbolic-links>, consultada em 2026-07-30) afirma:

> "Directory junctions can be created by non-administrator users by default. Therefore, they are a popular alternative to symbolic links."

E a Microsoft (<https://learn.microsoft.com/en-us/windows/win32/fileio/hard-links-and-junctions>, consultada em 2026-07-30):

> "A *junction* (also called a *soft link*) differs from a hard link in that the storage objects it references are separate directories. A junction can also link directories located on different local volumes on the same computer... Junctions are implemented through reparse points."

**Junction dispensa o privilégio que o symlink exige.** É exatamente o caso que quebra no Windows corporativo — e é o caso que uma junction resolve sem pedir nada a ninguém.

Confirmação de que isto é prática estabelecida, e não teoria: o `npx skills` faz precisamente isso (`src/installer.ts:255-257`, commit `7cb7db64`):

```ts
const symlinkType = platform() === 'win32' ? 'junction' : undefined;
const symlinkTarget = symlinkType === 'junction' ? resolvedTarget : relativePath;
await symlink(symlinkTarget, linkPath, symlinkType);
```

No Windows ele **nunca tenta symlink** — vai direto a junction, com alvo **absoluto**. Em POSIX, symlink com alvo relativo.

Limites da junction, que decidem quando ela não serve:

- **Só diretórios.** Não linka arquivos. Para skills isso não é limitação: a unidade é o diretório.
- **Só volumes locais.** "directories located on different local volumes on the same computer" — não atravessa rede. Num `$HOME` em share SMB corporativo, junction não resolve.
- **Alvo absoluto.** Perde a portabilidade que o link relativo dá (§3.1). Uma junction commitada e clonada em outro caminho aponta para o vazio — mas isso é irrelevante, porque junction **não é representável no git** de todo modo.

Em Python, junction sai de `_winapi.CreateJunction` (privado) ou de `os.symlink` via a camada do SO; não há API pública estável e documentada na stdlib para criá-la. O caminho honesto é `subprocess` com `mklink /J`, ou aceitar a dependência do privado. **Isto merece um ticket de implementação próprio** — a decisão é entre uma chamada de API privada e um subprocesso, e as duas têm custo.

A escada completa fica:

```
POSIX:    symlink relativo  →  cópia
Windows:  junction (absoluta)  →  cópia
          [symlink só se Developer Mode estiver ligado — e não vale a pena
           testar antes, porque a junction funciona nos dois casos]
```

### 5.5 Quando rodar o probe

**Uma vez por diretório de destino, por execução.** Não uma vez por skill (desperdício de I/O) e não uma vez por processo global (destinos diferentes podem estar em filesystems diferentes — é exatamente o caso de um repo em `/mnt/c` com `$HOME` em ext4).

Cachear o resultado por diretório dentro da execução. **Não persistir** entre execuções: o Developer Mode pode ser ligado, a política pode mudar, o repo pode mudar de disco — e persistir cache seria estado no alvo, contra o [axioma 2](../agents/domain.md#axiomas).

---

## 6. Marcar que um arquivo é gerado, e não autoral

O fallback de cópia cria arquivos que parecem autorais e não são. Sem marcação, eles serão editados por engano, revisados como código do time, e vão divergir da origem sem que ninguém perceba.

### 6.1 A restrição que limita as opções

O overpower **não pode injetar cabeçalho no `SKILL.md`**. Três razões:

1. O `SKILL.md` começa com frontmatter YAML; um comentário antes dele quebra o parser de alguns runtimes.
2. Alterar o conteúdo faria a cópia divergir por construção da origem, inutilizando qualquer comparação de hash.
3. Skills carregam `scripts/`, `assets/` e binários — não há sintaxe de comentário universal.

Portanto a marcação tem que ser **externa ao conteúdo**.

### 6.2 As convenções disponíveis

**`linguist-generated` — a única que serve, e é externa ao conteúdo.** Fonte: <https://docs.github.com/en/repositories/working-with-files/managing-files/customizing-how-changed-files-appear-on-github>, consultada em 2026-07-30:

> "To keep certain files from displaying in diffs by default, or counting toward the repository language, you can mark them with the `linguist-generated` attribute in a *.gitattributes* file."
>
> "Use the `linguist-generated` attribute to mark or unmark paths that you would like to be ignored for the repository's language statistics and hidden by default in diffs."

Ressalva de procedência: `linguist-generated` é convenção **do GitHub** (Linguist), não do git. Não consta de <https://git-scm.com/docs/gitattributes>. Fora do GitHub, não faz nada.

**`// Code generated ... DO NOT EDIT.` — a convenção do Go, e por que não serve aqui.** Fonte: <https://pkg.go.dev/cmd/go> (alcançada por `go.dev/s/generatedcode`), consultada em 2026-07-30:

> "To convey to humans and machine tools that code is generated, generated source should have a line that matches the following regular expression (in Go syntax):
>
> `^// Code generated .* DO NOT EDIT\.$`
>
> This line must appear before the first non-comment, non-blank text in the file."

É a convenção mais reconhecida que existe, e é **inaplicável** ao nosso caso pela restrição de §6.1: exige injetar uma linha no topo do arquivo, o que quebra o frontmatter YAML do `SKILL.md` e faz a cópia divergir da origem. Fica registrada como o padrão que o `.gitattributes` está substituindo, e o motivo.

**`@generated` (Meta)** — existe e está em uso real em repositórios oficiais (ex.: `facebook/hhvm`, com um `SignedSource<<hash>>` que detecta edição manual). Mas **não localizamos especificação textual oficial** da convenção — a evidência é de artefato, não de documento. Não adotar como referência normativa.

**SPDX — achado negativo confirmado.** A spec de `FileType` (SPDX 2.3, cláusula 8.3) **não tem** categoria para arquivo gerado; os valores são `SOURCE`, `BINARY`, `ARCHIVE`, `APPLICATION`, `AUDIO`, `IMAGE`, `TEXT`, `VIDEO`, `DOCUMENTATION`, `SPDX`, `OTHER`, e "generated artifacts" aparecem só como exemplo do catch-all `OTHER`. Não há convenção SPDX a seguir aqui.

**`metadata` no frontmatter da spec** — o único campo que a spec autoriza para dados de cliente. Cabe se e somente se o overpower for a origem do `SKILL.md`; para conteúdo vendorizado de terceiro, viola a razão (2) de §6.1.

### 6.3 Recomendação

**Um `.gitattributes` no diretório de aterrissagem, mais um manifesto de procedência fora dele.** Não tocar em `SKILL.md`.

```gitattributes
# .claude/skills/.gitattributes — escrito pelo overpower
* linguist-generated=true
```

Sobre o manifesto: ele é para o **humano que revisa o PR**, não para a máquina reconciliar — gravar um manifesto que o overpower depois **lê** para decidir seria estado no alvo e violaria o [axioma 2](../agents/domain.md#axiomas). A distinção é entre *documentar* e *depender*. O overpower escreve, nunca lê de volta; toda decisão sai de inspeção do disco.

---

## 7. Modelo de aterrissagem recomendado

### 7.1 Os dois modos

| | **Projeto** | **Global** |
| :--- | :--- | :--- |
| Canônico | `<repo>/.agents/skills/<nome>/` | `~/.agents/skills/<nome>/` |
| Aterrissagem | `<repo>/.claude/skills/<nome>` → link | `~/.claude/skills/<nome>` → link |
| Alcance | só este repo | todos os projetos |
| Precedência (Claude Code) | **perde** para a pessoal | **vence** a de projeto |
| Versionado | sim, junto com o repo | não |
| Quem consome | o time, via clone | só esta máquina |

**Manter `.agents/skills/` como diretório canônico** — e a razão mais forte não é compatibilidade com o `npx skills`, é §2.5: **`.agents/skills/` é caminho de leitura oficial de Cursor, Codex, Copilot e VS Code**, documentado por cada um. Escolhê-lo não é convenção, é acertar o alvo real.

As três razões, em ordem de peso:

1. **Para quatro dos cinco runtimes, escrever ali já é aterrissar.** Zero links, zero exposição a falha de symlink, zero fallback. O Claude Code é a única exceção que exige um link.
2. **É o único ponto de verdade.** Atualizar a skill é escrever num lugar só.
3. **É neutro entre vendors**, ao contrário de eleger `.claude/skills/` como canônico e fazer os outros apontarem para o diretório de um deles.

Segue a tabela real de trabalho por runtime, em modo projeto:

| Runtime | O que o overpower faz |
| :--- | :--- |
| Cursor, Codex, Copilot, VS Code | **nada além de escrever o canônico** — eles leem `.agents/skills/` direto |
| Claude Code | **um link** `.claude/skills/<nome>` → `../../.agents/skills/<nome>` |

Isso reduz drasticamente o alcance do problema desta pesquisa: **o fallback de cópia só é acionado por usuários de Claude Code em Windows sem Developer Mode** — e mesmo esses são atendidos primeiro por junction (§5.4).

### 7.2 O algoritmo de aterrissagem

Para cada skill do AI Framework selecionado:

```
1. Validar `name` contra a spec (regex, ≤64, casa com o diretório).
2. Escrever o conteúdo em <canônico>/<nome>/.           [sempre cópia real]
3. Para cada runtime alvo:
   a. SE o runtime lê o canônico (Cursor, Codex, Copilot, VS Code):
        nada a fazer — já aterrissou no passo 2. Seguir.       (§2.5)
   b. destino = <caminho do runtime>/<nome>                    [na prática: Claude Code]
   c. cap = probe_link(dirname(destino))                 [cacheado por diretório]
   d. se cap.reason == "dest-not-writable": abortar este runtime, reportar.
   e. resolver colisão (§7.5); se pular, seguir para o próximo runtime.
   f. remover o destino, RAMIFICANDO pelo tipo:               (§7.3, item 3)
        if destino.is_symlink(): destino.unlink()
        elif destino.is_dir():   shutil.rmtree(destino)
      — nunca rmtree() direto: num symlink ele falha, e com
        ignore_errors=True falha em silêncio, deixando o link velho.
   g. escolher o degrau mais alto disponível:                  (§5.4)
        POSIX + cap.supported → os.symlink(relpath(...), target_is_directory=True)
        Windows              → junction com alvo absoluto
        nenhum dos dois      → shutil.copytree(canônico, destino, symlinks=True)
                               registrar "degradado para cópia" + cap.reason
4. Escrever/atualizar o .gitattributes do diretório de aterrissagem.
5. Reportar: o que virou link, o que virou cópia, e por quê.
```

Pontos que não são detalhe:

- **O alvo do link é sempre relativo** (`os.path.relpath`), como faz o `npx skills`. Sobrevive a mover o `$HOME` e a clonar o repo em outro caminho. Um link absoluto não sobrevive a nenhum dos dois.
- **A cópia canônica é sempre real**, nunca link. O canônico é a origem; se ele for link, não há origem.
- **Fallback é por runtime, não global.** Um repo em `/mnt/c` com `$HOME` em ext4 pode legitimamente ter cópia no projeto e link no global, na mesma execução.
- **A degradação é reportada, sempre.** Cair para cópia em silêncio é o pior desfecho possível: perde-se o ponto único de verdade sem que ninguém saiba.

### 7.3 A mecânica da cópia — quatro armadilhas verificadas

Testei o caminho de fallback em Python 3.12. Quatro comportamentos que quebram uma implementação ingênua:

**1. `shutil.copytree` desreferencia symlinks internos por padrão.** Uma skill que carrega `LICENSE.txt → LICENSE` chega ao destino com duas cópias do arquivo, e o link some. Preservar exige `symlinks=True`:

```python
shutil.copytree(canon, dest, symlinks=True, dirs_exist_ok=True)
```

**2. `dirs_exist_ok=True` não remove o que ficou para trás.** Verificado: um `OBSOLETO.md` plantado no destino **sobrevive** à recópia. Se a origem removeu um arquivo, a cópia o mantém para sempre. `copytree` sobrepõe, não sincroniza. A reinstalação tem que **remover o destino antes** de copiar — ou aceitar deriva acumulativa e silenciosa.

**3. `shutil.rmtree` num symlink falha, e com `ignore_errors=True` falha em silêncio.**

```
>>> shutil.rmtree(link)
OSError: Cannot call rmtree on a symbolic link
>>> shutil.rmtree(link, ignore_errors=True)   # não levanta…
>>> link.is_symlink()
True                                          # …e não removeu nada
```

Este é o pior dos dois: o padrão comum `rmtree(dest, ignore_errors=True)` antes de reinstalar **não faz nada** quando o destino é um symlink de instalação anterior. A cópia nova falha com `FileExistsError`, ou pior, escreve **através do link, dentro do canônico**. A remoção tem que ramificar:

```python
if dest.is_symlink():
    dest.unlink()          # remove o link, preserva o alvo
elif dest.is_dir():
    shutil.rmtree(dest)
```

Confirmei que `unlink()` remove o link e **preserva o alvo** — a ordem certa nunca toca o canônico.

**4. Bit de execução sobrevive.** `copytree` preserva o modo: um `scripts/run.py` com `0o755` chega executável. A spec do Agent Skills prevê `scripts/` executáveis, então isto importa — e é um argumento contra implementar a cópia à mão com `read_bytes`/`write_bytes`.

### 7.4 O wizard

#### O fluxo real do `npx skills`, lido no código

Commit `7cb7db64` (o `gitHead` publicado com a v1.5.21, de 2026-07-30), `src/add.ts`. A ordem é:

1. **Skills** — só se a fonte tem mais de uma, sem `--skill`, sem `--yes`.
2. **Agentes** — quatro ramos: `--agent` explícito; nenhum detectado (prompt, ou todos se `--yes`); exatamente um detectado ou `--yes` (auto, sem prompt); mais de um (lista pesquisável). Pré-seleção vem de `lastSelectedAgents` do lockfile; sem histórico, o default é `['claude-code', 'opencode', 'codex']`. Agentes "universais" aparecem como **seção travada**, sempre selecionados e não-togláveis.
3. **Escopo** — só aparece se `--global` e `--yes` ausentes e algum agente suportar global (`src/add.ts:1517-1541`):

```ts
const scope = await p.select({
  message: 'Installation scope',
  options: [
    { value: false, label: 'Project', hint: 'Install in current directory (committed with your project)' },
    { value: true,  label: 'Global',  hint: 'Install in home directory (available across all projects)' },
  ],
});
```

4. **Método** — só se `--copy` e `--yes` ausentes **e houver mais de um diretório de destino distinto** (`uniqueDirs.size > 1`); com um só, vira `copy` automaticamente, porque linkar seria redundante:

```ts
options: [
  { value: 'symlink', label: 'Symlink (Recommended)', hint: 'Single source of truth, easy updates' },
  { value: 'copy',    label: 'Copy to all agents',    hint: 'Independent copies for each agent' },
]
```

5. **Resumo + confirmação** — `p.note` com os caminhos e avisos de sobrescrita, depois `p.confirm({ message: 'Proceed with installation?' })`.

Duas coisas que o desenho deles ensina e que valem herdar: **"Project" vem primeiro** na lista de escopo, e a pergunta de método **desaparece** quando não há escolha real a fazer. Uma pergunta cuja resposta não muda nada é ruído.

Uma que **não** vale herdar: o tratamento de erro do symlink deles é um `catch` genérico que devolve `false` para qualquer falha (`src/installer.ts:260-262`) — busca por `EPERM`/`EXDEV`/`ENOSYS` no fonte devolve zero ocorrências. Isso funde "não consigo linkar" com "não consigo escrever", que é exatamente a distinção que §5.3 mostra ser necessária para dar diagnóstico certo. O probe de §5.2 é deliberadamente mais fino.

#### O wizard recomendado

Perguntas, nesta ordem:

1. **Escopo**: projeto (este repo) ou global (`~`)? — Default: **projeto**, quando o cwd é um repo git. É a escolha reversível: `git checkout .` desfaz. O global exige limpeza manual.
2. **Framework(s)** do catálogo.
3. **Runtimes** de destino. Pré-selecionar os **detectados no disco** (existe `.claude/`? `.cursor/`? `.codex/`?), o que é melhor default que uma lista fixa.
4. **Confirmação**, mostrando o plano: cada caminho a escrever, e link ou cópia — **com o probe já rodado**, para que a degradação apareça *antes* da escrita, não depois.

Flags para pular (o CLI tem que ser inteiramente não-interativo, senão não roda em CI):

| Flag | Efeito |
| :--- | :--- |
| `--global` | escopo global, sem perguntar |
| `--framework <nome>` | seleciona framework(s) |
| `--runtime <nome>…` | seleciona runtimes |
| `--copy` | força cópia mesmo com symlink disponível |
| `--yes` | assume os defaults, não pergunta nada |
| `--dry-run` | imprime o plano e não escreve |

Duas observações de desenho:

- **`--copy` explícito é necessário.** Há casos em que o usuário quer cópia com symlink disponível: um repo cujo time inclui Windows, onde o link funcionaria na máquina de quem instala e quebraria na de quem clona. A capacidade local não é a do time. O `npx skills` também expõe essa flag.
- **`--dry-run` é adição nossa, não herança.** Busca por `dry-run`/`dryRun` no fonte do `npx skills` devolve zero ocorrências — a flag não existe lá. É o que torna o modelo auditável num ambiente onde escrever no repo alheio é ato sensível, e é justamente o tipo de coisa que um contexto corporativo exige e um contexto de conveniência não.

#### Os dois lockfiles do `npx skills`, e por que o overpower não tem nenhum

Achado que só a leitura do código dá: **são dois arquivos distintos**, com propósitos opostos.

| | `.skill-lock.json` | `skills-lock.json` |
| :--- | :--- | :--- |
| Onde | `~/.agents/` (ou `$XDG_STATE_HOME/skills/`) | **raiz do projeto** |
| Quando | só instalação **global** | só instalação de **projeto** |
| Versionado | não | **sim, por desenho** |
| Hash | `skillFolderHash` = tree SHA do GitHub | `computedHash` = SHA-256 local do conteúdo |
| Timestamps | `installedAt`/`updatedAt` | **nenhum, deliberadamente** |

O comentário do fonte sobre o de projeto (`src/local-lock.ts:10-13`) explica a ausência de timestamps:

> "Intentionally minimal and timestamp-free to minimize merge conflicts. Two branches adding different skills produce non-overlapping JSON keys that git can auto-merge cleanly."

É bom desenho. E é exatamente o que o [axioma 2](../agents/domain.md#axiomas) proíbe: **o `npx skills` grava manifesto proprietário no repositório alvo, e o overpower não vai gravar.**

Vale enunciar o custo dessa escolha em vez de fingir que não tem: sem `skills-lock.json`, o overpower não sabe dizer "esta skill veio de tal origem em tal revisão" a partir do repo. Ele troca essa capacidade por não deixar rastro proprietário. A compensação é §7.6: em vez de *ler um manifesto*, ele **inspeciona o disco** — que é a mesma fonte de verdade que o manifesto tentaria espelhar, e que §3.3 mostra que o manifesto **erra** (o `handoff` está no disco e ausente do lockfile).

Sobre memória de seleção: o `npx skills` persiste `lastSelectedAgents` e `dismissed`. O overpower não persiste no alvo. Se algum dia quiser memória de conveniência, ela mora em `~/.config/overpower/`, nunca no repositório — é preferência de UI, não estado de instalação.

### 7.5 Colisão de nome

Antes de escrever `<destino>/<nome>`, inspecionar o disco:

| Situação | Ação |
| :--- | :--- |
| Não existe | escrever |
| Existe, é symlink para o nosso canônico | no-op idempotente |
| Existe, é symlink para outro lugar | **perguntar**; `--yes` ⇒ pular e reportar |
| Existe, é diretório real | **perguntar**; `--yes` ⇒ pular e reportar |
| **Claude Code**: instalando em projeto e já existe em `~/.claude/skills/<nome>` | **avisar com certeza**: pela precedência documentada, a pessoal vence — o que você está instalando **não vai rodar** |
| **Cursor / Copilot / VS Code**: mesmo nome em projeto e global | **avisar de coexistência**, sem afirmar quem vence — a doc não diz (§2.6) |
| **Codex**: mesmo nome em projeto e global | avisar que **as duas aparecem** no seletor — a doc afirma que não há merge |

A última linha é a que a doc do Claude Code torna obrigatória, e a que a intuição não produz. Instalar uma skill em modo projeto quando existe pessoal de mesmo nome é escrever equipamento morto. O overpower tem que dizer isso na hora, e é barato: é um `os.path.exists`.

Simetricamente, no modo global, avisar que a instalação vai **sombrear** cópias de projeto existentes.

Isto é o mais perto que uma ferramenta genérica chega da cláusula de zero redundância de `panlabs-tech/skills`: não impõe a política, mas **torna a redundância visível no momento em que ela é criada**.

### 7.6 Verificação

O [axioma 2](../agents/domain.md#axiomas) diz que o git é o manifesto. §4.3 mostra que, **para symlinks**, isso não basta: sob `core.symlinks=false` o `git status` fica limpo com o equipamento quebrado.

Logo o overpower precisa de um verificador que **resolva os links**, e não é ciclo de vida (que está fora de escopo na v0.1.0) — é a única forma de saber se a instalação está de pé:

- para cada entrada de aterrissagem, `<destino>/<nome>/SKILL.md` **abre e parseia**?
- se a entrada é um arquivo de texto comum cujo conteúdo parece um caminho relativo, reportar **`core.symlinks=false` detectado** e sugerir `--copy`;
- entradas órfãs (link cujo alvo sumiu).

Este é o diagnóstico que transforma a falha silenciosa da §4.3 em erro legível, e é o argumento de existência mais forte do comando.

### 7.7 Recomendação para repositório com Windows no time

Aqui há uma assimetria que decide tudo, e que a junction **não** resolve.

**Modo global**: a máquina que instala é a que consome. O probe mede a capacidade certa, e a escada de §5.4 funciona — symlink no POSIX, junction no Windows, cópia só no resto. Nada a decidir.

**Modo projeto**: o que se escreve vai para o git e é consumido em **outra** máquina. E aí:

- **Junction não é representável no git.** Não há modo de arquivo para ela. Só o symlink (`120000`) atravessa o commit. Logo o degrau intermediário do Windows não existe no modo projeto — só symlink ou cópia.
- **A capacidade medida é a de quem instala, não a de quem clona.** Um symlink commitado por um dev Linux vira arquivo-texto inútil no clone do colega em Windows, e §4.3 mostra que **nada no `git status` dele denuncia**.

Portanto: **quando o time pode incluir Windows sem Developer Mode, a recomendação no modo projeto é `--copy`.**

Fica registrado o custo aceito: cópia no modo projeto abre mão do ponto único de verdade, e a deriva entre a cópia e o canônico passa a ser possível. O `.gitattributes` de §6.3 e o verificador de §7.6 são a mitigação — tornam a cópia visível no PR e a deriva detectável sob demanda.

E vale notar o alívio de §2.5: como Cursor, Codex, Copilot e VS Code leem `.agents/skills/` direto, **um repo cujo time não usa Claude Code nunca precisa de link nenhum** — o conteúdo versionado em `.agents/skills/` já é a aterrissagem, e a questão Windows simplesmente não surge.

---

## 8. Perguntas que esta pesquisa deixa em aberto

- **Como criar uma junction em Python**, concretamente. §5.4 estabelece *que* junction é o degrau certo no Windows; não estabelece *como* criá-la sem depender de `_winapi.CreateJunction` (privado) ou de `subprocess` com `mklink /J`. A escolha entre os dois tem custo dos dois lados e merece um ticket de implementação.
- **A mecânica de symlink do DrvFs no WSL** (`/mnt/c`) não está documentada em fonte primária. Verifiquei empiricamente que **funciona** nesta máquina (§5.1), e a doc da Microsoft confirma que symlinks em DrvFs são reparse points NTFS — mas não há afirmação oficial sobre quando o privilégio é exigido através de `/mnt/c`. O probe de §5.2 torna isso irrelevante na prática: ele mede em vez de supor.
- **Precedência projeto x usuário nos runtimes que não a declaram.** Cursor, Copilot e VS Code silenciam; Codex diz explicitamente que não há resolução. Consequência já incorporada em §2.6 e §7.5, mas se algum deles publicar uma regra, o aviso do overpower fica mais forte.
- **A checkbox "Enable symbolic links" do instalador do Git for Windows** e a variável `MSYS=winsymlinks` não constam do texto oficial vigente em `gitforwindows.org/symbolic-links`. São amplamente conhecidas, mas não confirmáveis hoje em fonte primária — não apoiar recomendação nelas.

---

## Fontes

| Fonte | O que sustenta | Consulta |
| :--- | :--- | :--- |
| <https://code.claude.com/docs/en/skills.md> | caminhos, precedência, symlink, `skillOverrides`, live reload | 2026-07-30 |
| <https://agentskills.io/specification> | frontmatter, layout, `name` casa com o diretório | 2026-07-30 |
| <https://github.com/agentskills/agentskills> | repo da spec e `skills-ref` | 2026-07-30 |
| <https://cursor.com/docs/skills> | Cursor lê `.agents/skills/` e `.claude/skills/` (compat) | 2026-07-30 |
| <https://developers.openai.com/codex/skills> | Codex lê `.agents/skills`; sem merge em colisão de nome | 2026-07-30 |
| <https://docs.github.com/en/copilot/concepts/agents/about-agent-skills> | Copilot lê `.github/skills`, `.claude/skills`, `.agents/skills` | 2026-07-30 |
| <https://code.visualstudio.com/docs/copilot/customization/agent-skills> | VS Code: caminhos e limites de frontmatter | 2026-07-30 |
| <https://agents.md> | AGENTS.md é Markdown livre; mais próximo na árvore vence | 2026-07-30 |
| <https://registry.npmjs.org/skills> | pacote `skills` v1.5.21 (pub. 2026-07-30), repo `vercel-labs/skills` | 2026-07-30 |
| `vercel-labs/skills` @ `7cb7db64` (`src/installer.ts`, `add.ts`, `agents.ts`, `blob.ts`, `local-lock.ts`) | junction no Windows, fallback de cópia, wizard, dois lockfiles, tree SHA | 2026-07-30 |
| <https://docs.python.org/3/library/os.html#os.symlink> | Developer Mode, `target_is_directory`, `OSError` | 2026-07-30 |
| <https://docs.python.org/3/library/os.html#os.supports_follow_symlinks> | não é probe de privilégio | 2026-07-30 |
| <https://learn.microsoft.com/en-us/windows/win32/debug/system-error-codes--1300-1699-> | `ERROR_PRIVILEGE_NOT_HELD` = 1314 | 2026-07-30 |
| <https://learn.microsoft.com/en-us/windows/win32/fileio/hard-links-and-junctions> | o que é uma junction | 2026-07-30 |
| <https://gitforwindows.org/symbolic-links> | junction sem privilégio; `ln -s` do Git Bash copia; FAT/exFAT | 2026-07-30 |
| <https://git-scm.com/docs/git-config> | texto literal de `core.symlinks` | 2026-07-30 |
| <https://git-scm.com/docs/git-fast-import> | `120000` = symlink, conteúdo é o alvo | 2026-07-30 |
| <https://docs.github.com/en/repositories/working-with-files/managing-files/customizing-how-changed-files-appear-on-github> | `linguist-generated` | 2026-07-30 |
| <https://pkg.go.dev/cmd/go> | regex `^// Code generated .* DO NOT EDIT\.$` | 2026-07-30 |
| `~/.agents/`, `~/.claude/skills/` desta máquina | lockfile, links relativos, deriva do `handoff` | 2026-07-30 |
| `panlabs-tech/panlabs`, `campfire` (git local) | modo projeto versionado, `120000`, diretório misto | 2026-07-30 |
| <https://github.com/panlabs-tech/skills> (README) | cláusula de zero redundância | 2026-07-30 |
| Laboratório git local (git 2.50.1) | `120000`, blob, `core.symlinks=false`, typechange | 2026-07-30 |
| Probe em Python nesta máquina (WSL2, Python 3.12) | capacidade ext4 x drvfs; armadilhas de `copytree`/`rmtree` | 2026-07-30 |
