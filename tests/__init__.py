"""Mirror of `src/overpower/`, one test module per source module.

A package and not a loose directory: `--import-mode=importlib` imports test
modules by path, so the `__init__.py` is what keeps the names addressable and
what makes `tests.support` importable from every module without a `sys.path`
trick. Layout decided in https://github.com/ThiagoPanini/overpower/issues/30.
"""
