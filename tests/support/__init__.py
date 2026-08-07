"""Machinery with no subject of its own.

Nothing here is tested directly. These four modules exist so that the tests that
*do* have a subject can be written the way the doctrine requires: a real disk, a
real `git`, a rendered screen, and a network gate that fails loudly instead of
skipping silently. See https://github.com/panlabs-tech/overpower/issues/30.

There is no `fakes.py` and no `contracts/` here, and the absence is declared
rather than forgotten: a contract test is owed for a *fake of a port with a real
adapter executable under the gate*, and this repository has none.
"""
