# Anatomia dos AI Frameworks candidatos

**Ticket**: [#6](https://github.com/panlabs-tech/overpower/issues/6) · **Data da pesquisa**: 2026-07-30 · **Idioma**: pt-BR

## Método e nível de evidência

Toda afirmação aqui vem de **fonte primária**: o repositório clonado, o arquivo de licença lido
byte a byte, o `pyproject.toml`/`package.json` do próprio projeto, ou o **instalador upstream
executado de verdade** contra um diretório vazio, com o resultado inventariado. Nenhum resumo de
terceiro foi usado como evidência de fato técnico. As buscas na web serviram só para **localizar**
o repositório canônico (caso do GSD) e para a varredura; o fato em si foi sempre reconferido na origem.

Commits exatos usados como base (clones `--depth 1` em 2026-07-30):

| Repo | HEAD | Data do HEAD |
| --- | --- | --- |
| `mattpocock/skills` | `2ab9580` | 2026-07-28 |
| `github/spec-kit` | `5e2f9bc` (v0.15.1.dev0) | 2026-07-31 |
| `bmad-code-org/BMAD-METHOD` | `9b672e1` (v6.10.0) | 2026-07-29 |
| `gsd-build/get-shit-done` | `bdcaab2` | 2026-05-31 |
| `open-gsd/gsd-core` | `7372d99` (v1.8.0) | 2026-07-30 |
| `obra/superpowers` | `44c9b2d` (v6.2.0) | 2026-07-27 |
| `Fission-AI/OpenSpec` | `1da6dfa` (v1.7.0) | 2026-07-31 |
| `buildermethods/agent-os` | `cae8e66` (v3.0) | 2026-05-05 |
| `anthropics/skills` | `b29e7cf` | 2026-07-24 |

### Correção de unidade: `du` não é tamanho de conteúdo

A cartografia registrou `mattpocock/skills` como **~948 KB**. Esse número é `du -sh skills/`, ou seja
**blocos de disco**, não bytes de conteúdo. Somando os bytes reais dos 113 arquivos sob `skills/`:
**280.346 bytes ≈ 274 KiB**. A diferença de 3,4× é padding de bloco de 4 KiB sobre muitos arquivos
pequenos — exatamente o perfil de um repo de skills.

Isso importa **diretamente para o orçamento do wheel**: um wheel é um ZIP, e o que conta é o byte
de conteúdo, não o bloco. **Todos os tamanhos deste documento são somas de bytes reais**, medidas
com `os.path.getsize`, excluindo `.git/`. Onde o `du` diverge de forma relevante, a divergência está
anotada.

---

## Tabela comparativa

Tamanho = bytes de conteúdo do que seria **vendorizado** (o subconjunto útil), e entre parênteses o
repo inteiro. "Aterrissa" = o que o instalador upstream de fato escreveu no alvo, medido.

| Framework | Origem | Licença SPDX (onde está declarada) | Tamanho vendorizável | O que contém | Como instala (canônico) | Aterrissa (Claude Code) | Estado proprietário no alvo | Reimplementar em Python |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **mattpocock/skills** | `github.com/mattpocock/skills` | **MIT** — `/LICENSE` (© 2026 Matt Pocock), `package.json:license`, `.claude-plugin/plugin.json:license`, API GitHub `spdx_id: MIT` | **274 KiB** / 113 arq. (repo: 471 KiB / 167 arq.) | 41 skills em 6 categorias (22 "promovidas"); 68 `.md`, 41 `.yaml`, 3 `.sh`, 1 `.cjs` | `claude plugins install mattpocock-skills` **ou** `npx skills@latest add mattpocock/skills` | `.claude/skills/<nome>/` — **achatado**, categoria descartada; 41 dirs / 108 arq. / 265 KiB | `skills-lock.json` na raiz (via `npx skills`); **nenhum** via plugin | **Trivial** — cópia recursiva byte-idêntica, verificado por `diff` |
| **github/spec-kit** | `github.com/github/spec-kit` | **MIT** — `/LICENSE` (© GitHub, Inc.), API GitHub `spdx_id: MIT`. ⚠️ **Sem metadado de licença no PyPI** | **~290 KiB** (`templates/` 146 KiB + `scripts/` 144 KiB); wheel PyPI inteiro = **756 KiB** (repo: 10,2 MiB / 530 arq.) | Ferramenta Python (`[project.scripts] specify`) + `core_pack` embutido no wheel: 5 templates de página, 10 templates de comando, scripts sh/ps/py, 4 extensions, 1 workflow, 2 presets | `uv tool install specify-cli` → `specify init <proj> --integration claude` | `.claude/skills/speckit-*/SKILL.md` ×10 + `.specify/{templates,scripts/bash,memory,workflows,integrations}`; 28 arq. / 213 KiB | `.specify/init-options.json`, `.specify/integration.json`, `.specify/integrations/*.manifest.json` | **Média** — transformação determinística e documentada (ver §2.4); custo real é a tabela de **37 integrações** |
| **BMAD-METHOD** | `github.com/bmad-code-org/BMAD-METHOD` | **MIT** — `/LICENSE` (© 2025 BMad Code, LLC) com **aviso de marca anexado**; `package.json:license: MIT`; `.claude-plugin/marketplace.json:license: MIT`; npm `bmad-method@6.10.0` = MIT. API GitHub diz `NOASSERTION` **por causa do anexo** (ver §3.1). Marcas **fora** da MIT (`TRADEMARK.md`) | **1,64 MiB** / 275 arq. (`src/`) (repo: 6,89 MiB / 619 arq.) | 50 `SKILL.md`, 197 `.md`, 38 `.toml`, 26 `.py`, 5 `.csv`; 2 módulos (`core`, `bmm`) + 5 módulos oficiais externos | `npx bmad-method install` (Node ≥20.12 + Python ≥3.10 + **uv**) | `.claude/skills/` 46 skills / 234 arq. / 1,58 MiB + `_bmad/` 16 arq. / 96 KiB + `_bmad-output/` + `docs/` | `_bmad/_config/manifest.yaml`, `files-manifest.csv` (sha256 por arquivo), `skill-manifest.csv`, `_bmad/config.toml` gerado das respostas do instalador | **Alta** — config gerada por entrevista, `customize.toml` por skill, e os skills **chamam `uv run _bmad/scripts/*.py` em runtime** |
| **GSD** (`open-gsd/gsd-core`) | `github.com/open-gsd/gsd-core` — **o repo antigo `gsd-build/get-shit-done` está ARQUIVADO** (§4.1) | **MIT** — `/LICENSE` (© 2026 Open GSD), `package.json:license: MIT`, API GitHub `spdx_id: MIT` | **4,8 MiB** mínimo (`gsd-core/` 3,63 MiB + `agents/` 0,66 + `commands/` 0,16 + `hooks/` 0,19 + `skills/` 0,16) (repo: 32,9 MiB / 2680 arq.) | 71 skills, 71 commands, 34 agents, 29 hooks JS, 13 scripts, runtime `gsd-core/` (307 arq.) | `npx @opengsd/gsd-core@latest` (Node ≥22). README: *"o instalador é obrigatório — **não copie arquivos de `agents/` ou `commands/` diretamente**"* | **7,74 MiB / 614 arq.**, tudo sob `.claude/` | `gsd-file-manifest.json` (67 KiB), `gsd-install-state.json` (motor de migração com checksums), `.gsd-profile`, `package.json`; **e reescreve `.claude/settings.local.json`** | **Proibitivo** — registra **15 hooks em 7 eventos** com **caminho absoluto do binário `node`** embutido; exige Node ≥22 em runtime |
| *(varredura)* **obra/superpowers** | `github.com/obra/superpowers` | **MIT** — `/LICENSE` (© 2025 Jesse Vincent), `.claude-plugin/plugin.json:license: MIT` | **343 KiB** / 50 arq. (`skills/`) (repo: 1,52 MiB / 180 arq.) | 14 skills + `hooks/` + manifests para 5 ecossistemas (`.claude-plugin`, `.codex-plugin`, `.cursor-plugin`, `.kimi-plugin`, `gemini-extension.json`) | `/plugin install superpowers@claude-plugins-official` | `.claude/skills/<nome>/` (via plugin, gerido pelo runtime) | Nenhum no modo plugin | **Baixa** — cópia de árvore; o extra é o hook de `SessionStart` |
| *(varredura)* **Fission-AI/OpenSpec** | `github.com/Fission-AI/OpenSpec` | **MIT** — `/LICENSE` (© 2024 OpenSpec Contributors), `package.json:license: MIT` | **108 KiB** / 13 arq. (`skills/`) (repo: 6,9 MiB / 1039 arq.) | 13 skills `openspec-*`, esqueleto `openspec/` (specs, changes, config.yaml), schemas | `npx @fission-ai/openspec@latest init` | `openspec/` + comandos por runtime (30+ suportados) | `openspec/config.yaml` | **Média** — não medido em execução; formato de artefato próprio |
| *(varredura)* **buildermethods/agent-os** | `github.com/buildermethods/agent-os` | **MIT** — `/LICENSE` (© 2025 CasJam Media LLC) | **109 KiB** / 22 arq. (repo inteiro) | `profiles/default`, `commands/agent-os`, 3 scripts bash, `config.yml` | Instalador bash (`scripts/project-install.sh`); README **não traz comando** — remete a `buildermethods.com/agent-os` | Não medido | Não medido | **Baixa** — mas veja §5.3: docs fora do repo e último push em 2026-05-05 |
| *(varredura)* **anthropics/skills** | `github.com/anthropics/skills` | ⚠️ **Sem SPDX** — API GitHub `license: null`, **não há arquivo LICENSE**. README: *"Many skills in this repo are open source (Apache 2.0)"*, mas `docx`/`pdf`/`pptx`/`xlsx` são *"source-available, **not** open source"* | 10,1 MiB / 405 arq. (`skills/`) | 18 skills + a spec do Agent Skills + template | `/plugin marketplace add anthropics/skills` | `.claude/skills/` via plugin | Nenhum | **Trivial tecnicamente, BLOQUEADO juridicamente** — ver §5.4 |
| *(varredura)* **ruvnet/claude-flow** → **Ruflo** | `github.com/ruvnet/claude-flow` | **MIT** — API GitHub `spdx_id: MIT` | **Inviável** — repo 540 MB; pacote npm 13,5 MB / 1711 arq. | Meta-harness de orquestração: swarms, memória, RAG, **servidor MCP** | `npx ruflo@latest init wizard`; MCP via `claude mcp add ruflo -- npx ruflo@latest mcp start` | `.claude/`, `.claude-flow/`, `CLAUDE.md`, helpers, settings | Sim (`.claude-flow/`) | **Proibitivo** — não é conteúdo; é um servidor MCP em Node |

**Legenda de dificuldade** — *Trivial*: cópia de árvore, zero transformação. *Baixa*: cópia + um
detalhe (hook, renomeação). *Média*: transformação determinística documentada, reprodutível a partir
de arquivos versionados. *Alta*: exige reproduzir lógica de instalação com estado e/ou runtime
externo. *Proibitivo*: o produto instalado **é** o runtime de terceiro.

---

## 1. `mattpocock/skills`

### 1.1 Conteúdo, medido

Repo inteiro (exceto `.git/`): **482.037 bytes / 167 arquivos**. Só `skills/`: **280.346 bytes /
113 arquivos**, 41 skills distribuídas assim:

| Categoria | Skills | Arquivos | Bytes | Promovida? |
| --- | ---: | ---: | ---: | --- |
| `engineering/` | 17 | 52 | 147.398 | ✅ |
| `productivity/` | 5 | 16 | 49.451 | ✅ |
| `in-progress/` | 9 | 21 | 51.021 | ❌ |
| `deprecated/` | 4 | 9 | 17.028 | ❌ |
| `misc/` | 4 | 10 | 12.592 | ❌ |
| `personal/` | 2 | 5 | 2.856 | ❌ |

Formatos sob `skills/`: 68 `.md`, 41 `.yaml`, 3 `.sh`, 1 `.cjs`. Nenhum binário. Maior arquivo:
`skills/productivity/writing-great-skills/GLOSSARY.md`, 18.488 bytes.

O termo **"promovida"** é do próprio repo (ADR `.agents/adr/0002-ship-as-a-claude-code-plugin.md`):
`engineering/` e `productivity/` são shipadas; `misc/`, `personal/`, `in-progress/` e `deprecated/`
**deliberadamente não são**.

### 1.2 O que o `.claude-plugin/` faz

Dois arquivos, e eles fazem coisas diferentes:

- **`.claude-plugin/plugin.json`** (v1.2.0) — manifesto de **plugin do Claude Code**. O campo
  `skills` é um **array de 22 caminhos explícitos** (17 de `engineering/`, 5 de `productivity/`).
  É esse array que implementa a curadoria: nada fora dele é instalado.
- **`.claude-plugin/marketplace.json`** — declara o repo como **marketplace de um plugin só**
  (`name: "mattpocock"`, `plugins: [{ name: "mattpocock-skills", source: "./" }]`). É o que permite
  `/plugin marketplace add mattpocock/skills` sem infraestrutura externa.

O ADR 0002 documenta **por que só existe manifesto de Claude Code**: o `.codex-plugin/plugin.json`
do Codex aceita `skills` apenas como **string de caminho único**, e descobre `SKILL.md`
recursivamente sob ele. Não há como nomear duas pastas de bucket nem curar um subconjunto a partir
de um caminho. Duas saídas foram testadas e rejeitadas pelo autor: apontar para `./skills/`
(shipparia `deprecated/`, `in-progress/`, `personal/`, `misc/`) e um diretório plano de **symlinks**
(o Codex copia a árvore para o cache e **descarta symlinks** — as skills chegam vazias).

> **Leitura para o overpower**: o array de 22 caminhos em `plugin.json` **é uma lista de curadoria
> pronta, mantida upstream**. Um catálogo que quiser "as skills promovidas do Matt Pocock" pode ler
> esse array em vez de manter a própria lista — e herdar as promoções/despromoções do autor.

### 1.3 Instalação canônica e destino, medidos

O README dá duas vias com filosofias declaradamente opostas ("Two ways in, two philosophies"):

1. **Plugin do Claude Code** — `claude plugins install mattpocock-skills` (está no marketplace
   oficial). Bundle read-only, gerido pelo runtime, atualiza quando o autor publica. **22 skills.**
2. **skills.sh** — `npx skills@latest add mattpocock/skills`. Copia arquivos editáveis para o repo.

O `npx skills` é o CLI `vercel-labs/skills` (MIT, 27.634 estrelas em 2026-07-30). Rodado de verdade
contra um repo git vazio:

```
npx skills@latest add mattpocock/skills --project --agent claude-code --skill '*' -y --copy
```

Resultado medido: **41 diretórios / 108 arquivos / 271.593 bytes** em `.claude/skills/`, mais
`skills-lock.json` na raiz. Três fatos que decidem o custo de reimplementação:

- **A cópia é byte-idêntica.** `diff .claude/skills/tdd/SKILL.md` contra
  `skills/engineering/tdd/SKILL.md` no upstream → **sem diferença**. Zero transformação de conteúdo.
- **O caminho é achatado.** `skills/engineering/tdd/` → `.claude/skills/tdd/`. A categoria some.
  Isso significa que **nomes de skill precisam ser únicos globalmente** no repo de origem — e são.
- **`--skill '*'` instala as 41**, inclusive `deprecated/` e `personal/`. A curadoria só existe
  na via de plugin. Um instalador próprio precisa **escolher qual das duas semânticas adota**.

O `skills-lock.json` guarda, por skill: `source`, `sourceType: github`, `skillPath` (o caminho
original **com** a categoria) e `computedHash` (sha256). É **manifesto proprietário no alvo** — algo
que o axioma 2 do overpower proíbe. A informação que ele carrega (`skillPath`) é justamente a que o
achatamento destrói; num repo git, `git log` do arquivo vendorizado a substitui.

### 1.4 O que muda se o overpower instalar por conta própria

Praticamente nada, e é o caso mais fácil do catálogo. `shutil.copytree` de
`skills/<categoria>/<nome>/` para `<dest>/<nome>/`, nada mais. Sem `npx`, sem clone em runtime, sem
lockfile. Ganha-se: a curadoria vira decisão do catálogo (as 22 promovidas, ou as 41, ou um
subconjunto), o `skills-lock.json` desaparece, e o `git diff` do alvo mostra exatamente o que entrou.
Perde-se: `npx skills update`, que o overpower já colocou fora de escopo (v0.2).

---

## 2. `github/spec-kit`

### 2.1 A premissa do ticket está desatualizada

O ticket diz: *"o `specify init` baixa templates de GitHub releases em runtime"*. **Isso deixou de
ser verdade em 2026-03-23.** Evidência primária, em três lugares:

1. `pyproject.toml`, seção `[tool.hatch.build.targets.wheel.force-include]`, com o comentário do
   próprio projeto:
   > `# Bundle core assets so 'specify init' works without network access (air-gapped / enterprise)`
2. `specify init --help`, texto de ajuda do comando:
   > *"Project files are scaffolded from assets bundled inside the specify-cli package, so
   > initialization does not need network access and templates match the installed CLI version."*
3. `CHANGELOG.md`, entrada **`[0.4.0] - 2026-03-23`**:
   > `feat(cli): embed core pack in wheel for offline/air-gapped deployment (#1803)`

O `_assets.py` confirma o mecanismo: `_locate_core_pack()` procura `specify_cli/core_pack/` ao lado
do módulo (só existe em instalação por wheel) e cai para a raiz do checkout quando ausente.

**Consequência para o overpower**: o spec-kit **já resolveu o problema que o overpower existe para
resolver** — ele é hoje uma CLI Python que funciona sem rede, publicada no PyPI, com os assets
dentro do wheel. Isso é confirmação forte da arquitetura escolhida no mapa, e ao mesmo tempo o caso
em que "reimplementar" tem o menor ganho relativo.

Download de rede ainda existe no `specify`, mas **fora do `init`**: `specify extension add --from
<url>`, `specify bundle`, `specify preset add`, `specify self upgrade` e a checagem de versão
(`GITHUB_API_LATEST = "https://api.github.com/repos/github/spec-kit/releases/latest"` em
`_version.py`). O caminho `init` é offline.

### 2.2 O que é redistribuível, e quanto pesa

O repo tem 10,24 MiB / 530 arquivos, mas a maior parte é `tests/` (4,2 MB), `media/` (2,2 MB) e
`src/` (2,6 MB) — nada disso aterrissa no alvo. O que aterrissa vem de:

| Fonte no repo | Bytes | Arquivos |
| --- | ---: | ---: |
| `templates/` (5 páginas + 10 comandos + vscode-settings) | 149.512 | 16 |
| `scripts/` (bash + powershell + python) | 147.747 | 15 |
| `workflows/speckit/` + `presets/` + `extensions/` | (opcionais) | — |

O **wheel publicado no PyPI** (`specify_cli-0.15.0-py3-none-any.whl`) tem **774.465 bytes (0,74
MiB)** — esse é o `core_pack` inteiro mais o código. O sdist tem 3,69 MiB.

⚠️ **O PyPI não declara licença**: `info.license` é `None` e não há classificador `License ::` no
metadado de `specify-cli 0.15.0`. A MIT está só no `/LICENSE` do repo GitHub (© GitHub, Inc.). Um
`NOTICE` do overpower precisa citar o arquivo do repo, não o metadado do pacote.

### 2.3 Destino por runtime, medido

Rodei `specify init` de verdade, a partir de um wheel construído do HEAD, para três integrações.

**`--integration claude`** — 28 arquivos / 217.864 bytes:

```
.claude/skills/speckit-{analyze,checklist,clarify,constitution,converge,
                        implement,plan,specify,tasks,taskstoissues}/SKILL.md
.specify/init-options.json
.specify/integration.json
.specify/integrations/{claude,speckit}.manifest.json
.specify/memory/{constitution.md,.constitution-template.json}
.specify/scripts/bash/{check-prerequisites,common,create-new-feature,setup-plan,setup-tasks}.sh
.specify/templates/{checklist,constitution,plan,spec,tasks}-template.md
.specify/workflows/speckit/workflow.yml
.specify/workflows/workflow-registry.json
```

**`--integration codex`** — idêntico, exceto que as skills vão para `.agents/skills/`.

**`--integration copilot`** — `.specify/` idêntico, mas o conteúdo de agente vira **20 arquivos em
dois formatos**: `.github/agents/speckit.<cmd>.agent.md` **e** `.github/prompts/speckit.<cmd>.prompt.md`,
mais `.vscode/settings.json`.

Ou seja: **`.specify/` é invariante entre runtimes; só a camada de comando/skill muda**. Essa é a
costura natural para o formato do catálogo.

A tabela completa de destinos está em `src/specify_cli/integrations/*/__init__.py`
(`registrar_config`). São **37 integrações**. Amostra:

| Chave | Runtime | `dir` | `extension` | `format` |
| --- | --- | --- | --- | --- |
| `claude` | Claude Code | `.claude/skills` | `/SKILL.md` | markdown |
| `codex` | Codex CLI | `.agents/skills` | `/SKILL.md` | markdown |
| `copilot` | GitHub Copilot | `.github/skills` | `/SKILL.md` | markdown |
| `cursor_agent` | Cursor | `.cursor/skills` | `/SKILL.md` | markdown |
| `gemini` | Gemini CLI | `.gemini/commands` | `.toml` | **toml** |
| `goose` | Goose | `.goose/recipes` | `.yaml` | **yaml** |
| `firebender` | Firebender | `.firebender/commands` | `.mdc` | markdown |
| `tabnine` | Tabnine CLI | `.tabnine/agent/commands` | `.toml` | **toml** |
| `zed` / `amp` / `agy` | Zed / Amp / Antigravity | `.agents/…` | varia | markdown |
| `hermes` | Hermes Agent | `~/.hermes/skills` | `/SKILL.md` | markdown |
| `generic` | traga o seu | `--commands-dir` obrigatório | `.md` | markdown |

Note `hermes`: destino **global** (`~/`), não no projeto. E `generic`: destino fornecido pelo usuário.
Ambos são casos que o wizard de aterrissagem do overpower (issue #5) precisa cobrir.

### 2.4 A transformação, e se dá para reproduzi-la sem executar o `specify`

**Dá.** É determinística e cabe em quatro regras. Comparando
`templates/commands/plan.md` (fonte) com `.claude/skills/speckit-plan/SKILL.md` (saída medida):

1. **Frontmatter é substituído, não editado.** A fonte traz `description`, `handoffs` e `scripts`;
   a saída traz `name`, `description`, `argument-hint`, `compatibility`, `metadata.{author,source}`,
   `user-invocable`, `disable-model-invocation`. O `argument-hint` vem de um dicionário
   `ARGUMENT_HINTS` fixo na integração Claude (`integrations/claude/__init__.py`).
2. **`{SCRIPT}` é resolvido pelo `scripts:` do frontmatter da fonte**, segundo o `--script` escolhido:
   `sh: scripts/bash/setup-plan.sh --json` → o corpo passa de
   ``Run `{SCRIPT}` from repo root`` para ``Run `.specify/scripts/bash/setup-plan.sh --json` from repo root``.
3. **Reescrita de prefixos de caminho**, implementada em `agents.py` (linhas ~201-224) via regex:
   `memory/` → `.specify/memory/`, `scripts/` → `.specify/scripts/`, `templates/` → `.specify/templates/`
   (com colapso de `.specify/.specify/`).
4. **Token de argumento e extensão são por integração**: `args` (`$ARGUMENTS` no Claude) e
   `extension` (`/SKILL.md`, `.md`, `.toml`, `.mdc`, `.yaml`).

Tudo isso opera sobre arquivos **versionados no repo** (`templates/`, `scripts/`) e uma tabela de 37
entradas **também versionada**. Nenhum passo consulta a rede, e nenhum depende de resposta do
usuário além de `--integration` e `--script`.

### 2.5 O que muda se o overpower instalar por conta própria

- **Ganha**: não precisa de `specify` instalado, nem de `uv tool install`. Vendoriza
  `templates/` + `scripts/` (~290 KiB) e implementa as quatro regras acima. Também escapa dos três
  arquivos de estado (`init-options.json`, `integration.json`, `integrations/*.manifest.json`), que
  violam o axioma 2.
- **Custa**: a tabela de 37 integrações vira **dívida de manutenção do overpower** — ela muda a cada
  release do spec-kit (o CHANGELOG mostra integrações novas em quase todo minor). Mitigação natural:
  o overpower só suporta o subconjunto que seu catálogo declara, e importa a tabela do
  `integrations/` upstream em vez de transcrevê-la.
- **Risco de fidelidade**: os arquivos gerados **não são** cópia dos versionados — são cópia
  transformada. Se a transformação divergir do upstream, as skills instaladas ficam sutilmente
  quebradas (ex.: `{SCRIPT}` não resolvido). Isso pede um teste de caracterização: gerar com o
  overpower, gerar com o `specify`, e comparar árvores. É o **único framework do catálogo em que um
  teste desses é obrigatório**.
- **Alternativa mais barata, que vale considerar**: o `core_pack` já está dentro do wheel do PyPI
  (774 KiB). Em vez de vendorizar do repo git, o overpower poderia declarar `specify-cli` como
  dependência e ler `specify_cli/core_pack/` via `importlib.resources`. Isso mantém o axioma 1
  (nenhum subprocesso alheio — é só leitura de arquivo de um pacote instalado) e elimina a dívida de
  vendorização, ao custo de uma dependência Python. **Decisão para a issue #11** (onde os assets vivem).

---

## 3. `bmad-code-org/BMAD-METHOD`

### 3.1 A licença real: **MIT**, e por que o GitHub diz `NOASSERTION`

A API do GitHub reporta `spdx_id: NOASSERTION` (conferido em 2026-07-30). **Não é ausência de
licença.** O arquivo `/LICENSE` do repo contém o texto MIT **completo e literal**:

```
MIT License

Copyright (c) 2025 BMad Code, LLC

This project incorporates contributions from the open source community.
See [CONTRIBUTORS.md](CONTRIBUTORS.md) for contributor attribution.

Permission is hereby granted, free of charge, to any person obtaining a copy
... [texto MIT íntegro] ...
```

…**seguido de um bloco extra**:

```
TRADEMARK NOTICE:
BMad™, BMad Method™, and BMad Core™ are trademarks of BMad Code, LLC, covering all
casings and variations (including BMAD, bmad, BMadMethod, BMAD-METHOD, etc.). ...
```

O classificador do GitHub (`licensee`) exige correspondência quase exata com o texto canônico. Uma
linha de atribuição inserida **antes** do "Permission is hereby granted" e um aviso de marca
**depois** do disclaimer quebram a correspondência, e o classificador cai para `NOASSERTION`. É
artefato de ferramenta, não posição jurídica.

**Quatro fontes primárias independentes confirmam MIT**, todas lidas em 2026-07-30:

| Fonte | Declaração |
| --- | --- |
| `/LICENSE` | `MIT License` + texto íntegro |
| `package.json` (v6.10.0) | `"license": "MIT"` |
| `.claude-plugin/marketplace.json` | `"license": "MIT"` |
| npm registry, `bmad-method@6.10.0` | `license: MIT` |

**A ressalva que importa juridicamente é de marca, não de copyright.** `TRADEMARK.md` é explícito:

> *"These trademarks are protected under trademark law and are **not** licensed under the MIT
> License. The MIT License applies to the software code only, not to the BMad brand identity."*

O documento permite: *"Refer to BMad to accurately describe compatibility or integration"*, *"Fork
the software and distribute your own version under a different name"*, e vender produtos que
incorporem o software. E proíbe: usar "BMad" ou variação confusamente similar como nome de produto,
serviço, empresa ou domínio; e sugerir endosso oficial.

> **Leitura para o overpower**: redistribuir o conteúdo BMAD dentro do wheel é **permitido pela MIT**,
> desde que o `/LICENSE` upstream viaje junto (o `NOTICE` já planejado na issue #11 resolve). O que a
> marca proíbe é chamar um artefato do overpower de "BMad *alguma coisa*" ou insinuar parceria. Uma
> entrada de catálogo `bmad-method` com descrição *"BMad Method™ — marca da BMad Code, LLC; código sob
> MIT"* está dentro das regras. **Corrigir o mapa**: a nota de "risco de redistribuição aceito" da
> issue #1 cita o BMAD como caso `NOASSERTION`. Ele não é — é MIT com aviso de marca. O risco real do
> catálogo é outro (§5.4).

### 3.2 Conteúdo, medido

`src/` = **1.724.498 bytes (1,64 MiB) / 275 arquivos**, dividido em dois módulos:

| Diretório | Bytes | Arquivos | Conteúdo |
| --- | ---: | ---: | --- |
| `src/bmm-skills/` | 999.184 (0,95 MiB) | 188 | `1-analysis/`, `2-plan-workflows/`, `3-solutioning/`, `4-implementation/` |
| `src/core-skills/` | 672.513 (0,64 MiB) | 78 | `bmad-{advanced-elicitation,brainstorming,customize,deep-recon,forge-idea,help,party-mode,review}` |

Formatos: **197 `.md`, 38 `.toml`, 26 `.py`, 5 `.csv`, 3 `.yaml`, 3 `.json`, 3 `.html`**. 50
`SKILL.md`. Os `.py` não são build-time — são **scripts que os skills executam em runtime**.

Além disso: `web-bundles/` (136.930 bytes, 18 arquivos) e `bmad-modules.yaml`, que registra **5 módulos
oficiais externos** (`bmad-loop`, BMB, TEA, BMGD, CIS), cada um num repo próprio. **A unidade
"BMAD-METHOD" não é o framework inteiro** — é o núcleo (`core` + `bmm`); os demais são origens
distintas, e portanto, pelo vocabulário do overpower, **AI Frameworks separados**.

### 3.3 Instalação canônica e destino, medidos

Pré-requisitos declarados no README: **Node.js ≥20.12, Python ≥3.10, e `uv`**.

```
npx bmad-method install                                          # interativo
npx bmad-method install --directory <p> --modules bmm \
                        --tools claude-code --yes                # CI
```

Rodado de verdade (`bmad-method@6.10.0` do npm) contra diretório vazio. Saída do próprio instalador:
`claude-code configured: 46 skills → .claude/skills`. Inventário medido: **250 arquivos /
1.755.628 bytes (1,67 MiB)**:

| Caminho | Bytes | Arquivos |
| --- | ---: | ---: |
| `.claude/skills/` (46 skills) | 1.656.917 | 234 |
| `_bmad/` | 98.711 | 16 |
| `_bmad-output/`, `docs/` | 0 | 0 (dirs vazios) |

`_bmad/` contém:

- `config.toml` — **gerado das respostas do instalador**. Cabeçalho: *"Installer-managed. Regenerated
  on every install — treat as read-only."* Traz `[core] project_name/document_output_language/output_folder`
  e uma tabela `[agents.<nome>]` por agente (persona, ícone, título…).
- `config.user.toml` — overrides pessoais (gitignored por convenção).
- `_config/manifest.yaml` — versão, `installDate`, `lastUpdated`, módulos e IDEs instalados.
- `_config/files-manifest.csv` — **sha256 por arquivo instalado**.
- `_config/skill-manifest.csv` — id, nome, descrição, módulo e path por skill.
- `scripts/{memlog,resolve_config,resolve_customization}.py`.
- `core/config.yaml`, `bmm/config.yaml`, `*/module-help.csv`.

Cada skill instalada ganha um **`customize.toml` gerado** ao lado do `SKILL.md` (*"DO NOT EDIT —
overwritten on every update"*), com a superfície de customização daquele workflow.

Destinos por runtime: `tools/installer/ide/platform-codes.yaml`, **45 plataformas**. `claude-code` →
`.claude/skills` (projeto) e `~/.claude/skills` (global). O destino mais frequente é o padrão
cross-tool `.agents/skills` (25 plataformas) / `~/.agents/skills` (17).

### 3.4 O `SKILL.md` do BMAD não é autocontido

Este é o achado que mais custa. Trecho literal de `bmad-brainstorming/SKILL.md`:

> *1. Resolve customization: `uv run {project-root}/_bmad/scripts/resolve_customization.py --skill
> {skill-root} --key workflow`.*
> *3. Resolve central config: `uv run {project-root}/_bmad/scripts/resolve_config.py --project-root
> {project-root} --key core` (merges `_bmad/config.toml`, `_bmad/config.user.toml`, and the
> `_bmad/custom/` overrides)…*

Ou seja: **o skill instalado invoca Python via `uv` toda vez que é ativado**, para resolver
`{user_name}`, `{communication_language}`, `{output_folder}`, `{project_name}`. Sem `_bmad/config.toml`
e sem `uv`, o skill degrada (os textos dizem "never block", mas caem em defaults neutros e perdem a
configuração do projeto).

### 3.5 O que muda se o overpower instalar por conta própria

- **A cópia de `src/` não basta.** Um `copytree` produz skills que ativam, mas sem
  `_bmad/config.toml` — e esse arquivo é **derivado de uma entrevista** (nome do projeto, idioma,
  pasta de saída) e contém uma tabela `[agents.*]` por agente. O overpower teria que **gerar** esse
  arquivo, ou seja, reimplementar o questionário do instalador. Isso é o que empurra a dificuldade
  para **Alta**.
- **Os manifestos violam o axioma 2 e podem ser omitidos.** `manifest.yaml`, `files-manifest.csv`,
  `skill-manifest.csv` são só bookkeeping do instalador para update/uninstall — nada os lê em runtime.
  Omitir é seguro e alinhado ao "git é o manifesto". Mas `config.toml` e `config.yaml` **são lidos em
  runtime** e não podem ser omitidos.
- **`uv` continua sendo dependência de runtime do conteúdo instalado.** O axioma 1 fala do
  *instalador* ("nunca invoca instalador de terceiro"), e instalar sem `npx` cumpre a letra. Mas o
  ambiente corporativo alvo precisará de `uv` para os skills BMAD funcionarem. O README do próprio
  BMAD reconhece: *"BMAD workflows increasingly run Python scripts via `uv run`"*. **Isso é uma
  decisão de catálogo, não de implementação**: o BMAD é elegível ao catálogo do overpower **se e
  somente se** `uv` puder existir no alvo — e como o overpower é invocado por `uvx`, na prática está.
- **A marca precisa aparecer no `NOTICE`.** MIT exige o aviso de copyright; `TRADEMARK.md` recomenda
  não usar "BMad" como nome de nada do overpower.

---

## 4. GSD

### 4.1 Qual é o "GSD" — e o repo canônico mudou

**GSD = "Get Shit Done"**, criado por **TÂCHES** (Lex Christopherson), *"a light-weight and powerful
meta-prompting, context engineering and spec-driven development system"*. É o mesmo GSD que o próprio
README do `mattpocock/skills` cita como referência de mercado:

> *"Approaches like GSD, BMAD, and Spec-Kit try to help by owning the process."*
> — `mattpocock/skills/README.md`, lido em 2026-07-30

**O repo que a cartografia não achou está arquivado.** Estado em 2026-07-30:

| | `gsd-build/get-shit-done` | `open-gsd/gsd-core` |
| --- | --- | --- |
| Estrelas | 64.792 | 7.458 |
| Arquivado? | **✅ SIM** | não |
| Último push | 2026-05-31 | 2026-07-30 |
| Licença | MIT (© 2025 Lex Christopherson) | MIT (© 2026 Open GSD) |
| Pacote npm | `get-shit-done-cc@1.42.3` | `@opengsd/gsd-core@1.8.0` |

O `README.md` do repo antigo hoje contém **apenas** o redirecionamento:

> `# GSD Has Moved`
> *"This repository is no longer the active home for GSD development. The project now continues as
> **GSD Core** in the Open GSD repository: https://github.com/open-gsd/gsd-core"*

**As estrelas ficaram no repo morto.** Quem procurar "GSD" pela métrica de tração acha 64,8k num repo
arquivado; o código vivo tem 7,5k porque o repo é novo. Isso provavelmente explica por que a
cartografia não conseguiu fixar o canônico. **O canônico é `open-gsd/gsd-core`.**

Ainda há forks ativos de terceiros (`shoootyou/get-shit-done-multi`, `rokicool/gsd-opencode`,
`toonight/get-shit-done-for-antigravity`) — **não são origem única** e não entram num catálogo curado.

### 4.2 Conteúdo, medido

Repo `open-gsd/gsd-core`: **34.485.843 bytes (32,89 MiB) / 2.680 arquivos**. Quase tudo é `tests/`
(18 MB) e `docs/` (6,4 MB). O `files` do `package.json` declara o que vai para o npm; o pacote
publicado tem **9,7 MB / 802 arquivos**. O núcleo redistribuível:

| Diretório | Bytes | Arquivos |
| --- | ---: | ---: |
| `gsd-core/` (runtime: `bin`, `contexts`, `references`, `templates`, `workflows`) | 3.802.133 | 307 |
| `agents/` | 695.735 | 34 |
| `hooks/` | 196.165 | 29 |
| `commands/` | 167.383 | 71 |
| `skills/` | 164.806 | 71 |

### 4.3 Instalação canônica e destino, medidos

```
npx @opengsd/gsd-core@latest              # interativo
npx @opengsd/gsd-core@latest --claude --local   # não-interativo
```

Node ≥22, npm ≥10. O README traz uma instrução que fala diretamente ao overpower:

> *"The installer is required for cross-runtime compatibility — **do not copy files from `agents/` or
> `commands/` directly**."*
> — `open-gsd/gsd-core/README.md`, lido em 2026-07-30

Rodei `npx @opengsd/gsd-core@latest --claude --local` num repo git vazio. Resultado medido:
**614 arquivos / 8.117.985 bytes (7,74 MiB)**, tudo sob `.claude/`:

| Caminho | Bytes | Arquivos |
| --- | ---: | ---: |
| `.claude/gsd-core/` | 6.862.144 | 464 |
| `.claude/agents/` | 709.413 | 34 |
| `.claude/commands/` | 186.086 | 71 |
| `.claude/hooks/` | 153.109 | 27 |
| `.claude/scripts/` | 133.092 | 13 |
| `.claude/gsd-file-manifest.json` | 68.596 | 1 |
| `.claude/settings.local.json` | 4.549 | 1 |
| `.claude/gsd-install-state.json` | 971 | 1 |
| `.claude/.gsd-profile`, `.claude/package.json` | 25 | 2 |

### 4.4 Por que é o caso proibitivo

Três razões, cada uma medida:

1. **O instalador reescreve `.claude/settings.local.json`** com **15 hooks em 7 eventos**
   (`SessionStart` ×2, `PreToolUse` ×5, `PostToolUse` ×4, `SubagentStop`, `Stop`, `PreCompact`,
   `FileChanged`), mais chaves `worktree` e `permissions`. Isso não é cópia de arquivo — é *merge* de
   JSON num arquivo que o usuário também edita, o mesmo problema que a issue #1 listou como névoa
   ("Instalação de configuração de MCP").
2. **Os hooks embutem o caminho absoluto do binário `node` da máquina**. Comando literal registrado
   na minha execução:
   `"/home/paninit/.local/share/mise/shims/node" "$CLAUDE_PROJECT_DIR"/.claude/hooks/gsd-check-update.js`.
   É um artefato **específico da máquina que instalou** — não pode ser vendorizado, tem que ser
   computado no momento da instalação, e **exige Node ≥22 presente no alvo**. Num ambiente corporativo
   sem esse ferramental — a razão declarada do axioma 1 — o GSD instalado **não funciona**, seja quem
   for que copie os arquivos.
3. **`gsd-install-state.json` é um motor de migração**, com `appliedMigrations` versionadas por
   checksum sha256 (vi 4+ migrações aplicadas, incluindo `2026-06-02-rename-get-shit-done-to-gsd-core`).
   Reproduzir isso é reimplementar `bin/install.js` — **13.558 linhas**.

### 4.5 Veredito

**GSD é framework instalável, e não é candidato ao catálogo da v0.1.0.** Não porque a licença
impeça (é MIT limpa), mas porque o produto instalado **é** um runtime Node com hooks — não um corpo
de arquivos. Copiar os arquivos produz uma instalação inerte, e o upstream diz isso explicitamente.

Se o GSD tiver que entrar em alguma versão, o caminho honesto é **um subconjunto declarado**: só
`skills/` (165 KiB / 71 arquivos), sem `hooks/`, sem `gsd-core/`, aceitando que o loop autônomo não
funciona. Isso muda o que "GSD" significa no catálogo — vira "as skills do GSD", não "o GSD" — e
**contradiz o vocabulário de AI Framework** ("se instala como unidade"). É decisão para a issue #10
(formato do catálogo), não para esta pesquisa.

---

## 5. Varredura: o que mais tem tração real em 2026

Métricas coletadas via API do GitHub em **2026-07-30**.

| Repo | Estrelas | SPDX (API) | Último push | Tamanho (API) | O que é |
| --- | ---: | --- | --- | ---: | --- |
| `obra/superpowers` | 263.952 | MIT | 2026-07-28 | 4,0 MB | Framework de skills + metodologia |
| `mattpocock/skills` | 196.217 | MIT | 2026-07-29 | 0,9 MB | Skills de engenharia |
| `anthropics/skills` | 165.267 | **null** | 2026-07-24 | 4,2 MB | Skills de referência da Anthropic |
| `github/spec-kit` | 124.666 | MIT | 2026-07-30 | 14,4 MB | Toolkit SDD (CLI Python) |
| `ruvnet/claude-flow` (→ Ruflo) | 66.601 | MIT | 2026-07-30 | **527 MB** | Meta-harness de orquestração + MCP |
| `gsd-build/get-shit-done` | 64.792 | MIT | 2026-05-31 | 19,8 MB | **ARQUIVADO** |
| `Fission-AI/OpenSpec` | 63.221 | MIT | 2026-07-30 | 6,2 MB | SDD leve, 30+ ferramentas |
| `bmad-code-org/BMAD-METHOD` | 51.307 | NOASSERTION (=MIT) | 2026-07-30 | 49,4 MB | Framework de agentes ágeis |
| `PatrickJS/awesome-cursorrules` | 40.469 | CC0-1.0 | 2026-05-30 | 2,9 MB | Lista curada (não instalável) |
| `wshobson/agents` | 38.382 | MIT | 2026-07-22 | 5,5 MB | Marketplace multi-harness de agentes |
| `github/awesome-copilot` | 37.256 | MIT | 2026-07-30 | 94,8 MB | Instruções/agents/skills p/ Copilot |
| `davila7/claude-code-templates` | 30.011 | MIT | 2026-07-30 | 208 MB | Templates + componentes |
| `eyaltoledano/claude-task-master` | 27.926 | NOASSERTION | 2026-04-28 | 28,6 MB | Gestão de tarefas por AI |
| `vercel-labs/skills` | 27.634 | MIT | 2026-07-30 | 1,3 MB | **O CLI `npx skills`** (transporte, não framework) |
| `AgentSkills/agentskills` | 23.673 | Apache-2.0 | 2026-07-10 | 0,7 MB | **A especificação** Agent Skills |
| `open-gsd/gsd-core` | 7.458 | MIT | 2026-07-30 | 42,9 MB | GSD vivo |
| `buildermethods/agent-os` | 5.141 | MIT | 2026-05-05 | 0,4 MB | Injeção de padrões de codebase |
| `Pimzino/spec-workflow-mcp` | 4.273 | **GPL-3.0** | 2026-07-03 | 63,7 MB | MCP de workflow — ⛔ copyleft |

### 5.1 `obra/superpowers` — o candidato mais forte que não estava no ticket

263.952 estrelas, **MIT** (`/LICENSE`, © 2025 Jesse Vincent; e `.claude-plugin/plugin.json`
`"license": "MIT"`, v6.2.0). Repo: 1,52 MiB / 180 arquivos. `skills/`: **351.137 bytes / 50 arquivos
/ 14 skills** (`brainstorming`, `systematic-debugging`, `test-driven-development`,
`writing-plans`, `executing-plans`, `subagent-driven-development`, `using-git-worktrees`,
`requesting-code-review`, `receiving-code-review`, `verification-before-completion`,
`dispatching-parallel-agents`, `finishing-a-development-branch`, `using-superpowers`, `writing-skills`).

**Instalação canônica**: `/plugin install superpowers@claude-plugins-official` (marketplace oficial
da Anthropic). Alternativas por harness documentadas no README: `agy plugin install <url>`
(Antigravity), marketplace do Codex (`openai/plugins`), `droid plugin marketplace add`, extensão do
Gemini CLI. O repo carrega manifesto para **cinco ecossistemas**: `.claude-plugin/`, `.codex-plugin/`,
`.cursor-plugin/`, `.kimi-plugin/`, `gemini-extension.json` — resolvendo o problema que o ADR 0002 do
Matt Pocock não resolveu, por ter estrutura plana em vez de bucketed.

**Reimplementar: Baixa.** Cópia de árvore de `skills/`. O extra é `hooks/` (4.205 bytes, 4 arquivos) e o hook de
`SessionStart` que carrega `using-superpowers` — omissível ao custo de o agente não descobrir as
skills sozinho no início da sessão.

**Nota comercial, não jurídica**: o README traz *"If you're using Superpowers in enterprise and could
benefit from commercial support… drop us a line at sales@primeradiant.com"*. A licença é MIT sem
ressalva; a menção é de suporte pago, não de restrição.

### 5.2 `Fission-AI/OpenSpec` — o quinto do "showdown"

63.221 estrelas, **MIT** (`/LICENSE`, © 2024 OpenSpec Contributors; `package.json` idem). npm
`@fission-ai/openspec@1.7.0`. `skills/`: **110.740 bytes / 13 arquivos**, todas `openspec-*`
(`propose`, `apply`, `archive`, `verify-change`, `new-change`, `sync-specs`, `onboard`, `explore`…).
Fluxo Propose → Apply → Archive, artefatos em `openspec/{changes,specs,initiatives,explorations,work}`
+ `openspec/config.yaml`. Suporta 30+ ferramentas. **Não executei o instalador** — a avaliação de
dificuldade (Média) é por leitura de estrutura, não medição.

### 5.3 `buildermethods/agent-os` — o menor, e o mais frio

5.141 estrelas, **MIT** (© 2025 CasJam Media LLC). **111.563 bytes / 22 arquivos — o repo inteiro.**
Conteúdo: `profiles/default`, `commands/agent-os`, `config.yml` (v3.0) e três scripts bash
(`project-install.sh`, `sync-to-profile.sh`, `common-functions.sh`).

Dois sinais de cautela: **o README não traz nenhum comando de instalação** — remete a
`buildermethods.com/agent-os` (documentação **fora** do repo, fonte primária que não posso versionar).
E o último push foi **2026-05-05**, ~3 meses de silêncio, contra pushes diários dos outros. Barato de
vendorizar; a dúvida é se está vivo.

### 5.4 ⚠️ `anthropics/skills` — a armadilha de licença do catálogo

165.267 estrelas, e **é o caso mais perigoso da lista**. A API do GitHub retorna `license: null`, e
**não existe arquivo `LICENSE` no repo** — só `THIRD_PARTY_NOTICES.md`, que atribui dependências de
terceiros e não licencia o repo. O README diz, literalmente:

> *"**Many** skills in this repo are open source (Apache 2.0). We've also included the document
> creation & editing skills that power Claude's document capabilities under the hood in the
> `skills/docx`, `skills/pdf`, `skills/pptx`, and `skills/xlsx` subfolders. **These are
> source-available, not open source**…"*
> — `anthropics/skills/README.md`, lido em 2026-07-30

Ou seja: licença **mista e não declarada por arquivo**. "Many" não é "all", e não há SPDX que diga
quais. Vendorizar isso dentro de um wheel publicado no PyPI é redistribuir código *source-available*
sem licença de redistribuição. **Este — e não o BMAD — é o `NOASSERTION` real do espaço.**
Recomendação: **fora do catálogo**, ou dentro só via um subconjunto onde cada skill tenha
Apache-2.0 comprovada arquivo a arquivo.

### 5.5 Descartados, com razão

- **`ruvnet/claude-flow` (→ Ruflo)** — MIT, 66,6k estrelas, mas repo de **527 MB** e pacote npm de
  13,5 MB. Instala **servidor MCP** (`claude mcp add ruflo -- npx ruflo@latest mcp start`) e escreve
  `.claude/`, `.claude-flow/`, `CLAUDE.md`. É runtime, não conteúdo. Mesmo veredito do GSD, por
  ordens de grandeza mais forte.
- **`Pimzino/spec-workflow-mcp`** — **GPL-3.0**. Redistribuir dentro de um wheel proprietário/permissivo
  é incompatível. ⛔ Descarte por licença.
- **`eyaltoledano/claude-task-master`** — `NOASSERTION` na API, 28,6 MB, sem push desde 2026-04-28.
  Exigiria a mesma investigação de licença do BMAD antes de qualquer decisão.
- **`PatrickJS/awesome-cursorrules`, `github/awesome-copilot`, `davila7/claude-code-templates`** —
  são **listas/catálogos**, não "corpo coerente de origem única que se instala como unidade". Não
  atendem à definição de AI Framework do `docs/agents/domain.md`.
- **`AgentSkills/agentskills`** (Apache-2.0) — é **a especificação** do formato Agent Skills, não um
  framework instalável. Útil como referência normativa para o overpower, não como item de catálogo.
- **`vercel-labs/skills`** (MIT) — é o **transporte** (`npx skills`), exatamente a categoria de
  ferramenta que o overpower substitui em Python. Referência de comportamento, não item de catálogo.

---

## 6. Conclusões que alimentam o formato do catálogo (issue #10)

1. **Há dois tipos de framework, e o catálogo precisa distinguir.**
   *Conteúdo puro* (mattpocock, superpowers, anthropics) — a instalação é cópia de árvore.
   *Ferramenta com conteúdo* (spec-kit, BMAD, GSD, OpenSpec) — a instalação **gera** arquivos que
   não existem versionados. O ticket previu que o spec-kit poderia quebrar o formato; ele quebra
   menos do que parecia (a geração é determinística e offline desde v0.4.0), mas **GSD quebra de
   verdade** e BMAD quebra parcialmente.

2. **Um campo de "transformação" é inevitável.** Mínimo viável: `copy` (mattpocock, superpowers) e
   `render` (spec-kit: substituição de frontmatter + resolução de `{SCRIPT}` + reescrita de prefixo
   de caminho). BMAD acrescenta um terceiro: `generate-config`.

3. **O destino não é um caminho — é uma tabela (framework × runtime).** Três fontes upstream
   independentes já mantêm essa tabela: spec-kit tem **37 integrações**, BMAD tem **45 plataformas**,
   e ambas convergem para `.agents/skills` como padrão cross-tool. Há destinos **globais** no meio
   (`hermes` → `~/.hermes/skills`) e destinos **fornecidos pelo usuário** (`generic`), o que conecta
   direto à issue #5.

4. **Todo instalador upstream grava manifesto proprietário no alvo** — `skills-lock.json`,
   `.specify/integration.json`, `_bmad/_config/*.csv`, `gsd-file-manifest.json`. Nenhum desses é lido
   em runtime pelo conteúdo instalado; todos são bookkeeping de update/uninstall. **O axioma 2 do
   overpower é gratuito**: omitir todos não quebra nada. A exceção crítica é **`_bmad/config.toml`
   do BMAD**, que os skills leem em runtime — esse não é manifesto, é configuração, e precisa existir.

5. **O critério de elegibilidade que a pesquisa revelou** não é licença nem tamanho, é: *o conteúdo
   instalado funciona sem o runtime do instalador?* mattpocock ✅ · superpowers ✅ · spec-kit ✅
   (offline desde v0.4.0) · OpenSpec ✅ provável · BMAD ⚠️ (precisa de `uv`) · GSD ❌ (precisa de
   Node ≥22 + hooks) · Ruflo ❌ (é um servidor MCP).

6. **Correções a registrar no mapa**: (a) BMAD **não** é `NOASSERTION` — é MIT com aviso de marca
   anexado; o `NOASSERTION` real do espaço é `anthropics/skills`; (b) spec-kit **não** baixa mais
   templates em runtime; (c) o repo GSD canônico é `open-gsd/gsd-core`, não `gsd-build/get-shit-done`
   (arquivado); (d) `mattpocock/skills` são **274 KiB** de conteúdo, não 948 KB.

---

## Fontes primárias

Todas lidas ou executadas em **2026-07-30**.

**Repositórios (clone `--depth 1`, HEADs na tabela de método)**
`github.com/mattpocock/skills` · `github.com/github/spec-kit` · `github.com/bmad-code-org/BMAD-METHOD` ·
`github.com/gsd-build/get-shit-done` · `github.com/open-gsd/gsd-core` · `github.com/obra/superpowers` ·
`github.com/Fission-AI/OpenSpec` · `github.com/buildermethods/agent-os` · `github.com/anthropics/skills`

**Arquivos de licença lidos integralmente**
`mattpocock/skills/LICENSE` · `github/spec-kit/LICENSE` · `bmad-code-org/BMAD-METHOD/LICENSE` +
`TRADEMARK.md` · `gsd-build/get-shit-done/LICENSE` · `open-gsd/gsd-core/LICENSE` ·
`obra/superpowers/LICENSE` · `Fission-AI/OpenSpec/LICENSE` · `buildermethods/agent-os/LICENSE` ·
`anthropics/skills` (**inexistente**; `THIRD_PARTY_NOTICES.md` + README)

**Código de instalação lido**
`spec-kit/pyproject.toml` (`[project.scripts]`, `[tool.hatch.build.targets.wheel.force-include]`) ·
`spec-kit/src/specify_cli/_assets.py` · `spec-kit/src/specify_cli/agents.py` ·
`spec-kit/src/specify_cli/integrations/*/__init__.py` (37) ·
`BMAD-METHOD/tools/installer/ide/platform-codes.yaml` (45) · `BMAD-METHOD/bmad-modules.yaml` ·
`gsd-core/bin/install.js` · `mattpocock/skills/.claude-plugin/{plugin,marketplace}.json` ·
`mattpocock/skills/.agents/adr/0002-ship-as-a-claude-code-plugin.md`

**Instaladores executados de verdade, e o resultado inventariado**
`specify init --integration {claude,codex,copilot} --ignore-agent-tools --script sh` (wheel do HEAD) ·
`npx bmad-method@latest install --modules bmm --tools claude-code --yes` ·
`npx @opengsd/gsd-core@latest --claude --local` ·
`npx skills@latest add mattpocock/skills --agent claude-code --skill '*' -y --copy`

**Registries**
PyPI JSON API — `specify-cli` 0.15.0 · npm registry — `skills`, `bmad-method`, `get-shit-done-cc`,
`@opengsd/gsd-core`, `claude-flow` · GitHub REST API `/repos/{owner}/{repo}` (estrelas, SPDX,
`archived`, `pushed_at`, `size`)

**Busca na web** (só para localizar o canônico do GSD e para a varredura; nenhum fato técnico daqui)
`gsd.build` · `github.com/topics/get-shit-done` · comparativos de mercado 2026 que nomeiam o conjunto
Superpowers / BMAD / SpecKit / GSD / OpenSpec.
