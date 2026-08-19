---
title: Targets
description: The 77 runtimes, the two scopes, and where each artifact lands on disk.
---

# Targets

Where a skill lands is a function of three things: the artifact type, the runtime you named, and the scope you are writing in. This page covers the last two.

## The two scopes

**Project** is the default, and it only applies inside a git repository — outside one, a plain flag line refuses, exit `2`, because the rule this product follows is that *the git is the manifest*: nothing else on a machine can audit what a silent write left behind. **Global** (`--global` / `-g`) writes under the home directory instead, and needs no git at all.

The two scopes are not the same operation at a different root — they write differently.

In **project** scope, every landing is a real copy, never a symlink. This is deliberate: under `core.symlinks=false` — a git config value that a clone can inherit silently — a committed symlink checks out as an ordinary text file instead of a link, and the equipment would be broken for anyone who cloned it. Copying sidesteps that failure mode entirely, and `git status` is the safety net that makes an unwanted copy easy to see and undo.

In **global** scope, each selection climbs a small ladder: the first destination in the runtime table's own order receives a real copy, and every destination after it becomes a **relative symlink** pointing at that first copy — relative, specifically so the link keeps working if `$HOME` itself moves. On Windows, the same role is filled by a junction, which needs no elevated privilege to create. Where neither a symlink nor a junction can be created, the write silently degrades to a second real copy instead, prints a warning saying so, and still exits `0` — nothing is lost either way, only the space saved by linking.

`--force` / `-f` belongs to global scope alone. Project scope has `git status` to reveal or undo an unwanted overwrite; global scope has nothing like it, so a destination that already exists there is refused instead of clobbered — in a terminal it asks first, off one (or under `--yes` or `--dry-run`) it refuses outright, exit `3`, since there is no one to ask. `--force` skips that question either way and overwrites without asking.

## The universal group

Several runtimes read the exact same directory. In **project** scope, 19 of the 77 runtimes — including the synthetic `universal` key itself — read `.agents/skills`, which makes it the single largest shared destination, though not, despite the name, a path that reaches every runtime: measured against Claude Code 2.1.223, it does not discover skills there, and Codex does not read `.claude/skills` either. In **global** scope the same group shrinks to 6: `cline`, `dexto`, `kimi-code-cli`, `loaf`, `warp`, and `zed` all read `~/.agents/skills`, while `amp` reads `~/.config/agents/skills` on its own XDG-derived path, `codex` reads `~/.codex/skills`, and `cursor` reads `~/.cursor/skills` — three runtimes that happen to share the project-scope folder but keep separate global homes.

The plan always names every destination and who reads it, so a selection landing in a shared folder is shown as one write serving several runtimes, never as a promise of one install per runtime.

## The runtime table

77 rows: 76 transcribed from the upstream `vercel-labs/skills` project's own runtime map (attributed in `NOTICE`), plus `vscode`, which has no skill destination in either scope and exists in this table purely so the MCP graft step of the wizard has a name for it — see [MCP servers](/targets/mcp). 74 of the 77 have a destination in global scope; `eve`, `promptscript`, and `vscode` do not, so asking for one of those three under `--global` is a valid line with a negative answer, exit `3`, rather than an invalid one.

Global paths below use `~` for the home directory. Several are actually resolved through an environment variable first, falling back to the path shown only when that variable is unset: `claude-code` honours `CLAUDE_CONFIG_DIR`, `codex` honours `CODEX_HOME`, `autohand-code` honours `AUTOHAND_HOME`, `grok` honours `GROK_HOME`, `hermes-agent` honours `HERMES_HOME`, and `mistral-vibe` honours `VIBE_HOME`. Six more — `amp`, `devin`, `goose`, `opencode`, `replit`, and `universal` — resolve through `XDG_CONFIG_HOME`, falling back to `~/.config`. `crush` and `kimchi` also land under `~/.config`, but transcribed exactly as upstream wrote them, they read it as a literal path and do **not** honour `XDG_CONFIG_HOME` — the one place this table's fidelity to upstream produces an inconsistency rather than resolving it. `openclaw` checks three candidate directories (`~/.openclaw`, `~/.clawdbot`, `~/.moltbot`) for whichever already exists before falling back to the first.

| Runtime (`--runtime` key) | Project scope | Global scope |
| --- | --- | --- |
| `aider-desk` — AiderDesk | `.aider-desk/skills` | `~/.aider-desk/skills` |
| `amp` — Amp | `.agents/skills` | `~/.config/agents/skills` |
| `antigravity` — Antigravity | `.agents/skills` | `~/.gemini/antigravity/skills` |
| `antigravity-cli` — Antigravity CLI | `.agents/skills` | `~/.gemini/antigravity-cli/skills` |
| `astrbot` — AstrBot | `data/skills` | `~/.astrbot/data/skills` |
| `autohand-code` — Autohand Code CLI | `.autohand/skills` | `~/.autohand/skills` |
| `augment` — Augment | `.augment/skills` | `~/.augment/skills` |
| `bob` — IBM Bob | `.bob/skills` | `~/.bob/skills` |
| `claude-code` — Claude Code | `.claude/skills` | `~/.claude/skills` |
| `openclaw` — OpenClaw | `skills` | `~/.openclaw/skills` |
| `cline` — Cline | `.agents/skills` | `~/.agents/skills` |
| `codearts-agent` — CodeArts Agent | `.codeartsdoer/skills` | `~/.codeartsdoer/skills` |
| `codebuddy` — CodeBuddy | `.codebuddy/skills` | `~/.codebuddy/skills` |
| `codemaker` — Codemaker | `.codemaker/skills` | `~/.codemaker/skills` |
| `codestudio` — Code Studio | `.codestudio/skills` | `~/.codestudio/skills` |
| `codex` — Codex | `.agents/skills` | `~/.codex/skills` |
| `command-code` — Command Code | `.commandcode/skills` | `~/.commandcode/skills` |
| `continue` — Continue | `.continue/skills` | `~/.continue/skills` |
| `cortex` — Cortex Code | `.cortex/skills` | `~/.snowflake/cortex/skills` |
| `crush` — Crush | `.crush/skills` | `~/.config/crush/skills` |
| `cursor` — Cursor | `.agents/skills` | `~/.cursor/skills` |
| `deepagents` — Deep Agents | `.agents/skills` | `~/.deepagents/agent/skills` |
| `devin` — Devin for Terminal | `.devin/skills` | `~/.config/devin/skills` |
| `dexto` — Dexto | `.agents/skills` | `~/.agents/skills` |
| `droid` — Droid | `.factory/skills` | `~/.factory/skills` |
| `eve` — Eve | `agent/skills` | — |
| `firebender` — Firebender | `.agents/skills` | `~/.firebender/skills` |
| `forgecode` — ForgeCode | `.forge/skills` | `~/.forge/skills` |
| `gemini-cli` — Gemini CLI | `.agents/skills` | `~/.gemini/skills` |
| `github-copilot` — GitHub Copilot | `.agents/skills` | `~/.copilot/skills` |
| `goose` — Goose | `.goose/skills` | `~/.config/goose/skills` |
| `grok` — Grok Build | `.grok/skills` | `~/.grok/skills` |
| `hermes-agent` — Hermes Agent | `.hermes/skills` | `~/.hermes/skills` |
| `inference-sh` — inference.sh | `.inferencesh/skills` | `~/.inferencesh/skills` |
| `jazz` — Jazz | `.jazz/skills` | `~/.jazz/skills` |
| `junie` — Junie | `.junie/skills` | `~/.junie/skills` |
| `iflow-cli` — iFlow CLI | `.iflow/skills` | `~/.iflow/skills` |
| `kilo` — Kilo Code | `.kilocode/skills` | `~/.kilocode/skills` |
| `kimchi` — Kimchi | `.kimchi/skills` | `~/.config/kimchi/harness/skills` |
| `kimi-code-cli` — Kimi Code CLI | `.agents/skills` | `~/.agents/skills` |
| `kiro-cli` — Kiro CLI | `.kiro/skills` | `~/.kiro/skills` |
| `kode` — Kode | `.kode/skills` | `~/.kode/skills` |
| `lingma` — Lingma | `.lingma/skills` | `~/.lingma/skills` |
| `loaf` — Loaf | `.agents/skills` | `~/.agents/skills` |
| `mcpjam` — MCPJam | `.mcpjam/skills` | `~/.mcpjam/skills` |
| `minimax-code` — MiniMax Code | `.minimax/skills` | `~/.minimax/skills` |
| `mistral-vibe` — Mistral Vibe | `.vibe/skills` | `~/.vibe/skills` |
| `moxby` — Moxby | `.moxby/skills` | `~/.moxby/skills` |
| `mux` — Mux | `.mux/skills` | `~/.mux/skills` |
| `opencode` — OpenCode | `.agents/skills` | `~/.config/opencode/skills` |
| `openhands` — OpenHands | `.openhands/skills` | `~/.openhands/skills` |
| `ona` — Ona | `.ona/skills` | `~/.ona/skills` |
| `pi` — Pi | `.pi/skills` | `~/.pi/agent/skills` |
| `qoder` — Qoder | `.qoder/skills` | `~/.qoder/skills` |
| `qoder-cn` — Qoder CN | `.qoder/skills` | `~/.qoder-cn/skills` |
| `qwen-code` — Qwen Code | `.qwen/skills` | `~/.qwen/skills` |
| `replit` — Replit | `.agents/skills` | `~/.config/agents/skills` |
| `reasonix` — Reasonix | `.reasonix/skills` | `~/.reasonix/skills` |
| `rovodev` — Rovo Dev | `.rovodev/skills` | `~/.rovodev/skills` |
| `roo` — Roo Code | `.roo/skills` | `~/.roo/skills` |
| `tabnine-cli` — Tabnine CLI | `.tabnine/agent/skills` | `~/.tabnine/agent/skills` |
| `terramind` — Terramind | `.terramind/skills` | `~/.terramind/skills` |
| `tinycloud` — Tinycloud | `.tinycloud/skills` | `~/.tinycloud/skills` |
| `trae` — Trae | `.trae/skills` | `~/.trae/skills` |
| `trae-cn` — Trae CN | `.trae/skills` | `~/.trae-cn/skills` |
| `warp` — Warp | `.agents/skills` | `~/.agents/skills` |
| `windsurf` — Windsurf | `.windsurf/skills` | `~/.codeium/windsurf/skills` |
| `zed` — Zed | `.agents/skills` | `~/.agents/skills` |
| `zcode` — ZCode | `.zcode/skills` | `~/.zcode/skills` |
| `zencoder` — Zencoder | `.zencoder/skills` | `~/.zencoder/skills` |
| `zenflow` — Zenflow | `.zencoder/skills` | `~/.zencoder/skills` |
| `neovate` — Neovate | `.neovate/skills` | `~/.neovate/skills` |
| `pochi` — Pochi | `.pochi/skills` | `~/.pochi/skills` |
| `promptscript` — PromptScript | `.agents/skills` | — |
| `adal` — AdaL | `.adal/skills` | `~/.adal/skills` |
| `vscode` — VS Code | — | — |
| `universal` — Universal | `.agents/skills` | `~/.config/agents/skills` |

`vscode` has no row in either column here because it is not a skill destination at all — it exists in the table only for the MCP graft, which reads and writes `.vscode/mcp.json` and nothing under `skills/`. `universal` is not a real tool; it is a synthetic key naming the shared `.agents/skills` destination directly, for when you want to equip that folder without naming every runtime that happens to read it.
