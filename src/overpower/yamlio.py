"""The sanctioned way to reach the YAML reader, typed as `object`.

Sibling of `overpower.jsonio`, and the same tripwire for the same reason plus
one of its own. `yaml.load` and `yaml.safe_load` are banned repo-wide (`TID251`,
`pyproject.toml`) because they answer `Any`, and an `Any` crossing into a module
checked with `pyright --strict` takes the checking with it — measured in
https://github.com/ThiagoPanini/overpower/issues/2, `return data["name"]` inside
a `-> str` function passes the type checker and fails at runtime.

The reason of its own is that `yaml.load` **without** a `Loader` constructs
arbitrary Python objects out of the document. The product reads YAML it did not
write — the frontmatter of somebody else's `SKILL.md`, and next the federated
manifest of a homemade repository — so the door is nailed shut here rather than
watched in review: the loader is named, and it is the safe one.

The exemption for this file was written before the file was, so the tripwire
cannot be defused by deleting the module it points at.

The wrapper narrows nothing and repairs nothing. It answers `object`, which is
the truthful type of *whatever was in that text*, and forces the caller to say
what it expects before it may read anything off the result.
"""

from __future__ import annotations

import yaml

__all__ = ["loads_yaml"]


def loads_yaml(text: str) -> object:
    """`text` as whatever YAML says it is, or `ValueError` when it says nothing.

    `ValueError` is the same answer `overpower.jsonio` gives, and translating to
    it is what keeps the confinement total: a caller that had to catch
    `yaml.YAMLError` would need to import `yaml`, and the decode surface would
    be back out in the open. The parser's own message is carried through whole,
    because it names the line and column the author has to go fix.

    An empty document answers `None`, which is YAML saying *"nothing"* rather
    than failing. Whoever asked decides whether nothing is an answer.
    """
    try:
        return yaml.load(text, Loader=yaml.SafeLoader)
    except yaml.YAMLError as error:
        raise ValueError(str(error)) from error
