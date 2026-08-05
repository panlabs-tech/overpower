"""PROTOTYPE — throwaway. Shared data, copy and console for the three variants.

Ticket #12. Not production code.

Framework numbers are MEASURED (#15: 22 skills / 68 files / 196,849 bytes;
#11: wheel 419,965 bytes / 194 files with three frameworks).
Pool sizes are MEASURED from ~/.agents/skills on this machine.
Bundle composition is ILLUSTRATIVE — no ticket has decided it yet.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rich.console import Console
from rich.theme import Theme

# --------------------------------------------------------------------------- #
# theme
# --------------------------------------------------------------------------- #

THEME = Theme(
    {
        "op.brand": "bold magenta",
        "op.ok": "bold green",
        "op.warn": "bold yellow",
        "op.err": "bold red",
        "op.dim": "dim",
        "op.key": "cyan",
    }
)

out = Console(theme=THEME, highlight=False)
err = Console(theme=THEME, stderr=True, highlight=False)

VERSION = "0.1.0"


# --------------------------------------------------------------------------- #
# catalog
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Item:
    kind: str  # ai-framework | skill | bundle
    name: str
    desc_pt: str
    desc_en: str
    origin: str
    files: int
    size: int
    contents: tuple[str, ...] = field(default=())


FRAMEWORKS = [
    Item(
        kind="ai-framework",
        name="matt-pocock",
        desc_pt="As 22 skills promovidas: engenharia e produtividade.",
        desc_en="The 22 promoted skills: engineering and productivity.",
        origin="mattpocock/skills",
        files=68,
        size=196_849,
    ),
]

SKILLS = [
    Item(
        kind="skill",
        name="panlabs-python-standards",
        desc_pt="Regua de forma para backend Python: contratos, erro, testes.",
        desc_en="Shape ruler for Python backends: contracts, errors, tests.",
        origin="panlabs-tech",
        files=8,
        size=234_458,
    ),
    Item(
        kind="skill",
        name="prompt-engineering-patterns",
        desc_pt="Padroes de prompt para producao: confiabilidade e controle.",
        desc_en="Production prompt patterns: reliability and control.",
        origin="curadoria propria",
        files=10,
        size=81_149,
    ),
    Item(
        kind="skill",
        name="grilling",
        desc_pt="Sabatina uma decisao ate ela ficar afiada.",
        desc_en="Grills a decision until it gets sharp.",
        origin="mattpocock/skills",
        files=2,
        size=948,
    ),
    Item(
        kind="skill",
        name="tdd",
        desc_pt="Red-green-refactor com teste de integracao.",
        desc_en="Red-green-refactor with integration tests.",
        origin="mattpocock/skills",
        files=4,
        size=6_995,
    ),
    Item(
        kind="skill",
        name="research",
        desc_pt="Investiga contra fonte primaria e grava o achado no repo.",
        desc_en="Investigates against primary sources, writes findings down.",
        origin="mattpocock/skills",
        files=2,
        size=893,
    ),
    Item(
        kind="skill",
        name="writing-great-skills",
        desc_pt="Vocabulario e principios para escrever skill previsivel.",
        desc_en="Vocabulary and principles for writing predictable skills.",
        origin="mattpocock/skills",
        files=3,
        size=28_020,
    ),
]

BUNDLES = [
    Item(
        kind="bundle",
        name="api-python",
        desc_pt="Equipamento para trabalhar numa API Python.",
        desc_en="Equipment for working on a Python API.",
        origin="curadoria propria",
        files=14,
        size=242_346,
        contents=("panlabs-python-standards", "tdd", "research"),
    ),
    Item(
        kind="bundle",
        name="terraform-development",
        desc_pt="Equipamento para trabalhar em infraestrutura.",
        desc_en="Equipment for working on infrastructure.",
        origin="curadoria propria",
        files=12,
        size=82_042,
        contents=("prompt-engineering-patterns", "research", "writing-great-skills"),
    ),
]

ALL = FRAMEWORKS + SKILLS + BUNDLES

# The 22 promoted skills of matt-pocock, for `list --ai-framework matt-pocock`.
MATT_POCOCK_SKILLS = [
    "ask-matt",
    "caveman",
    "code-review",
    "domain-modeling",
    "frontend-design",
    "grill-me",
    "grill-with-docs",
    "grilling",
    "handoff",
    "implement",
    "prototype",
    "research",
    "setup-matt-pocock-skills",
    "tdd",
    "teach",
    "to-spec",
    "to-tickets",
    "triage",
    "wayfinder",
    "writing-great-skills",
    "verifying-skills",
    "skill-testing",
]

# What a real install of `matt-pocock` writes, for the progress/summary screens.
WRITTEN = [
    ".agents/skills/ask-matt/SKILL.md",
    ".agents/skills/code-review/SKILL.md",
    ".agents/skills/domain-modeling/SKILL.md",
    ".agents/skills/grilling/SKILL.md",
    ".agents/skills/prototype/SKILL.md",
    ".agents/skills/tdd/SKILL.md",
    ".agents/skills/triage/SKILL.md",
    ".agents/skills/wayfinder/SKILL.md",
]


def human(n: int) -> str:
    """Bytes as KiB, the way the research reported them."""
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KiB"
    return f"{n / 1024 / 1024:.2f} MiB"


# --------------------------------------------------------------------------- #
# copy — the open decision this ticket owns: product voice, pt-BR or English
# --------------------------------------------------------------------------- #

COPY = {
    "pt": {
        "tagline": "instala equipamento de agente curado",
        "catalog": "catalogo",
        "frameworks": "AI Frameworks",
        "frameworks_note": "instala inteiro",
        "skills": "Skills do pool",
        "skills_note": "instala sozinha",
        "bundles": "Bundles",
        "bundles_note": "so lista artefatos do pool",
        "col_name": "nome",
        "col_desc": "descricao",
        "col_origin": "origem",
        "col_size": "tamanho",
        "col_files": "arq",
        "inside": "dentro de",
        "skills_word": "skills",
        "hint_list": "para ver o conteudo:",
        "hint_install": "para instalar:",
        "q_what": "O que instalar?",
        "q_where": "Onde?",
        "q_confirm": "Escrever?",
        "opt_project": "projeto  ./.agents/  (este repo)",
        "opt_global": "maquina  ~/.agents/  (todo repo seu)",
        "plan": "plano",
        "will_write": "vai escrever",
        "files": "arquivos",
        "in_": "em",
        "installing": "instalando",
        "wrote": "escritos",
        "linked": "symlink",
        "done": "pronto",
        "next": "proximo",
        "next_cmd": "git status",
        "next_hint": "confira o que entrou antes de commitar.",
        "err_collision_t": "colisao",
        "err_collision_b": (
            "[bold]grilling[/] chega por dois caminhos nesta linha:\n"
            "  pelo AI Framework [op.key]matt-pocock[/]  ->  .agents/skills/grilling/\n"
            "  pela skill do pool [op.key]grilling[/]    ->  .agents/skills/grilling/\n\n"
            "Nada foi escrito. Escolha um dos dois, ou repita com [bold]--force[/]\n"
            "para deixar a skill do pool vencer (o mais especifico ganha)."
        ),
        "err_collision_1": "[bold]grilling[/] chega por dois caminhos nesta linha.",
        "err_collision_2": "nada foi escrito. escolha um, ou use --force (o mais especifico vence).",
        "err_symlink_t": "symlink indisponivel",
        "err_symlink_b": (
            "Nao consegui criar [bold]~/.claude/skills[/] como link.\n"
            "[op.dim]OSError: [WinError 1314] required privilege is not held[/]\n\n"
            "Cai para [bold]copia real[/]. Nada foi perdido, e o conteudo esta la."
        ),
        "err_symlink_1": "nao consegui criar ~/.claude/skills como link.",
        "err_symlink_2": "cai para copia real. nada foi perdido.",
        "exit": "saida",
        "aborted": "cancelado",
    },
    "en": {
        "tagline": "installs curated agent equipment",
        "catalog": "catalog",
        "frameworks": "AI Frameworks",
        "frameworks_note": "installs whole",
        "skills": "Pool skills",
        "skills_note": "installs alone",
        "bundles": "Bundles",
        "bundles_note": "lists pool artifacts only",
        "col_name": "name",
        "col_desc": "description",
        "col_origin": "origin",
        "col_size": "size",
        "col_files": "files",
        "inside": "inside",
        "skills_word": "skills",
        "hint_list": "to see what is inside:",
        "hint_install": "to install:",
        "q_what": "What to install?",
        "q_where": "Where?",
        "q_confirm": "Write?",
        "opt_project": "project  ./.agents/  (this repo)",
        "opt_global": "machine  ~/.agents/  (all your repos)",
        "plan": "plan",
        "will_write": "will write",
        "files": "files",
        "in_": "in",
        "installing": "installing",
        "wrote": "written",
        "linked": "symlink",
        "done": "done",
        "next": "next",
        "next_cmd": "git status",
        "next_hint": "check what landed before you commit.",
        "err_collision_t": "collision",
        "err_collision_b": (
            "[bold]grilling[/] arrives by two paths on this line:\n"
            "  from AI Framework [op.key]matt-pocock[/]  ->  .agents/skills/grilling/\n"
            "  from pool skill [op.key]grilling[/]       ->  .agents/skills/grilling/\n\n"
            "Nothing was written. Pick one, or run again with [bold]--force[/]\n"
            "to let the pool skill win (most specific wins)."
        ),
        "err_collision_1": "[bold]grilling[/] arrives by two paths on this line.",
        "err_collision_2": "nothing written. pick one, or use --force (most specific wins).",
        "err_symlink_t": "symlink unavailable",
        "err_symlink_b": (
            "Could not create [bold]~/.claude/skills[/] as a link.\n"
            "[op.dim]OSError: [WinError 1314] required privilege is not held[/]\n\n"
            "Fell back to a [bold]real copy[/]. Nothing was lost, the content is there."
        ),
        "err_symlink_1": "could not create ~/.claude/skills as a link.",
        "err_symlink_2": "fell back to a real copy. nothing was lost.",
        "exit": "exit",
        "aborted": "aborted",
    },
}
