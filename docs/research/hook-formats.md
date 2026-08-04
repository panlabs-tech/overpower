# Formato de hook por runtime

**Ticket**: [Formato de hook por runtime](https://github.com/panlabs-tech/overpower/issues/23)
**Data**: 2026-08-03
**Insumo**: [`docs/agents/domain.md`](../agents/domain.md), regra 4 — *o contrato de um artefato de enxerto é lógico, não literal*. Molde de rigor: [`docs/research/mcp-config-formats.md`](https://github.com/panlabs-tech/overpower/blob/research/mcp-config-formats/docs/research/mcp-config-formats.md).

## Enquadramento — esta pesquisa não desbloqueia mais a v0.1.0

O ticket foi escrito quando o `obra/superpowers` era candidato à v0.1.0. O [#15](https://github.com/panlabs-tech/overpower/issues/15) fechou depois e mudou a premissa: **a v0.1.0 leva um único AI Framework, `mattpocock/skills`, 22 skills promovidas, Markdown puro, zero hook, zero MCP.** O superpowers não entra.

Logo a pergunta deixa de ser *"o superpowers pode entrar?"* e passa a ser a que este documento responde: **quando o enxerto de hook for implementado, qual é o formato de cada runtime, e o que o hook do superpowers exigiria?** A medição existe para que a v0.2 comece com ela pronta, não do zero.

---

## Método

Quatro runtimes estão instalados nesta máquina. Três foram **executados**; um foi lido do binário.

| Alvo | Versão | Como foi apurado |
| --- | --- | --- |
| Claude Code | `2.1.221` | **Executado** em sandbox (`HOME` redirecionado). Hook real, sessão real, modelo real. Ingestão verificada pela **resposta do modelo**, não pelo log |
| GitHub Copilot CLI | `1.0.78` | **Executado** em sandbox (`COPILOT_HOME` redirecionado), em repositório git. Ingestão verificada pela resposta do modelo |
| Codex CLI | `codex-cli 0.144.6` | **Fonte Rust lido** na tag `rust-v0.144.6` — exatamente a versão instalada — mais binário (`strings`) e `--help`. **Não executado com hook ativo** |
| VS Code | `1.131.0` | **Só doc oficial.** Ver ressalva |
| Cursor | — | **Não instalado.** Só doc oficial. Nada aqui é medido |
| `obra/superpowers` | `6.2.0` | Árvore clonada e lida; hook **executado** dentro e fora de plugin |

Convenção: **medido** = executado e observado; **doc** = documentação oficial do fornecedor; **fonte** = código-fonte lido na versão instalada; **binário** = string lida do executável instalado.

**Ressalva de honestidade, idêntica à da pesquisa de MCP**: nesta máquina o `code` é o remote-cli do Remote-WSL, que encaminha argumentos por IPC para a instância real no Windows. A extensão Copilot Chat que roda no lado WSL (`copilot-chat` v0.59.0) **não** contém a implementação de hooks do VS Code — o bundle `extensions/copilot/dist/cli.js` que ela carrega é uma **cópia vendorizada do Claude Code**, não código de hook do VS Code (verificado: contém `claude plugin disable`, `marketplace.json`, `CLAUDE_PLUGIN_ROOT` e a lista de eventos do Claude Code). Medir hooks do VS Code exigiria escrever na configuração real do dev. **Não foi feito.** Toda a fatia do VS Code é doc.

Nenhuma configuração real do desenvolvedor foi escrita. A única leitura do config real foi copiar `~/.claude/.credentials.json` para o `HOME` de sandbox, para que a sessão de teste autenticasse.

---

## Veredito: hook existe nos cinco, e o campo de injeção tem três grafias incompatíveis

O ticket previa que "não existe hook neste runtime" seria uma resposta frequente. **É falsa em todos os cinco.** Os cinco runtimes têm sistema de hooks, e os cinco têm um evento de início de sessão capaz de injetar texto no contexto do modelo.

O problema não é ausência. É que **o campo que carrega o texto injetado tem três grafias, e nenhum runtime aceita a do outro**:

| Grafia | Quem consome | Forma |
| --- | --- | --- |
| `hookSpecificOutput.additionalContext` | **Claude Code**, **VS Code**, **Codex** | aninhada, com `hookEventName` irmão |
| `additionalContext` | **Copilot CLI** | topo, camelCase |
| `additional_context` | **Cursor** | topo, snake_case |

Isso é a versão de hook do achado da pesquisa de MCP: **não existe formato canônico, e um renderizador por alvo é obrigatório.** A diferença é que aqui o modo de falha é pior — no MCP a chave errada costuma gerar erro; aqui ela gera **silêncio com exit 0**.

---

## Tabela runtime × campo

| | **Claude Code** | **Cursor** | **VS Code** | **Codex CLI** | **Copilot CLI** |
| --- | --- | --- | --- | --- | --- |
| **Arquivo de projeto** (commitável) | `.claude/settings.json` | `.cursor/hooks.json` | `.github/hooks/*.json` **e** `.claude/settings.json` | `<repo>/.codex/hooks.json` **ou** `[hooks]` em `<repo>/.codex/config.toml` | `.github/hooks/*.json` — **documentado, medido inerte** |
| **Arquivo de máquina** | `~/.claude/settings.json` | `~/.cursor/hooks.json` | `~/.claude/settings.json`, `~/.copilot/hooks` | `~/.codex/hooks.json` **ou** `[hooks]` em `~/.codex/config.toml` | `~/.copilot/hooks/*.json` (`$COPILOT_HOME`) |
| **Escopo local não-versionado** | `.claude/settings.local.json` | **não existe** | `.claude/settings.local.json` | — | — |
| **Tipo de arquivo** | JSON estrito | JSON | JSON | **JSON e TOML**, ambos válidos | JSON |
| **Chave raiz** | `hooks` | `hooks` (+ `version: 1` **obrigatório**) | `hooks` (sem `version`) | `hooks` (sem `version`) | `hooks` (+ `version: 1` **obrigatório**) |
| **Grafia dos eventos** | **PascalCase** (`SessionStart`) | **camelCase** (`sessionStart`) | **PascalCase** (`SessionStart`) | **PascalCase** (`SessionStart`) ¹ | **camelCase** (`sessionStart`), com alias PascalCase |
| **Forma da entrada** | `{matcher, hooks:[{type,command,…}]}` — **dois níveis** | `{command, type?, timeout?, matcher?}` — **um nível** | igual ao Claude Code | **dois níveis, igual ao Claude Code** | `{type, command, bash?, powershell?, cwd?, env?, timeoutSec?, matcher?}` |
| **`matcher`** | aplicado | existe | **parseado e NÃO aplicado** (doc) | aplicado | existe |
| **Campo de injeção** | `hookSpecificOutput.additionalContext` | `additional_context` (topo) | `hookSpecificOutput.additionalContext` | `hookSpecificOutput.additionalContext` — **ou stdout puro não-JSON** | `additionalContext` (topo) |
| **Campo errado** | **ignorado em silêncio, exit 0, hook = "success"** | não medido | não medido | JSON inválido **falha duro** (fonte) | não medido |
| **Variável de caminho no `command`** | `${CLAUDE_PROJECT_DIR}`, `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PLUGIN_DATA}` | **nenhuma documentada** | — | **só em plugin**: `${PLUGIN_ROOT}`, `${CLAUDE_PLUGIN_ROOT}`, `${PLUGIN_DATA}`, `${CLAUDE_PLUGIN_DATA}`. Em config: **nenhuma** | — |
| **Variável no *ambiente* do hook** | `CLAUDE_PROJECT_DIR`, `CLAUDE_ENV_FILE` | `CURSOR_PROJECT_DIR` + alias `CLAUDE_PROJECT_DIR` | — | as quatro acima, **só em plugin** | — |
| **Hooks de plugin** | autodiscovery de `hooks/hooks.json` | `hooks/hooks.json` ou campo `hooks` | `hooks/hooks.json` ou `hooks.json` | autodiscovery de `hooks/hooks.json` **só se o manifesto omitir `hooks`** | `hooks.json` ou `hooks/hooks.json` |
| **Gate de confiança para hook** | **nenhum** (medido) | workspace trust (doc) | trust prompt de marketplace (doc) | **dois gates**: `trust_level` do projeto **e** trust por hook com hash (fonte) | não determinado |
| **Merge entre escopos** | **acumula** (medido) | todos rodam; conflito por prioridade | workspace vence usuário | **aditivo, sem override** (fonte) | policy → user → project → plugins |

¹ PascalCase é a grafia **na config** e nos schemas de saída. O snake_case (`session_start`) que aparece no binário é o rótulo interno usado na **chave de trust**, não na configuração.

---

## O achado que muda o desenho: a aterrissagem por cópia quebra o hook em silêncio

Esta é a medição central do documento, e ela **contraria a suposição registrada no ticket**.

A suposição era: `${CLAUDE_PLUGIN_ROOT}` só existe quando o runtime instalou como plugin; sob a aterrissagem por cópia do overpower a variável **vem vazia**, e o comando tem de virar caminho concreto. **A primeira metade está errada e a segunda é insuficiente.**

### 1. A variável não vem vazia — o Claude Code recusa o hook, com mensagem exata

Medido. Um hook em `.claude/settings.json` cujo `command` contenha `${CLAUDE_PLUGIN_ROOT}` **não roda**. O runtime detecta e recusa:

```
[ERROR] Hook failed to run (SessionStart:startup): Hook command references
${CLAUDE_PLUGIN_ROOT} but the hook is not associated with a plugin. This
variable is only available in hooks defined in a plugin's hooks/hooks.json
file, not in settings.json.
```

Isso é **melhor** que a suposição: falha alto, não baixo. Um `hooks.json` do superpowers copiado cru para `.claude/settings.json` não produz um comando com caminho quebrado — produz uma recusa nomeada. Bom para diagnóstico.

E a recusa é **por hook, não por arquivo**: no mesmo `SessionStart` outro hook irmão rodou normalmente.

### 2. Trocar por caminho concreto faz o hook rodar — e ainda assim não injetar nada

Medido, ponta a ponta, com a árvore real do `obra/superpowers@6.2.0` copiada para `.claude/overpower/superpowers/` e o hook declarado assim:

```json
"command": "\"${CLAUDE_PROJECT_DIR}/.claude/overpower/superpowers/hooks/run-hook.cmd\" session-start"
```

`${CLAUDE_PROJECT_DIR}` **expande corretamente** (medido; `$CLAUDE_PROJECT_DIR` sem chaves também, porque o comando roda sob shell). O `run-hook.cmd` executa. O `session-start` lê o `SKILL.md`. Exit 0. E o modelo respondeu **`NAO_SUPERPOWERS`**.

A causa está no próprio `hooks/session-start` do superpowers: ele **detecta a plataforma pela variável de ambiente**, não por argumento.

```bash
if [ -n "${CURSOR_PLUGIN_ROOT:-}" ]; then          # → additional_context
elif [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -z "${COPILOT_CLI:-}" ]; then  # → hookSpecificOutput.additionalContext
else                                               # → additionalContext (topo)
```

Medido: num hook de `settings.json`, `CLAUDE_PLUGIN_ROOT` está **ausente do ambiente** (`CLAUDE_PROJECT_DIR` está presente; `CLAUDE_PLUGIN_ROOT` e `CLAUDE_PLUGIN_DATA` não). O script cai no `else` e emite `additionalContext` no topo — que é a grafia do **Copilot CLI**, não a do Claude Code.

E o Claude Code descarta:

```
[DEBUG] Hook JSON output had unrecognized keys (ignored): additionalContext.
        Did you mean hookSpecificOutput.additionalContext (with a hookEventName)?
[DEBUG] Hook SessionStart:startup (SessionStart) success:
```

**Reportado como `success`. Exit 0. Nenhum aviso na saída normal.** A única evidência existe sob `--debug hooks`, em nível DEBUG. Um usuário vê uma sessão perfeitamente normal, sem superpowers, sem nenhum sinal de que algo falhou.

**Portanto: consertar o caminho é necessário e não é suficiente.** O enxerto de hook do overpower não é reescrever uma string de comando — é reproduzir o *contrato de ambiente* que o runtime-como-plugin fornecia.

### 3. O conserto, medido

Injetar a variável no próprio comando resolve:

```json
"command": "CLAUDE_PLUGIN_ROOT=\"${CLAUDE_PROJECT_DIR}/.claude/overpower/superpowers\" \"${CLAUDE_PROJECT_DIR}/.claude/overpower/superpowers/hooks/run-hook.cmd\" session-start"
```

Medido: `provided additionalContext (3276 chars)`, e o modelo respondeu **`SIM_SUPERPOWERS`**. Idêntico ao caminho de plugin.

Isso funciona porque o `command` do Claude Code roda sob shell quando não há `args`. É uma dependência de detalhe de implementação de *outro projeto* — o overpower estaria acoplado ao `if/elif/else` interno do `session-start` do superpowers, que a doc de porte deles descreve como ponto de extensão volátil (*"add a fourth branch"*).

### 4. Como baseline: pelo caminho de plugin, funciona inteiro

Medido com `--plugin-dir` apontando para a árvore real:

```
[DEBUG] Read hooks.json for plugin superpowers (enabled=true): …/sp/hooks/hooks.json
[DEBUG] Registered 1 hooks from 1 plugins
[DEBUG] Hook SessionStart ("${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd" session-start)
        provided additionalContext (3276 chars)
```

`hooks/hooks.json` é **autodescoberto** (o `.claude-plugin/plugin.json` do superpowers não declara campo `hooks`), `${CLAUDE_PLUGIN_ROOT}` expande, o bootstrap injeta, o modelo confirma. **O hook do superpowers funciona — como plugin. É a aterrissagem por cópia que o quebra.**

---

## Resposta direta: o superpowers **não** faz o que reprovou o GSD

A primeira pergunta do ticket era se o instalador do superpowers **escreve** em `.claude/settings.json` / `settings.local.json`, como o `open-gsd/gsd-core`. **Não escreve, e a proibição é explícita e escrita.**

`docs/porting-to-a-new-harness.md` do próprio repo, regra 2, verbatim:

> **"Everything ships through the harness's own install mechanism. Never edit the user's files."** […] A port **must not** reach into a user's global or personal config (`~/.gemini/config/AGENTS.md`, `settings.json`, `trustedFolders.json`, a hand-edited `~/.bashrc`, etc.) to inject anything.

E adiante, sobre o caso em que o instalador não consegue carregar o bootstrap:

> "If the install mechanism genuinely can't carry the bootstrap, that is a limitation to surface — **never a license to hand-edit the user's config.**"

O hook viaja **dentro da árvore do framework**, e cada ecossistema o lê pelo seu próprio mecanismo:

| Manifesto | Campo `hooks` | Efeito |
| --- | --- | --- |
| `.claude-plugin/plugin.json` | **ausente** | autodiscovery de `hooks/hooks.json` |
| `.cursor-plugin/plugin.json` | `"hooks": "./hooks/hooks-cursor.json"` | aponta o arquivo |
| `.codex-plugin/plugin.json` | `"hooks": {}` | **objeto vazio deliberado**, para suprimir autodiscovery — o Codex expõe skills nativamente e não roda hook de sessão |
| `.kimi-plugin/plugin.json` | `"sessionStart": {"skill": "using-superpowers"}` | mecanismo próprio, sem hook |
| `gemini-extension.json` | — | `contextFileName` → `GEMINI.md` |

Ou seja: **o superpowers é elegível pelo critério que reprovou o GSD.** A distinção do #15 se mantém — mas ela se mantém *porque ele é instalado como plugin*. **A aterrissagem por cópia do overpower é exatamente o que dissolve essa distinção**: o overpower teria de escrever o hook em `.claude/settings.json`, isto é, fazer com um framework aprovado o gesto que reprovou outro.

A diferença defensável é de **grau, não de espécie**: uma entrada de `SessionStart` num arquivo de projeto contra quinze hooks em sete eventos reescritos por um instalador de terceiro. É defensável. Mas é uma decisão de desenho a tomar explicitamente, não um fato que a pesquisa resolve.

---

## Uma seção por runtime

### Claude Code `2.1.221` — medido

**Onde**: `hooks` na raiz de `~/.claude/settings.json` (usuário), `.claude/settings.json` (projeto, commitável), `.claude/settings.local.json` (local), managed, e `hooks/hooks.json` de plugin.

**Forma**, com **dois níveis** de aninhamento (evento → array de grupos com `matcher` → array de hooks):

```json
{
  "hooks": {
    "SessionStart": [
      { "matcher": "startup|clear|compact",
        "hooks": [ { "type": "command", "command": "…", "shell": "bash", "async": false } ] }
    ]
  }
}
```

`shell`, `async`, `asyncRewake`, `args`, `if`, `timeout`, `statusMessage` são documentados. Tipos: `command`, `http`, `mcp_tool`, `prompt`, `agent` [doc].

**Eventos** — 31 documentados. `SessionStart`, `Setup`, `UserPromptSubmit`, `UserPromptExpansion`, `PreToolUse`, `PermissionRequest`, `PermissionDenied`, `PostToolUse`, `PostToolUseFailure`, `PostToolBatch`, `Notification`, `MessageDisplay`, `SubagentStart`, `SubagentStop`, `TaskCreated`, `TaskCompleted`, `Stop`, `StopFailure`, `TeammateIdle`, `InstructionsLoaded`, `ConfigChange`, `CwdChanged`, `DirectoryAdded`, `FileChanged`, `WorktreeCreate`, `WorktreeRemove`, `PreCompact`, `PostCompact`, `Elicitation`, `ElicitationResult`, `SessionEnd` [doc].

**stdin do `SessionStart`**, medido:
```json
{"session_id":"…","transcript_path":"…","cwd":"…","hook_event_name":"SessionStart","source":"startup"}
```

**Ambiente do hook**, medido (hook de `settings.json`): `CLAUDE_PROJECT_DIR`, `CLAUDE_ENV_FILE`, `CLAUDE_CODE_ENTRYPOINT`, `CLAUDE_CODE_SESSION_ID`, `CLAUDECODE`, `CLAUDE_PID`. **Sem** `CLAUDE_PLUGIN_ROOT`, **sem** `CLAUDE_PLUGIN_DATA`.

**Merge**: medido — `.claude/settings.json` e `.claude/settings.local.json` declarando ambos `SessionStart` fazem **os dois hooks rodarem**. Acumula, não substitui. A doc é silente; a medição não é.

**Ingestão**, medido, quatro execuções independentes com marcadores distintos:

| Saída do hook | Modelo recebeu? |
| --- | --- |
| `{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"…"}}` | **sim** |
| `{"additionalContext":"…"}` | **não** — `unrecognized keys (ignored)` |
| `{"additional_context":"…"}` | **não** — `unrecognized keys (ignored)` |
| as três juntas | **injeta uma vez só**, a aninhada |

**A quarta linha refuta o comentário no fonte do superpowers.** O `hooks/session-start` afirma:

> *"Claude Code reads BOTH additional_context and hookSpecificOutput without deduplication, so we must emit only the field the current platform consumes."*

Medido falso na `2.1.221`: emitindo as três, o log registra `unrecognized keys (ignored): additionalContext, additional_context` e injeta **3276 caracteres uma vez**. Não há dupla injeção. Ou o comportamento mudou, ou o comentário sempre foi impreciso. De um jeito ou de outro, **é o tipo de premissa que precisa de teste, não de leitura** — e a defesa que o superpowers construiu contra ele (o `if/elif/else` por variável de ambiente) é justamente a peça que quebra fora de plugin.

**Gate de confiança: não existe.** Medido — em diretório recém-criado, nunca aberto antes, com `HOME` limpo, o hook de `.claude/settings.json` **rodou na primeira sessão, sem prompt**. Nada foi gravado em `~/.claude.json`: nenhum `hasTrustDialogAccepted`, nenhuma entrada em `projects`. Contraste direto com MCP, onde um servidor de `.mcp.json` nasce `⏸ Pending approval`. **Um `.claude/settings.json` com hook, num repo clonado, é execução de código arbitrário na primeira sessão.**

Ressalva: medido em modo headless (`-p`). O diálogo de trust interativo do TUI não foi exercido — ver *Onde a evidência é fraca*.

Existem freios, mas são do lado do usuário/organização, não do repo: `disableAllHooks`, `allowManagedHooksOnly`, `allowedHttpHookUrls` [doc].

### GitHub Copilot CLI `1.0.78` — medido

**Onde** [doc]: policy `/etc/github-copilot/policy.d/*.json` → usuário `~/.copilot/hooks/` (ou `$COPILOT_HOME/hooks/`) → repositório `.github/hooks/*.json` → plugins. Também settings inline em `~/.copilot/settings.json` e `.github/copilot/settings.json`.

**Forma**: raiz `{"version": 1, "disableAllHooks": false, "hooks": {…}}`. `version: 1` obrigatório. Entrada com `type` (`command`|`http`|`prompt`), `bash`, `powershell`, `command`, `cwd`, `env`, `timeoutSec`, `matcher`. Eventos camelCase com alias PascalCase.

**Ingestão**, medido: hook de usuário em `$COPILOT_HOME/hooks/*.json` disparou, e `{"additionalContext":"…"}` **no topo** chegou ao modelo — ele ecoou o marcador. Confirma a grafia do `else` do superpowers.

**Divergência doc × medido**: o **hook de repositório em `.github/hooks/*.json` não disparou**. Testado dentro de um repositório git inicializado, na raiz, com arquivo de schema idêntico ao de usuário que funcionou — só a localização mudou. O hook de usuário rodou; o de repositório não deixou rastro. A doc lista `.github/hooks/*.json` como fonte de carga.

Isto repete exatamente o padrão que a pesquisa de MCP mediu neste mesmo runtime (`.mcp.json` em ancestrais: falso; `.github/mcp.json`: falso). **A causa não foi isolada** — pode ser gate de confiança de pasta sem prompt em modo `-p`, pode ser regressão. Mas a consequência de desenho vale nos dois casos: **para o Copilot CLI, o overpower não pode contar com o repositório como veículo de hook.**

Nota: o `--version` reportou `1.0.60` no início da sessão e `1.0.78` depois; o binário se atualizou durante a medição. Os resultados acima são de `1.0.78`.

### Codex CLI `0.144.6` — fonte Rust, não executado

O Codex **tem** um sistema de hooks real, completo, `Stable` e **ligado por padrão** — e é o **único runtime do conjunto com gate de confiança específico para hook**. Tudo abaixo vem do fonte na tag `rust-v0.144.6`, exatamente a versão instalada.

Evidência de primeira ordem — `codex --help`, flag global verbatim:

> `--dangerously-bypass-hook-trust` — *"Run enabled hooks without requiring persisted hook trust for this invocation. DANGEROUS. Intended only for automation that already vets hook sources"*

**Feature flag**: `Feature::CodexHooks`, `key: "hooks"`, `stage: Stable`, `default_enabled: true` (`codex-rs/features/src/lib.rs`). Confirmado no binário instalado: `codex features list` devolve `hooks  stable  true`. Virou padrão na `rust-v0.125.0`.

**Onde**: duas representações por camada, **ambas válidas** — `hooks.json` na pasta da camada, e `[hooks]` dentro do `config.toml` da mesma camada. Se as duas coexistirem, **as duas carregam**, com warning: *"loading hooks from both {} and {}; prefer a single representation for this layer"*.

**Forma** — dois níveis, igual ao Claude Code (evento → grupos com `matcher` → handlers):

```json
{ "hooks": { "SessionStart": [ { "hooks": [ { "type": "command", "command": "…" } ] } ] } }
```
```toml
[[hooks.SessionStart]]
hooks = [{ type = "command", command = "…", timeout = 30 }]
```

**Não existe campo `event`** — o evento é a chave da tabela. `HooksFile` tem `deny_unknown_fields`: campo desconhecido na raiz **derruba o arquivo inteiro**.

**Eventos — 10 em `0.144.6`**, PascalCase: `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PreCompact`, `PostCompact`, `SessionStart`, `UserPromptSubmit`, `SubagentStart`, `SubagentStop`, `Stop`. **`SessionEnd` não existe nesta versão** — está só no `main`, e escrito hoje é ignorado em silêncio (o nível de evento não é `deny_unknown_fields`).

**`SessionStart` é acionável**, com quatro origens (`Startup`, `Resume`, `Clear`, `Compact`). Detalhe operacional: **não dispara no boot do processo — dispara no início do primeiro turno**. Abrir o TUI e não digitar nada não aciona o hook.

**Saída**: `hookSpecificOutput.additionalContext`, camelCase e aninhada — idêntica ao Claude Code. Mais `continue`, `stopReason`, `suppressOutput`, `systemMessage`. Aceita `additionalContext` em `SessionStart`, `SubagentStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`.

**Atalho que nenhum outro runtime tem**: stdout que **não parece JSON vira contexto automaticamente**. Um `echo "texto"` já injeta. Mas se parecer JSON e for inválido, **falha duro**: *"hook returned invalid session start JSON output"*. É o oposto do Claude Code, que engole chave errada em silêncio.

**Exit codes**: `0` sucesso; `2` **bloqueia**, com o motivo lido do **stderr**; qualquer outro é falha. Execução via `$SHELL -lc <command>` — **login shell**, então o `.zshrc`/`.zprofile` do usuário carrega.

**Handlers que não funcionam**: `type: "prompt"`, `type: "agent"` e `async: true` parseiam e são **descartados com warning** — *"prompt hooks are not supported yet"*, *"async hooks are not supported yet"*. Subconjunto do vocabulário do Claude Code. `timeout` default 600s.

**Trust — dois gates independentes, e os dois precisam passar:**

1. **`trust_level` do projeto.** Verbatim do fonte: *"To load project-local config, hooks, and exec policies, add {trust_key} as a trusted project in {user_config_file}."* Projeto não confiável → a camada nem é lida. É o mesmo `[projects."<path>"] trust_level = "trusted"` que a pesquisa de MCP já mediu.
2. **Trust persistido por hook**, gravado em `~/.codex/config.toml` sob `[hooks.state."<chave>"]` com `trusted_hash` e `enabled`. O hash é sobre a identidade normalizada (evento + matcher + handler), não sobre o texto do arquivo — **editar o comando invalida o trust e força nova aprovação**.

Prompt verbatim (snapshot de teste do TUI):

```
  Hooks need review
  2 hooks are new or changed.
  Hooks can run outside the sandbox after you trust them.

› 1. Review hooks
  2. Trust all and continue
  3. Continue without trusting (hooks won't run)
```

Note o aviso: *"Hooks can run **outside the sandbox** after you trust them."* Hook aprovado não é sandboxed.

E a proteção que fecha o círculo: **`hooks.state` só é lido das camadas User e SessionFlags.** Comentário verbatim do fonte: *"Project, managed, and plugin layers can discover hooks, but they do not get to write user hook state."* **Um repositório não pode se auto-confiar.** É exatamente a garantia que falta ao Claude Code.

**Variáveis**: quatro, e **só para hooks de plugin** — `${PLUGIN_ROOT}`, `${CLAUDE_PLUGIN_ROOT}`, `${PLUGIN_DATA}`, `${CLAUDE_PLUGIN_DATA}`. O comentário no fonte é explícito: *"For OOTB compat with existing plugins that use this env var."* A substituição é `String::replace` puro na forma `${NOME}` — `$NOME` sem chaves não é substituído nessa etapa (mas o shell expande depois, porque também entram no ambiente).

**Para hooks de config (user/project/system) o mapa de env é vazio: zero expansão.** Consequência direta para o overpower: **no Codex, um hook de escopo de config não tem nenhuma variável de caminho.** Caminho relativo resolve contra o **cwd da sessão**, não contra o arquivo de config. Sobra caminho absoluto — o padrão que reprovou o GSD.

**Merge**: aditivo, **sem override**. Managed → camadas em ordem crescente de precedência → plugins. Todos rodam. Dedup só de pasta; dois escopos com o mesmo comando **executam duas vezes**. Kill switch corporativo: `allow_managed_hooks_only = true` em `requirements.toml`.

**Sobre o `"hooks": {}` do superpowers — a doc deles está correta, e o mecanismo é mais sutil do que parece.** O campo `hooks` do manifesto é `untagged` e aceita quatro formas (string, array de strings, objeto inline, array de objetos). Um `{}` casa com **objeto inline vazio**, ou seja `Some(…)`, **não `None`** — e o autodiscovery de `hooks/hooks.json` só roda no braço `None`. O `{}` é então descartado por estar vazio. Resultado: zero hooks carregados **e** `hooks/hooks.json` ignorado. Exatamente o efeito descrito.

Isto **corrige** uma leitura que eu havia feito do binário: a frase *"`skills`, `hooks` … are supplemented on top of default component discovery; they do not replace defaults"* **não** descreve este caminho de código. O fonte mostra substituição, com teste dedicado que a prova.

O que a doc do superpowers descreve com imprecisão é a *razão*: eles dizem que o Codex *"runs no session-start hook"*. Em `0.144.6` ele roda — `SessionStart` é evento de primeira classe. A supressão continua produzindo o efeito pretendido, mas a premissa envelheceu.

`codex doctor` **não reporta hooks** (medido) — mesmo ponto cego que a pesquisa de MCP registrou para trust de projeto. E **não existe `codex hooks` na CLI**; a gestão é pelo `/hooks` no TUI.

### Cursor — doc, não medido

**Onde** [doc]: projeto `<raiz>/.cursor/hooks.json`; usuário `~/.cursor/hooks.json`; enterprise em `/etc/cursor/hooks.json` (Linux/WSL), `/Library/Application Support/Cursor/hooks.json` (macOS), `C:\ProgramData\Cursor\hooks.json` (Windows); e times via dashboard.

**Forma**: `{"version": 1, "hooks": {…}}`. `version` obrigatório. Entrada de **um nível só** — `{command, type?, timeout?, matcher?, loop_limit?, failClosed?}`. Sem o aninhamento `matcher`+`hooks[]` do Claude Code.

**Eventos**, camelCase: `sessionStart`, `sessionEnd`, `preToolUse`, `postToolUse`, `postToolUseFailure`, `subagentStart`, `subagentStop`, `beforeShellExecution`, `afterShellExecution`, `beforeMCPExecution`, `afterMCPExecution`, `beforeReadFile`, `afterFileEdit`, `beforeSubmitPrompt`, `preCompact`, `stop`, `afterAgentResponse`, `afterAgentThought`, mais `beforeTabFileRead`/`afterTabFileEdit` (Tab) e `workspaceOpen` (app).

**Saída do `sessionStart`** [doc], verbatim:
```json
{ "env": { "<key>": "<value>" }, "additional_context": "<context to add to conversation>" }
```

**Caminho relativo**, verbatim: *"Project hooks run from the **project root**, so use `.cursor/hooks/script.sh` (not `./hooks/script.sh`)."* Isto explica o `"command": "./hooks/run-hook.cmd session-start"` do `hooks-cursor.json` do superpowers — ele depende de o CWD ser a raiz do projeto, que só é verdade quando o plugin *é* a raiz.

**Variáveis**: o Cursor entrega `CURSOR_PROJECT_DIR`, `CURSOR_VERSION`, `CURSOR_TRANSCRIPT_PATH` e um **alias `CLAUDE_PROJECT_DIR`** no *ambiente* do processo. **Expansão de `${…}` dentro da string `command` não é documentada.** Isto é material para o overpower: no Cursor não há o equivalente ao `${CLAUDE_PROJECT_DIR}` do Claude Code para montar caminho concreto — o caminho relativo à raiz do projeto é o único mecanismo documentado.

**Precedência**: Enterprise → Team → Project → User; verbatim *"All matching hooks from every source run; when responses conflict, higher-priority sources take precedence during merge."*

**Gate**, verbatim: *"Project hooks run in any trusted workspace and are checked into version control with your project."* O gate é o workspace trust genérico, não um gate de hook.

### VS Code `1.131.0` — doc, não medido

Hooks em **Preview** desde a 1.109; a própria doc avisa que *"the configuration format and behavior might change in future releases."*

**Onde** [doc]: workspace em `.github/hooks/*.json`, **`.claude/settings.json`** e **`.claude/settings.local.json`**; usuário em `~/.copilot/hooks` e `~/.claude/settings.json`. Controlado por `chat.hookFilesLocations`, cujo default documentado é:

```json
"chat.hookFilesLocations": {
  ".github/hooks": true,
  ".claude/settings.local.json": true,
  ".claude/settings.json": true,
  "~/.claude/settings.json": true
}
```

**Isto é o achado mais aproveitável para o overpower depois do principal**: escrever `.claude/settings.json` atende **dois** runtimes de uma vez. É o análogo em hook do `.mcp.json` compartilhado — e, ao contrário daquele, aqui não há mecanismo de segredo a perder, então a armadilha do caso MCP não se repete.

**Eventos** PascalCase, subconjunto do Claude Code: `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PreCompact`, `SubagentStart`, `SubagentStop`, `Stop`. Sem chave `version`.

**Saída do `SessionStart`**: `hookSpecificOutput.additionalContext`, aninhada — idêntica ao Claude Code. Verbatim: *"VS Code uses the same hook format as Claude Code and Copilot CLI for compatibility."*

**Duas ressalvas documentadas que quebram a compatibilidade prometida**: `matcher` é *"parsed but not applied"*; e propriedades de input de tool usam camelCase no VS Code contra snake_case no Claude Code.

---

## O hook do superpowers, renderizado em cada formato

O mesmo hook — `SessionStart` que executa `run-hook.cmd session-start` — sob a aterrissagem por cópia do overpower, com a árvore em `<repo>/.claude/overpower/superpowers/`.

### Claude Code — `.claude/settings.json` (medido, funciona)

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|clear|compact",
        "hooks": [
          {
            "type": "command",
            "command": "CLAUDE_PLUGIN_ROOT=\"${CLAUDE_PROJECT_DIR}/.claude/overpower/superpowers\" \"${CLAUDE_PROJECT_DIR}/.claude/overpower/superpowers/hooks/run-hook.cmd\" session-start",
            "shell": "bash",
            "async": false
          }
        ]
      }
    ]
  }
}
```

Duas decisões de linha, ambas com razão medida:
- **`${CLAUDE_PLUGIN_ROOT}` do original é substituído por `${CLAUDE_PROJECT_DIR}`** — a original é recusada por nome fora de plugin.
- **`CLAUDE_PLUGIN_ROOT=` é reintroduzido como variável de ambiente do comando** — sem isso o `session-start` emite a grafia errada e nada injeta. Este prefixo é o preço de acoplar-se ao `if/elif/else` do script alheio.

Alternativa mais limpa e **não medida**: o overpower gerar seu próprio script de bootstrap em vez de invocar o `session-start` do superpowers. Troca acoplamento a script de terceiro por dever de manter um renderizador.

Este mesmo arquivo é lido pelo **VS Code** [doc] — mas o prefixo `CLAUDE_PLUGIN_ROOT=` só é correto porque o VS Code também consome a forma aninhada. Não verificado.

### Cursor — `.cursor/hooks.json` (não medido)

```json
{
  "version": 1,
  "hooks": {
    "sessionStart": [
      { "command": ".claude/overpower/superpowers/hooks/run-hook.cmd session-start" }
    ]
  }
}
```

Sem `matcher`, sem `type`, sem `async` — o schema do Cursor não os tem nesta posição. Caminho **relativo à raiz do projeto**, conforme a doc. E aqui o `session-start` funciona **sem prefixo**: o Cursor exporta `CURSOR_PLUGIN_ROOT` quando é plugin, e fora de plugin o script cai no `else`… que emite `additionalContext`, **não** o `additional_context` que o Cursor consome. **Mesmo modo de falha do Claude Code, e não medido.** Um `CURSOR_PLUGIN_ROOT=` prefixado seria o análogo do conserto.

### Copilot CLI — `~/.copilot/hooks/superpowers.json` (escopo de máquina; medido)

```json
{
  "version": 1,
  "hooks": {
    "sessionStart": [
      { "type": "command", "command": "/caminho/absoluto/superpowers/hooks/run-hook.cmd session-start" }
    ]
  }
}
```

Aqui o `else` do `session-start` acerta a grafia sem conserto — `additionalContext` no topo é exatamente o que o Copilot consome (medido). **Mas o escopo de repositório está indisponível** (medido inerte), então este arquivo só existe na máquina, com **caminho absoluto** — precisamente o padrão que reprovou o `open-gsd/gsd-core`.

### VS Code — `.github/hooks/superpowers.json` (não medido)

```json
{
  "hooks": {
    "SessionStart": [
      { "matcher": "startup", "hooks": [ { "type": "command", "command": "…/run-hook.cmd session-start" } ] }
    ]
  }
}
```

Sem `version`. `matcher` é aceito e **ignorado** [doc]. Ou, preferível, reusar o `.claude/settings.json` acima.

### Codex — `<repo>/.codex/hooks.json` (não medido)

```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [ { "type": "command", "command": "/caminho/absoluto/superpowers/hooks/run-hook.cmd session-start" } ] } ]
  }
}
```

Três coisas o distinguem, e todas vêm do fonte:

- **Caminho absoluto é obrigatório.** Hooks de escopo de config não recebem nenhuma variável, e caminho relativo resolve contra o cwd da sessão. É o único runtime onde o overpower não tem como escrever um caminho portátil num arquivo commitável.
- **O `session-start` do superpowers cairia no `else`** e emitiria `additionalContext` no topo, que o Codex **não** consome — mesmo modo de falha do Claude Code. O conserto é o mesmo prefixo, e aqui ele tem apoio: o Codex já define `CLAUDE_PLUGIN_ROOT` para hooks de plugin, *"for OOTB compat"*.
- **Nada disso roda sem dois consentimentos humanos**: marcar o projeto como `trusted` e aprovar o hook no `/hooks`. Nenhum outro runtime exige isso.

O superpowers **desliga** o hook no Codex de propósito (`"hooks": {}`), então esta renderização é do que o overpower teria de emitir, não do que o superpowers emite.

---

## Divergências entre doc/fonte e comportamento medido

| Origem | A fonte diz | Medido |
| --- | --- | --- |
| `obra/superpowers`, comentário em `hooks/session-start` | *"Claude Code reads BOTH additional_context and hookSpecificOutput without deduplication"* | **Falso na 2.1.221.** Emitindo as três grafias, as duas de topo são `unrecognized keys (ignored)` e a injeção acontece **uma vez** |
| Suposição registrada no ticket | `${CLAUDE_PLUGIN_ROOT}` fora de plugin "vem vazia" | **Falso.** O Claude Code detecta e **recusa o hook** com mensagem nomeada. Falha alta, não baixa |
| Doc do Copilot CLI | `.github/hooks/*.json` é fonte de carga de repositório | **Não disparou** na `1.0.78`, em repo git, na raiz, com schema idêntico ao de usuário que funcionou |
| Doc do Claude Code | silente sobre gate de confiança para hook | **Não existe gate.** Diretório novo, `HOME` limpo, hook de `.claude/settings.json` roda na primeira sessão sem prompt e sem registro de consentimento |
| Doc do Claude Code | silente sobre merge de hooks entre escopos | **Acumula.** `settings.json` e `settings.local.json` rodam ambos |
| Doc de porte do `obra/superpowers` | `"hooks": {}` suprime o autodiscovery de `hooks/hooks.json` no Codex | **Confirmado no fonte**, com o mecanismo exato: `{}` casa com "objeto inline vazio" (`Some`), e o autodiscovery só roda no braço `None` |
| Doc de porte do `obra/superpowers` | Codex *"surfaces skills natively and runs no session-start hook"* | **Envelhecido.** `SessionStart` é evento de primeira classe em `0.144.6`, `Stable` e ligado por padrão desde a `0.125.0`. A supressão ainda funciona; a razão dela não vale mais |
| Doc do VS Code | *"VS Code uses the same hook format as Claude Code and Copilot CLI for compatibility"* | A mesma página registra que `matcher` é *"parsed but not applied"* e que a grafia de propriedades de tool difere. A compatibilidade é parcial e a própria doc diz onde |

---

## Armadilhas, por quanto doem

1. **Copiar `hooks/hooks.json` do superpowers para `.claude/settings.json` sem tocar no comando.** O hook é recusado por nome. Barulhento — a armadilha barata.
2. **Consertar só o caminho.** O hook roda, sai 0, é reportado como `success`, e **não injeta nada**. Silencioso — a armadilha cara. É a diferença entre "o comando resolve" e "o contrato de ambiente foi reproduzido".
3. **Confiar em exit code ou em log de sucesso como prova de injeção.** Nos dois runtimes medidos a prova só veio da **resposta do modelo**. `success` não significa consumido.
4. **Reusar a grafia do campo entre alvos.** `hookSpecificOutput.additionalContext` (Claude Code, VS Code, Codex) ≠ `additionalContext` (Copilot CLI) ≠ `additional_context` (Cursor). Erra e falha em silêncio.
5. **Reusar a *forma* da entrada.** Claude Code e VS Code têm dois níveis (`matcher` + `hooks[]`); Cursor tem um. Copilot e Cursor exigem `version: 1`; Claude Code e VS Code não o têm.
6. **Reusar a grafia dos eventos.** `SessionStart` (Claude Code, VS Code, **Codex**) ≠ `sessionStart` (Cursor, Copilot — este com alias PascalCase). O snake_case (`session_start`) existe no Codex, mas é rótulo **interno de chave de trust**; escrevê-lo na config não aciona nada.
7. **Assumir que `matcher` faz algo.** No VS Code é parseado e ignorado [doc]. Um hook que dependa dele para *não* rodar, roda.
8. **Contar com o repositório como veículo no Copilot CLI.** Medido inerte. Sobra o escopo de máquina, com caminho absoluto — o padrão que reprovou o GSD.
9. **Assumir que hook de repo clonado é gated.** No Claude Code não é (medido). O overpower escreve um vetor de execução automática, e o axioma de "sem estado no alvo" não protege contra isso.
10. **Assumir que o Codex não tem hooks.** Tem, `Stable` e ligado por padrão, com **dois** gates de confiança. Um enxerto lá exige **dois passos humanos** que nenhum outro runtime exige — e o trust quebra sozinho quando o comando muda ou os hooks são reordenados no arquivo. Um `overpower install` que reescreva o arquivo faz o usuário reaprovar tudo.
13. **Escrever caminho relativo no `command` do Codex.** Não resolve contra o arquivo de config nem contra a raiz do plugin — resolve contra o **cwd da sessão**. Muda quando o usuário roda `codex` de um subdiretório.
14. **Emitir JSON quase-válido no Codex.** Stdout não-JSON vira contexto de graça; stdout que *parece* JSON e está quebrado **falha duro**. O caminho do meio é o perigoso.
11. **Acoplar-se ao `if/elif/else` do `session-start` alheio.** O próprio superpowers descreve esse bloco como ponto de extensão que cresce por harness. Injetar `CLAUDE_PLUGIN_ROOT=` funciona hoje e é frágil por construção.
12. **Escrever `.claude/settings.local.json`.** Já é onde mora a aprovação de MCP. Hooks acumulam entre os dois arquivos (medido), então escrever nos dois duplica a execução em vez de sobrepor.

---

## O que isso entrega para os tickets de desenho

**Para a regra 4 do modelo de domínio** — confirmada e endurecida de novo, e por um motivo novo. No MCP, o contrato lógico precisava carregar o *nome* do slot em vez da string. Aqui a lição é mais forte: **o contrato de um artefato de hook não pode carregar nem o comando**. O comando depende de qual variável de caminho o alvo expande (`${CLAUDE_PROJECT_DIR}` só no Claude Code; caminho relativo à raiz no Cursor; absoluto no Copilot) **e** do contrato de ambiente que o script invocado espera. O contrato tem de carregar *evento lógico* + *o que executar* + *que texto injetar*; a forma é toda do renderizador.

**Para o axioma 2 (o git é o manifesto)** — pior que no MCP. Lá o enxerto de projeto era duas escritas, uma no repo e uma na máquina. Aqui, **para o Copilot CLI o repositório não funciona** (medido): a escrita é só na máquina, com caminho absoluto. O `git diff` não conta nada dessa história. Isso não reabre o mapa — a v0.1.0 não tem hook — mas a v0.2 precisa decidir se "instalar um framework com hook" é uma operação que o repositório consegue descrever.

**Para o critério de elegibilidade ([#15](https://github.com/panlabs-tech/overpower/issues/15))** — a distinção entre superpowers e GSD **se sustenta**, e a pesquisa mostra exatamente onde ela é fina. O superpowers proíbe editar config do usuário por escrito, e o GSD reescreve `settings.local.json` com 15 hooks. Mas isso vale para os *instaladores deles*. Quando o overpower aterrissa por cópia, **é o overpower que escreve na config do usuário** — e a diferença vira "quantos hooks, em quantos eventos, com que caminho". Um critério que hoje é binário ("o instalador escreve?") precisará virar graduado ("o que escrevemos, e o usuário consegue ver?").

**Para a semântica de escrita ([#9](https://github.com/panlabs-tech/overpower/issues/9))** — o merge acumulativo medido no Claude Code cria um caso que a colisão de caminho não tinha: rodar o overpower duas vezes **duplica o hook** se ele não for idempotente por identidade. Não há chave natural — a entrada é um objeto num array. O renderizador precisa de uma marca própria para reconhecer o que ele mesmo escreveu.

**Para a integridade de referência cruzada ([#16](https://github.com/panlabs-tech/overpower/issues/16))** — um artefato de hook depende de **dois** alvos, não um: o arquivo de config e o script que o comando invoca. Se a cópia da árvore falhar, o hook continua declarado e passa a executar um caminho inexistente a cada sessão.

**Para o risco, que o ticket pediu explicitamente** — hook é execução de código no início da sessão, e **o conjunto está partido ao meio**. O Codex trata isso como decisão de segurança: dois gates, hash por hook, revisão nomeada, aviso de que hook confiado roda **fora do sandbox**, e a garantia de que *"project, managed, and plugin layers … do not get to write user hook state"* — um repositório não pode se auto-confiar. O Claude Code não tem gate nenhum (medido): um `.claude/settings.json` num repo clonado executa na primeira sessão, sem prompt e sem registro. Cursor e VS Code ficam no meio, apoiados em workspace trust genérico [doc].

Isso importa para o overpower por dois motivos opostos. Escrevendo hook no repositório, ele **cria** esse vetor no runtime mais permissivo — e o axioma "sem estado no alvo" não protege contra isso, porque o problema é o conteúdo do arquivo, não a existência dele. E escrevendo no Codex, ele produz um artefato **inerte até aprovação manual**, que é o mesmo modo de falha silenciosa que a pesquisa de MCP registrou para `trust_level`. O enxerto de hook precisa dizer ao usuário o que acabou de instalar; nenhum dos dois runtimes fará isso por ele.

**Para o desenho do enxerto de hook, o item concreto** — a decisão de fundo não é de formato, é esta: **o overpower renderiza um comando que invoca o script do framework, ou gera o seu próprio bootstrap?** Invocar o script alheio custa acoplamento ao `if/elif/else` interno dele (medido frágil). Gerar o próprio custa manter um renderizador por alvo — que a regra 4 já obriga de qualquer forma. A medição inclina para gerar, mas a alternativa não foi construída nem medida.

---

## Onde a evidência é fraca

Listado sem maquiagem.

1. **Cursor não foi medido.** Não está instalado. Toda a fatia é doc do fornecedor. Em particular, **não foi verificado se `additional_context` de fato chega ao modelo** — e o padrão medido no Copilot CLI (campo documentado, ignorado até a 1.0.11) sugere que essa é justamente a verificação que não se deve pular.
2. **VS Code não foi medido**, pela restrição do Remote-WSL descrita no Método. Que `chat.hookFilesLocations` realmente leia `.claude/settings.json` — o achado mais aproveitável do documento depois do principal — **é doc, não medição**.
3. **Codex não foi executado com hook ativo.** Toda a fatia vem do fonte Rust na tag exata da versão instalada — evidência forte, mas **o fluxo do prompt de trust, a gravação de `hooks.state` e a injeção efetiva do `additionalContext` não foram observados em execução.** O `hooks.json` de máquina que escrevi não produziu sinal em `codex doctor`, e não persegui a causa.
   Duas armadilhas do Codex que herdo do fonte e não confirmei rodando: a chave de trust é **posicional** (`…:0:0`, com um `TODO` no próprio código pedindo um id durável), então **reordenar hooks num arquivo invalida o trust de todos que se moveram**; e `SessionStart` dispara no **primeiro turno**, não no launch.
4. **O gate de confiança do Claude Code foi medido só em modo headless (`-p`).** O diálogo de trust interativo do TUI não foi exercido. É possível que a sessão interativa se comporte diferente na primeira abertura de um diretório. A afirmação "não existe gate" vale para o modo medido.
5. **A causa de o `.github/hooks/` do Copilot CLI não disparar não foi isolada.** Observei a ausência; não distingui entre gate de confiança silencioso, exigência de estrutura que não reproduzi, e regressão.
6. **O conserto do `CLAUDE_PLUGIN_ROOT=` prefixado foi medido só no Claude Code.** O análogo `CURSOR_PLUGIN_ROOT=` para o Cursor é inferência por simetria de leitura do script, não medição.
7. **A alternativa "overpower gera o próprio bootstrap" não foi prototipada.** A recomendação inclina-se a ela por eliminação, não por comparação medida.
8. **A lista de 31 eventos do Claude Code e a de eventos do Cursor vêm da doc**, não de enumeração no binário. Não conferi se a doc está completa.
9. **A supressão por `"hooks": {}` no Codex foi resolvida no fonte, não em execução.** O caminho de código e o teste que o cobre são inequívocos, mas não plantei um plugin real para ver o efeito.
10. **Não varri runtimes fora do conjunto** (Gemini CLI, Kimi, OpenCode, pi, Antigravity, Factory). O `obra/superpowers` publica para todos eles, e a doc de porte dele mostra que pelo menos três usam mecanismos que **não são hook** (arquivo de contexto declarado, plugin in-process, `sessionStart.skill` de manifesto).
11. **A árvore do superpowers medida é a `main` de 2026-08-03, versão de manifesto `6.2.0`.** O `--plugin-dir` carregou **14 skills**, não as 22 que o #15 cita para o `mattpocock/skills` — números de frameworks diferentes, mas registro o que a medição viu para não se confundirem depois.
