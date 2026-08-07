"""Render one screen the way the doctrine asserts it: as a screen, not as bytes.

Measured in https://github.com/panlabs-tech/overpower/issues/30: in the captures
of the prototype the *only* ANSI sequences present are two lines of cursor
control from the transient `Progress` — `ESC[?25l`, `ESC[2K`, `ESC[1A`,
`ESC[?25h` — and none of colour. Two consequences, and both are why this module
exists instead of a raw-stdout capture:

- a snapshot of the byte stream records the **animation**, not the screen:
  `ESC[1A` plus `ESC[2K` mean the final result has one line where the capture
  has two;
- layout is entirely present without colour, which is what reproduces the
  property measured in https://github.com/panlabs-tech/overpower/issues/12 —
  changing the brand colour broke zero of nine tests, because the snapshot froze
  layout and not colour.

So: `Console(record=True).export_text()`, colour asserted structurally and never
recorded. Width is an input because the variant that shipped has a frame,
indentation and re-wrapping — 80 and 60 are the two the doctrine names.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    from rich.console import RenderableType

WIDTHS = (80, 60)
"""The two terminal widths every screen snapshot is taken at."""


def console(width: int) -> Console:
    """A console that renders as a terminal would, into memory.

    `force_terminal` is what makes the renderable take the terminal branch —
    without it rich detects the pytest capture as a pipe and the screen under
    test would not be the screen a user sees.
    """
    return Console(
        record=True,
        width=width,
        force_terminal=True,
        no_color=True,
        highlight=False,
        soft_wrap=False,
    )


def render(renderable: RenderableType, width: int) -> str:
    """The screen as text: what a user reads, with the colour taken out."""
    target = console(width)
    target.print(renderable)
    return target.export_text(clear=False, styles=False)
