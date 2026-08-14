"""Surgical insertion into a document that is not ours: text in, text out.

**The additive diff is a requirement, not a taste** (ADR 0016). Axiom 2 —
*"in a repository the git is the manifest"* — only holds if `git diff` answers
**exactly** what the tool wrote, and measured, re-serialising even the friendliest
possible case reflows a server nobody touched:

```diff
     "antigo": {
       "command": "node",
-      "args": ["server.js"]
+      "args": [
+        "server.js"
+      ]
```

So the document is parsed into a model that keeps every byte of whitespace and
every comment, one key is added or replaced, and the model is dumped back. A
round trip with no mutation is byte-identical, and that is the property
everything here rests on.

**The two measured traps of the library are why this docstring is long**, and
both are live in `json-five` 1.1.2:

1. the obvious insertion API — `obj.key_value_pairs.append(kvp)` — **fails in
   silence**: exit 0, no exception, output byte-identical to the input, graft
   gone. `key_value_pairs` is a `@property` that rebuilds the list out of
   `zip(self.keys, self.values)` on every access, so `.append()` mutates a
   throwaway. `_appended` below uses `keys` and `values`, which are the real
   lists;
2. the correct API inserts **with no formatting at all** — everything on one
   line — because whitespace is not implied by the model: it is carried on the
   nodes, in `wsc_before`, `wsc_after` and `leading_wsc`. Authoring those is what
   the rest of this module does.

The first trap is exactly the class of defect this product exists not to commit,
and it lives *inside* the dependency bought to avoid it. What catches it is not a
unit test over this function: it is asserting the **content of the file** after
the write, which is where `tests/test_writing.py` puts it — and it has to be,
because `pyright --strict` has a measured blind spot on `Any` and this is the one
module that reads third-party JSON. Every value the parser hands back is narrowed
here in the open, the way `overpower.written` narrows TOML.

**Whitespace is reused before it is invented.** The indent of a new entry is read
off the entry already there, the whitespace before the closing brace is *moved*
onto the new last value rather than rebuilt, and the line ending is whatever the
file already uses. Three consequences, each asserted in the suite: a file
indented with tabs stays tabs, a CRLF file stays CRLF, and a comment sitting at
the end of the object survives instead of being swallowed by the comma the
insertion has to add.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, assert_never, cast

from json5.dumper import BaseDumper, ModelDumper, dumps
from json5.loader import ModelLoader, loads
from json5.model import (
    BooleanLiteral,
    Comment,
    DoubleQuotedString,
    Identifier,
    JSONArray,
    JSONObject,
    JSONText,
    String,
    Value,
)

from overpower.errors import RefusedError
from overpower.rendering import Fragment, Inputs

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from overpower.rendering import Graft, JsonValue

EMPTY_DOCUMENT = "{}\n"
"""What a document that does not exist yet is grafted into.

Creating a file is not repairing one: the refusal below is about a document that
**is** there and does not parse, which is a file whose shape somebody chose.
"""

_INDENT = re.compile(r"^([ \t]+)\S", re.MULTILINE)
"""The first indented line of the document — one indent unit, whatever it is."""

_DEFAULT_UNIT = "  "
"""What a document with no indented line to learn from gets."""


@dataclass(frozen=True)
class _Layout:
    """How the document is laid out where a node is about to be written.

    The four travel together because none of them means anything alone: an
    indent unit without a depth writes nothing, and a depth without the file's
    own line ending writes the wrong bytes on Windows.
    """

    unit: str
    """One level of indentation, as this document spells it."""

    newline: str
    """The line ending this document already uses."""

    entry: str
    """The indentation of the line the node starts on."""

    closing: str
    """The indentation of the brace that closes the object it is going into."""

    @property
    def inner(self) -> _Layout:
        """The layout one level deeper: fields indent one unit past their object."""
        return _Layout(self.unit, self.newline, self.entry + self.unit, self.entry)


class MalformedDocumentError(RefusedError):
    """The configuration file is already broken, and the overpower does not repair it.

    Exit **3**: the invocation was well formed, the product ran, and the answer
    is no. It is also what the official CLIs do — measured, `claude mcp add` and
    `codex mcp add` both refuse and leave the file alone — and the reason is
    stronger here than there: repairing means editing, on our own initiative, a
    file that is not ours.

    The refusal lands **before the first byte** rather than mid-write, because
    `--dry-run` has to mirror the exit code of the real run — which is what
    `overpower.planning.refuse_broken_documents` is for.
    """

    def __init__(self, path: Path, why: str) -> None:
        """Name the file and what is wrong with it, so the fix is one edit."""
        self.path = path
        self.why = why
        super().__init__(f"{path} is not ours to repair, and it is broken: {why}")


def read_document(path: Path) -> str:
    r"""The document exactly as it is on disk, with **no newline translation**.

    `newline=""` is load-bearing, not tidiness: the default translates `\r\n`
    to `\n` on the way in, so a CRLF file written back would arrive with every
    line ending changed — the largest possible non-additive diff, produced by
    the one function whose whole purpose is not to produce one. It is spelled
    with `open` rather than `read_text(newline=...)` because that keyword only
    exists from Python 3.13 and the floor here is 3.12.
    """
    with path.open(encoding="utf-8", newline="") as handle:
        return handle.read()


def write_document(path: Path, text: str) -> None:
    r"""Put `text` on disk byte for byte, creating the folder that holds it.

    The `newline=""` twin of `read_document`, and the same reason: with the
    default, every `\n` becomes `\r\n` on Windows and the file the graft
    preserved so carefully arrives rewritten.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        _ = handle.write(text)


def refuse_if_broken(path: Path, text: str, graft: Graft) -> None:
    """Refuse `text` unless `grafted` could put `graft` in it.

    Separate from `grafted` because of *when*: the caller runs it over every
    document the plan touches **before the first write**, so a `--dry-run`
    reports the same refusal the real run would give.

    It takes the graft rather than only the path because *broken* is a question
    about the place the graft is going, not just about the file: a document whose
    `mcpServers` is a string parses perfectly and still has nowhere to receive a
    server, and one whose `inputs` is an object has nowhere to receive a prompt.
    Checking only the top level was measured answering **0** to a dry run whose
    real run answers 3.
    """
    model = _document(path, text)
    root = _object_at(path, model.value, "its top level")
    index = _index_of(root, graft.root_key)
    if index is None:
        return
    named = f"`{graft.root_key}`"
    match graft:
        case Fragment():
            _ = _object_at(path, root.values[index], named)
        case Inputs():
            _ = _array_at(path, root.values[index], named)
        case _ as unreachable:
            assert_never(unreachable)


def grafted(path: Path, text: str, graft: Graft) -> str:
    """`text` with `graft` in it, and every other byte of it untouched.

    Overwriting is unconditional and asks nothing (ADR 0013): an entry already
    carrying the same identity is replaced, keeping the whitespace that
    surrounded it, so nothing else in the document moves.

    The two shapes are two mechanics and one property. A `Fragment` is a key in a
    table, and the identity is the key. `Inputs` are elements of a list, which
    have no key — their identity is a **field inside them**, named by the plan —
    so *"the same entry"* is a lookup and not a subscript. Both are idempotent
    for the same reason and it is not cosmetic: measured, VS Code's trust of this
    file is `TrustedOnNonce` over the hash of the launch, so a graft that
    appended a duplicate on every run would make the user re-approve every server
    every time.
    """
    model = _document(path, text)
    root = _object_at(path, model.value, "its top level")
    unit = _unit(text)
    newline = "\r\n" if "\r\n" in text else "\n"
    match graft:
        case Fragment(root_key, name, value):
            holder, inside = _holder(path, root, root_key, unit, newline)
            _set(holder, name, _node(value, inside), inside)
        case Inputs(root_key, entries, identity):
            listing, inside = _listing(path, root, root_key, unit, newline)
            for entry in entries:
                _set_element(listing, identity, entry, inside)
        case _ as unreachable:
            assert_never(unreachable)
    return dumps(model, dumper=_model_dumper())


def _model_dumper() -> BaseDumper:
    """The round-tripping dumper, typed the way `dumps` asks for it.

    Upstream, `ModelDumper` does **not** inherit `BaseDumper` even though `dumps`
    declares that parameter as one — the two agree on the surface `dumps` uses
    (`dump` and `env`) and on nothing else. The cast records the library's own
    inconsistency in one place instead of at the call site.
    """
    return cast("BaseDumper", ModelDumper())


def _document(path: Path, text: str) -> JSONText:
    """The parsed document, with the parser's own failures renamed as ours."""
    try:
        parsed: object = loads(text, loader=ModelLoader())
    # The parser raises a hierarchy of its own, and every member of it means the
    # same thing to a caller: this file is not one we can graft into.
    except Exception as broken:
        raise MalformedDocumentError(path, str(broken)) from broken
    if not isinstance(parsed, JSONText):  # pragma: no cover — the model loader returns one
        message = f"the parser answered {type(parsed).__name__}"
        raise MalformedDocumentError(path, message)
    _object_at(path, parsed.value, "its top level")
    return parsed


def _object_at(path: Path, node: object, named: str) -> JSONObject:
    """`node` as an object, or the refusal that says what it is instead."""
    if not isinstance(node, JSONObject):
        message = f"{named} is {type(node).__name__} and not an object"
        raise MalformedDocumentError(path, message)
    return node


def _array_at(path: Path, node: object, named: str) -> JSONArray:
    """`node` as a list, or the refusal that says what it is instead.

    The twin of `_object_at`, and it exists because the second root key of a
    document is a **list**: `inputs` holding an object parses and has nowhere to
    receive a prompt, exactly the way a `mcpServers` holding a string does.
    """
    if not isinstance(node, JSONArray):
        message = f"{named} is {type(node).__name__} and not a list"
        raise MalformedDocumentError(path, message)
    return node


def _holder(
    path: Path, root: JSONObject, root_key: str, unit: str, newline: str
) -> tuple[JSONObject, _Layout]:
    """The object the servers live in, and how its entries are laid out.

    Creating the root key when it is absent is not repairing the document: the
    key is ours to write, and a graft that refused a file for not already
    carrying `mcpServers` would refuse every first install.
    """
    # The root object's own entries sit at `outer`; anything inside one of them
    # is one level deeper, which is what `.inner` means.
    at_root = _Layout(unit, newline, _indent_of(root.leading_wsc) or unit, "")
    index = _index_of(root, root_key)
    if index is None:
        holder = JSONObject()
        _appended(root, root_key, holder, at_root)
        return holder, at_root.inner
    holder = _object_at(path, root.values[index], f"`{root_key}`")
    entry = _indent_of(holder.leading_wsc)
    # The holder was already there, so its entries are laid out however **it**
    # lays them out — computed only when it has none to read from.
    return holder, at_root.inner if entry is None else replace(at_root.inner, entry=entry)


def _set(holder: JSONObject, name: str, value: Value, layout: _Layout) -> None:
    """Replace `name` if it is there, append it if it is not."""
    index = _index_of(holder, name)
    if index is None:
        _appended(holder, name, value, layout)
        return
    previous = holder.values[index]
    value.wsc_before = previous.wsc_before
    value.wsc_after = previous.wsc_after
    holder.values[index] = value


def _listing(
    path: Path, root: JSONObject, root_key: str, unit: str, newline: str
) -> tuple[JSONArray, _Layout]:
    """The list the prompts live in, and how its elements are laid out.

    The `_holder` of the second shape, down to why it creates the key when it is
    absent: `inputs` is ours to write, and refusing a `.vscode/mcp.json` for not
    already carrying one would refuse every first install.
    """
    at_root = _Layout(unit, newline, _indent_of(root.leading_wsc) or unit, "")
    index = _index_of(root, root_key)
    if index is None:
        listing = JSONArray()
        _appended(root, root_key, listing, at_root)
        return listing, at_root.inner
    listing = _array_at(path, root.values[index], f"`{root_key}`")
    entry = _indent_of(listing.leading_wsc)
    # The list was already there, so its elements sit however **it** sits them —
    # computed only when it has none to read from.
    return listing, at_root.inner if entry is None else replace(at_root.inner, entry=entry)


def _set_element(
    listing: JSONArray, identity: str, entry: Mapping[str, JsonValue], layout: _Layout
) -> None:
    """Replace the element carrying this identity, or append it if none does.

    *"The same entry"* is a field and not a position: two recipes needing
    `GITHUB_TOKEN` derive the same id, so the second install has to land on the
    first one's prompt rather than beside it. Appending a twin would ask the
    person for the same secret twice and, measured, invalidate the nonce that VS
    Code trusts the whole file by.
    """
    wanted = entry.get(identity)
    index = None if not isinstance(wanted, str) else _element_index_of(listing, identity, wanted)
    value = _node(entry, layout)
    if index is None:
        _appended_element(listing, value, layout)
        return
    previous = listing.values[index]
    value.wsc_before = previous.wsc_before
    value.wsc_after = previous.wsc_after
    listing.values[index] = value


def _element_index_of(listing: JSONArray, identity: str, wanted: str) -> int | None:
    """Where the element whose `identity` field is `wanted` sits, or `None`.

    Elements that are not objects, and objects without the field, are skipped
    rather than refused: the list is the user's too, and something else living in
    it is not a document we may not graft into — it is one we leave alone.

    Read through `String` rather than `DoubleQuotedString` because this is a
    **value** and JSON5 admits both quotes for one; a hand-written `'git-token'`
    is the same id as `"git-token"`, and treating it as a different one would
    append the duplicate this function exists to prevent.
    """
    for index, element in enumerate(listing.values):
        if not isinstance(element, JSONObject):
            continue
        at = _index_of(element, identity)
        if at is None:
            continue
        found = element.values[at]
        if isinstance(found, String) and found.characters == wanted:
            return index
    return None


def _appended_element(listing: JSONArray, value: Value, layout: _Layout) -> None:
    """Add `value` as the last element, moving the closing whitespace onto it.

    `_appended` without the key, and the difference is where the newline goes: in
    an object the **key** carries the indentation of the line, and in a list
    there is no key, so the value carries it itself. Everything else is the same
    move for the same reason — the comma lands before the trailing whitespace, so
    a comment sitting at the end of the list survives the insertion.
    """
    if listing.values:
        tail = listing.values[-1].wsc_after
        listing.values[-1].wsc_after = []
        value.wsc_before = _wsc(layout.newline + layout.entry)
    else:
        tail = listing.leading_wsc
        listing.leading_wsc = _wsc(layout.newline + layout.entry)
    if not any(isinstance(part, str) and "\n" in part for part in tail):
        tail = [*tail, layout.newline + layout.closing]
    value.wsc_after = tail
    listing.values.append(value)


def _appended(obj: JSONObject, name: str, value: Value, layout: _Layout) -> None:
    """Add `name` as the last pair, moving the closing whitespace onto it.

    Moving rather than rebuilding is what saves a comment at the end of the
    object: the comma this insertion has to add goes **before** that whitespace,
    so a `// note` never ends up with a comma glued to it — which would put the
    comma inside the comment and drop it from the document.
    """
    key = _key(name)
    if obj.keys:
        tail = obj.values[-1].wsc_after
        obj.values[-1].wsc_after = []
        key.wsc_before = _wsc(layout.newline + layout.entry)
    else:
        tail = obj.leading_wsc
        obj.leading_wsc = _wsc(layout.newline + layout.entry)
    if not any(isinstance(part, str) and "\n" in part for part in tail):
        tail = [*tail, layout.newline + layout.closing]
    value.wsc_before = _wsc(" ")
    value.wsc_after = tail
    obj.keys.append(key)
    obj.values.append(value)


def _node(value: JsonValue, layout: _Layout) -> Value:
    """`value` as model nodes, with the whitespace that makes it readable.

    **Objects expand and arrays stay inline**, which is one rule per shape and
    both of them the shape those two carry in the measured files: a server reads
    as a block of fields, an argument list reads as a line. The one list that is
    *not* inline — `inputs`, whose elements are objects — never reaches here as a
    list: its elements arrive one at a time, laid out by `_appended_element`,
    because appending to it has to be idempotent and a whole list cannot be.

    `bool` is checked before everything, and not for tidiness: `True` would fall
    through a `Sequence` test on some shapes and a boolean is the one scalar the
    document needs written unquoted — `"password": "true"` is a **string**, and
    measured it is not what turns the keychain on.
    """
    if isinstance(value, bool):
        return BooleanLiteral(value=value)
    if isinstance(value, str):
        return _string(value)
    if isinstance(value, Mapping):
        return _object(value, layout)
    array = JSONArray(*(_node(item, layout) for item in value))
    for item in array.values[1:]:
        item.wsc_before = _wsc(" ")
    return array


def _object(value: Mapping[str, JsonValue], layout: _Layout) -> JSONObject:
    """A table, one field per line, indented one unit past the entry that holds it."""
    obj = JSONObject()
    inner = layout.inner
    for index, (name, child) in enumerate(value.items()):
        key = _key(name)
        if index:
            key.wsc_before = _wsc(layout.newline + inner.entry)
        node = _node(child, inner)
        node.wsc_before = _wsc(" ")
        obj.keys.append(key)
        obj.values.append(node)
    if obj.keys:
        obj.leading_wsc = _wsc(layout.newline + inner.entry)
        obj.values[-1].wsc_after = _wsc(layout.newline + layout.entry)
    return obj


def _index_of(obj: JSONObject, name: str) -> int | None:
    """Where `name` sits among the object's keys, or `None` when it is not there.

    A key is a quoted string in every measured file and may be a bare identifier
    in JSON5, so both spellings answer: a document written by hand as
    `{mcpServers: {}}` is still a document that has that key.
    """
    for index, key in enumerate(obj.keys):
        if isinstance(key, DoubleQuotedString) and key.characters == name:
            return index
        if isinstance(key, Identifier) and key.name == name:
            return index
    return None


def _indent_of(wsc: Sequence[str | Comment]) -> str | None:
    """The indentation an entry of this object already sits at, or `None` if it is inline.

    Read off the whitespace verbatim rather than computed, so a document that
    indents with four spaces or with tabs keeps doing so — and read off the
    **last** run of whitespace, because a comment can sit between the brace and
    the first key.
    """
    for part in reversed(wsc):
        if isinstance(part, str) and "\n" in part:
            return part.rsplit("\n", 1)[1]
    return None


def _unit(text: str) -> str:
    """One level of indentation, learned from the document's first indented line."""
    found = _INDENT.search(text)
    return found.group(1) if found else _DEFAULT_UNIT


def _key(name: str) -> DoubleQuotedString:
    """A key node. Quoted, always: it is what every measured document writes."""
    return _string(name)


def _string(value: str) -> DoubleQuotedString:
    """A JSON string literal node, escaped.

    `json.dumps` over **one string** and never over a document: what ADR 0016
    forbids is re-serialising the user's file, and this is the standard escape of
    a scalar with none of their bytes in it. The library's own dumper reaches for
    the same call, for the same reason.
    """
    return DoubleQuotedString(characters=value, raw_value=json.dumps(value))


def _wsc(text: str) -> list[str | Comment]:
    """Whitespace, in the list type the model's fields declare.

    A plain `[text]` is a `list[str]`, which is not a `list[str | Comment]` under
    an invariant checker — so the annotation lives here once instead of at every
    assignment.
    """
    return [text]
