"""Render one screen the way the doctrine asserts it: as a screen, not as bytes.

Measured in https://github.com/ThiagoPanini/overpower/issues/30: in the captures
of the prototype the *only* ANSI sequences present are two lines of cursor
control from the transient `Progress` — `ESC[?25l`, `ESC[2K`, `ESC[1A`,
`ESC[?25h` — and none of colour. Two consequences, and both are why this module
exists instead of a raw-stdout capture:

- a snapshot of the byte stream records the **animation**, not the screen:
  `ESC[1A` plus `ESC[2K` mean the final result has one line where the capture
  has two;
- layout is entirely present without colour, which is what reproduces the
  property measured in https://github.com/ThiagoPanini/overpower/issues/12 —
  changing the brand colour broke zero of nine tests, because the snapshot froze
  layout and not colour.

So: `Console(record=True).export_text()`, colour asserted structurally and never
recorded. Width is an input because the variant that shipped has a frame,
indentation and re-wrapping — 80 and 60 are the two the doctrine names.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

from rich.console import Console

from overpower.screens import THEME

if TYPE_CHECKING:
    from rich.console import RenderableType

WIDTHS = (80, 60)
"""The two terminal widths every screen snapshot is taken at."""


def console(width: int) -> Console:
    """A console that renders as a terminal would, into memory.

    `force_terminal` is what makes the renderable take the terminal branch —
    without it rich detects the pytest capture as a pipe and the screen under
    test would not be the screen a user sees.

    Three inputs are **pinned**, and all three were found by the Windows cells of
    the matrix, because a recording that is not identical on the nine cells is
    not a recording:

    - `file` is an explicit `StringIO`. Rich swaps the box characters for ASCII
      when the file it writes to cannot encode UTF-8
      (`ConsoleOptions.ascii_only`), so a console inheriting whatever
      `sys.stdout` happens to be records a different frame on a different
      platform. A `StringIO` carries no encoding, and rich then assumes UTF-8;
    - `legacy_windows` is off. Measured: with it on, rich substitutes `ROUNDED`
      for `SQUARE` — `┌─┐` where the variant that shipped draws `╭─╮` — and it
      is detected from the *console* the tests happen to run under;
    - `width`, because the frame re-wraps and width is therefore an input.

    None of the three is a product decision: on a real legacy console the
    product *does* draw square corners, and that is rich degrading on purpose.
    What the recording asserts is the layout the code produces, and it can only
    do that if the platform is held still.

    The theme is the product's, because a screen is written in the product's
    style names — a console without it cannot resolve `op.key` at all.
    """
    return Console(
        file=io.StringIO(),
        record=True,
        width=width,
        force_terminal=True,
        legacy_windows=False,
        no_color=True,
        highlight=False,
        soft_wrap=False,
        theme=THEME,
    )


def render(renderable: RenderableType, width: int) -> str:
    """The screen as text: what a user reads, with the colour taken out."""
    target = console(width)
    target.print(renderable)
    return target.export_text(clear=False, styles=False)
