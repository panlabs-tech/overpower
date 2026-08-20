"""The one exception the product raises on purpose, and the seam the CLI catches.

The error model of v0.1.0 has four codes, and the axis between `2` and `3` is
*whose defect it is* (https://github.com/ThiagoPanini/overpower/issues/8):

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


class BadInvocationError(OverpowerError):
    """The named half of code `2`: the defect is in what was typed.

    It is a subclass rather than a sibling because the *rendering* of the two is
    identical — a panel carrying a message someone can act on — and only the
    number differs. That keeps every handler that already catches
    `OverpowerError` correct, and puts the whole of the 1-versus-2 axis in one
    `except` order at the top of the CLI.

    What belongs here is what the caller can fix by typing something else: a
    name outside a closed list, two selectors where the command answers about
    one, a required selector that was not given at all. What does *not* belong
    here is *"ran, and the answer is no"* — that is code `3`, and the defect
    there is on our side of the question, not on theirs.
    """


class RefusedError(OverpowerError):
    """The named half of code `3`: the invocation was correct, and the answer is no.

    A subclass for the same reason `BadInvocationError` is: the rendering is
    identical, and only the number differs. ADR 0009 is where the axis against
    `2` was drawn — *"whose defect is it"* — and settled that a value that
    exists, named by a flag that exists, refused only because the table has no
    destination for the pair, is not a typo. `--runtime eve --global` and a
    global destination that already exists without `--force` both belong here:
    the line was well-formed, the product ran, computed the answer, and the
    answer is no.
    """
