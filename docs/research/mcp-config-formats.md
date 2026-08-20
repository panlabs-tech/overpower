# Formatos de configuração de MCP por runtime

**Ticket**: [Formatos de configuração de MCP por runtime](https://github.com/ThiagoPanini/overpower/issues/17)
**Data**: 2026-08-01
**Insumo**: [`docs/agents/domain.md`](../agents/domain.md), regra 4 — *o contrato de um artefato de enxerto é lógico, não literal*.

## Método

Quatro dos cinco alvos estão instalados nesta máquina e foram **medidos**, não lidos:

| Alvo | Versão | Como foi apurado |
| --- | --- | --- |
| Claude Code | `2.1.220` | Executado em sandbox (`HOME` + `CLAUDE_CONFIG_DIR` redirecionados). Expansão verificada contra **processo filho real** e **listener HTTP local** |
| Codex CLI | `codex-cli 0.144.6` | Executado em sandbox (`HOME` + `CODEX_HOME`). Cruzado com o fonte Rust de `openai/codex@feee0b07` |
| VS Code | `1.131.0` | Schema e lógica lidos do **bundle instalado** (`workbench.desktop.main.js`) e do fonte `microsoft/vscode@main`. `--add-mcp` **não** executado (ver ressalva) |
| GitHub Copilot CLI | `1.0.60` | Executado em sandbox (`HOME` + `COPILOT_HOME`) |
| Cursor | — | **Não instalado.** Só documentação oficial. Nada aqui é medido |

Convenção usada abaixo: **medido** = executado e observado; **doc** = documentação oficial ou schema publicado; **fonte** = código-fonte lido.

Ressalva de honestidade: nesta máquina o `code` é o remote-cli do Remote-WSL, que encaminha argumentos por IPC para a instância real no Windows e não aceita `--user-data-dir`. Rodar `code --add-mcp` teria escrito na configuração real do dev. O comportamento de **escrita** do VS Code está apurado por fonte, não por medição.

---

## Veredito: não existe formato canônico

A pergunta estratégica por trás do ticket era se existe um formato do qual os outros são dialetos. **Não existe, e a própria especificação MCP reconhece isso como problema em aberto.**

O schema normativo da spec (`schema/2025-06-18/schema.json`, 91 definitions) tem **zero** ocorrências de `mcpServers`, `command`, `args` ou `mcp.json`. A spec padroniza o protocolo — mensagens, transporte, lifecycle, autorização — e nada sobre arquivo de configuração de cliente.

A prova documental é a **SEP-2633, "Standard Client-Side Configuration Format — mcp.json"**, PR **aberto** no repo da spec desde 2026-04-21 (última atualização 2026-07-28). O abstract e a motivação dizem literalmente:

> "The MCP ecosystem has server.json (the MCP Registry package specification) […] But there's no standard for the other side: how a client will connect to its servers."

> "Today every MCP client invents its own format for server configuration. Clients use different file names, and even different file types (JSON, JSONC, and TOML). They use different top-level keys (including `servers` and `mcpServers`). They use different values for the `type` field. They use different mechanisms and encodings for secret interpolation. The list goes on."

E o survey dos autores (Claude Code, VS Code, Cursor, Goose, Kiro, Codex, RooCode/Cline, LangChain) conclui: *"these clients differ in almost all aspects, with no two being fully compatible."* O próprio SEP admite que, se aceito, *"few, if any"* clientes atuais serão compatíveis com ele.

**Consequência direta**: a regra 4 do modelo de domínio não é uma conveniência — é a única arquitetura possível. Um renderizador por alvo é obrigatório. Não existe "escreva um, adapte três".

### E não há denominador comum em `.agents/`

A pesquisa de [Aterrissagem projeto × global](https://github.com/ThiagoPanini/overpower/issues/5) estabeleceu que `.agents/skills/` é caminho de leitura oficial de quatro runtimes. **O análogo para MCP não existe**, e a resposta negativa tem quatro verificações independentes:

1. A spec do `AGENTS.md` (agents.md) não menciona MCP em lugar nenhum.
2. A spec do Agent Skills (agentskills.io/specification) não menciona MCP — **e nem sequer padroniza `.agents/skills`**; ela descreve a pasta da skill, não onde o cliente a procura. `.agents/skills` é convergência *de facto* por fornecedor, não cláusula normativa. Isso refina o achado do [#5](https://github.com/ThiagoPanini/overpower/issues/5).
3. A mesma página do Cursor que enumera `.agents/skills/` põe MCP em `.cursor/mcp.json`. A mesma doc do Codex que enumera `.agents/skills` põe MCP em `.codex/config.toml`.
4. Os sites `dotagentsprotocol.com` e `agentsstandard.com`, que propõem `~/.agents/mcp-settings.json` como "universal MCP config", **não são doc de fornecedor** — são terceiros propondo um padrão que nenhum runtime documenta ler.

O consenso `.agents/` cobre **conteúdo, não configuração**, e a separação parece deliberada. Existe até uma ferramenta de terceiro (`amtiYo/agents`) que *sincroniza* uma pasta `.agents` para os formatos nativos — o que é a própria evidência de que o denominador comum não existe: alguém precisou escrever um sincronizador.

---

## Tabela runtime × campo

| | **Claude Code** | **Cursor** | **VS Code** | **Codex CLI** | **Copilot CLI** |
| --- | --- | --- | --- | --- | --- |
| **Arquivo de projeto** (commitável) | `.mcp.json` | `.cursor/mcp.json` | `.vscode/mcp.json` | `<repo>/.codex/config.toml` | `.mcp.json` |
| **Arquivo de máquina** | `~/.claude.json` → `mcpServers` (raiz) | `~/.cursor/mcp.json` | `<perfil>/mcp.json` ¹ | `~/.codex/config.toml` (`$CODEX_HOME`) | `~/.copilot/mcp-config.json` (`$COPILOT_HOME`) |
| **Terceiro escopo** | `local` → `~/.claude.json` → `projects["<abs>"].mcpServers` | **não existe** | `.code-workspace` → `settings.mcp`; devcontainer | `${PWD}/config.toml`, `/etc/codex/config.toml`, perfis | `--additional-mcp-config` (efêmero) |
| **Tipo de arquivo** | JSON **estrito** | JSON (JSONC não documentado) | **JSONC** (comentários + vírgula final) | **TOML** | JSONC no de usuário; **estrito** no `.mcp.json` |
| **Chave raiz** | `mcpServers` | `mcpServers` | **`servers`** (+ `inputs`, `sandbox`) | **`[mcp_servers.<nome>]`** | `mcpServers` (ou objeto "pelado") |
| **Chave errada** | erro explícito e ótimo | — | inválido no schema (`additionalProperties:false`) | **descartado em silêncio**, exit 0 | `servers` ignorado |
| **stdio: campos** | `command`, `args`, `env` | `command`, `args`, `env`, `envFile` | `command`, `args`, `env`, `cwd`, `envFile`, `sandboxEnabled`, `dev` | `command`, `args`, `env`, `env_vars`, `cwd` | `command`, `args`, `env`, `tools`, `timeout` |
| **http: campos** | `url`, `headers`, `oauth`, `headersHelper` | `url`, `headers`, `auth` | `url`, `headers`, `oauth` | `url`, `bearer_token_env_var`, `http_headers`, `env_http_headers`, `auth` | `url`, `headers`, `tools`, `timeout` |
| **Discriminação de transporte** | campo `type` (**sem `type` = stdio, sempre**) | inferido por `url` vs `command` | inferido (`command` → stdio, `url` → http) | inferido por `url` vs `command` | `type` ou inferência |
| **Campo desconhecido no servidor** | preservado | — | rejeitado (`additionalProperties:false`) | **engolido em silêncio** | — |
| **Escopo local não-versionado** | sim (`local`) | **não existe** | `mcp.json` de perfil, ou `envFile` | `~/.codex/config.toml` | `~/.copilot/mcp-config.json` |
| **Gate para o arquivo commitado funcionar** | **aprovação** por servidor | nenhum (só aprovação de *tool*) | Workspace Trust | **`trust_level = "trusted"`** na config de máquina | trust de pasta no primeiro launch |
| **Onde o gate fica gravado** | `<repo>/.claude/settings.local.json` — **dentro da árvore** | — | `state.vscdb` — **nunca no repo** | `~/.codex/config.toml` — fora do repo | `~/.copilot/` (não verificado) |

¹ `%APPDATA%\Code\User\mcp.json` · `~/Library/Application Support/Code/User/mcp.json` · `$XDG_CONFIG_HOME/Code/User/mcp.json` · perfil não-default em `<userDataDir>/User/profiles/<id>/mcp.json` · Remote-WSL/SSH tem um **segundo** `mcp.json` no servidor remoto.

---

## Transportes

O ticket perguntava o que fazer quando o alvo não suporta o transporte declarado. A matriz:

| Transporte | Claude Code | Cursor | VS Code | Codex | Copilot CLI |
| --- | --- | --- | --- | --- | --- |
| `stdio` | ✅ `"stdio"` | ✅ `"stdio"` ² | ✅ `"stdio"` | ✅ inferido | ✅ **grava `"local"`** |
| Streamable HTTP | ✅ `"http"` | ✅ sem `type` documentado | ✅ `"http"` | ✅ inferido de `url` | ✅ `"http"` |
| `sse` | ✅ (doc: deprecado) | ✅ (sem aviso de deprecação) | ✅ (schema aceita) | ❌ **não existe** | ✅ (doc: deprecado) |
| `ws` | ✅ só via `add-json` | ❌ | ❌ | ❌ | ❌ |
| `streamable-http` literal | alias → normalizado para `http` | — | ❌ rejeitado | ❌ | ❌ **derruba o arquivo inteiro** |

² A tabela normativa do Cursor marca `type` como **Required: Yes** para stdio, mas **nenhum exemplo oficial da mesma página o inclui**. A doc se contradiz.

**Só existem dois buracos reais, e o perigoso é o segundo:**

- **`ws` é exclusivo do Claude Code.** Um artefato que declare WebSocket só renderiza para um alvo.
- **`sse` no Codex não falha — vira outra coisa em silêncio.** `type = "sse"` é campo desconhecido (engolido), sobra a `url`, e o Codex conecta como **streamable HTTP**. Não há mensagem nem exit code para capturar. Um artefato SSE renderizado para o Codex vira bug de runtime, não erro de configuração. **O overpower tem de recusar SSE na origem, porque o Codex não vai recusar.**

E SSE é dívida com prazo em todo lugar: a revisão **current** da spec é `2026-07-28` e define **dois** bindings, stdio e Streamable HTTP. HTTP+SSE saiu da lista — está deprecado desde `2025-03-26` e foi reclassificado formalmente como **Deprecated** em `2026-07-28` (SEP-2596), com janela mínima de doze meses antes de elegibilidade para remoção.

### Cinco grafias para o mesmo transporte

| Origem | Valor para HTTP |
| --- | --- |
| Registro oficial (`server.json`), SEP-2633 | `streamable-http` |
| Goose, LangChain, Codex dentro de skill (`openai.yaml`) | `streamable_http` |
| VS Code, Claude Code, Copilot CLI | `http` |
| Cursor, Codex no `config.toml` | ausente — inferido |
| A spec, em prosa | `Streamable HTTP` |

**Nenhum runtime usa o nome da spec literalmente.**

---

## Mecanismo de segredo — a pergunta que decide o desenho

A regra 4 diz que o contrato carrega *slots de segredo, nunca valores*. A pesquisa mostra que **"slot" não é um conceito, são três mecanismos incompatíveis — e um alvo não tem nenhum.**

| Runtime | Mecanismo | Sintaxe | Campos cobertos | Default | Variável ausente |
| --- | --- | --- | --- | --- | --- |
| **Claude Code** | interpolação na leitura | `${VAR}` | `command`, `args`, `env`, `url`, `headers` | ✅ **`${VAR:-default}`** | **vaza a string crua** para o processo e para a rede |
| **Cursor** | interpolação na leitura | `${env:VAR}` | `command`, `args`, `env`, `url`, `headers`, `auth` | ❌ | não documentado |
| **VS Code** | interpolação na leitura | `${env:VAR}` | **todos** (walker recursivo, inclusive chaves) | ❌ — `${env:X:-y}` procura a variável `X:-y` | **string vazia**, em silêncio |
| **VS Code** | prompt + cofre do SO | `${input:<id>}` + bloco `inputs[]` | os mesmos | `default` = valor pré-preenchido do prompt | pergunta ao usuário |
| **Codex** | **referência por nome** | `env_vars = ["VAR"]`, `bearer_token_env_var`, `env_http_headers` | stdio e http | ❌ | header omitido em silêncio; `codex doctor` acusa |
| **Copilot CLI** | **nenhum** | — | — | — | valor literal é a única forma |

### O Codex é o alvo mais amigável, e o Copilot CLI é o mais hostil

O Codex **nunca precisa do valor no arquivo**. Ele tem canal dedicado por nome de variável em todos os transportes, **recusa ativamente** `bearer_token` literal (exit 1, e derruba o carregamento do config inteiro), e ainda entrega `codex doctor` como verificador de preenchimento de slot, de graça. Medido: com um servidor stdio real lançado por `codex exec`, o processo filho recebeu `INTERPOLADO=${MEU_SEGREDO}` **cru** e `MEU_SEGREDO=SUPER-SECRETO-42` **resolvido via `env_vars`** — a prova de que interpolação não existe e a referência por nome funciona.

Detalhe relevante para o modelo de ameaça: o servidor stdio do Codex **não herda o ambiente inteiro**. Recebe uma allowlist (`HOME`, `LOGNAME`, `PATH`, `SHELL`, `USER`, `LANG`, `LC_ALL`, `TERM`, `TMPDIR`, `TZ`, `__CF_USER_TEXT_ENCODING`) mais o que `env_vars` e `env` declararem. O Claude Code faz o oposto: **o filho herda o ambiente completo** — medido, uma variável não declarada em `env` apareceu no processo do servidor.

O Copilot CLI não tem placeholder nenhum. Medido: `.mcp.json` com `"env": {"TOK": "${MY_SECRET}"}` e `MY_SECRET` exportada devolve `TOK: ${MY_SECRET}` literal. O `***` da saída é **só máscara de exibição** — `--show-secrets` revela. A doc confirma a ausência: *"The `PATH` variable is automatically inherited from your environment. All other environment variables must be configured here."*

### O `${VAR}` do Claude Code é o único com default — e o único que vaza na rede

Medido contra listener HTTP local: com `Authorization: Bearer ${NAO_EXISTE}` e a variável ausente, **a string literal saiu na requisição**. O servidor remoto recebe `Bearer ${NAO_EXISTE}` e responde 401/400. É erro de runtime, longe da causa. Também medido: `$VAR` sem chaves não expande, e `$${VAR}` **não é escape** — produz `$` + valor. Não existe forma de escrever um `${...}` literal.

### As três sintaxes são mutuamente ilegíveis, e falham em silêncio

Este é o modo de falha mais caro do espaço inteiro:

- `${GITHUB_TOKEN}` num `.cursor/mcp.json` **não expande** — vira header literal, 401 em runtime.
- `${env:GITHUB_TOKEN}` num `.mcp.json` do Claude Code **não expande** — a sintaxe dele não tem o prefixo `env:`; vira `${env:GITHUB_TOKEN}` cru na rede.
- `${env:TOKEN:-fallback}` no VS Code procura uma variável literalmente chamada `TOKEN:-fallback`, não acha, e devolve **string vazia**. Sem erro.

Nenhum desses casos falha no parse. Todos falham no runtime, longe da causa.

### A armadilha do `inputs` do VS Code

O `password: true` não é cosmético — é o que liga o AES-GCM. Com ele, o valor digitado é criptografado com chave no cofre do SO (`mcpEncryptionKey` no Keychain/DPAPI/libsecret) e o ciphertext vai para o `state.vscdb`, no escopo **workspace** quando a origem é `.vscode/mcp.json`. **Sem `password: true`, o valor vai em texto puro** para o mesmo banco. Em nenhum dos dois casos o segredo toca o repositório — commitar `.vscode/mcp.json` com `${input:id}` é seguro.

---

## O `.mcp.json` compartilhado: o ponto de encontro que é uma armadilha

Três runtimes leem o **mesmo arquivo** `.mcp.json` na raiz do projeto, em formato Claude (`{"mcpServers": {...}}`):

- **Claude Code** — é o formato nativo dele, escopo `project`.
- **VS Code 1.131.0** — via `WorkspaceDotMcpDiscovery`; confirmado no bundle instalado, com comentário no próprio fonte: *"Discovers MCP servers defined in `.mcp.json` files at workspace folder roots. Uses the Claude-style format."*
- **Copilot CLI 1.0.60** — escopo workspace (medido: **só no CWD**, ver divergências).

É tentador: um arquivo, três runtimes, e sobram só Cursor e Codex. **Mas ele é o mais pobre dos formatos, e o custo é exatamente o mecanismo de segredo.**

| | Claude Code lendo `.mcp.json` | VS Code lendo `.mcp.json` | Copilot lendo `.mcp.json` |
| --- | --- | --- | --- |
| `${VAR}` expande? | ✅ **sim** | ❌ **não** | ❌ **não** |
| `${input:id}` | n/a | ❌ **não** — sem `variableReplacement` | ❌ |
| `env` com `url` | usado | **descartado** | usado |
| JSONC | ❌ estrito | ❌ estrito (`JSON.parse` puro dentro de `catch { return }`) | ❌ estrito |

No VS Code o `.mcp.json` passa por `claudeConfigToServerDefinition`, que monta o `McpServerDefinition` **sem** o campo `variableReplacement` — e `_replaceVariablesInLaunch` sai na primeira linha quando ele está ausente. Resultado: `${env:X}` e `${input:x}` chegam **literais** ao processo do servidor.

**Portanto**: um `.mcp.json` com `"Authorization": "Bearer ${GITHUB_TOKEN}"` funciona no Claude Code e entrega a string crua ao servidor remoto no VS Code e no Copilot CLI. O arquivo compartilhado só é seguro para servidores **sem segredo**.

---

## Semântica de merge e validação

| | Claude Code | Cursor | VS Code | Codex | Copilot CLI |
| --- | --- | --- | --- | --- | --- |
| **Nome duplicado no mesmo arquivo** | **recusa**, exit 1, sem `--force` | não documentado | **sobrescreve calado** (`existingServers[name] = config`) | **sobrescreve calado**, exit 0 | — |
| **Merge entre escopos** | por servidor inteiro — *"fields are not merged across scopes"* | **não documentado** | coleções separadas com `order`; colisão de *tool* via `chat.mcp.collisionBehavior` (`disable`/`suffix`) | **campo a campo** ⚠️ | **workspace vence usuário**, sem aviso |
| **Precedência** | local → project → user → plugin → connector | não documentada | por `order` da coleção | admin → system → cloud → user → profile → cwd → tree → repo → runtime | workspace > user |
| **Arquivo inválido** | reporta, **mas exit 0** em `mcp list`; mensagem sem linha/coluna | — | `mcp.json`: erro com offset. `.mcp.json`: **`catch { return }`, silêncio total** | erro com **linha e coluna**, exit 1 | **silêncio total**; uma entrada ruim derruba o arquivo inteiro |
| **Escrever sobre arquivo quebrado** | recusa, exit 1, não repara | — | — | recusa, exit 1 | — |

### O merge campo a campo do Codex é a armadilha mais sutil do relatório

A camada de projeto **não substitui o servidor** — ela sobrepõe campo a campo. Medido:

```toml
# ~/.codex/config.toml (máquina)
[mcp_servers.merge_test]
command = "cmd-global"
args = ["a-global"]
startup_timeout_sec = 99
[mcp_servers.merge_test.env]
DO_GLOBAL = "1"
```
```toml
# <repo>/.codex/config.toml (projeto)
[mcp_servers.merge_test]
command = "cmd-projeto"
```
```json
// resultado efetivo
{ "command": "cmd-projeto",     // do projeto
  "args": ["a-global"],          // VAZOU do global
  "env": { "DO_GLOBAL": "1" },   // VAZOU do global
  "startup_timeout_sec": 99.0 }  // VAZOU do global
```

Um `[mcp_servers.git]` que o overpower escreva no repo **não é um `git` limpo** — é um `git` fundido com o que já existia na máquina do usuário. O overpower precisa emitir o conjunto **completo** de campos, ou aceitar herança imprevisível.

### O arquivo commitado sozinho não funciona

Duas descobertas convergentes, e elas mudam o que "instalar um MCP no projeto" significa:

- **Claude Code**: servidor vindo de `.mcp.json` nasce `⏸ Pending approval` e **não conecta**. A matriz de aprovação foi medida inteira: settings de **usuário** (`enableAllProjectMcpServers` / `enabledMcpjsonServers`) aprovam sempre; settings **do projeto** (`.claude/settings.json` e `.claude/settings.local.json`) só valem depois de `hasTrustDialogAccepted: true` — *"a cloned repository can't approve its own servers"*. O "aprovei" mora em `<repo>/.claude/settings.local.json`, **dentro da árvore de trabalho**, em arquivo convencionalmente não rastreado.
- **Codex**: `<repo>/.codex/config.toml` só é carregado se o projeto estiver marcado `trust_level = "trusted"` em `~/.codex/config.toml`. Sem isso, `codex mcp list` diz *"No MCP servers configured yet"* e o `codex doctor` chega a dizer `✓ mcp no MCP servers configured` — **falso positivo**. O `disabled_reason` existe no código, mas nenhum caminho de CLI o exibe.

**Ou seja: o enxerto de projeto é, nos dois casos, duas escritas — uma no repositório e uma na máquina.** Um artefato entregue só no repo é inerte e invisível: nenhuma mensagem, nenhum exit code, nenhum sinal.

---

## As CLIs oficiais não servem como escritor

| CLI | Por quê |
| --- | --- |
| `claude mcp add` | **Não tem `--force`**; duplicata falha com exit 1, exigindo `remove` antes. **Apaga chaves raiz desconhecidas em silêncio** (`$schema` some). `-s project` grava no **CWD**, não na raiz do git. Grava sem newline final |
| `codex mcp add` | **Só escreve global**, mesmo com projeto presente e confiado. `--env` grava o **segredo literal**, e **não existe flag** para emitir `env_vars` — a CLI oficial é o caminho inseguro |
| `code --add-mcp` | Escreve via `JSON.stringify(..., '\t')`: destrói comentários, reescreve `"type": "sse"` para `"http"`, e **deleta o arquivo** se ele ficar sem `servers`/`inputs`/`sandbox` |
| `copilot mcp add` | Grava segredo em texto puro. Reserializa o arquivo, destruindo comentários (medido) |

Some-se o axioma 1 — *o overpower nunca invoca instalador de terceiro* — e a conclusão é dupla: o overpower **tem** de escrever os arquivos ele mesmo, e assume sozinho a responsabilidade de não destruir a configuração do usuário.

---

## O lado do escritor: o que o Python consegue enxertar

Medido nesta máquina (Python 3.12.3; venv de laboratório em 3.14 para o `json-five`).

### TOML: a stdlib não escreve

`tomllib` expõe **apenas** `load`, `loads`, `TOMLDecodeError`. Não tem `dump` nem `dumps`. Escrever a config do Codex **exige dependência de terceiro** — não há caminho stdlib.

Enxertando um servidor `git` num `config.toml` realista (comentários, chaves não-MCP, um servidor preexistente):

**`tomlkit` 0.15.1 — diff puramente aditivo, zero linha do usuário tocada:**
```diff
 [mcp_servers.meu-servidor-antigo]
 command = "node"
 args = ["server.js"]
+
+[mcp_servers.git]
+command = "uvx"
+args = ["mcp-server-git", "--repository", "."]
+
+[mcp_servers.git.env]
+GIT_TOKEN = "${GIT_TOKEN}"
```

**`tomllib` + `tomli-w` 1.2.0 — destrói 3 comentários e reflui um array intocado:**
```diff
-# Configuração pessoal do Codex — NÃO MEXER SEM LER
 model = "gpt-5-codex"
-approval_policy = "on-request"   # confio, mas confiro
+approval_policy = "on-request"
 [mcp_servers.meu-servidor-antigo]
 command = "node"
-args = ["server.js"]
+args = [
+    "server.js",
+]
```

O `config.toml` do Codex **não é um arquivo de MCP** — carrega modelo, política de aprovação, sandbox e perfis. `tomli-w` reescreve tudo isso.

### JSON: a stdlib nem lê JSONC, e escrever gera churn

`json.loads` sobre `.vscode/mcp.json` com um comentário: `JSONDecodeError: Expecting property name enclosed in double quotes`.

Ler com `json5` e escrever com `json.dumps(indent=2)` num `.vscode/mcp.json` de 13 linhas: **13 linhas fora, 31 dentro**. Comentário destruído, tabs viram espaços, arrays inline explodem.

E o pior: **mesmo no melhor caso possível** — `.mcp.json` estrito, sem comentários, `indent=2` idêntico ao do usuário — o diff não é aditivo:

```diff
     "antigo": {
       "command": "node",
-      "args": ["server.js"]
+      "args": [
+        "server.js"
+      ]
+    },
+    "git": { ... }
```

O `git diff` acusa alteração num servidor que o overpower **não tocou**. Isso colide de frente com o axioma 2: *"o git é o manifesto"* só vale se o diff responder exatamente o que a ferramenta escreveu.

### `json-five` 1.1.2: cirúrgico, com duas armadilhas

- Round-trip puro (parse → dump, sem mutação): **byte-idêntico**, comentários e tabs preservados.
- Inserção pela API **óbvia** — `obj.key_value_pairs.append(kvp)` — **falha em silêncio**: exit 0, nenhuma exceção, saída byte-idêntica à entrada, o enxerto some. Causa no fonte (`json5/model.py:165-167`): `key_value_pairs` é `@property` que reconstrói a lista a cada acesso via `zip(self.keys, self.values)`; `.append()` muta um descartável.
- Inserção pela API **correta** (`obj.keys.append` + `obj.values.append`) funciona e o diff é mínimo, mas o texto inserido sai **sem formatação alguma**:
```diff
-	},
+	,"git":{"type":"stdio","command":"uvx","args":["mcp-server-git","--repository","."]}},
```
Formatar exige autorar à mão os nós de whitespace (`wsc_before`/`wsc_after`, `leading_wsc`) de cada nó inserido.
- Armadilha de empacotamento: o pacote PyPI `json-five` instala o **módulo `json5`** — mesmo nome do pacote PyPI `json5`. Os dois no mesmo ambiente é colisão de módulo.

### Resumo do escritor

| | TOML (Codex) | JSON estrito (`.mcp.json`) | JSONC (`.vscode/mcp.json`) |
| --- | --- | --- | --- |
| stdlib lê? | sim (`tomllib`) | sim | **não** |
| stdlib escreve? | **não existe writer** | sim, com churn | não |
| diff aditivo com stdlib | impossível | **não** | impossível |
| dependência que resolve | `tomlkit` (limpo) | `json-five` (cirúrgico, sem formatação) | `json-five` (idem) |

**A tensão honesta**: as ferramentas nativas são piores que `json.dumps` — o VS Code destrói comentários e deleta arquivos vazios, o Claude Code apaga chaves raiz, o Codex apaga comentários dentro de `[mcp_servers.*]`, o Copilot reserializa tudo. Um gerador com `json.dumps` **não é pior que o comportamento nativo**. Mas o overpower tem um requisito que eles não têm: o axioma 2 faz do `git diff` o manifesto. Decidir aqui é escolher entre "não pior que o nativo" e "o diff diz a verdade".

---

## Os dois servidores canônicos, renderizados

O mesmo par em todo formato: um **stdio** (`git`, com slot `GIT_TOKEN`) e um **http** (`github`, com slot `GITHUB_TOKEN` num header `Authorization: Bearer`).

### Claude Code — `.mcp.json` (gerado pela CLI e copiado do disco)

```json
{
  "mcpServers": {
    "git": {
      "type": "stdio",
      "command": "uvx",
      "args": [
        "mcp-server-git",
        "--repository",
        "."
      ],
      "env": {
        "GIT_TOKEN": "${GIT_TOKEN}"
      }
    },
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/",
      "headers": {
        "Authorization": "Bearer ${GITHUB_TOKEN}"
      }
    }
  }
}
```

Validado: o `github` **alcançou o endpoint real da GitHub** e recebeu HTTP 400 do token falso, o que prova que o header saiu montado. *(A CLI grava sem newline final. E a mensagem de confirmação imprime a URL sem a barra final; o disco preserva.)*

O mesmo esquema vale nos escopos `user` (raiz de `~/.claude.json`) e `local` (`projects["<abs>"].mcpServers`), com expansão funcionando idêntica nos três.

### Cursor — `.cursor/mcp.json`

```json
{
  "mcpServers": {
    "git": {
      "type": "stdio",
      "command": "uvx",
      "args": ["mcp-server-git", "--repository", "${workspaceFolder}"],
      "env": {
        "GIT_TOKEN": "${env:GIT_TOKEN}"
      }
    },
    "github": {
      "url": "https://api.githubcopilot.com/mcp/",
      "headers": {
        "Authorization": "Bearer ${env:GITHUB_TOKEN}"
      }
    }
  }
}
```

Três decisões de linha, todas com razão registrada:
- `"type": "stdio"` incluído porque a tabela oficial marca **Required: Yes**, embora nenhum exemplo oficial o traga. A tabela é normativa; os exemplos, ilustrativos.
- **`github` sem `type`** — não existe valor de `type` documentado para remoto no Cursor. `"type": "http"` seria adivinhação.
- **`--repository "."` trocado por `${workspaceFolder}`** — o Cursor não documenta `cwd`, então um `.` relativo tem diretório de trabalho indefinido. Se o requisito for literalmente `"."`, é reversível, mas o comportamento é indefinido.

### VS Code — `.vscode/mcp.json`, variante `${env:}`

```jsonc
{
  // JSONC é válido aqui — mas o VS Code apaga estes comentários se escrever no arquivo.
  "servers": {
    "git": {
      "type": "stdio",
      "command": "uvx",
      "args": ["mcp-server-git", "--repository", "."],
      "env": { "GIT_TOKEN": "${env:GIT_TOKEN}" }
    },
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/",
      "headers": { "Authorization": "Bearer ${env:GITHUB_TOKEN}" }
    }
  }
}
```

Se as variáveis não existirem **no ambiente do processo do VS Code**, o valor vira `""` — sem erro, sem prompt.

### VS Code — `.vscode/mcp.json`, variante `inputs`

```jsonc
{
  "inputs": [
    { "type": "promptString", "id": "git-token",    "description": "GIT_TOKEN",    "password": true },
    { "type": "promptString", "id": "github-token", "description": "GITHUB_TOKEN", "password": true }
  ],
  "servers": {
    "git": {
      "type": "stdio",
      "command": "uvx",
      "args": ["mcp-server-git", "--repository", "."],
      "env": { "GIT_TOKEN": "${input:git-token}" }
    },
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/",
      "headers": { "Authorization": "Bearer ${input:github-token}" }
    }
  }
}
```

Esta é a única variante do espaço inteiro em que o segredo é **guardado com proteção do SO** em vez de apenas referenciado.

### Codex — `<repo>/.codex/config.toml` (forma recomendada, escrita à mão e validada)

```toml
[mcp_servers.git]
command = "uvx"
args = ["mcp-server-git", "--repository", "."]
env_vars = ["GIT_TOKEN"]

[mcp_servers.github]
url = "https://api.githubcopilot.com/mcp/"
bearer_token_env_var = "GITHUB_TOKEN"
```

**Nenhum valor de segredo no arquivo, e a palavra `Bearer` não aparece** — o Codex monta o header sozinho lendo `$GITHUB_TOKEN`. Validado: `codex mcp list` mostra `GIT_TOKEN=*****` e `Auth: Bearer token`.

Contraste com o que a CLI oficial produz — `codex mcp add git --env GIT_TOKEN=... ` grava:
```toml
[mcp_servers.git.env]
GIT_TOKEN = "PLACEHOLDER"   # ← valor literal; não há flag para emitir env_vars
```

E o arquivo precisa da contrapartida na máquina:
```toml
# ~/.codex/config.toml
[projects."/caminho/absoluto/do/repo"]
trust_level = "trusted"
```

### Copilot CLI — `.mcp.json` de workspace (commitável, **sem segredo possível**)

```json
{
  "mcpServers": {
    "git": {
      "type": "local",
      "command": "uvx",
      "args": ["mcp-server-git", "--repository", "."]
    },
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/"
    }
  }
}
```

Os slots **não têm como ser expressos**. O segredo só existe em `~/.copilot/mcp-config.json`, em texto puro:

```json
{
  "mcpServers": {
    "git": {
      "tools": ["*"], "type": "local", "command": "uvx",
      "args": ["mcp-server-git", "--repository", "."],
      "env": { "GIT_TOKEN": "<TOKEN EM TEXTO PURO>" }
    },
    "github": {
      "type": "http", "url": "https://api.githubcopilot.com/mcp/", "tools": ["*"],
      "headers": { "Authorization": "Bearer <TOKEN EM TEXTO PURO>" }
    }
  }
}
```

---

## Divergências entre doc e comportamento medido

| Runtime | A doc diz | Medido |
| --- | --- | --- |
| Claude Code | Seção intitulada *"Environment variable expansion **in `.mcp.json`**"* | Funciona idêntico nos **três** escopos, inclusive dentro de `~/.claude.json`. É propriedade do **loader**, não do arquivo |
| Claude Code | `.mcp.json` fica *"in project root"* | `-s project` grava no **CWD**; a leitura carrega CWD **e** ancestrais |
| Claude Code | apresenta stdio/sse/http/ws como quatro opções | `--transport` aceita só três; `ws` exige `add-json` — e servidores `ws` **não aparecem** em `claude mcp list` |
| Copilot CLI | lê `.mcp.json` *"in any directory from working directory up to repository root"* | **Falso** via `copilot mcp list`. De `proj/sub/deep` com `.mcp.json` na raiz: nenhum servidor de workspace |
| Copilot CLI | lê também `.github/mcp.json` | **Falso**. Arquivo válido em `proj/.github/mcp.json` → nada listado, com e sem repo git |
| Cursor | tabela normativa marca `type` como Required=Yes para stdio | **Nenhum** exemplo oficial da mesma página inclui `type`. A doc se contradiz |
| Cursor | lista SSE como transporte de primeira classe | Sem aviso de deprecação, apesar de a spec ter deprecado em `2025-03-26` |
| Codex | *"Project-scoped overrides can be added in `.codex/config.toml`"* | Verdade, **mas** só com `trust_level = "trusted"`; sem isso, `codex doctor` reporta `✓ no MCP servers configured` — falso positivo |

---

## Armadilhas, por quanto doem

1. **Assumir que existe um formato base e os outros são dialetos.** Não existe. Renderizador por alvo é obrigatório.
2. **Reusar a sintaxe de interpolação entre alvos.** `${VAR}` (Claude Code) ≠ `${env:VAR}` (Cursor, VS Code) ≠ `env_vars` (Codex) ≠ nada (Copilot). Erra e falha em **runtime**, não em parse.
3. **Assumir default de variável.** Só o Claude Code tem `${VAR:-x}`. No VS Code `${env:X:-y}` vira **string vazia** em silêncio. Se o overpower quer default, resolve **no momento da geração**.
4. **Escolher `.mcp.json` como formato comum** aos três runtimes que o leem — custa o mecanismo de segredo inteiro do VS Code e do Copilot.
5. **Chave raiz errada.** `mcpServers` no VS Code é arquivo válido-como-JSON e **inerte**. `mcpServers` camelCase no Codex é **descartado em silêncio, exit 0** — e `--strict-config` não funciona em `codex mcp`.
6. **Merge de camada campo a campo no Codex.** Emitir o conjunto completo de campos, sempre.
7. **`sse` no Codex vira streamable HTTP calado.** Recusar SSE na origem.
8. **Entregar só o arquivo commitado.** Claude Code exige aprovação; Codex exige trust. Sem a segunda escrita, o artefato é inerte e invisível.
9. **Variável ausente sem default no Claude Code vaza a string crua na rede.** Tratar o aviso `Missing environment variables` como erro.
10. **`inputs` sem `password: true`** grava o valor em **texto puro** no `state.vscdb`.
11. **`json.dumps` reescreve o arquivo inteiro**, e `tomli-w` apaga comentários. O `git diff` deixa de dizer a verdade.
12. **`json-five`: `key_value_pairs.append()` falha calada.** Exit 0, saída idêntica, enxerto sumiu.
13. **Um erro derruba o arquivo inteiro no Copilot CLI**, sem mensagem — não é degradação parcial.
14. **`claude mcp list` sai 0 com JSON quebrado.** Inútil como gate de CI.
15. **Reescrever `.mcp.json` pela CLI do Claude Code apaga chaves raiz desconhecidas** (`$schema` some, sem aviso).
16. **`.codex/` não é gitignorado por padrão**, e `env`/`http_headers` aceitam literais. É fácil commitar segredo por acidente.
17. **O prompt de trust do `.mcp.json` no VS Code é `TrustedOnNonce`** — o nonce é o hash do launch. Um gerador que reescreva o arquivo a cada build faz o usuário reaprovar **todo servidor, toda vez**.
18. **No Remote-WSL há dois `mcp.json` de usuário** (Windows local e servidor Linux remoto). Escrever no errado é não-op silencioso.
19. **`--transport stdio` do Copilot grava `"type": "local"`.** O vocabulário de escrita difere do de leitura.
20. **`mcp` dentro de `settings.json` do VS Code está em migração ativa** — a ferramenta avisa e **remove** o bloco. Não é alvo válido de geração.
21. **O servidor stdio do Claude Code herda o ambiente inteiro** da sessão, não só o bloco `env`.

---

## O que isso entrega para os tickets seguintes

**Para a regra 4 do modelo de domínio** — ela está **confirmada e endurecida**. Mas a pesquisa mostra que o contrato lógico não pode carregar a *string* do slot (`"${GITHUB_TOKEN}"`), porque a sintaxe é diferente em cada alvo e um alvo não tem sintaxe nenhuma. O contrato tem de carregar o **nome** do slot e o papel dele (variável de ambiente do processo? header bearer? header arbitrário?), e o renderizador decide a forma. Um contrato que guardasse `${GITHUB_TOKEN}` quebraria no Cursor, no VS Code e no Codex de três jeitos diferentes.

**Para o axioma 2 (sem estado no alvo)** — o enxerto de projeto é **duas escritas**, uma no repo e uma na máquina, nos dois runtimes que têm gate (Claude Code e Codex). A escrita de máquina não fere o axioma (não é o alvo), mas significa que "instalar um MCP no projeto" não é uma operação atômica no repositório, e que o `git diff` **não conta a história inteira** desse artefato — pela primeira vez no projeto.

**Para o formato do catálogo ([#10](https://github.com/ThiagoPanini/overpower/issues/10))** — se um dia o catálogo descrever enxertos, o campo não é "conteúdo do fragmento", é uma **declaração lógica**: transporte, comando/url, e a lista de slots com o papel de cada um. E precisa de um eixo que ainda não existe no vocabulário: **quais alvos esse artefato consegue atender**, porque `ws` só existe no Claude Code e segredo em `.mcp.json` compartilhado não existe em lugar nenhum.

**Para a semântica de escrita ([#9](https://github.com/ThiagoPanini/overpower/issues/9))** — aquela decisão fixou escrita **incondicional** para colisão de **caminho** (cópia). Para colisão de **chave** (enxerto) ela não vale automaticamente: o Claude Code **recusa** duplicata, o Codex e o VS Code **sobrescrevem calados**, e o arquivo é do usuário. Sobrescrever a chave de um servidor homônimo do dev é destruir configuração que não é nossa.

**Para a integridade de referência cruzada ([#16](https://github.com/ThiagoPanini/overpower/issues/16))** — o ticket pergunta se a dependência vale para enxerto. Vale, e com um agravante que a cópia não tem: um artefato de enxerto pode depender de um **slot preenchido**, não de outro artefato. O `codex doctor` já faz essa verificação de graça, e é o único runtime que faz.

**Sobre `server.json` do registro oficial** — ele é normativo e resolve **outro** problema: é template de publicação, não config de cliente. A tabela do SEP-2633 formaliza a divisão: `server.json` é *"highly configurable — variables, templates"*, o arquivo do cliente é *"fully resolved — only auth secrets remain as interpolatable variables"*. **Não serve como formato de saída do overpower, mas é o modelo interno certo**: um artefato de enxerto de MCP é conceitualmente um `server.json` resolvido, renderizado para N dialetos. Ele já tem o campo `isSecret` em `environmentVariables[]` e `headers[]` — exatamente o conceito de slot que a regra 4 precisa.

---

## Onde a evidência é fraca

Listado sem maquiagem.

1. **Cursor não foi medido.** Não está instalado. Toda a fatia é doc do fornecedor, sem checagem cruzada com implementação (o Cursor é closed source).
2. **Se `.cursor/mcp.json` é destinado ao git, a doc não diz.** Zero ocorrências de `version control`, `commit`, `source control` ou `gitignore` na página inteira. A conclusão "versionável, segredo por `${env:}`" é inferência a partir de três fatos documentados.
3. **Precedência de merge projeto × global no Cursor: não documentada.** Nem quem ganha, nem se somam, nem colisão de nomes.
4. **Se o Cursor aceita `type: "http"` em entrada remota: desconhecido.** A recomendação de omitir é conservadora, não verificada.
5. **Limite de ferramentas do Cursor: não confirmado.** Não está na doc; só em fórum, que não é fonte primária. Relatos de 2026 sugerem 80, com cap diferente na CLI. Se existir, um bundle grande pode fazer ferramentas **sumirem em silêncio**.
6. **`code --add-mcp` não foi executado** (justificativa no Método). O comportamento de escrita do VS Code vem do fonte.
7. **O prompt de trust de pasta do Copilot CLI não foi medido** — exige sessão autenticada. Onde o consentimento fica gravado não foi verificado.
8. **A ausência de gate de consentimento por projeto no Cursor é conclusão por ausência na doc**, não afirmação da doc. Um teste com o Cursor instalado resolve em cinco minutos.
9. **SEP-2633 é draft, PR aberto.** Citado como **evidência de que o padrão não existe** — esse uso é sólido. Usá-lo como formato-alvo seria erro.
10. **A tabela de divergências de `type` para RooCode/Cline, Goose e LangChain** vem do survey do SEP-2633, que é fonte do repo da spec mas é levantamento de terceiro sobre esses clientes.
11. **`~/.agents/mcp-settings.json` foi descartado, não refutado.** Verificado que Cursor, Codex e VS Code não o documentam; não varri runtimes menores (Gemini CLI, Amp, Factory, Kiro).

---

## Nota de segurança, fora do escopo do ticket

Durante a medição foi lido um exemplo real nesta máquina — `panlabs-tech/ethitorial/.vscode/mcp.json` — e ele contém um **`COOLIFY_ACCESS_TOKEN` em texto puro**. Se esse arquivo estiver versionado, o token está no git. É exatamente o modo de falha que a regra 4 existe para evitar.

---

## Adendo 2026-08-13 — Devin CLI, e nada aqui é medido

O ticket original não cobria o Devin, e a spec de MCP o escolheu como alvo. Este adendo levanta o que a doc oficial diz, e **não** o promove ao mesmo grau de confiança do resto do documento: o binário `devin` **não estava nesta máquina** quando este adendo foi escrito (`claude 2.1.231`, `code 1.132.1`, `copilot 1.0.78` e `codex 0.144.6` estavam; `devin` e `cursor` não), e a CLI exige conta para sessão de agente. **Evidência: doc do fornecedor, lida direto** — [`docs.devin.ai/cli/extensibility/mcp/configuration`](https://docs.devin.ai/cli/extensibility/mcp/configuration) e [`.../mcp/overview`](https://docs.devin.ai/cli/extensibility/mcp/overview). É a mesma classe de evidência do Cursor, que este documento já lista entre as fraquezas.

*(Ver § "Medição 2026-08-14" logo abaixo: o binário foi instalado depois, e duas das linhas da tabela ganharam grau **medido**. O resto fica como estava, com a lacuna marcada onde a conta bloqueou.)*

| Campo | Devin CLI |
| --- | --- |
| **Arquivo de projeto** (commitável) | `.devin/mcp_config.json` |
| **Arquivo de projeto, gitignored** | `.devin/mcp_config.local.json` — *"keep tokens out of committed config"*, convenção do próprio fornecedor |
| **Arquivo de máquina** | `~/.config/devin/mcp_config.json` (`%APPDATA%\devin\mcp_config.json` no Windows) |
| **Chave raiz** | `mcpServers` |
| **stdio: campos** | `command`, `args`, `env`, `disabled` |
| **http: campos** | `url`, `transport`, `headers`, `oauthClientId`, `oauthClientSecret`, `oauthResource`, `disabled` |
| **Discriminação de transporte** | `transport` = `"http"` (default) ou `"sse"`; stdio inferido por `command` |
| **Transportes** | stdio, Streamable HTTP, SSE (legado). **Sem `ws`** |
| **Mecanismo de segredo** | interpolação na leitura: `${env:VAR}` — **mais `${file:/path}`**, que nenhum outro alvo tem |
| **Default** | nenhum documentado |
| **Precedência** | local → projeto → usuário |
| **OAuth** | `devin mcp login <server>`, fluxo de browser |
| **Gate para o arquivo de projeto valer** | **medido: nenhum, para leitura/listagem** — ver § "Medição 2026-08-14" |
| **Chave raiz errada ou campo desconhecido** | **medido: falha calada, exit 0** — ver § "Medição 2026-08-14" |

Duas notas que mudam o desenho e que só a medição fecha:

- **A grafia é a do Cursor e do VS Code**, `${env:VAR}`, e não a do Claude Code. Terceira grafia num trio de três alvos — a regra 4 sai daqui mais firme, não menos.
- **`${file:/path}`** é mecanismo que não existe em nenhum outro alvo medido: o segredo mora num arquivo do disco e a config carrega só o caminho.

**As três dúvidas que a doc não fecha** — registradas abertas nesta data, e fechadas na medida do possível no dia seguinte (§ abaixo):

1. **Se `${env:}` vale em `command`/`args`.** A doc cita a expansão *"para campos sensíveis como `oauthClientSecret` e `oauthResource`"*. Se o alcance for só esse, um `env` com slot chega **cru** ao processo — que é exatamente o modo de falha medido no Copilot CLI. **Segue aberta** — o processo do servidor MCP só nasce dentro de uma sessão de agente, e a sessão exige login.
2. **Se existe portão de confiança para `.devin/mcp_config.json`.** Ausência na doc **não é** afirmação de ausência: o Codex também não documentava `trust_level`, e sem ele o `codex doctor` reporta `✓ no MCP servers configured` — falso positivo. **Parcialmente fechada** — ler e listar o arquivo não passa por portão nenhum; se o portão existir para o *uso* do servidor (spawn do processo), fica sem verificação pela mesma razão da dúvida 1.
3. **O que ele faz com chave raiz errada ou campo desconhecido.** É onde Codex e Copilot CLI falham **calados, com exit 0**, e onde o Claude Code falha alto. **Fechada** — o Devin fica do lado calado, e do jeito mais extremo do grupo: até JSON malformado sai como `"No MCP servers configured"`, exit 0, indistinguível de "nunca houve arquivo".

---

## Medição 2026-08-14 — as três dúvidas do Devin, na medida do possível

O binário instala sem conta: `curl -fsSL https://cli.devin.ai/install.sh | bash` baixa um bundle assinado (checksum sha256 contra manifesto), verificado, e o resultado é `devin 3000.4.25` funcional para os subcomandos que não tocam LLM. **Método**: instalado numa sandbox com `HOME`/`XDG_DATA_HOME` redirecionados para um diretório descartável — nunca contra a configuração real desta máquina, mesmo padrão usado para Codex e Copilot CLI em outras seções deste documento. Nenhuma conta foi criada.

`devin mcp list`, `devin mcp get <nome>` e `devin mcp add` leem e escrevem `.devin/mcp_config.json`/`mcp_config.local.json` diretamente, sem exigir login e sem qualquer prompt de confiança — isso é o que a dúvida 2 mede. Já **iniciar uma sessão de agente** (`devin -p "..."`, com ou sem `--respect-workspace-trust false`) falha primeiro em `Error: Login canceled`, antes de qualquer coisa relacionada a MCP ou a confiança de workspace — é o portão que fecha a dúvida 1 e a metade não medida da dúvida 2: o processo do servidor stdio só nasce depois desse login, então se `${env:}` expande em `command`/`args` no processo filho é observação que exige conta real, não disponível aqui.

**Achado adjacente, não uma das três dúvidas mas relevante para elas**: `devin --help`/`man devin` documentam uma flag `--respect-workspace-trust` (default `true`) — um mecanismo de confiança de workspace **existe no binário e não está em nenhuma página da doc pública consultada**. Se ele se estende à leitura ou ao spawn do MCP não foi possível confirmar: `mcp list`/`get`/`add` não o disparam (testado numa pasta nunca antes vista pelo Devin), e a sessão completa — o único caminho que poderia disparar o spawn do servidor — está atrás do login.

**Dúvida 3, medida com quatro variações do arquivo de projeto**, todas com `devin mcp list` depois:

| Variação | Resultado |
| --- | --- |
| Campo desconhecido dentro da entrada do servidor (`"totallyUnknownField": "surprise"`) | Servidor lista normal, campo ignorado, exit 0 |
| Chave desconhecida na raiz, ao lado de `mcpServers` válido | `mcpServers` lista normal, chave extra ignorada, exit 0 |
| Chave raiz errada (`"servers"` em vez de `"mcpServers"`) | `"No MCP servers configured. Use 'devin mcp add' to add servers."`, exit 0 |
| JSON malformado (`{ this is not json`) | **Mesma mensagem** de "nenhum servidor configurado", exit 0 |

A última linha é o caso mais caro: um arquivo quebrado por erro de sintaxe e um arquivo genuinamente vazio produzem a mesma tela. O Devin não só falha calado — ele **normaliza erro de sintaxe em ausência**, o que nem Codex nem Copilot CLI fazem (ambos ao menos preservam a distinção entre "não configurado" e "configurado errado", mesmo quando não avisam alto). Confirma e reforça, não apenas confirma, a hipótese que a dúvida 3 registrava.

`devin mcp get` também revelou um comportamento de exibição sem relação direta com as três dúvidas mas que interessa à regra 4: valores do mapa `env` saem redigidos (`<redacted>`) por padrão, `command`/`args` não — e nenhum dos dois resolve `${env:VAR}` na exibição, o valor sai literal. Não decide a dúvida 1 (isso é comportamento de *display*, não de *spawn*), mas mostra que, se a expansão *não* alcançar `command`/`args` no processo filho, ela ao menos não vaza pela listagem.
