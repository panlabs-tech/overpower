"""The one exception the product raises on purpose, and the seam the CLI catches.

The error model of v0.1.0 has four codes, and the axis between `2` and `3` is
*whose defect it is* (https://github.com/panlabs-tech/overpower/issues/8):

| code | meaning |
| --- | --- |
| 0 | did what was asked |
| 1 | could not run |
| 2 | you invoked me wrong |
| 3 | ran, and the answer is no |

`OverpowerError` is the *named* half of code `1`: a defect the product can point
at — a content tree that does not obey its own convention, a written file that
does not parse. It exists so the top-level handler can render a message the user
can act on instead of a library stack, which is the whole reason that handler is
mandatory: an unhandled exception exits 1 dumping a rich traceback into the
terminal, and shipping that leaks library internals to whoever ran the command.

An exception that is *not* one of these is a bug, and the handler says so — it
still refuses to print a traceback, because a traceback is a diagnostic for us
and noise for the person who typed the command.
"""

from __future__ import annotations


class OverpowerError(Exception):
    """A failure the product named, with a message written for the user.

    Subclasses build their message in `__init__` and keep the values that made
    it as attributes, so a caller can assert on the value rather than on the
    prose.
    """
