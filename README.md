# overpower

A CLI that installs curated **AI Frameworks** — named bodies of agent equipment
from a single upstream — into a repository or onto a machine.

```bash
uvx overpower@latest install --ai-framework matt-pocock --runtime claude-code,cursor
```

Three commands, and they answer three questions. `list` says what there is.
`install` writes it. `doctor` says whether what was written is still what was
written. Every item — a skill, a bundle, an AI Framework, an MCP server — prints
whole, never truncated, with the exact line that installs it:

```
╭─ Bundles  lists pool artifacts only ─────────────────────╮
│                                                          │
│  api-python                         229.0 KiB · 8 files  │
│    Equipment for working on a Python API.                │
│                                                          │
│      overpower install --bundle api-python               │
│      overpower list --bundle api-python                  │
│                                                          │
╰──────────────────────────────────────────────────────────╯
```

Full documentation — every command, every flag, the runtime table, how content
is curated and how a release ships — lives at
**[thiagopanini.github.io/overpower](https://thiagopanini.github.io/overpower/)**.
