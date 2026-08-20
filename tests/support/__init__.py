"""Machinery with no subject of its own.

Nothing here is tested directly. These modules exist so that the tests that *do*
have a subject can be written the way the doctrine requires: a real disk, a real
`git`, a real content tree with the CLI aimed at it, a rendered screen, and a
network gate that fails loudly instead of skipping silently. See
https://github.com/ThiagoPanini/overpower/issues/30.

This is one of the **three houses outside the mirror of `src/`**, and the line
that decides what lands here rather than in a `fakes.py` is whether it talks to
real infrastructure: everything here does, which is why there is no fake among
them.

There is no `fakes.py` and no `contracts/` here, and the absence is declared
rather than forgotten: a contract test is owed for a *fake of a port with a real
adapter executable under the gate*, and this repository has none.
"""
