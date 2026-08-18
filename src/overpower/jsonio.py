"""The sanctioned way to reach the standard library's JSON reader, typed as `object`.

`json.loads` is banned repo-wide (`TID251`, `pyproject.toml`) because it answers
`Any`, and an `Any` crossing into a module checked with `pyright --strict` takes
the checking with it — every attribute of it is allowed, so a typo becomes a
runtime failure the gate promised to catch. The exemption for this file was
written before the file was, so the tripwire could not be defused by deleting
the module it points at.

The wrapper narrows nothing and repairs nothing. It answers `object`, which is
the truthful type of *whatever was in that text*, and forces the caller to say
what it expects before it may read anything off the result.
"""

from __future__ import annotations

import json

__all__ = ["loads_json"]


def loads_json(text: str) -> object:
    """`text` as whatever JSON says it is, or `ValueError` when it says nothing.

    Strict JSON, deliberately: this is the reader the **runtimes** use, not the
    tolerant one the graft edits documents through. A caller asking this
    question is asking whether some other program could read the file, and the
    answer has to be that program's and not ours.
    """
    return json.loads(text)
