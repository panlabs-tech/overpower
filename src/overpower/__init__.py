"""overpower — installs curated AI Frameworks into a repository or a machine.

The catalog it installs from ships inside this package, in two sibling roots with
opposite invariants: `content/`, which lands whole in the target, and `catalog/`,
which never lands. `overpower.packaged` is where both are found.

Because the catalog ships here, **the version of this package is the version of
the catalog** (rule 5): there is no second number to read and nothing to refresh
in place. That is what makes `uvx overpower@latest` a correctness requirement
rather than a habit — `uvx` freezes a bare name on first use, with no TTL.
"""
